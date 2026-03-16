"""
BL Agent Orchestrator

Runs a ReAct (Reason + Act) loop that uses GPT-4o with tool-calling to:
  1. Explore a Black-Litterman recipe
  2. Stress-test assumptions / views
  3. Find allocations suited to a stated risk profile
  4. Synthesise findings into a narrative

The agent terminates when it calls the ``synthesise`` tool, or when
MAX_STEPS is reached.

Public API
----------
run_agent(thesis_name, goal, max_steps=MAX_STEPS) -> dict
    Execute a full agent run and return the audit record.

list_audits(limit=50) -> list[dict]
    Return summary rows from agent_costs.db.

load_audit(audit_id) -> dict
    Load a previously-saved audit JSON from data/agent_audits/.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from app.orchestrators.bl_agent_tools import TOOLS, dispatch_tool
from app.orchestrators.bl_orchestrator import run_black_litterman
from app.orchestrators.view_orchestrator import load_recipe
from app.services.llm_client import (
    AgentCostTracker,
    chat_with_history,
)
from app.services.price_data.load_data import load_market_data

# ---------------------------------------------------------------------------
# Paths & tunables
# ---------------------------------------------------------------------------

_BACKEND_DIR = Path(__file__).resolve().parents[2]
AGENT_COSTS_DB = _BACKEND_DIR / "data" / "agent_costs.db"
AGENT_AUDITS_DIR = _BACKEND_DIR / "data" / "agent_audits"
AGENT_AUDITS_DIR.mkdir(parents=True, exist_ok=True)

MAX_STEPS = 8
AGENT_MODEL = "gpt-4o"

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

AGENT_SYSTEM_PROMPT = """You are an expert quantitative portfolio analyst assistant.
You are given a Black-Litterman recipe — a set of investor views, model parameters,
and universe constraints — and a stated goal.

Your task is to reason carefully and use the available tools to:
  1. Understand the base recipe (call get_recipe_summary first).
  2. Run the base scenario to establish the benchmark allocation.
  3. Diagnose which views and assumptions drive the allocation:
     a. Use view_importance_test to identify the most impactful views.
     b. Use view_fragility_scan to test sensitivity of important views.
     c. Use factor_shock_scan to explore macro factor sensitivity (if factor_shocks exist).
  4. Stress-test critical assumptions (confidence levels, view magnitudes,
     model parameters) by running targeted scenarios.
  5. If the goal involves a risk profile, explore weight_bounds or
     risk_aversion adjustments to find a suitable allocation.
  6. Use allocation_envelope to assess stability across scenarios.
  7. Compare scenarios to understand sensitivity.
  8. When you have gathered enough evidence, call synthesise() with a
     thorough narrative, risk flags, and (optionally) your recommended weights.

Be systematic. Use tool results to decide the next tool to call — do not
call synthesise too early. Prefer structured diagnostics (view_importance_test,
view_fragility_scan, factor_shock_scan, allocation_envelope) over ad-hoc
parameter sweeps. Aim for at least 3-5 diagnostic steps before synthesising
unless the recipe is trivially simple.

TOOL USAGE RULES:
  * run_stress_sweep sweep_parameter for confidence MUST use one of the exact
    labels returned in the recipe summary's "sweepable_confidence_params" field.
    NEVER invent a view label — only use labels that exist in the recipe.
  * To stress-test "expected return assumptions", use run_bl_scenario with
    override_expected_return: {asset: value} mutations — one scenario per asset
    or a combined scenario. Do NOT use confidence sweeps for this purpose.
  * If a base scenario result includes a "constraint_warning", acknowledge it in
    your reasoning. An equal-weight result means the cap is fully constraining;
    explore override_expected_return scenarios to find meaningful differences.
  * run_stress_sweep returns a grid summary — it does NOT save a named scenario
    whose weights can be used later. If the sweep identifies a parameter value
    that best satisfies the user's goal (highest Sharpe, lowest vol, best
    diversification, etc.), you MUST follow up with a dedicated run_bl_scenario
    call using that parameter override (e.g. mutations:
    {set_model_parameters: {risk_aversion: 3.0}}) to capture the exact weights
    as a named scenario. Then pass those weights as recommended_weights in
    the synthesise call.
  * ALWAYS populate recommended_weights in synthesise with the allocation that
    best satisfies the stated goal. Evaluate 'best' relative to the goal —
    for a Sharpe goal pick highest Sharpe, for a vol goal pick lowest vol,
    for a diversification goal pick lowest concentration, etc.
    If no scenario improved on base by any measure, pass the base weights.
  * view_fragility_scan and factor_shock_scan are limited to 5 points each.
    Choose meaningful test values (e.g., ±20%, ±50% around base magnitude).
  * Use view_importance_test early in your workflow to identify which views
    matter most, then focus fragility testing on those important views.
  * Use allocation_envelope toward the end to summarize stability across
    all scenarios you've run.

CRITICAL — GOAL CONSTRAINTS:
  * If the goal states a per-position cap (e.g. "max 20% per asset", "no single
    asset above X%"), you MUST include weight_bounds: [0.0, X] in the mutations
    of EVERY run_bl_scenario and run_stress_sweep call, without exception.
  * Do NOT run any scenario without applying stated position limits — a result
    that violates the goal constraint is meaningless.
  * Any goal_mutations provided in the user message must be included in every
    mutation dict you pass to run_bl_scenario or run_stress_sweep.

DIAGNOSTIC WORKFLOW (RECOMMENDED):
  1. get_recipe_summary
  2. view_importance_test (identify critical views)
  3. view_fragility_scan (test top 1-2 important views)
  4. factor_shock_scan (if factor exposures exist)
  5. run_bl_scenario / run_stress_sweep (targeted stress tests)
  6. allocation_envelope (summarize stability)
  7. synthesise (with comprehensive narrative and recommended weights)

Output only tool calls. Do not return free-form text outside of the
synthesise narrative field."""


# ---------------------------------------------------------------------------
# Goal-constraint extraction  (LLM-powered, regex fallback)
# ---------------------------------------------------------------------------

import re as _re

_CONSTRAINT_EXTRACTION_PROMPT = """\
You are a constraint parser for a portfolio optimisation system.

Given a natural-language goal, extract any hard portfolio constraints and
return ONLY a valid JSON object (no markdown, no explanation).

Supported output keys (omit keys that are not mentioned):
  "weight_bounds": [min_float, max_float]   -- per-asset weight limits (0–1 scale)
  "risk_aversion": float                    -- override risk-aversion parameter
  "long_only": bool                         -- true = no short positions

Examples
--------
Goal: "No single asset above 20%, moderate risk"
Output: {"weight_bounds": [0.0, 0.2]}

Goal: "Conservative investor, max 15% per position, long only"
Output: {"weight_bounds": [0.0, 0.15], "long_only": true}

Goal: "Maximise Sharpe with no constraints"
Output: {}

Goal: "Keep each name under a quarter of the portfolio"
Output: {"weight_bounds": [0.0, 0.25]}

Now parse the following goal and return ONLY the JSON object:
"""

def _extract_goal_mutations(goal: str) -> dict:
    """
    Use the LLM to extract hard portfolio constraints from the goal string.
    Falls back to a simple regex if the LLM call fails.
    """
    # --- LLM extraction ---
    try:
        content, _ = chat_with_history(
            messages=[
                {"role": "user", "content": _CONSTRAINT_EXTRACTION_PROMPT + goal},
            ],
            service="bl_agent",
            operation="extract_goal_constraints",
            model="gpt-4o-mini",   # cheap — single-shot extraction
            temperature=0.0,
            agent_cost_db_path=AGENT_COSTS_DB,
        )
        if content:
            # Strip markdown code fences if the model added them
            cleaned = content.strip().strip("```json").strip("```").strip()
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
    except Exception:
        pass  # fall through to regex

    # --- Regex fallback ---
    mutations: dict = {}
    cap_pattern = _re.compile(
        r'(?:max(?:imum)?|no\s+single\s+asset\s+above|cap\s+of|<=?)\s*'
        r'(\d+(?:\.\d+)?)\s*%',
        _re.IGNORECASE,
    )
    match = cap_pattern.search(goal)
    if match:
        mutations['weight_bounds'] = [0.0, float(match.group(1)) / 100.0]
    return mutations


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_price_data() -> pd.DataFrame:
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        price_df, *_ = load_market_data()
    return price_df


def _build_base_summary(recipe: dict, price_df: pd.DataFrame) -> dict:
    """Run the unmodified recipe and return a result summary for caching."""
    from app.orchestrators.bl_agent_tools import _summarise_result
    result = run_black_litterman(recipe, price_df)
    return _summarise_result(result, recipe)


def _tool_call_to_message(tc) -> dict:
    """Convert an OpenAI ChatCompletionMessageToolCall to a 'tool' message."""
    return {
        "tool_call_id": tc.id,
        "role": "tool",
        "name": tc.function.name,
        "content": "",  # filled in after dispatch
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_agent(
    thesis_name: str,
    goal: str,
    max_steps: int = MAX_STEPS,
) -> dict:
    """
    Execute a full agentic BL analysis run.

    Parameters
    ----------
    thesis_name:
        The name of a BL recipe stored in ``data/bl_recipes/<name>.json``.
    goal:
        Natural-language description of what the agent should analyse,
        e.g. "Stress-test all views and find allocation for a conservative
        investor with max 15% per position."
    max_steps:
        Hard cap on ReAct iterations (default: 8).

    Returns
    -------
    audit : dict
        Full audit record including base recipe snapshot, step log,
        synthesis output, cost breakdown, and final recommended weights.
        The same dict is written to ``data/agent_audits/<audit_id>.json``.
    """
    audit_id = str(uuid.uuid4())
    run_start = datetime.now()

    # ---- Load recipe & price data ----------------------------------------
    recipe = load_recipe(thesis_name)
    price_df = _load_price_data()

    # ---- Extract hard constraints from the goal --------------------------
    goal_mutations = _extract_goal_mutations(goal)

    # ---- Establish base run -----------------------------------------------
    try:
        from app.orchestrators.bl_agent_tools import _summarise_result, _quiet_bl, _apply_mutations
        with _quiet_bl():
            # Apply goal-level constraints (e.g. weight cap) to the base run
            base_recipe_for_run = _apply_mutations(recipe, goal_mutations) if goal_mutations else recipe
            raw_base = run_black_litterman(base_recipe_for_run, price_df)
        base_summary = _summarise_result(raw_base, base_recipe_for_run, price_df)
    except Exception as exc:
        base_summary = {"error": str(exc)}

    # ---- Run cache (label -> summary) ------------------------------------
    run_cache: Dict[str, dict] = {"base": base_summary}

    # ---- Conversation history --------------------------------------------
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Thesis: '{thesis_name}'\n"
                f"Goal: {goal}\n"
                + (
                    f"\nGoal constraints (MUST be included in every mutation): "
                    f"{json.dumps(goal_mutations)}\n"
                    if goal_mutations else ""
                )
                + f"\nBase BL result summary:\n{json.dumps(base_summary, indent=2)}"
            ),
        },
    ]

    # ---- Audit bookkeeping -----------------------------------------------
    steps_log: List[Dict[str, Any]] = []
    synthesis: Optional[Dict[str, Any]] = None

    # ---- ReAct loop -------------------------------------------------------
    for step_idx in range(max_steps):
        agent_metadata = {
            "audit_id": audit_id,
            "thesis_name": thesis_name,
            "step": step_idx,
            "tool_called": None,  # filled after we know which tool was called
        }

        content, tool_calls = chat_with_history(
            messages=messages,
            service="bl_agent",
            operation="react_step",
            tools=TOOLS,
            model=AGENT_MODEL,
            temperature=0.2,
            agent_cost_db_path=AGENT_COSTS_DB,
            agent_metadata=agent_metadata,
        )

        # Append assistant message to history
        assistant_msg: Dict[str, Any] = {"role": "assistant", "content": content}
        if tool_calls:
            # OpenAI expects the tool_calls list in the assistant message
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in tool_calls
            ]
        messages.append(assistant_msg)

        if not tool_calls:
            # Model produced plain text — treat as implicit synthesis
            steps_log.append(
                {
                    "step": step_idx,
                    "type": "text_termination",
                    "content": content,
                }
            )
            synthesis = {"narrative": content or "", "done": True}
            break

        # Process each tool call
        for tc in tool_calls:
            tool_name: str = tc.function.name
            try:
                tool_args: dict = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                tool_args = {}

            tool_result = dispatch_tool(
                tool_name=tool_name,
                tool_args=tool_args,
                base_recipe=recipe,
                run_cache=run_cache,
                price_df=price_df,
                goal_mutations=goal_mutations,
            )

            result_text = json.dumps(tool_result)

            # Record step in audit log
            steps_log.append(
                {
                    "step": step_idx,
                    "tool": tool_name,
                    "args": tool_args,
                    "result": tool_result,
                }
            )

            # Append tool result to conversation
            messages.append(
                {
                    "tool_call_id": tc.id,
                    "role": "tool",
                    "name": tool_name,
                    "content": result_text,
                }
            )

            # Check for termination
            if tool_name == "synthesise" and tool_result.get("done"):
                synthesis = tool_result
                break

        if synthesis and synthesis.get("done"):
            break

    # ---- Build cost breakdown from agent_costs.db ------------------------
    act = AgentCostTracker(AGENT_COSTS_DB)
    cost_breakdown = act.get_audit_cost(audit_id)
    step_costs = act.get_audit_steps(audit_id)

    # ---- Compute weight delta vs base ------------------------------------
    final_weights: Optional[Dict[str, float]] = None
    if synthesis and synthesis.get("recommended_weights"):
        final_weights = synthesis["recommended_weights"]
    else:
        # Use the last successfully-run scenario's weights
        for lbl in reversed(list(run_cache.keys())):
            if lbl != "base" and "weights" in run_cache[lbl]:
                final_weights = run_cache[lbl]["weights"]
                break

    weight_delta_vs_base: Optional[Dict[str, float]] = None
    if final_weights and "weights" in base_summary:
        from app.orchestrators.bl_agent_tools import _weight_delta
        weight_delta_vs_base = _weight_delta(base_summary["weights"], final_weights)

    # ---- Extract diagnostic results --------------------------------------
    diagnostics: Dict[str, Any] = {}
    
    # Collect view fragility scans
    fragility_scans = [
        s["result"] for s in steps_log
        if s.get("tool") == "view_fragility_scan" and "error" not in s.get("result", {})
    ]
    if fragility_scans:
        diagnostics["view_fragility"] = fragility_scans
    
    # Collect factor shock scans
    factor_scans = [
        s["result"] for s in steps_log
        if s.get("tool") == "factor_shock_scan" and "error" not in s.get("result", {})
    ]
    if factor_scans:
        diagnostics["factor_transmission"] = factor_scans
    
    # Collect view importance tests
    importance_tests = [
        s["result"] for s in steps_log
        if s.get("tool") == "view_importance_test" and "error" not in s.get("result", {})
    ]
    if importance_tests:
        diagnostics["view_importance"] = importance_tests
    
    # Collect allocation envelopes
    envelopes = [
        s["result"] for s in steps_log
        if s.get("tool") == "allocation_envelope" and "error" not in s.get("result", {})
    ]
    if envelopes:
        diagnostics["allocation_envelope"] = envelopes

    # ---- Assemble audit record -------------------------------------------
    audit: Dict[str, Any] = {
        "audit_id": audit_id,
        "thesis_name": thesis_name,
        "goal": goal,
        "run_timestamp": run_start.isoformat(),
        "model": AGENT_MODEL,
        "base_recipe_snapshot": recipe,
        "base_result_summary": base_summary,
        "steps": steps_log,
        "mutations_applied": [
            s["args"].get("mutations")
            for s in steps_log
            if s.get("tool") == "run_bl_scenario"
        ],
        "scenarios_run": {k: v for k, v in run_cache.items() if k != "base"},
        "diagnostics": diagnostics,
        "synthesis": synthesis or {"narrative": "Max steps reached without synthesis."},
        "final_weights": final_weights,
        "weight_delta_vs_base": weight_delta_vs_base,
        "cost_breakdown": cost_breakdown,
        "step_costs": step_costs,
    }

    # ---- Persist to disk -------------------------------------------------
    audit_path = AGENT_AUDITS_DIR / f"{audit_id}.json"
    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump(audit, f, indent=2)

    return audit


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def list_audits(limit: int = 50) -> List[dict]:
    """
    List past agent runs from agent_costs.db.

    Returns summary rows (audit_id, thesis_name, first_timestamp,
    steps, total_tokens, total_cost_usd).
    """
    act = AgentCostTracker(AGENT_COSTS_DB)
    return act.list_audit_summaries(limit=limit)


def load_audit(audit_id: str) -> dict:
    """
    Load a previously-saved full audit JSON.

    Raises
    ------
    FileNotFoundError if audit does not exist on disk.
    """
    audit_path = AGENT_AUDITS_DIR / f"{audit_id}.json"
    if not audit_path.exists():
        raise FileNotFoundError(f"No audit found for id '{audit_id}' at {audit_path}")
    with open(audit_path, "r", encoding="utf-8") as f:
        return json.load(f)

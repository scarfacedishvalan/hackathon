"""
BL Agent Tools

Defines the tools available to the agentic BL orchestrator and
the dispatch logic that executes them.

Core Tools
----------
get_recipe_summary   -- surface the loaded recipe's key facts
run_bl_scenario      -- run BL with a dict of mutations applied
run_stress_sweep     -- run a sweep of one numeric parameter across a grid
compare_scenarios    -- diff two cached scenario results
synthesise           -- produce the final narrative (terminates the loop)

Diagnostic Tools
----------------
view_fragility_scan  -- analyze portfolio sensitivity to view magnitude changes
factor_shock_scan    -- simulate macro factor shocks and observe portfolio response
view_importance_test -- determine importance of each view by removal
allocation_envelope  -- compute min/max weight ranges across scenarios

Mutation keys supported by _apply_mutations()
---------------------------------------------
drop_views           list[str]   view labels to remove
override_confidence  dict        {label: float}  new omega scalars (0-1)
override_expected_return dict    {asset: float}  override posterior return
set_model_parameters dict        {tau|risk_aversion|risk_free_rate: float}
scale_factor_shock   dict        {label: float}  multiply existing factor shock magnitude
weight_bounds        [float, float]  new [min, max] global weight bounds
"""

from __future__ import annotations

import contextlib
import copy
import io
import json
import logging
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def _quiet_bl():
    """Suppress stdout from the verbose BL engine print statements."""
    with contextlib.redirect_stdout(io.StringIO()):
        yield


# ---------------------------------------------------------------------------
# OpenAI tool schemas (JSON Schema format)
# ---------------------------------------------------------------------------

TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_recipe_summary",
            "description": (
                "Return a concise summary of the loaded BL recipe: universe, "
                "views (labels, directions, confidence), model parameters, and "
                "constraints. Use this first to orient yourself before running "
                "scenarios."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_bl_scenario",
            "description": (
                "Run a Black-Litterman optimisation with a set of mutations "
                "applied to the base recipe. Returns optimal weights, posterior "
                "returns, Sharpe ratio, and weight delta vs the base run. "
                "Cache key is auto-assigned; refer to it in compare_scenarios."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "label": {
                        "type": "string",
                        "description": "Short human-readable label for this scenario, e.g. 'low_confidence'.",
                    },
                    "mutations": {
                        "type": "object",
                        "description": (
                            "Dict of mutations to apply. Supported keys:\n"
                            "  drop_views: list[str]  -- view labels to remove\n"
                            "  override_confidence: {label: float}  -- omega scalars 0-1\n"
                            "  override_expected_return: {asset: float}\n"
                            "  set_model_parameters: {tau|risk_aversion|risk_free_rate: float}\n"
                            "  scale_factor_shock: {label: float}\n"
                            "  weight_bounds: [min, max]"
                        ),
                        "properties": {
                            "drop_views": {"type": "array", "items": {"type": "string"}},
                            "override_confidence": {"type": "object"},
                            "override_expected_return": {"type": "object"},
                            "set_model_parameters": {"type": "object"},
                            "scale_factor_shock": {"type": "object"},
                            "weight_bounds": {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 2,
                                "maxItems": 2,
                            },
                        },
                        "additionalProperties": False,
                    },
                },
                "required": ["label", "mutations"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_stress_sweep",
            "description": (
                "Run a parameter sweep: execute the BL model at each value in a "
                "grid, varying a single mutation parameter. Returns a list of "
                "result summaries (one row per grid point) to analyse sensitivity."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sweep_parameter": {
                        "type": "string",
                        "description": (
                            "Which parameter to sweep. One of: "
                            "'tau', 'risk_aversion', 'confidence/<view_label>', "
                            "'factor_shock/<view_label>'."
                        ),
                    },
                    "grid": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Numeric values to iterate over.",
                    },
                    "base_mutations": {
                        "type": "object",
                        "description": "Optional additional mutations applied on top of each grid step.",
                    },
                },
                "required": ["sweep_parameter", "grid"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_scenarios",
            "description": (
                "Compare two previously-run scenarios from the cache. Returns a "
                "weight-delta table and return-delta table side-by-side."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "label_a": {"type": "string", "description": "Label of first scenario."},
                    "label_b": {"type": "string", "description": "Label of second scenario."},
                },
                "required": ["label_a", "label_b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "synthesise",
            "description": (
                "Terminate the reasoning loop and produce a final narrative "
                "synthesis covering: base allocation, stress findings, robustness "
                "assessment, and recommended action. Call this only when you have "
                "gathered sufficient evidence."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "narrative": {
                        "type": "string",
                        "description": "Full synthesis text in plain English.",
                    },
                    "recommended_weights": {
                        "type": "object",
                        "description": (
                            "Final weight recommendation {asset: weight} for the "
                            "allocation that best satisfies the user's stated goal. "
                            "Always provide this — use the best scenario weights found, "
                            "or the base weights if no scenario improved on the goal metric."
                        ),
                    },
                    "risk_flags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Bullet-point risk flags identified during the analysis.",
                    },
                },
                "required": ["narrative"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "view_fragility_scan",
            "description": (
                "Analyze how portfolio weights change as a view's magnitude varies. "
                "Useful for identifying fragile views that cause disproportionate allocation shifts."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "view_label": {
                        "type": "string",
                        "description": "Label of the view to test (must exist in bottom_up_views).",
                    },
                    "magnitude_values": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "List of magnitude values to test (max 5 points).",
                    },
                    "scenario_prefix": {
                        "type": "string",
                        "description": "Prefix for scenario labels (e.g., 'fragility').",
                    },
                },
                "required": ["view_label", "magnitude_values", "scenario_prefix"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "factor_shock_scan",
            "description": (
                "Simulate macro factor shocks and observe portfolio response. "
                "Tests sensitivity to factor exposures."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "factor": {
                        "type": "string",
                        "description": "Factor name (must exist in factor_shocks).",
                    },
                    "shock_values": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "List of shock magnitudes to test (max 5 points).",
                    },
                    "scenario_prefix": {
                        "type": "string",
                        "description": "Prefix for scenario labels (e.g., 'factor').",
                    },
                },
                "required": ["factor", "shock_values", "scenario_prefix"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "view_importance_test",
            "description": (
                "Determine how important each view is by running BL with each view "
                "removed one at a time. Returns Sharpe change and allocation shift for each."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "views": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of view labels to test (optional; defaults to all bottom_up_views).",
                    },
                    "scenario_prefix": {
                        "type": "string",
                        "description": "Prefix for scenario labels (default: 'view_removed').",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "allocation_envelope",
            "description": (
                "Compute min/max weight ranges across previously executed scenarios. "
                "Helps understand allocation stability and robustness."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "scenario_labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of scenario labels to analyze (optional; defaults to all in run_cache).",
                    },
                },
                "required": [],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Mutation application
# ---------------------------------------------------------------------------

def _apply_mutations(recipe: dict, mutations: dict) -> dict:
    """
    Return a *deep copy* of *recipe* with *mutations* applied.

    Supported mutation keys
    -----------------------
    drop_views : list[str]
        Remove bottom-up views or factor shocks whose label matches.
    override_confidence : dict {label: float}
        Replace the confidence scalar for matching bottom-up views.
    override_expected_return : dict {asset: float}
        Insert or replace expected_return on matching bottom-up views.
    set_model_parameters : dict
        Merge key/value pairs into recipe["model_parameters"].
    scale_factor_shock : dict {label: float}
        Multiply the magnitude of matching factor shocks by the given scale.
    weight_bounds : [min, max]
        Set recipe["constraints"]["weight_bounds"].
    """
    recipe = copy.deepcopy(recipe)
    bottom_up: list = recipe.get("bottom_up_views", [])
    top_down: dict = recipe.get("top_down_views", {})
    factor_shocks: list = top_down.get("factor_shocks", [])

    # ---- drop_views --------------------------------------------------------
    for label in mutations.get("drop_views", []):
        bottom_up = [v for v in bottom_up if v.get("label") != label]
        factor_shocks = [s for s in factor_shocks if s.get("label") != label]

    # ---- override_confidence -----------------------------------------------
    overrides: dict = mutations.get("override_confidence", {})
    for view in bottom_up:
        lbl = view.get("label")
        if lbl in overrides:
            view["confidence"] = float(overrides[lbl])

    # ---- override_expected_return ------------------------------------------
    ret_overrides: dict = mutations.get("override_expected_return", {})
    for view in bottom_up:
        asset = view.get("asset")
        if asset and asset in ret_overrides:
            view["expected_return"] = float(ret_overrides[asset])

    # ---- set_model_parameters ----------------------------------------------
    mp: dict = mutations.get("set_model_parameters", {})
    if mp:
        recipe.setdefault("model_parameters", {}).update(mp)

    # ---- scale_factor_shock ------------------------------------------------
    shock_scales: dict = mutations.get("scale_factor_shock", {})
    for shock in factor_shocks:
        lbl = shock.get("label")
        if lbl in shock_scales:
            shock["shock"] = shock.get("shock", 0.0) * float(shock_scales[lbl])

    # ---- weight_bounds -----------------------------------------------------
    wb = mutations.get("weight_bounds")
    if wb is not None:
        recipe.setdefault("constraints", {})["weight_bounds"] = list(wb)

    # Write mutation results back
    recipe["bottom_up_views"] = bottom_up
    if "top_down_views" in recipe:
        recipe["top_down_views"]["factor_shocks"] = factor_shocks
    return recipe


# ---------------------------------------------------------------------------
# Result summariser
# ---------------------------------------------------------------------------

def _summarise_result(
    result: dict, recipe: dict, price_df: "pd.DataFrame | None" = None
) -> dict:
    """Extract a compact summary dict from a run_black_litterman() result."""
    weights: dict = result.get("weights", {})
    posterior: dict = result.get("posterior_returns", {})
    prior: dict = result.get("prior_returns", {})
    universe: list = result.get("universe", list(weights.keys()))

    import numpy as np
    try:
        from app.services.bl_engine.bl_standalone import sample_cov
        if price_df is None:
            from app.services.price_data.load_data import load_market_data
            price_df, *_ = load_market_data()
        price_subset = price_df[universe].dropna()
        cov = sample_cov(price_subset).values
        w = [weights.get(a, 0.0) for a in universe]
        mu = [posterior.get(a, 0.0) for a in universe]
        port_ret = float(np.dot(w, mu))
        port_vol = float(np.sqrt(np.dot(w, np.dot(cov, w))))
        sharpe = port_ret / port_vol if port_vol > 1e-8 else 0.0
    except Exception:
        logger.warning("Portfolio metric calculation failed; defaulting to zeros", exc_info=True)
        port_ret, port_vol, sharpe = 0.0, 0.0, 0.0

    top_weights = sorted(weights.items(), key=lambda x: -x[1])[:5]
    return_deltas = {
        a: round(posterior.get(a, 0.0) - prior.get(a, 0.0), 4)
        for a in universe
    }
    return {
        "portfolio_return": round(port_ret, 4),
        "portfolio_vol": round(port_vol, 4),
        "sharpe": round(sharpe, 4),
        "top_weights": {k: round(float(v), 4) for k, v in top_weights},
        "weights": {k: round(float(v), 4) for k, v in weights.items()},
        "return_delta_vs_prior": return_deltas,
    }


def _weight_delta(base_weights: dict, other_weights: dict) -> dict:
    keys = set(base_weights) | set(other_weights)
    return {
        k: round(other_weights.get(k, 0.0) - base_weights.get(k, 0.0), 4)
        for k in sorted(keys)
    }


# ---------------------------------------------------------------------------
# Diagnostic tool helpers
# ---------------------------------------------------------------------------

def _apply_view_override(recipe: dict, view_label: str, magnitude: float) -> dict:
    """
    Override a view's expected_return or outperformance magnitude.
    Returns a mutated copy of the recipe.
    """
    from copy import deepcopy
    recipe = deepcopy(recipe)
    bottom_up = recipe.get("bottom_up_views", [])
    
    for view in bottom_up:
        if view.get("label") == view_label:
            if view.get("type") == "absolute":
                view["expected_return"] = magnitude
            elif view.get("type") == "relative":
                # For relative views, magnitude is the outperformance
                view["expected_outperformance"] = magnitude
            break
    
    recipe["bottom_up_views"] = bottom_up
    return recipe


def _apply_factor_shock_override(recipe: dict, factor: str, shock: float) -> dict:
    """
    Override a factor shock magnitude.
    Returns a mutated copy of the recipe.
    """
    from copy import deepcopy
    recipe = deepcopy(recipe)
    top_down = recipe.get("top_down_views", {})
    factor_shocks = top_down.get("factor_shocks", [])
    
    for fs in factor_shocks:
        if fs.get("factor") == factor:
            fs["shock"] = shock
            break
    
    top_down["factor_shocks"] = factor_shocks
    recipe["top_down_views"] = top_down
    return recipe


def _compute_weight_shift(base_weights: dict, scenario_weights: dict) -> float:
    """
    Compute the sum of absolute weight changes (allocation shift).
    """
    delta = _weight_delta(base_weights, scenario_weights)
    return round(sum(abs(v) for v in delta.values()), 4)


# ---------------------------------------------------------------------------
# Tool dispatcher
# ---------------------------------------------------------------------------

def dispatch_tool(
    tool_name: str,
    tool_args: dict,
    base_recipe: dict,
    run_cache: Dict[str, dict],
    price_df: pd.DataFrame,
    goal_mutations: Optional[dict] = None,
) -> dict:
    """
    Execute a tool call from the agent loop.

    Parameters
    ----------
    tool_name   Name of the tool (must match one of TOOLS[*].function.name).
    tool_args   Parsed JSON arguments dict from the model.
    base_recipe Original (unmodified) recipe.
    run_cache   Dict[label -> result_summary]; caller accumulates this.
    price_df    Price DataFrame required by run_black_litterman.
    goal_mutations  Hard constraints extracted from the goal (e.g. weight_bounds)
                    that are always merged into every scenario mutation.

    Returns
    -------
    A JSON-serialisable dict that becomes the tool-result message content.
    """
    from app.orchestrators.bl_orchestrator import run_black_litterman

    # ------------------------------------------------------------------ #
    if tool_name == "get_recipe_summary":
        bottom_up = base_recipe.get("bottom_up_views", [])
        top_down = base_recipe.get("top_down_views", {})
        factor_shocks = top_down.get("factor_shocks", [])
        meta = base_recipe.get("meta", {})
        mp = base_recipe.get("model_parameters", {})
        constraints = base_recipe.get("constraints", {})
        return {
            "name": meta.get("name", "unnamed"),
            "universe": base_recipe.get("universe", {}).get("assets", []),
            "model_parameters": mp,
            "constraints": constraints,
            "bottom_up_views": [
                {
                    "label": v.get("label"),
                    "asset": v.get("asset"),
                    "direction": v.get("direction"),
                    "expected_return": v.get("expected_return"),
                    "confidence": v.get("confidence"),
                }
                for v in bottom_up
            ],
            "factor_shocks": [
                {
                    "label": s.get("label"),
                    "factor": s.get("factor"),
                    "magnitude": s.get("magnitude"),
                }
                for s in factor_shocks
            ],
            "view_labels": [v.get("label") for v in bottom_up] + [s.get("label") for s in factor_shocks],
            "sweepable_confidence_params": [
                f"confidence/{v.get('label')}" for v in bottom_up
            ] + [
                f"confidence/{s.get('label')}" for s in factor_shocks
            ],
            "note": (
                f"To stress-test expected return assumptions use run_bl_scenario with "
                f"override_expected_return: {{asset: new_return}} mutations, or "
                f"run_stress_sweep with sweep_parameter='risk_aversion'. "
                f"Use ONLY the exact labels listed in view_labels for confidence sweeps."
            ),
        }

    # ------------------------------------------------------------------ #
    elif tool_name == "run_bl_scenario":
        label: str = tool_args["label"]
        mutations: dict = tool_args.get("mutations", {})
        # Hard-merge goal-level constraints (e.g. weight_bounds) so they are
        # always applied even if the model omitted them from the mutation dict.
        if goal_mutations:
            merged = copy.deepcopy(goal_mutations)
            merged.update(mutations)   # agent mutations win on non-critical keys
            # But goal weight_bounds always takes priority (more restrictive)
            if "weight_bounds" in goal_mutations:
                merged["weight_bounds"] = goal_mutations["weight_bounds"]
            mutations = merged
        mutated_recipe = _apply_mutations(base_recipe, mutations)
        try:
            with _quiet_bl():
                result = run_black_litterman(mutated_recipe, price_df)
            summary = _summarise_result(result, mutated_recipe, price_df)

            # Detect equal-weight trap: when cap * n_assets == 1.0 the optimizer
            # is fully constrained and posterior views have no effect.
            wb = mutations.get("weight_bounds")
            if wb is not None:
                n = len(summary.get("weights", {}))
                if n > 0 and abs(wb[1] * n - 1.0) < 0.01:
                    summary["constraint_warning"] = (
                        f"Weight cap {wb[1]:.0%} × {n} assets = 100%: portfolio is "
                        f"forced to equal-weight. Views cannot differentiate allocation. "
                        f"Consider loosening the cap or varying expected returns directly."
                    )

            # Compute delta vs base
            if "base" in run_cache:
                summary["weight_delta_vs_base"] = _weight_delta(
                    run_cache["base"]["weights"], summary["weights"]
                )
            run_cache[label] = summary
            return {"label": label, "status": "ok", **summary}
        except Exception as exc:
            logger.exception("Tool run_bl_scenario failed [label=%s]: %s", label, exc)
            run_cache[label] = {"error": str(exc)}
            return {"label": label, "status": "error", "error": str(exc)}

    # ------------------------------------------------------------------ #
    elif tool_name == "run_stress_sweep":
        sweep_param: str = tool_args["sweep_parameter"]
        grid: list = tool_args["grid"]
        base_mutations: dict = tool_args.get("base_mutations", {})
        # Merge goal-level constraints into every sweep step
        if goal_mutations:
            merged_base = copy.deepcopy(goal_mutations)
            merged_base.update(base_mutations)
            if "weight_bounds" in goal_mutations:
                merged_base["weight_bounds"] = goal_mutations["weight_bounds"]
            base_mutations = merged_base

        rows = []
        for value in grid:
            step_mutations = copy.deepcopy(base_mutations)

            # Map sweep_parameter → mutation key
            if sweep_param in ("tau", "risk_aversion", "risk_free_rate"):
                step_mutations.setdefault("set_model_parameters", {})[sweep_param] = value
            elif sweep_param.startswith("confidence/"):
                view_label = sweep_param.split("/", 1)[1]
                step_mutations.setdefault("override_confidence", {})[view_label] = value
            elif sweep_param.startswith("factor_shock/"):
                # scale to ratio relative to base magnitude
                shock_label = sweep_param.split("/", 1)[1]
                step_mutations.setdefault("scale_factor_shock", {})[shock_label] = value
            else:
                rows.append({"value": value, "error": f"Unknown sweep_parameter '{sweep_param}'"})
                continue

            mutated_recipe = _apply_mutations(base_recipe, step_mutations)
            try:
                with _quiet_bl():
                    result = run_black_litterman(mutated_recipe, price_df)
                summary = _summarise_result(result, mutated_recipe, price_df)
                rows.append({
                    "value": value,
                    "sharpe": summary["sharpe"],
                    "portfolio_return": summary["portfolio_return"],
                    "portfolio_vol": summary["portfolio_vol"],
                    "top_weights": summary["top_weights"],
                })
            except Exception as exc:
                logger.exception("Tool run_stress_sweep failed at value=%s [param=%s]: %s", value, sweep_param, exc)
                rows.append({"value": value, "error": str(exc)})

        return {"sweep_parameter": sweep_param, "grid_results": rows}

    # ------------------------------------------------------------------ #
    elif tool_name == "compare_scenarios":
        label_a: str = tool_args["label_a"]
        label_b: str = tool_args["label_b"]

        missing = [lbl for lbl in (label_a, label_b) if lbl not in run_cache]
        if missing:
            return {
                "error": f"Scenario(s) not found in cache: {missing}. Run them first."
            }

        a = run_cache[label_a]
        b = run_cache[label_b]
        weight_delta = _weight_delta(a.get("weights", {}), b.get("weights", {}))
        return_delta_a = a.get("return_delta_vs_prior", {})
        return_delta_b = b.get("return_delta_vs_prior", {})

        return {
            "scenario_a": label_a,
            "scenario_b": label_b,
            "sharpe_a": a.get("sharpe"),
            "sharpe_b": b.get("sharpe"),
            "portfolio_return_a": a.get("portfolio_return"),
            "portfolio_return_b": b.get("portfolio_return"),
            "portfolio_vol_a": a.get("portfolio_vol"),
            "portfolio_vol_b": b.get("portfolio_vol"),
            "weight_delta_b_minus_a": weight_delta,
            "return_delta_a": return_delta_a,
            "return_delta_b": return_delta_b,
        }

    # ------------------------------------------------------------------ #
    elif tool_name == "synthesise":
        # Caller catches this as the termination signal
        return {
            "done": True,
            "narrative": tool_args.get("narrative", ""),
            "recommended_weights": tool_args.get("recommended_weights"),
            "risk_flags": tool_args.get("risk_flags", []),
        }

    # ------------------------------------------------------------------ #
    elif tool_name == "view_fragility_scan":
        view_label: str = tool_args["view_label"]
        magnitude_values: list = tool_args["magnitude_values"]
        scenario_prefix: str = tool_args.get("scenario_prefix", "fragility")
        
        # Performance safeguard
        if len(magnitude_values) > 5:
            return {"error": "Maximum 5 magnitude points allowed for fragility scan."}
        
        # Verify view exists
        bottom_up = base_recipe.get("bottom_up_views", [])
        view_found = any(v.get("label") == view_label for v in bottom_up)
        if not view_found:
            return {"error": f"View '{view_label}' not found in bottom_up_views."}
        
        fragility_scan = []
        for mag in magnitude_values:
            label = f"{scenario_prefix}_{view_label}_{mag}"
            mutated_recipe = _apply_view_override(base_recipe, view_label, mag)
            
            # Apply goal mutations if present
            if goal_mutations:
                mutated_recipe = _apply_mutations(mutated_recipe, goal_mutations)
            
            try:
                with _quiet_bl():
                    result = run_black_litterman(mutated_recipe, price_df)
                summary = _summarise_result(result, mutated_recipe, price_df)
                
                fragility_scan.append({
                    "magnitude": mag,
                    "weights": summary["weights"],
                    "sharpe": summary["sharpe"],
                    "volatility": summary["portfolio_vol"],
                })
                
                # Cache the scenario
                run_cache[label] = {
                    **summary,
                    "source": "fragility_scan",
                    "view_label": view_label,
                    "magnitude": mag,
                }
            except Exception as exc:
                logger.exception("Tool view_fragility_scan failed [view=%s magnitude=%s]: %s", view_label, mag, exc)
                fragility_scan.append({
                    "magnitude": mag,
                    "error": str(exc),
                })
        
        return {
            "view_label": view_label,
            "fragility_scan": fragility_scan,
        }

    # ------------------------------------------------------------------ #
    elif tool_name == "factor_shock_scan":
        factor: str = tool_args["factor"]
        shock_values: list = tool_args["shock_values"]
        scenario_prefix: str = tool_args.get("scenario_prefix", "factor")
        
        # Performance safeguard
        if len(shock_values) > 5:
            return {"error": "Maximum 5 shock points allowed for factor scan."}
        
        # Verify factor exists
        top_down = base_recipe.get("top_down_views", {})
        factor_shocks = top_down.get("factor_shocks", [])
        factor_found = any(fs.get("factor") == factor for fs in factor_shocks)
        if not factor_found:
            return {"error": f"Factor '{factor}' not found in factor_shocks."}
        
        shock_results = []
        for shock in shock_values:
            label = f"{scenario_prefix}_{factor}_{shock}"
            mutated_recipe = _apply_factor_shock_override(base_recipe, factor, shock)
            
            # Apply goal mutations if present
            if goal_mutations:
                mutated_recipe = _apply_mutations(mutated_recipe, goal_mutations)
            
            try:
                with _quiet_bl():
                    result = run_black_litterman(mutated_recipe, price_df)
                summary = _summarise_result(result, mutated_recipe, price_df)
                
                shock_results.append({
                    "shock": shock,
                    "portfolio_return": summary["portfolio_return"],
                    "volatility": summary["portfolio_vol"],
                    "weights": summary["weights"],
                    "sharpe": summary["sharpe"],
                })
                
                # Cache the scenario
                run_cache[label] = {
                    **summary,
                    "source": "factor_shock",
                    "factor": factor,
                    "shock_magnitude": shock,
                }
            except Exception as exc:
                logger.exception("Tool factor_shock_scan failed [factor=%s shock=%s]: %s", factor, shock, exc)
                shock_results.append({
                    "shock": shock,
                    "error": str(exc),
                })
        
        return {
            "factor": factor,
            "shock_results": shock_results,
        }

    # ------------------------------------------------------------------ #
    elif tool_name == "view_importance_test":
        views_to_test: list = tool_args.get("views")
        scenario_prefix: str = tool_args.get("scenario_prefix", "view_removed")
        
        # Default to all bottom_up views
        if not views_to_test:
            all_views = base_recipe.get("bottom_up_views", [])
            views_to_test = [v.get("label") for v in all_views if v.get("label")]
        
        if not views_to_test:
            return {"error": "No views found to test."}
        
        # Get base scenario weights for comparison
        base_weights = run_cache.get("base", {}).get("weights", {})
        base_sharpe = run_cache.get("base", {}).get("sharpe", 0.0)
        
        view_importance = []
        for view_label in views_to_test:
            label = f"{scenario_prefix}_{view_label}"
            mutations = {"drop_views": [view_label]}
            
            # Merge goal mutations
            if goal_mutations:
                merged = copy.deepcopy(goal_mutations)
                merged.update(mutations)
                mutations = merged
            
            mutated_recipe = _apply_mutations(base_recipe, mutations)
            
            try:
                with _quiet_bl():
                    result = run_black_litterman(mutated_recipe, price_df)
                summary = _summarise_result(result, mutated_recipe, price_df)
                
                sharpe_change = round(summary["sharpe"] - base_sharpe, 4)
                allocation_shift = _compute_weight_shift(base_weights, summary["weights"])
                
                view_importance.append({
                    "view": view_label,
                    "sharpe_change": sharpe_change,
                    "allocation_shift": allocation_shift,
                    "sharpe_without_view": summary["sharpe"],
                })
                
                # Cache the scenario
                run_cache[label] = {
                    **summary,
                    "source": "view_removed",
                    "removed_view": view_label,
                }
            except Exception as exc:
                logger.exception("Tool view_importance_test failed [view=%s]: %s", view_label, exc)
                view_importance.append({
                    "view": view_label,
                    "error": str(exc),
                })
        
        # Sort by allocation shift (descending) to highlight most impactful views
        view_importance_sorted = sorted(
            [v for v in view_importance if "error" not in v],
            key=lambda x: abs(x["allocation_shift"]),
            reverse=True
        )
        errors = [v for v in view_importance if "error" in v]
        
        return {
            "view_importance": view_importance_sorted + errors,
        }

    # ------------------------------------------------------------------ #
    elif tool_name == "allocation_envelope":
        scenario_labels: list = tool_args.get("scenario_labels")
        
        # Default to all scenarios in run_cache
        if not scenario_labels:
            scenario_labels = list(run_cache.keys())
        
        if not scenario_labels:
            return {"error": "No scenarios available in run_cache."}
        
        # Collect all weights
        all_weights = {}
        for label in scenario_labels:
            if label not in run_cache:
                continue
            scenario = run_cache[label]
            if "weights" not in scenario:
                continue
            for asset, weight in scenario["weights"].items():
                if asset not in all_weights:
                    all_weights[asset] = []
                all_weights[asset].append(weight)
        
        if not all_weights:
            return {"error": "No valid weight data found in specified scenarios."}
        
        # Compute envelope
        allocation_envelope = {}
        for asset, weights_list in all_weights.items():
            allocation_envelope[asset] = {
                "min": round(min(weights_list), 4),
                "max": round(max(weights_list), 4),
                "range": round(max(weights_list) - min(weights_list), 4),
            }
        
        # Sort by range (descending) to highlight most variable allocations
        sorted_envelope = dict(
            sorted(allocation_envelope.items(), key=lambda x: x[1]["range"], reverse=True)
        )
        
        return {
            "allocation_envelope": sorted_envelope,
            "scenarios_analyzed": len([l for l in scenario_labels if l in run_cache]),
        }

    # ------------------------------------------------------------------ #
    else:
        return {"error": f"Unknown tool: '{tool_name}'"}

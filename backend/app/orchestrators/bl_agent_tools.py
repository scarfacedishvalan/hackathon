"""
BL Agent Tools

Defines the five tools available to the agentic BL orchestrator and
the dispatch logic that executes them.

Tools
-----
get_recipe_summary   -- surface the loaded recipe's key facts
run_bl_scenario      -- run BL with a dict of mutations applied
run_stress_sweep     -- run a sweep of one numeric parameter across a grid
compare_scenarios    -- diff two cached scenario results
synthesise           -- produce the final narrative (terminates the loop)

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
from typing import Any, Dict, List, Optional

import pandas as pd


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
                            "Optional final weight recommendation {asset: weight}. "
                            "Omit if you cannot improve on the base BL result."
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
    views_section = recipe.get("views", {})
    bottom_up: list = views_section.get("bottom_up", [])
    top_down: dict = views_section.get("top_down", {})
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
            shock["magnitude"] = shock.get("magnitude", 0.0) * float(shock_scales[lbl])

    # ---- weight_bounds -----------------------------------------------------
    wb = mutations.get("weight_bounds")
    if wb is not None:
        recipe.setdefault("constraints", {})["weight_bounds"] = list(wb)

    # Write mutation results back
    views_section["bottom_up"] = bottom_up
    if "top_down" in views_section:
        views_section["top_down"]["factor_shocks"] = factor_shocks
    recipe["views"] = views_section
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
        "top_weights": {k: round(v, 4) for k, v in top_weights},
        "weights": {k: round(v, 4) for k, v in weights.items()},
        "return_delta_vs_prior": return_deltas,
    }


def _weight_delta(base_weights: dict, other_weights: dict) -> dict:
    keys = set(base_weights) | set(other_weights)
    return {
        k: round(other_weights.get(k, 0.0) - base_weights.get(k, 0.0), 4)
        for k in sorted(keys)
    }


# ---------------------------------------------------------------------------
# Tool dispatcher
# ---------------------------------------------------------------------------

def dispatch_tool(
    tool_name: str,
    tool_args: dict,
    base_recipe: dict,
    run_cache: Dict[str, dict],
    price_df: pd.DataFrame,
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

    Returns
    -------
    A JSON-serialisable dict that becomes the tool-result message content.
    """
    from app.orchestrators.bl_orchestrator import run_black_litterman

    # ------------------------------------------------------------------ #
    if tool_name == "get_recipe_summary":
        views = base_recipe.get("views", {})
        bottom_up = views.get("bottom_up", [])
        factor_shocks = views.get("top_down", {}).get("factor_shocks", [])
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
        }

    # ------------------------------------------------------------------ #
    elif tool_name == "run_bl_scenario":
        label: str = tool_args["label"]
        mutations: dict = tool_args.get("mutations", {})
        mutated_recipe = _apply_mutations(base_recipe, mutations)
        try:
            with _quiet_bl():
                result = run_black_litterman(mutated_recipe, price_df)
            summary = _summarise_result(result, mutated_recipe, price_df)

            # Compute delta vs base
            if "base" in run_cache:
                summary["weight_delta_vs_base"] = _weight_delta(
                    run_cache["base"]["weights"], summary["weights"]
                )
            run_cache[label] = summary
            return {"label": label, "status": "ok", **summary}
        except Exception as exc:
            run_cache[label] = {"error": str(exc)}
            return {"label": label, "status": "error", "error": str(exc)}

    # ------------------------------------------------------------------ #
    elif tool_name == "run_stress_sweep":
        sweep_param: str = tool_args["sweep_parameter"]
        grid: list = tool_args["grid"]
        base_mutations: dict = tool_args.get("base_mutations", {})

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
    else:
        return {"error": f"Unknown tool: '{tool_name}'"}

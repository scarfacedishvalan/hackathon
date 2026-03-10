"""
Black-Litterman Orchestrator

Simple orchestration layer that wraps ``run_bl_recipe`` with automatic
loading of market metadata (market caps, factor exposures) from the
``data/market_data.json`` registry.

Public interface
----------------
``run_black_litterman(recipe, price_data)``
    Execute a BL recipe.  Only the recipe dict and a price DataFrame are
    required — all market metadata is resolved internally.
"""

from __future__ import annotations

import json
import sys
import os
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Path wrangling (support both ``python -m`` and direct execution)
# ---------------------------------------------------------------------------

_BACKEND_DIR = Path(__file__).resolve().parents[2]  # backend/
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from run_bl_recipe import run_bl_recipe  # noqa: E402
from app.services.bl_engine.bl_standalone import (  # noqa: E402
    EfficientFrontier,
    sample_cov,
    market_implied_prior_returns,
)

# ---------------------------------------------------------------------------
# Market metadata
# ---------------------------------------------------------------------------

_MARKET_DATA_PATH = _BACKEND_DIR / "data" / "market_data.json"


def _load_metadata() -> Dict[str, Any]:
    """Return the full ``market_data.json`` dict (cached per process)."""
    if not hasattr(_load_metadata, "_cache"):
        with open(_MARKET_DATA_PATH, "r", encoding="utf-8") as f:
            _load_metadata._cache = json.load(f)
    return _load_metadata._cache


def _get_market_caps(assets: list[str]) -> Dict[str, float]:
    """Return market-cap mapping for *assets* from the metadata registry."""
    raw = _load_metadata()["market_caps"]
    # Drop the internal _note key
    caps = {k: v for k, v in raw.items() if not k.startswith("_")}
    missing = [a for a in assets if a not in caps]
    if missing:
        raise KeyError(
            f"Market caps not found for: {missing}. "
            "Add them to data/market_data.json → market_caps."
        )
    return {a: caps[a] for a in assets}


def _get_factor_matrix(assets: list[str]) -> tuple[np.ndarray, Dict[str, int]]:
    """
    Return the factor exposure matrix B (n_assets × n_factors) with rows
    aligned to *assets*, plus a factor-name → column-index map.
    """
    md = _load_metadata()
    factor_names: list[str] = md["factor_names"]
    raw_exposures: Dict[str, list] = {
        k: v for k, v in md["factor_exposures"].items() if not k.startswith("_")
    }
    missing = [a for a in assets if a not in raw_exposures]
    if missing:
        raise KeyError(
            f"Factor exposures not found for: {missing}. "
            "Add them to data/market_data.json → factor_exposures."
        )
    B = np.array([raw_exposures[a] for a in assets])
    factor_index_map = {name: idx for idx, name in enumerate(factor_names)}
    return B, factor_index_map


def _apply_model_defaults(recipe: dict) -> dict:
    """
    Return a copy of *recipe* with ``model_parameters`` filled in from
    ``model_defaults`` for any key that is absent.
    """
    defaults = _load_metadata().get("model_defaults", {})
    recipe = json.loads(json.dumps(recipe))  # deep copy
    params = recipe.setdefault("model_parameters", {})
    for key in ("tau", "risk_aversion", "risk_free_rate"):
        if key not in params and key in defaults:
            params[key] = defaults[key]
    return recipe


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_black_litterman(
    recipe: dict,
    price_data: pd.DataFrame,
    *,
    covariance_estimator=None,
    return_estimator=None,
) -> dict:
    """
    Execute a Black-Litterman recipe.

    Parameters
    ----------
    recipe : dict
        BL recipe.  Required keys: ``meta``, ``universe.assets``.
        ``model_parameters`` defaults are filled from ``market_data.json``
        if absent.  See ``run_bl_recipe`` docstring for the full schema.
    price_data : pd.DataFrame
        Historical price DataFrame with ticker columns.  Only columns
        matching the recipe universe are used.
    covariance_estimator : callable, optional
        Custom covariance function (default: ``sample_cov``).
    return_estimator : callable, optional
        Custom prior return function (default: ``market_implied_prior_returns``).

    Returns
    -------
    dict
        Recipe execution results — weights, posterior/prior returns,
        view matrices, and model parameters.
    """
    # Fill missing model parameters from registry defaults
    recipe = _apply_model_defaults(recipe)

    universe: list[str] = recipe["universe"]["assets"]

    # weight_bounds is now a single [min, max] pair applied to all assets.
    # If an old dict-style entry sneaked in (e.g. manual edit), drop it so
    # run_bl_recipe falls back to the global long-only bounds instead of
    # silently applying stale per-asset floors.
    bounds_raw = recipe.get("constraints", {}).get("weight_bounds", None)
    if isinstance(bounds_raw, dict):
        # Legacy per-asset dict — discard it; rely on long_only fallback
        recipe["constraints"]["weight_bounds"] = None

    # Filter price data to universe
    missing_prices = [a for a in universe if a not in price_data.columns]
    if missing_prices:
        raise ValueError(
            f"price_data is missing columns for: {missing_prices}"
        )
    price_subset = price_data[universe].dropna()

    # Load market metadata aligned to universe order
    market_caps = _get_market_caps(universe)
    factor_matrix, factor_index_map = _get_factor_matrix(universe)

    result = run_bl_recipe(
        recipe=recipe,
        price_data=price_subset,
        market_caps=market_caps,
        factor_exposures=factor_matrix,
        factor_index_map=factor_index_map,
        covariance_estimator=covariance_estimator,
        return_estimator=return_estimator,
    )

    # Augment result with chart-ready data
    chart_data = _compute_chart_data(result, recipe, price_subset, market_caps)
    result.update(chart_data)
    return result


# ---------------------------------------------------------------------------
# Chart data computation
# ---------------------------------------------------------------------------


def _compute_chart_data(
    result: dict,
    recipe: dict,
    price_subset: "pd.DataFrame",
    market_caps: Dict[str, float],
) -> Dict[str, Any]:
    """
    Compute ``efficientFrontier``, ``allocation``, and ``topDownContribution``
    from the raw BL recipe result.

    These match the frontend mock shapes exactly.
    """
    universe: list[str] = result["universe"]
    params = recipe["model_parameters"]
    risk_aversion: float = params["risk_aversion"]
    risk_free_rate: float = params["risk_free_rate"]

    # Re-compute covariance + equilibrium returns (cheap — needed for Σ)
    cov_matrix = sample_cov(price_subset)
    pi = market_implied_prior_returns(market_caps, cov_matrix, risk_aversion)
    Sigma = cov_matrix.values  # numpy array

    # ── Weights ────────────────────────────────────────────────────────────────

    total_cap = sum(market_caps[a] for a in universe)
    prior_weights = {a: market_caps[a] / total_cap for a in universe}
    w_mkt = np.array([prior_weights[a] for a in universe])

    w_bl = np.array([result["weights"].get(a, 0.0) for a in universe])
    mu_bl = np.array([result["posterior_returns"][a] for a in universe])
    mu_pi = np.array([float(pi[a]) for a in universe])

    # ── Prior / Posterior portfolio stats ─────────────────────────────────────

    prior_ret = float(w_mkt @ mu_pi)
    prior_vol = float(np.sqrt(w_mkt @ Sigma @ w_mkt))
    post_ret = float(w_bl @ mu_bl)
    post_vol = float(np.sqrt(w_bl @ Sigma @ w_bl))

    # ── Efficient frontier curve ───────────────────────────────────────────────

    n_points = 40
    curve: list[Dict[str, float]] = []
    try:
        # Lower bound: min-volatility portfolio expected return
        ef_min = EfficientFrontier(
            dict(zip(universe, mu_bl)),
            cov_matrix,
            weight_bounds=(0.0, 1.0),
            risk_free_rate=risk_free_rate,
        )
        ef_min.min_volatility()
        w_min = np.array(list(ef_min.clean_weights().values()))
        min_ret = float(w_min @ mu_bl)

        # Upper bound: highest individual posterior return (reachable w/o short)
        max_ret = float(np.max(mu_bl)) * 0.98  # stay just inside feasible region

        for target_ret in np.linspace(min_ret, max_ret, n_points):
            try:
                ef_pt = EfficientFrontier(
                    dict(zip(universe, mu_bl)),
                    cov_matrix,
                    weight_bounds=(0.0, 1.0),
                    risk_free_rate=risk_free_rate,
                )
                ef_pt.efficient_return(target_ret)
                w_pt = np.array(list(ef_pt.clean_weights().values()))
                vol_pt = float(np.sqrt(w_pt @ Sigma @ w_pt))
                curve.append({"vol": round(vol_pt, 6), "ret": round(float(w_pt @ mu_bl), 6)})
            except Exception:
                pass  # infeasible target — skip quietly
    except Exception:
        pass  # fallback: empty curve

    # ── Allocation ─────────────────────────────────────────────────────────────

    allocation = [
        {
            "ticker": a,
            "priorWeight": round(float(prior_weights[a]), 6),
            "blWeight": round(float(result["weights"].get(a, 0.0)), 6),
        }
        for a in universe
    ]

    # ── Top-down / sector contributions ───────────────────────────────────────

    md = _load_metadata()
    # sector_map format: { asset: sector_name }
    asset_sector: Dict[str, str] = md.get("sector_map", {})

    # Group universe assets by sector
    sectors: Dict[str, list[int]] = {}
    for idx, asset in enumerate(universe):
        sector = asset_sector.get(asset, "Other")
        sectors.setdefault(sector, []).append(idx)

    # Σ @ w_BL — used for marginal risk contributions
    sigma_w = Sigma @ w_bl

    top_down_contribution = [
        {
            "sector": sector,
            "returnContribution": round(float(np.sum(w_bl[idxs] * mu_bl[idxs])), 6),
            "riskContribution": round(float(np.sum(w_bl[idxs] * sigma_w[idxs])), 6),
        }
        for sector, idxs in sectors.items()
        if float(np.sum(w_bl[idxs])) > 1e-6  # omit zero-weight sectors
    ]

    return {
        "efficientFrontier": {
            "curve": curve,
            "prior": {"vol": round(float(prior_vol), 6), "ret": round(float(prior_ret), 6)},
            "posterior": {"vol": round(float(post_vol), 6), "ret": round(float(post_ret), 6)},
        },
        "allocation": allocation,
        "topDownContribution": top_down_contribution,
    }

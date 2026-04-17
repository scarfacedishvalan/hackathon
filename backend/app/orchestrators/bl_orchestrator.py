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
from typing import Any, Dict, Optional, List

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

    # Load market metadata from embedded market_context
    market_context = recipe["market_context"]
    market_caps = market_context["market_caps"]
    factor_exposures_dict = market_context["factor_exposures"]
    factor_names = market_context["factor_names"]
    
    # Build factor matrix aligned to universe order
    factor_matrix = np.array([factor_exposures_dict[asset] for asset in universe])
    factor_index_map = {name: idx for idx, name in enumerate(factor_names)}

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


def _capture_calculation_steps(
    result: dict,
    recipe: dict,
    price_subset: pd.DataFrame,
    market_caps: Dict[str, float],
    Sigma: np.ndarray,
    pi: pd.Series,
    universe: List[str],
    optimal_weights: np.ndarray,
    factor_matrix: Optional[np.ndarray] = None,
    factor_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Capture all intermediate BL calculation steps for LaTeX display.
    
    Returns dict with all matrices and intermediate calculations.
    """
    # Get P, Q, Omega from result (if available)
    P = result.get("P")
    Q = result.get("Q")
    Omega = result.get("Omega")
    
    if P is None or Q is None or Omega is None:
        return None  # No views, skip calculation steps
    
    params = recipe["model_parameters"]
    tau = params["tau"]
    
    # Recreate the BL model to capture intermediate steps
    tau_Sigma = tau * Sigma
    tau_Sigma_inv = np.linalg.inv(tau_Sigma)
    Omega_inv = np.linalg.inv(Omega)
    
    # Posterior precision matrix
    posterior_precision = tau_Sigma_inv + P.T @ Omega_inv @ P
    posterior_cov_inner = np.linalg.inv(posterior_precision)
    
    # Posterior returns calculation
    pi_array = pi.values.reshape(-1, 1)
    Q_array = Q.reshape(-1, 1) if Q.ndim == 1 else Q
    posterior_returns_array = posterior_cov_inner @ (tau_Sigma_inv @ pi_array + P.T @ Omega_inv @ Q_array)
    posterior_returns = pd.Series(posterior_returns_array.flatten(), index=universe)
    
    # Posterior covariance
    posterior_cov = Sigma + posterior_cov_inner
    
    # Convert optimal weights to Series with asset names
    weights_series = pd.Series(optimal_weights, index=universe, name="Optimal Weights")
    
    # Capture individual views for translation section
    bottom_up_views = recipe.get('bottom_up_views', [])
    top_down_views = recipe.get('top_down_views', {})
    factor_shocks = top_down_views.get('factor_shocks', [])
    
    # Build asset to index mapping
    asset_to_idx = {asset: idx for idx, asset in enumerate(universe)}
    
    # Process bottom-up views
    bottom_up_view_details = []
    n_bottom = result.get('n_bottom_up_views', 0)
    for i, view in enumerate(bottom_up_views[:n_bottom]):  # Only processed views
        view_type = view['type']
        confidence = view['confidence']
        label = view.get('label', f'View {i+1}')
        
        if view_type == 'absolute':
            asset = view['asset']
            if asset not in asset_to_idx:
                continue
            expected_return = view['expected_return']
            asset_idx = asset_to_idx[asset]
            P_row = np.zeros(len(universe))
            P_row[asset_idx] = 1.0
            Q_val = expected_return
            description = f"{asset} expected return: {expected_return:.2%}"
            
        elif view_type == 'relative':
            assets_in_view = view['assets']
            if not all(a in asset_to_idx for a in assets_in_view):
                continue
            weights = view['weights']
            expected_outperformance = view['expected_outperformance']
            P_row = np.zeros(len(universe))
            for asset, weight in zip(assets_in_view, weights):
                P_row[asset_to_idx[asset]] = weight
            Q_val = expected_outperformance
            # Build description
            if weights == [1, -1]:
                description = f"{assets_in_view[0]} outperforms {assets_in_view[1]} by {expected_outperformance:+.2%}"
            else:
                description = label
        else:
            continue
            
        bottom_up_view_details.append({
            'label': label,
            'type': view_type,
            'description': description,
            'P_row': P_row,
            'Q_val': Q_val,
            'confidence': confidence,
            'row_index': i
        })
    
    # Process top-down views (factor shocks)
    top_down_view_details = []
    n_top = result.get('n_top_down_views', 0)

    # Build factor index lookup if factor data is available
    factor_index_map = {}
    if factor_names:
        factor_index_map = {name: idx for idx, name in enumerate(factor_names)}

    for i, shock_spec in enumerate(factor_shocks[:n_top]):
        factor_name = shock_spec['factor']
        shock = shock_spec['shock']
        confidence = shock_spec['confidence']
        label = shock_spec.get('label', factor_name)

        # P_row: factor exposure vector for this factor across all assets (column of B)
        # This shows which assets are exposed to this factor and by how much.
        fi = factor_index_map.get(factor_name)
        if fi is not None and factor_matrix is not None:
            P_row = factor_matrix[:, fi]  # shape (n_assets,)
        else:
            P_row = np.zeros(len(universe))

        # Q_val: the factor-level shock (not the combined asset-level shift)
        Q_val = shock

        description = f"{factor_name} factor shock: {shock:+.2%}"
        
        top_down_view_details.append({
            'label': label,
            'factor': factor_name,
            'description': description,
            'P_row': P_row,
            'Q_val': Q_val,
            'confidence': confidence,
            'row_index': n_bottom + i
        })
    
    return {
        "tau": tau,
        "Sigma": Sigma,
        "pi": pi,
        "P": P,
        "Q": Q,
        "Omega": Omega,
        "assets": universe,
        "factor_matrix": factor_matrix,
        "factor_names": factor_names,
        "tau_Sigma": tau_Sigma,
        "tau_Sigma_inv": tau_Sigma_inv,
        "Omega_inv": Omega_inv,
        "posterior_precision": posterior_precision,
        "posterior_cov_inner": posterior_cov_inner,
        "posterior_returns": posterior_returns,
        "posterior_cov": posterior_cov,
        "optimal_weights": weights_series,
        "bottom_up_view_details": bottom_up_view_details,
        "top_down_view_details": top_down_view_details,
        "n_bottom_up_views": n_bottom,
        "n_top_down_views": n_top,
    }


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

    # Filter market_caps to universe assets only — the full market_context may
    # contain more assets than the current universe, and market_implied_prior_returns
    # requires market_caps and cov_matrix to have matching asset counts.
    universe_market_caps = {a: market_caps[a] for a in universe if a in market_caps}

    # Re-compute covariance + equilibrium returns (cheap — needed for Σ)
    cov_matrix = sample_cov(price_subset)
    pi = market_implied_prior_returns(universe_market_caps, cov_matrix, risk_aversion)
    Sigma = cov_matrix.values  # numpy array

    # ── Weights ────────────────────────────────────────────────────────────────

    total_cap = sum(universe_market_caps[a] for a in universe)
    prior_weights = {a: universe_market_caps[a] / total_cap for a in universe}
    w_mkt = np.array([prior_weights[a] for a in universe])

    w_bl = np.array([result["weights"].get(a, 0.0) for a in universe])
    mu_bl = np.array([result["posterior_returns"][a] for a in universe])
    mu_pi = np.array([float(pi[a]) for a in universe])

    # ── Prior / Posterior portfolio stats ─────────────────────────────────────

    prior_ret = float(w_mkt @ mu_pi)
    prior_vol = float(np.sqrt(w_mkt @ Sigma @ w_mkt))
    post_ret = float(w_bl @ mu_bl)
    post_vol = float(np.sqrt(w_bl @ Sigma @ w_bl))
    prior_sharpe = (prior_ret - risk_free_rate) / prior_vol if prior_vol > 1e-9 else 0.0
    post_sharpe  = (post_ret  - risk_free_rate) / post_vol  if post_vol  > 1e-9 else 0.0
    
    # VaR at 95% confidence (parametric, assuming normal distribution)
    # VaR_95 = expected return - 1.645 * volatility
    prior_var_95 = float(prior_ret - 1.645 * prior_vol)
    post_var_95 = float(post_ret - 1.645 * post_vol)

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
        raise

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

    # sector_map format: { asset: sector_name }
    asset_sector: Dict[str, str] = recipe["market_context"]["sectors"]

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

    # ── Calculation Steps for LaTeX Display ───────────────────────────────────
    market_context = recipe.get("market_context", {})
    factor_matrix_ctx = np.array([
        market_context["factor_exposures"][asset] for asset in universe
    ]) if "factor_exposures" in market_context else None
    factor_names_ctx = market_context.get("factor_names")

    calculation_steps = _capture_calculation_steps(
        result, recipe, price_subset, market_caps, Sigma, pi, universe, w_bl,
        factor_matrix=factor_matrix_ctx,
        factor_names=factor_names_ctx,
    )
    
    if calculation_steps:
        from app.orchestrators.bl_latex_utils import build_calculation_latex
        latex_sections = build_calculation_latex(calculation_steps)
    else:
        latex_sections = []

    return {
        "efficientFrontier": {
            "curve": curve,
            "prior": {"vol": round(float(prior_vol), 6), "ret": round(float(prior_ret), 6)},
            "posterior": {"vol": round(float(post_vol), 6), "ret": round(float(post_ret), 6)},
        },
        "allocation": allocation,
        "topDownContribution": top_down_contribution,
        "portfolioStats": {
            "prior": {
                "ret":    round(prior_ret,    6),
                "vol":    round(prior_vol,    6),
                "sharpe": round(prior_sharpe, 4),
                "var95":  round(prior_var_95, 6),
            },
            "posterior": {
                "ret":    round(post_ret,    6),
                "vol":    round(post_vol,    6),
                "sharpe": round(post_sharpe, 4),
                "var95":  round(post_var_95, 6),
            },
        },
        "calculationSteps": latex_sections,
    }

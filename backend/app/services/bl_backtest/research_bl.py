"""Translate validated research strength into explicit illustrative BL views."""

import math

import numpy as np
import pandas as pd

from app.services.bl_backtest.data_interface.load import ResearchData
from app.services.bl_backtest.data_interface.query import select_prices
from app.services.bl_backtest.schema import ResearchContext, ViewBatch, validate_views
from app.services.bl_engine.bl_standalone import market_implied_prior_returns, sample_cov
from run_bl_recipe import run_bl_recipe


def generate_bl_allocation(
    views_df: pd.DataFrame,
    context: ResearchContext,
    data: ResearchData,
    *,
    max_annual_alpha: float,
) -> dict:
    """Use the application's BL runner and its market-cap prior comparison."""
    if isinstance(max_annual_alpha, bool) or not math.isfinite(max_annual_alpha) or max_annual_alpha <= 0:
        raise ValueError("max_annual_alpha must be a finite, strictly positive annual fraction")
    batch = validate_views(ViewBatch.model_validate({"views": views_df.to_dict("records")}), context)
    universe = context.request.universe
    request = context.request.model_copy(update={"as_of": context.observation_date})
    prices, _ = select_prices(data, request)
    params = dict(data.metadata["model_defaults"])
    lookback = params.get("covariance_lookback_years")
    if lookback:
        prices = prices.loc[prices.index[-1] - pd.Timedelta(days=365 * lookback):]
    if len(prices) < 3:
        raise ValueError("BL covariance estimation requires at least three price observations")
    caps = {asset: data.metadata["market_caps"][asset] for asset in universe}
    if any(not math.isfinite(value) or value <= 0 for value in caps.values()):
        raise ValueError("BL market caps must be finite and strictly positive")
    covariance = sample_cov(prices)
    if not np.isfinite(covariance.to_numpy()).all():
        raise ValueError("BL covariance contains non-finite values")
    prior = market_implied_prior_returns(caps, covariance, params["risk_aversion"])
    signs = {"positive": 1, "negative": -1}
    bottom_up = []
    omitted = []
    for view in batch.views:
        if view.direction == "neutral" or view.confidence == 0:
            omitted.append(view.asset)
            continue
        bottom_up.append({
            "type": "absolute",
            "asset": view.asset,
            "expected_return": float(prior[view.asset]) + signs[view.direction] * view.magnitude * max_annual_alpha,
            "confidence": view.confidence,
            "label": view.rationale,
        })
    recipe = {
        "meta": {
            "name": "research_views_bl",
            "description": "Research strength mapped to explicit annual prior-relative alpha targets.",
        },
        "universe": {"assets": universe},
        "model_parameters": params,
        "constraints": {"long_only": True, "weight_bounds": [0.0, 1.0]},
        "bottom_up_views": bottom_up,
        "top_down_views": {"factor_shocks": []},
    }
    factors = data.metadata["factor_names"]
    exposures = np.array([data.metadata["factor_exposures"][asset] for asset in universe])
    result = run_bl_recipe(
        recipe, prices, caps, exposures, {factor: i for i, factor in enumerate(factors)},
    )
    weights = result["weights"]
    if set(weights) != set(universe) or any(
        not math.isfinite(value) or value < 0 or value > 1 for value in weights.values()
    ) or not math.isclose(sum(weights.values()), 1, abs_tol=1e-4):
        raise ValueError("BL optimizer returned invalid long-only allocation weights")
    total_cap = sum(caps.values())
    result["allocation"] = [
        {
            "ticker": asset,
            "priorWeight": round(caps[asset] / total_cap, 6),
            "blWeight": round(float(weights[asset]), 6),
        }
        for asset in universe
    ]
    result["recipe"] = recipe
    result["calibration"] = {
        "max_annual_alpha": max_annual_alpha,
        "horizon": "annualized, following the existing 252-observation covariance convention",
        "target": "market-implied prior + direction_sign * magnitude * max_annual_alpha",
        "confidence": "existing runner Omega = tau * asset_variance / confidence",
        "omitted_assets": omitted,
        "note": "Illustrative calibration, not an empirically estimated return forecast. "
                "Uses the application's existing prior/risk-free conventions unchanged. "
                "Market caps and ETF NAV proxies are static, not historical estimates.",
    }
    return result

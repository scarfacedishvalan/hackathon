"""
Black-Litterman Router

Exposes POST /bl/run — runs the full BL pipeline from the current recipe
stored in current.json and returns all data required by the three frontend
charts (EfficientFrontierChart, BLAllocationChart, TopDownContribution).
"""

from fastapi import APIRouter, HTTPException
from app.orchestrators import bl_orchestrator, view_orchestrator
from app.services.price_data.load_data import load_market_data

router = APIRouter(prefix="/bl", tags=["bl"])


@router.post("/run")
async def run_bl():
    """
    Execute the Black-Litterman optimisation from the current recipe.

    Reads ``current.json`` for the recipe (views + model_parameters), loads
    price data, runs the full BL pipeline, and returns chart-ready data.

    Response shape::

        {
          "efficientFrontier": {
            "curve": [{"vol": float, "ret": float}, ...],
            "prior":     {"vol": float, "ret": float},
            "posterior": {"vol": float, "ret": float}
          },
          "allocation": [
            {"ticker": str, "priorWeight": float, "blWeight": float}, ...
          ],
          "topDownContribution": [
            {"sector": str, "returnContribution": float, "riskContribution": float}, ...
          ],
          "portfolioStats": {
            "prior":     {"ret": float, "vol": float, "sharpe": float},
            "posterior": {"ret": float, "vol": float, "sharpe": float}
          },
          "weights":           {ticker: float, ...},
          "posterior_returns": {ticker: float, ...},
          "prior_returns":     {ticker: float, ...},
          "n_bottom_up_views": int,
          "n_top_down_views":  int
        }
    """
    # ── Load recipe ────────────────────────────────────────────────────────────
    try:
        recipe = view_orchestrator.load_recipe("current")
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="No current recipe found. Please add views first.",
        )

    # ── Load price data ────────────────────────────────────────────────────────
    try:
        price_df, _market_caps, _B, _factor_names, _all_assets = load_market_data()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load price data: {exc}",
        )

    # ── Run BL pipeline ────────────────────────────────────────────────────────
    try:
        result = bl_orchestrator.run_black_litterman(recipe, price_df)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"BL optimisation failed: {exc}",
        )

    # ── Return only what the frontend needs ───────────────────────────────────
    return {
        "efficientFrontier":   result.get("efficientFrontier"),
        "allocation":          result.get("allocation"),
        "topDownContribution": result.get("topDownContribution"),
        "portfolioStats":      result.get("portfolioStats"),
        "weights":             result.get("weights"),
        "posterior_returns":   result.get("posterior_returns"),
        "prior_returns":       result.get("prior_returns"),
        "n_bottom_up_views":   result.get("n_bottom_up_views"),
        "n_top_down_views":    result.get("n_top_down_views"),
    }

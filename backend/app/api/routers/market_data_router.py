"""
Market Data Router

Thin FastAPI router exposing the editable model-assumption subset of
``market_data.json`` (market caps, factor exposures, factor names).
Orchestration is delegated entirely to market_data_orchestrator.
"""

from fastapi import APIRouter, HTTPException
from app.orchestrators import market_data_orchestrator

router = APIRouter(prefix="/market-data", tags=["market-data"])


@router.get("/assumptions")
async def get_assumptions():
    """Return all_assets, factor_names, market_caps, and factor_exposures from market_data.json."""
    return market_data_orchestrator.get_assumptions()


@router.put("/assumptions")
async def update_assumptions(body: dict):
    """
    Update market_caps and/or factor_exposures in market_data.json.

    Accepted keys: ``market_caps`` (dict[asset, number]),
    ``factor_exposures`` (dict[asset, list[number]]). Returns the refreshed
    assumptions on success.
    """
    try:
        return market_data_orchestrator.update_assumptions(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

"""
Backtest Router

POST /backtest/parse          — NL text  → recipe JSON (via LLM)
POST /backtest/run            — recipe JSON → metrics + equity curve
GET  /backtest/theses         — list saved BL thesis names
POST /backtest/run-portfolio  — thesis-driven equal-weight portfolio backtest
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/backtest", tags=["backtest"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ParseRequest(BaseModel):
    text: str


class RunRequest(BaseModel):
    recipe: dict[str, Any]


class PortfolioRunRequest(BaseModel):
    thesis_name: str
    strategy_name: str
    strategy_params: dict[str, Any] | None = None
    start: str | None = None
    end: str | None = None
    cash: float = 10_000.0
    commission: float | str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/parse")
async def parse_strategy(body: ParseRequest) -> dict[str, Any]:
    """
    Convert a natural-language description into a validated backtest recipe.

    Request body::
        { "text": "Backtest SmaCross on AAPL daily from 2021-01-01…" }

    Response::
        {
          "strategy_name": "SmaCross",
          "timeframe": "daily",
          "data": { "symbol": "AAPL", "start": "2021-01-01", … },
          "backtest": { "cash": 10000, … },
          "strategy_params": { "fast": 20, "slow": 50 },
          "rules": { "entry": "…", "exit": "…" },
          "risk": { … },
          "optimize": { … }
        }
    """
    if not body.text or not body.text.strip():
        raise HTTPException(status_code=422, detail="text must not be empty")

    try:
        from app.orchestrators.backtest_orchestrator import parse_strategy as _parse
        recipe = _parse(body.text)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Failed to parse strategy: {exc}",
        )

    return recipe


@router.post("/run")
async def run_backtest(body: RunRequest) -> dict[str, Any]:
    """
    Execute a backtest recipe and return serialised results.

    Request body::
        { "recipe": { …BacktestingRecipe… } }

    Response::
        {
          "recipe":      { … },
          "metrics":     { returnPct, sharpeRatio, maxDrawdownPct, … },
          "equityCurve": [{ "date": "YYYY-MM-DD", "equity": float }, …],
          "trades":      [{ "entryTime": …, "exitTime": …, "pnl": … }, …]
        }
    """
    if not body.recipe:
        raise HTTPException(status_code=422, detail="recipe must not be empty")

    try:
        from app.orchestrators.backtest_orchestrator import run_recipe
        result = run_recipe(body.recipe)
    except (ValueError, NotImplementedError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Backtest execution failed: {exc}",
        )

    return result


# ---------------------------------------------------------------------------
# Portfolio backtest endpoints
# ---------------------------------------------------------------------------

@router.get("/theses")
async def list_theses() -> list[str]:
    """Return the names of all saved BL theses (stems of *.json in bl_recipes/)."""
    from pathlib import Path
    recipes_dir = Path(__file__).resolve().parents[3] / "data" / "bl_recipes"
    if not recipes_dir.exists():
        return []
    return sorted(p.stem for p in recipes_dir.glob("*.json"))


@router.post("/run-portfolio")
async def run_portfolio_backtest(body: PortfolioRunRequest) -> dict[str, Any]:
    """
    Run an equal-weight portfolio backtest driven by a saved BL thesis.

    The asset universe is taken from ``thesis.universe.assets``.
    Each asset is backtested independently with the same strategy;
    results are combined into an aggregate portfolio equity curve.

    Response shape::

        {
          "recipe":      { "thesis_name": str, "strategy_name": str,
                           "assets": [...], "weights": {...}, ... },
          "metrics":     { returnPct, sharpeRatio, maxDrawdownPct, ... },
          "equityCurve": [{ "date": "YYYY-MM-DD", "equity": float }, ...],
          "assetCurves": { "AAPL": [...], "MSFT": [...], ... },
          "weights":     { "AAPL": 0.2, ... },
          "trades":      { "AAPL": [...], "MSFT": [...], ... }
        }
    """
    try:
        from app.orchestrators.backtest_orchestrator import run_portfolio_recipe
        result = run_portfolio_recipe(
            thesis_name=body.thesis_name,
            strategy_name=body.strategy_name,
            strategy_params=body.strategy_params,
            start=body.start,
            end=body.end,
            cash=body.cash,
            commission=body.commission,
        )
    except (ValueError, NotImplementedError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Portfolio backtest failed: {exc}",
        )

    return result

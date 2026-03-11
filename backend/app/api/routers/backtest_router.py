"""
Backtest Router

POST /backtest/parse   — NL text  → recipe JSON (via LLM)
POST /backtest/run     — recipe JSON → metrics + equity curve
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

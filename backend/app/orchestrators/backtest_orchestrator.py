"""
Backtest Orchestrator

Orchestration layer for the two-step backtest pipeline:
  1. parse_strategy(text)  — LLM text → validated recipe dict
  2. run_recipe(recipe)    — recipe dict → serialised stats + equity curve
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd


# ---------------------------------------------------------------------------
# Step 1: LLM parse
# ---------------------------------------------------------------------------

def parse_strategy(text: str) -> dict[str, Any]:
    """
    Convert a natural-language backtest description into a recipe dict.

    Returns the validated recipe dict (matches BacktestingRecipe schema).
    Raises ParserError subclasses on LLM or schema failures.
    """
    from app.services.recipe_interpreter.llm_parser import parse_text_to_json
    return parse_text_to_json(text)


# ---------------------------------------------------------------------------
# Step 2: Run recipe → serialised result
# ---------------------------------------------------------------------------

def _safe_float(value: Any) -> float | None:
    """Convert a Stats value to a plain Python float, returning None for NaN/inf."""
    try:
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _serialize_stats(stats: Any) -> dict[str, Any]:
    """
    Extract the key fields from a backtesting.py Stats object and return
    a plain dict suitable for JSON serialisation.

    Handles both the normal run() result and the optimize() result
    (which is also a Stats Series).
    """
    def g(key: str) -> Any:
        try:
            return stats[key]
        except (KeyError, IndexError):
            return None

    metrics: dict[str, Any] = {
        "start":             str(g("Start"))  if g("Start")  is not None else None,
        "end":               str(g("End"))    if g("End")    is not None else None,
        "duration":          str(g("Duration")) if g("Duration") is not None else None,
        "equityFinal":       _safe_float(g("Equity Final [$]")),
        "equityPeak":        _safe_float(g("Equity Peak [$]")),
        "returnPct":         _safe_float(g("Return [%]")),
        "buyHoldReturnPct":  _safe_float(g("Buy & Hold Return [%]")),
        "annualReturnPct":   _safe_float(g("Return (Ann.) [%]")),
        "annualVolatilityPct": _safe_float(g("Volatility (Ann.) [%]")),
        "sharpeRatio":       _safe_float(g("Sharpe Ratio")),
        "sortinoRatio":      _safe_float(g("Sortino Ratio")),
        "calmarRatio":       _safe_float(g("Calmar Ratio")),
        "maxDrawdownPct":    _safe_float(g("Max. Drawdown [%]")),
        "avgDrawdownPct":    _safe_float(g("Avg. Drawdown [%]")),
        "numTrades":         _safe_int(g("# Trades")),
        "winRatePct":        _safe_float(g("Win Rate [%]")),
        "bestTradePct":      _safe_float(g("Best Trade [%]")),
        "worstTradePct":     _safe_float(g("Worst Trade [%]")),
        "avgTradePct":       _safe_float(g("Avg. Trade [%]")),
        "profitFactor":      _safe_float(g("Profit Factor")),
        "sqn":               _safe_float(g("SQN")),
    }

    equity_curve: list[dict[str, Any]] = []
    try:
        ec: pd.DataFrame = stats["_equity_curve"]
        if ec is not None and not ec.empty:
            # Resample to daily to cap payload size
            eq = ec["Equity"] if "Equity" in ec.columns else ec.iloc[:, 0]
            # Downsample: at most ~500 points
            step = max(1, len(eq) // 500)
            for ts, val in eq.iloc[::step].items():
                fval = _safe_float(val)
                if fval is not None:
                    equity_curve.append({
                        "date": ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts),
                        "equity": round(fval, 2),
                    })
    except (KeyError, TypeError, AttributeError):
        pass

    trades: list[dict[str, Any]] = []
    try:
        tdf: pd.DataFrame = stats["_trades"]
        if tdf is not None and not tdf.empty:
            for _, row in tdf.iterrows():
                trades.append({
                    "entryTime":  str(row.get("EntryTime",  "")),
                    "exitTime":   str(row.get("ExitTime",   "")),
                    "entryPrice": _safe_float(row.get("EntryPrice")),
                    "exitPrice":  _safe_float(row.get("ExitPrice")),
                    "pnl":        _safe_float(row.get("PnL")),
                    "returnPct":  _safe_float(row.get("ReturnPct")),
                    "size":       _safe_int(row.get("Size")),
                })
    except (KeyError, TypeError, AttributeError):
        pass

    return {"metrics": metrics, "equityCurve": equity_curve, "trades": trades}


def run_recipe(recipe: dict[str, Any]) -> dict[str, Any]:
    """
    Execute a backtest recipe and return serialised results.

    Returns::
        {
            "recipe":     dict,                  # the recipe that was run
            "metrics":    dict,                  # key performance figures
            "equityCurve": [{date, equity}, ...],# portfolio value over time
            "trades":     [{entryTime, ...}, ...]# individual trade log
        }

    Raises ValueError / NotImplementedError from run_from_recipe on bad recipes.
    """
    from app.services.recipe_interpreter.backtesting_from_json import run_from_recipe

    stats = run_from_recipe(recipe, plot_path=None, open_plot=False)
    serialised = _serialize_stats(stats)
    return {
        "recipe": recipe,
        **serialised,
    }

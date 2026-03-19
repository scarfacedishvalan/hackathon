"""
Backtest Orchestrator

Orchestration layer for the two-step backtest pipeline:
  1. parse_strategy(text)       — LLM text → validated recipe dict
  2. run_recipe(recipe)         — recipe dict → serialised stats + equity curve
  3. run_portfolio_recipe(...)  — thesis-driven equal-weight portfolio backtest
"""

from __future__ import annotations

import logging
import math
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


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
    
    logger.info(f"Parsing strategy from text: {text[:100]}...")
    try:
        recipe = parse_text_to_json(text)
        logger.info(f"Successfully parsed strategy: {recipe.get('strategy_name')}")
        return recipe
    except Exception as exc:
        logger.error(f"Failed to parse strategy: {exc}", exc_info=True)
        raise


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

    logger.info(f"Running single-asset backtest: {recipe.get('strategy_name')} on {recipe.get('data', {}).get('symbol')}")
    try:
        stats = run_from_recipe(recipe, plot_path=None, open_plot=False)
        serialised = _serialize_stats(stats)
        logger.info(f"Backtest completed: {serialised['metrics'].get('returnPct')}% return")
        return {
            "recipe": recipe,
            **serialised,
        }
    except Exception as exc:
        logger.error(f"Backtest failed for recipe: {exc}", exc_info=True)
        raise
        raise


# ---------------------------------------------------------------------------
# Step 3: Portfolio recipe — thesis-driven, equal-weight
# ---------------------------------------------------------------------------

def _extract_equity_series(stats: Any) -> pd.Series | None:
    """Pull the raw equity curve Series from a backtesting.py Stats object."""
    try:
        ec: pd.DataFrame = stats["_equity_curve"]
        if ec is not None and not ec.empty:
            return ec["Equity"] if "Equity" in ec.columns else ec.iloc[:, 0]
    except (KeyError, TypeError, AttributeError):
        pass
    return None


def _downsample_equity(eq: pd.Series, max_points: int = 500) -> list[dict[str, Any]]:
    """Convert a pd.Series to [{date, equity}] capped at max_points."""
    step = max(1, len(eq) // max_points)
    result = []
    for ts, val in eq.iloc[::step].items():
        fval = _safe_float(val)
        if fval is not None:
            result.append({
                "date": ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts),
                "equity": round(fval, 2),
            })
    return result


def _portfolio_metrics(
    portfolio_eq: pd.Series,
    cash: float,
    risk_free_rate: float = 0.0,
) -> dict[str, Any]:
    """
    Compute key performance metrics from a combined portfolio equity series.

    Returns the same metric keys as ``_serialize_stats`` so the frontend
    receives a uniform shape. Fields that require per-trade data are None.
    """
    if portfolio_eq.empty:
        return {}

    total_return = (portfolio_eq.iloc[-1] / portfolio_eq.iloc[0] - 1) * 100
    n_days = max((portfolio_eq.index[-1] - portfolio_eq.index[0]).days, 1)
    years = n_days / 365.25

    daily_returns = portfolio_eq.pct_change().dropna()
    ann_return = ((1 + total_return / 100) ** (1 / years) - 1) * 100 if years > 0 else 0.0
    ann_vol = float(daily_returns.std() * (252 ** 0.5) * 100) if len(daily_returns) > 1 else 0.0
    sharpe = (ann_return / 100 - risk_free_rate) / (ann_vol / 100) if ann_vol > 1e-9 else 0.0

    rolling_max = portfolio_eq.cummax()
    drawdown_pct = (portfolio_eq - rolling_max) / rolling_max * 100
    max_dd = float(drawdown_pct.min())

    return {
        "start":               str(portfolio_eq.index[0]),
        "end":                 str(portfolio_eq.index[-1]),
        "duration":            str(portfolio_eq.index[-1] - portfolio_eq.index[0]),
        "equityFinal":         round(float(portfolio_eq.iloc[-1]), 2),
        "equityPeak":          round(float(portfolio_eq.max()), 2),
        "returnPct":           round(total_return, 4),
        "annualReturnPct":     round(ann_return, 4),
        "annualVolatilityPct": round(ann_vol, 4),
        "sharpeRatio":         round(sharpe, 4),
        "maxDrawdownPct":      round(max_dd, 4),
        # Not computable at portfolio level without merged trade log
        "buyHoldReturnPct":    None,
        "sortinoRatio":        None,
        "calmarRatio":         None,
        "avgDrawdownPct":      None,
        "numTrades":           None,
        "winRatePct":          None,
        "bestTradePct":        None,
        "worstTradePct":       None,
        "avgTradePct":         None,
        "profitFactor":        None,
        "sqn":                 None,
    }


def run_portfolio_recipe(
    thesis_name: str,
    strategy_name: str,
    *,
    strategy_params: dict[str, Any] | None = None,
    start: str | None = None,
    end: str | None = None,
    cash: float = 10_000.0,
    commission: float | str | None = None,
) -> dict[str, Any]:
    """
    Run an equal-weight portfolio backtest for all assets in a saved BL thesis.

    Each asset is backtested independently using the same strategy and an
    equal share of ``cash``.  The portfolio equity curve is the weighted sum
    of normalised per-asset curves rescaled to total cash.

    Parameters
    ----------
    thesis_name : str
        Stem of a saved BL recipe in ``data/bl_recipes/``
        (e.g. ``"current"`` or ``"alpha_tilt"``).
    strategy_name : str
        One of ``BuyAndHold``, ``SmaCross``, ``EmaCross``, ``RsiReversion``.
    strategy_params : dict, optional
        Strategy class-variable overrides (e.g. ``{"fast": 10, "slow": 30}``).
    start, end : str, optional
        ISO date strings to filter the backtest window.
    cash : float
        Total portfolio cash, split equally across all assets.
    commission : float or str, optional
        Per-trade commission, e.g. ``0.002`` or ``"0.2%"``.

    Returns
    -------
    dict with keys:
        ``recipe``, ``metrics``, ``equityCurve``,
        ``assetCurves``, ``weights``, ``trades``
    """
    from backtesting import Backtest

    from app.orchestrators.view_orchestrator import load_recipe
    from app.services.price_data.load_data import load_market_data
    from app.services.recipe_interpreter.backtesting_from_json import (
        _STRATEGY_MAP,
        _apply_strategy_params,
        _coerce_ohlc,
        _parse_date,
        _parse_percent_or_number,
    )

    # 1. Load thesis → universe
    logger.info(f"Starting portfolio backtest: thesis={thesis_name}, strategy={strategy_name}, cash={cash}")
    
    try:
        thesis = load_recipe(thesis_name)
        logger.info(f"Loaded thesis '{thesis_name}'")
    except Exception as exc:
        logger.error(f"Failed to load thesis '{thesis_name}': {exc}", exc_info=True)
        raise ValueError(f"Thesis '{thesis_name}' not found: {exc}")
    
    if "universe" not in thesis or "assets" not in thesis["universe"]:
        logger.error(f"Thesis '{thesis_name}' missing universe.assets field")
        raise ValueError(
            f"Thesis '{thesis_name}' does not contain universe.assets. "
            "Re-save the thesis from the BL tab."
        )
    assets: list[str] = thesis["universe"]["assets"]
    if not assets:
        logger.error(f"Thesis '{thesis_name}' has empty asset list")
        raise ValueError(f"Thesis '{thesis_name}' has an empty asset universe.")
    
    logger.info(f"Asset universe: {assets}")

    n = len(assets)
    weight = 1.0 / n
    weights: dict[str, float] = {a: weight for a in assets}

    # 2. Validate strategy before loading price data
    if strategy_name not in _STRATEGY_MAP:
        raise NotImplementedError(
            f"Strategy {strategy_name!r} is not implemented. "
            f"Available: {sorted(_STRATEGY_MAP)}"
        )

    # 3. Load all price data from DB once
    logger.info("Loading market data from database...")
    try:
        price_df, *_ = load_market_data()
        logger.info(f"Loaded price data: {len(price_df)} rows, {len(price_df.columns)} columns")
    except Exception as exc:
        logger.error(f"Failed to load market data: {exc}", exc_info=True)
        raise ValueError(f"Market data loading failed: {exc}")
    
    missing = [a for a in assets if a not in price_df.columns]
    if missing:
        logger.error(f"Missing assets in database: {missing}. Available: {sorted(price_df.columns.tolist())}")
        raise ValueError(
            f"Assets from thesis '{thesis_name}' not found in the database: {missing}. "
            f"Available: {sorted(price_df.columns.tolist())}"
        )

    # 4. Prepare shared backtest kwargs
    per_asset_cash = cash * weight
    bt_kwargs: dict[str, Any] = {"cash": per_asset_cash}
    parsed_commission = _parse_percent_or_number(commission)
    if parsed_commission is not None:
        bt_kwargs["commission"] = parsed_commission

    start_ts = _parse_date(start)
    end_ts = _parse_date(end)

    # Apply strategy params once (mutates class vars — same as single-asset path)
    strategy_cls = _apply_strategy_params(_STRATEGY_MAP[strategy_name], strategy_params)

    # 5. Per-asset backtest loop
    logger.info(f"Starting backtests for {n} assets with {strategy_name}")
    raw_stats: dict[str, Any] = {}
    for idx, asset in enumerate(assets, 1):
        try:
            logger.info(f"  [{idx}/{n}] Running {asset}...")
            col = price_df[[asset]].rename(columns={asset: "Close"})
            if start_ts is not None:
                col = col.loc[col.index >= start_ts]
            if end_ts is not None:
                col = col.loc[col.index <= end_ts]
            df = _coerce_ohlc(col)
            logger.debug(f"  [{asset}] Data shape: {df.shape}, date range: {df.index[0]} to {df.index[-1]}")
            bt = Backtest(df, strategy_cls, finalize_trades=True, **bt_kwargs)
            raw_stats[asset] = bt.run()
            logger.info(f"  [{asset}] Completed — {raw_stats[asset]['# Trades']} trades, "
                       f"{raw_stats[asset].get('Return [%]', 0):.2f}% return")
        except Exception as exc:
            logger.error(f"  [{asset}] Backtest failed: {exc}", exc_info=True)
            raise ValueError(f"Backtest failed for {asset}: {exc}")

    # 6. Serialise per-asset results
    asset_curves: dict[str, list[dict[str, Any]]] = {}
    asset_trades: dict[str, list[dict[str, Any]]] = {}
    equity_series: dict[str, pd.Series] = {}

    for asset, stats in raw_stats.items():
        serialised = _serialize_stats(stats)
        asset_curves[asset] = serialised["equityCurve"]
        asset_trades[asset] = serialised["trades"]
        eq = _extract_equity_series(stats)
        if eq is not None:
            equity_series[asset] = eq

    # 7. Combine into portfolio equity curve
    logger.info("Combining asset backtests into portfolio equity curve...")
    portfolio_equity: pd.Series | None = None
    if equity_series:
        try:
            # Align on a common DatetimeIndex; forward/back fill small edge gaps
            combined = pd.DataFrame(equity_series).sort_index()
            combined = combined.ffill().bfill()
            logger.debug(f"Combined equity series shape: {combined.shape}")
            # Rebase each asset to 1.0 at start, apply equal weight, scale to cash
            normalised = combined.div(combined.iloc[0])
            portfolio_norm = normalised.mul(weight).sum(axis=1)
            portfolio_equity = portfolio_norm * cash
            logger.info(f"Portfolio equity curve created: {len(portfolio_equity)} points")
        except Exception as exc:
            logger.error(f"Failed to combine equity curves: {exc}", exc_info=True)
            raise ValueError(f"Portfolio aggregation failed: {exc}")

    # 8. Portfolio-level metrics
    logger.info("Computing portfolio-level metrics...")
    metrics = _portfolio_metrics(portfolio_equity, cash) if portfolio_equity is not None else {}
    equity_curve = _downsample_equity(portfolio_equity) if portfolio_equity is not None else []
    
    logger.info(f"Portfolio backtest complete: {metrics.get('returnPct', 0):.2f}% return, "
               f"{metrics.get('sharpeRatio', 0):.2f} Sharpe, {metrics.get('maxDrawdownPct', 0):.2f}% max DD")

    return {
        "recipe": {
            "thesis_name":    thesis_name,
            "strategy_name":  strategy_name,
            "strategy_params": strategy_params,
            "assets":         assets,
            "weights":        weights,
            "start":          start,
            "end":            end,
            "cash":           cash,
            "commission":     commission,
        },
        "metrics":     metrics,
        "equityCurve": equity_curve,
        "assetCurves": asset_curves,
        "weights":     weights,
        "trades":      asset_trades,
    }

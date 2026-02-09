"""Run Backtesting.py strategies from a semantic JSON recipe.

This script is meant to be the execution layer for JSON produced by the
recipe-interpreter prompts (Backtesting.py target).

Usage:
  python backtesting_from_json.py prompts/backtesting_example_expected_output.json
  python backtesting_from_json.py recipe.json --plot

Notes:
- Requires: backtesting, pandas
- Optional: yfinance (only needed if recipe specifies a symbol without a path)
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping

import pandas as pd

try:
    from backtesting import Backtest, Strategy
    from backtesting.lib import crossover
except Exception as exc:  # pragma: no cover
    raise SystemExit(
        "Missing dependency: backtesting. Install with `pip install backtesting`."
    ) from exc


def _parse_date(value: Any) -> pd.Timestamp | None:
    if value is None:
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return pd.Timestamp(value)
    if isinstance(value, str):
        # Keep it permissive; pandas handles many formats.
        return pd.to_datetime(value)
    raise TypeError(f"Unsupported date value: {value!r}")


def _parse_percent_or_number(value: Any) -> float | None:
    """Convert either numeric or strings like '0.1%' to a float fraction.

    Returns a float for backtesting params (commission, stops, etc.).
    """

    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        if s.endswith("%"):
            num = float(s[:-1].strip())
            return num / 100.0
        return float(s)

    raise TypeError(f"Unsupported numeric value: {value!r}")


def _coerce_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure df has Backtesting.py OHLCV columns with correct capitalization."""

    if df.empty:
        raise ValueError("DataFrame is empty")

    # Normalize column names.
    cols = {c: c.strip() for c in df.columns}
    df = df.rename(columns=cols)

    # If both 'Close' and 'Adj Close' are present, prefer 'Close' and drop 'Adj Close'
    # to avoid duplicate columns that can break stats computations.
    if "Close" in df.columns and ("Adj Close" in df.columns or "Adj_Close" in df.columns or "AdjClose" in df.columns):
        for adj in ("Adj Close", "Adj_Close", "AdjClose"):
            if adj in df.columns:
                df = df.drop(columns=[adj])

    # Common variants
    mapping = {
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        # Only map adjusted close to Close if Close is absent (handled below).
        "volume": "Volume",
    }

    for c in list(df.columns):
        key = c.lower()
        if key in mapping and c != mapping[key]:
            df = df.rename(columns={c: mapping[key]})

    # If Close is still missing but adjusted close exists, use it.
    if "Close" not in df.columns:
        for adj in ("Adj Close", "Adj_Close", "AdjClose", "adj close", "adj_close"):
            if adj in df.columns:
                df = df.rename(columns={adj: "Close"})
                break

    # If only Close exists, synthesize others.
    if "Close" in df.columns and not {"Open", "High", "Low"}.issubset(df.columns):
        df = df.copy()
        if "Open" not in df.columns:
            df["Open"] = df["Close"]
        if "High" not in df.columns:
            df["High"] = df["Close"]
        if "Low" not in df.columns:
            df["Low"] = df["Close"]

    required = ["Open", "High", "Low", "Close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required OHLC columns: {missing}")

    # Backtesting.py requires a DatetimeIndex.
    if not isinstance(df.index, pd.DatetimeIndex):
        if "Date" in df.columns:
            df = df.set_index("Date")
        else:
            raise ValueError("Data must have a DatetimeIndex or a 'Date' column")

    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    return df


def _load_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Try common date columns
    for date_col in ("Date", "date", "Datetime", "datetime", "Time", "time"):
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col])
            df = df.rename(columns={date_col: "Date"})
            break
    return df


def _load_data(recipe: Mapping[str, Any]) -> pd.DataFrame:
    data = recipe.get("data") or {}

    path = data.get("path")
    symbol = data.get("symbol")
    source = data.get("source")

    start = _parse_date(data.get("start"))
    end = _parse_date(data.get("end"))

    if path:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Data path does not exist: {p}")
        if p.suffix.lower() in (".csv",):
            df = _load_csv(p)
        elif p.suffix.lower() in (".parquet", ".pq"):
            df = pd.read_parquet(p)
        else:
            raise ValueError(f"Unsupported data file type: {p.suffix}")
        df = _coerce_ohlc(df)
    else:
        if not symbol:
            raise ValueError("Recipe must provide data.path or data.symbol")

        # If the recipe doesn't explicitly state a source, we attempt yfinance.
        if source not in (None, "yfinance"):
            raise ValueError(
                f"Unsupported data.source {source!r} without a path. "
                "Provide data.path or set data.source to 'yfinance'."
            )

        try:
            import yfinance as yf  # type: ignore
        except Exception as exc:
            raise SystemExit(
                "Recipe specifies a symbol but no data.path; install yfinance (pip install yfinance) "
                "or provide a CSV/Parquet path in recipe.data.path."
            ) from exc

        interval = _map_timeframe_to_yf_interval(recipe.get("timeframe"))
        df = yf.download(
            symbol,
            start=None if start is None else start.to_pydatetime(),
            end=None if end is None else end.to_pydatetime(),
            interval=interval,
            auto_adjust=False,
            progress=False,
        )
        # yfinance uses capitalized OHLC already.
        if isinstance(df.columns, pd.MultiIndex):
            # Sometimes yfinance returns multi-index for multiple tickers.
            df = df.xs(symbol, axis=1, level=-1, drop_level=True)
        df = _coerce_ohlc(df)

    if start is not None:
        df = df.loc[df.index >= start]
    if end is not None:
        df = df.loc[df.index <= end]

    return df


def _map_timeframe_to_yf_interval(timeframe: Any) -> str:
    if timeframe is None:
        return "1d"
    if not isinstance(timeframe, str):
        return "1d"

    tf = timeframe.strip().lower()
    mapping = {
        "daily": "1d",
        "day": "1d",
        "1d": "1d",
        "weekly": "1wk",
        "1w": "1wk",
        "monthly": "1mo",
        "1mo": "1mo",
        "hourly": "1h",
        "1h": "1h",
        "30m": "30m",
        "15m": "15m",
        "5m": "5m",
        "1m": "1m",
    }
    return mapping.get(tf, "1d")


def SMA(series: pd.Series, n: int) -> pd.Series:
    # Backtesting.py passes its own internal array type (not a pandas Series).
    # Convert to a pandas Series for rolling-window computation, and return a
    # NumPy array (the format Backtesting.py indicators expect).
    s = pd.Series(series)
    return s.rolling(int(n)).mean().to_numpy()


class BuyAndHold(Strategy):
    def next(self) -> None:
        if not self.position:
            self.buy()


class SmaCross(Strategy):
    fast: int = 10
    slow: int = 30

    def init(self) -> None:
        self.ma_fast = self.I(SMA, self.data.Close, self.fast)
        self.ma_slow = self.I(SMA, self.data.Close, self.slow)

    def next(self) -> None:
        if crossover(self.ma_fast, self.ma_slow):
            self.buy()
        elif crossover(self.ma_slow, self.ma_fast):
            self.position.close()


_STRATEGY_MAP: dict[str, type[Strategy]] = {
    "BuyAndHold": BuyAndHold,
    "SmaCross": SmaCross,
}


def _apply_strategy_params(strategy_cls: type[Strategy], params: Mapping[str, Any] | None) -> type[Strategy]:
    if not params:
        return strategy_cls

    # Backtesting.py uses class variables as parameters.
    for k, v in params.items():
        if not hasattr(strategy_cls, k):
            # Keep it strict: parameter must exist on class.
            raise ValueError(f"Strategy {strategy_cls.__name__} has no parameter {k!r}")
        setattr(strategy_cls, k, v)

    return strategy_cls


def _parse_constraint(expr: str) -> Callable[..., bool]:
    """Parse a tiny subset of constraints like 'fast < slow'.

    The returned function is suitable for Backtest.optimize(constraint=...).
    """

    # Very small safe grammar: <param> <op> <param|number>
    m = re.fullmatch(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*(<=|>=|<|>|==)\s*([A-Za-z_][A-Za-z0-9_]*|\d+(?:\.\d+)?)\s*", expr)
    if not m:
        raise ValueError(f"Unsupported constraint expression: {expr!r}")

    left, op, right = m.group(1), m.group(2), m.group(3)

    def _get_value(kwargs: Mapping[str, Any], token: str) -> float:
        if token in kwargs:
            return float(kwargs[token])
        return float(token)

    def _constraint(**kwargs: Any) -> bool:
        a = _get_value(kwargs, left)
        b = _get_value(kwargs, right)
        if op == "<":
            return a < b
        if op == "<=":
            return a <= b
        if op == ">":
            return a > b
        if op == ">=":
            return a >= b
        return a == b

    return _constraint


def _maximize_metric_name(metric: Any) -> str | Callable[[pd.Series], float] | None:
    if metric is None:
        return None
    if not isinstance(metric, str):
        return str(metric)

    m = metric.strip().lower()
    # Backtesting.py stats keys are title cased (e.g., 'Sharpe Ratio')
    aliases = {
        "sharpe": "Sharpe Ratio",
        "sharpe ratio": "Sharpe Ratio",
        "sortino": "Sortino Ratio",
        "sortino ratio": "Sortino Ratio",
        "return": "Return [%]",
        "return %": "Return [%]",
        "return [%]": "Return [%]",
    }
    return aliases.get(m, metric)


@dataclass(frozen=True)
class BacktestConfig:
    cash: float | None
    commission: float | None
    margin: float | None
    trade_on_close: bool | None
    hedging: bool | None
    exclusive_orders: bool | None


def _parse_backtest_config(recipe: Mapping[str, Any]) -> BacktestConfig:
    bt_cfg = recipe.get("backtest") or {}
    return BacktestConfig(
        cash=None if bt_cfg.get("cash") is None else float(bt_cfg.get("cash")),
        commission=_parse_percent_or_number(bt_cfg.get("commission")),
        margin=None if bt_cfg.get("margin") is None else float(bt_cfg.get("margin")),
        trade_on_close=bt_cfg.get("trade_on_close"),
        hedging=bt_cfg.get("hedging"),
        exclusive_orders=bt_cfg.get("exclusive_orders"),
    )


def run_from_recipe(
    recipe: Mapping[str, Any],
    *,
    plot_path: Path | None = None,
    open_plot: bool = False,
) -> Any:
    df = _load_data(recipe)

    strategy_name = recipe.get("strategy_name")
    if strategy_name is None:
        raise ValueError("recipe.strategy_name is required to run a backtest")

    if strategy_name not in _STRATEGY_MAP:
        raise NotImplementedError(
            f"Strategy {strategy_name!r} is not implemented in this runner. "
            f"Available: {sorted(_STRATEGY_MAP)}"
        )

    strategy_cls = _STRATEGY_MAP[strategy_name]
    strategy_cls = _apply_strategy_params(strategy_cls, recipe.get("strategy_params"))

    bt_config = _parse_backtest_config(recipe)

    kwargs: dict[str, Any] = {}
    if bt_config.cash is not None:
        kwargs["cash"] = bt_config.cash
    if bt_config.commission is not None:
        kwargs["commission"] = bt_config.commission
    if bt_config.margin is not None:
        kwargs["margin"] = bt_config.margin
    if bt_config.trade_on_close is not None:
        kwargs["trade_on_close"] = bool(bt_config.trade_on_close)
    if bt_config.hedging is not None:
        kwargs["hedging"] = bool(bt_config.hedging)
    if bt_config.exclusive_orders is not None:
        kwargs["exclusive_orders"] = bool(bt_config.exclusive_orders)

    bt = Backtest(df, strategy_cls, finalize_trades=True, **kwargs)

    optimize = recipe.get("optimize") or {}
    opt_params = optimize.get("params")

    if opt_params:
        maximize_name = _maximize_metric_name(optimize.get("metric"))
        constraint_expr = optimize.get("constraint")
        constraint_fn = None
        if isinstance(constraint_expr, str) and constraint_expr.strip():
            constraint_fn = _parse_constraint(constraint_expr)

        stats = bt.optimize(
            maximize=maximize_name,
            constraint=constraint_fn,
            return_heatmap=False,
            **opt_params,
        )
    else:
        stats = bt.run()

    print(stats)

    if plot_path is not None:
        bt.plot(filename=str(plot_path), open_browser=bool(open_plot))

    return stats


if __name__ == "__main__":
    recipe_path = r"C:\Python\recipe-interpreter\prompts\backtesting_example_expected_output.json"

    with open(recipe_path, "r") as f:
        recipe = json.load(f)

    plot_path = None

    run_from_recipe(recipe, plot_path=plot_path, open_plot=False)
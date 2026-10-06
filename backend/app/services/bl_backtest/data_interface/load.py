"""Load and check the repository's existing evidence, without filling data."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from app.orchestrators.market_data_orchestrator import load_market_data_raw

DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "mock_timeseries"
ROUNDING_RTOL = 1e-6
ROUNDING_ATOL = 1e-7


@dataclass(frozen=True)
class ResearchData:
    eps: pd.DataFrame
    rates: pd.DataFrame
    prices: pd.DataFrame
    returns: pd.DataFrame
    metadata: dict


def check_close(actual, expected, label: str) -> None:
    if not np.allclose(
        actual, expected, rtol=ROUNDING_RTOL, atol=ROUNDING_ATOL, equal_nan=True
    ):
        raise ValueError(f"{label}: inconsistent values beyond CSV rounding tolerance")


def validate_prices(prices: pd.DataFrame) -> None:
    if prices.empty or not isinstance(prices.index, pd.DatetimeIndex):
        raise ValueError("prices require a nonempty DatetimeIndex")
    if prices.index.tz is not None or not prices.index.equals(prices.index.normalize()):
        raise ValueError("prices require timezone-naive daily observation dates")
    if prices.index.has_duplicates or prices.index.hasnans:
        raise ValueError("prices have duplicate/invalid dates")
    if not prices.index.is_monotonic_increasing:
        raise ValueError("prices must be sorted by observation date")
    if prices.columns.has_duplicates:
        raise ValueError("prices have duplicate asset columns")
    if not np.isfinite(prices.to_numpy(dtype=float)).all() or (prices <= 0).any().any():
        raise ValueError("prices must be finite and strictly positive")


def _read(directory: Path, name: str, required: list[str], *, long: bool = False):
    frame = pd.read_csv(directory / name)
    if not set(required) <= set(frame.columns):
        raise ValueError(f"{name}: missing columns {sorted(set(required) - set(frame.columns))}")
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    if frame.empty or frame["date"].isna().any():
        raise ValueError(f"{name}: empty data or invalid dates")
    if frame["date"].dt.tz is not None or not frame["date"].equals(frame["date"].dt.normalize()):
        raise ValueError(f"{name}: expected timezone-naive daily observation dates")
    keys = ["date", "ticker"] if long else ["date"]
    if frame.duplicated(keys).any():
        raise ValueError(f"{name}: duplicate observations")
    return frame.sort_values(keys).reset_index(drop=True)


def load_research_data(directory: Path = DATA_DIR, *, metadata: dict | None = None) -> ResearchData:
    metadata = load_market_data_raw() if metadata is None else metadata
    assets = metadata["all_assets"]
    prices = _read(directory, "market_prices.csv", ["date", *assets]).set_index("date")[assets]
    returns = _read(directory, "market_returns.csv", ["date", *assets]).set_index("date")[assets]
    validate_prices(prices)
    if not returns.index.equals(prices.index[1:]):
        raise ValueError("market_returns.csv: dates must match successive price observations")
    if not np.isfinite(returns.to_numpy(dtype=float)).all():
        raise ValueError("market_returns.csv: non-finite values")
    check_close(returns.to_numpy(), prices.pct_change(fill_method=None).iloc[1:].to_numpy(), "returns")

    rates = _read(directory, "rates_10y.csv", ["date", "yield_10y_pct", "change_bp"])
    eps = _read(
        directory, "eps_estimates_revisions.csv",
        ["date", "ticker", "eps_applicable", "eps_estimate_usd", "revision_usd", "revision_pct"],
        long=True,
    )
    if not pd.DatetimeIndex(rates["date"]).equals(prices.index):
        raise ValueError("rates_10y.csv: observation dates do not match prices")
    if set(eps["ticker"]) != set(assets):
        raise ValueError("EPS universe does not match registry")
    if not np.isfinite(rates["yield_10y_pct"]).all():
        raise ValueError("rates_10y.csv: invalid yields")
    check_close(rates["change_bp"], rates["yield_10y_pct"].diff() * 100, "rate changes")
    if eps["eps_applicable"].dtype != bool:
        raise ValueError("eps_applicable must contain booleans")
    for asset, group in eps.groupby("ticker"):
        if not pd.DatetimeIndex(group["date"]).equals(prices.index):
            raise ValueError(f"{asset}: EPS observation dates do not match prices")
        expected_applicable = metadata["asset_metadata"][asset]["asset_class"] == "Equity"
        if not (group["eps_applicable"] == expected_applicable).all():
            raise ValueError(f"{asset}: inconsistent EPS applicability")
        numeric = group[["eps_estimate_usd", "revision_usd", "revision_pct"]]
        if not expected_applicable:
            if not numeric.isna().all().all():
                raise ValueError(f"{asset}: non-applicable EPS must be empty")
            continue
        levels = group["eps_estimate_usd"]
        if not np.isfinite(levels).all() or (levels <= 0).any():
            raise ValueError(f"{asset}: invalid EPS estimates")
        check_close(group["revision_usd"], levels.diff(), f"{asset} EPS revisions")
        check_close(
            group["revision_pct"], levels.pct_change(fill_method=None), f"{asset} EPS fractional revisions"
        )
    return ResearchData(eps, rates, prices, returns, metadata)

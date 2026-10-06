"""Select a reproducible observation cutoff and security universe."""

from datetime import date

import pandas as pd

from app.services.bl_backtest.data_interface.load import ResearchData, validate_prices, check_close
from app.services.bl_backtest.schema import ResearchRequest


def rebalance_date(as_of: pd.Timestamp) -> date:
    timestamp = pd.Timestamp(as_of)
    if pd.isna(timestamp) or timestamp.tzinfo is not None:
        raise ValueError("as_of requires a valid timezone-naive rebalance timestamp")
    return timestamp.date()


def select_prices(
    data: ResearchData, request: ResearchRequest, price_window: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, date]:
    unknown = set(request.universe) - set(data.metadata["all_assets"])
    if unknown:
        raise ValueError(f"unknown assets: {sorted(unknown)}")
    cutoff = request.as_of or data.prices.index[-1].date()
    if not data.prices.index[0].date() <= cutoff <= data.prices.index[-1].date():
        raise ValueError("as_of is outside evidence coverage")
    if price_window is None:
        selected = data.prices.loc[:str(cutoff), request.universe].copy()
    else:
        validate_prices(price_window)
        if set(price_window.columns) != set(request.universe):
            raise ValueError("price_window must contain exactly the selected universe")
        if price_window.index[-1].date() > cutoff:
            raise ValueError("price_window contains observations after as_of")
        selected = price_window.loc[:, request.universe].copy()
        expected = data.prices.loc[:str(cutoff), request.universe]
        dates = expected.index[expected.index >= selected.index[0]]
        if not selected.index.equals(dates):
            raise ValueError("price_window must be a contiguous observed window through as_of")
        check_close(selected.to_numpy(), expected.loc[dates].to_numpy(), "price_window vs source")
    return selected, selected.index[-1].date()

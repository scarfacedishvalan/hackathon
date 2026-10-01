"""
Market Data Orchestrator

Single canonical loader/writer for ``backend/data/market_data.json`` — the
source-of-truth registry for the asset universe, market caps, and factor
exposures used across the Black-Litterman pipeline.

Every other module that needs this data should read it through
``load_market_data_raw()`` (or the narrower ``get_assumptions()``) instead
of opening the file directly, so a write here (e.g. from the "Model
Assumptions" UI tab) is immediately visible everywhere without a process
restart.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

_MARKET_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "market_data.json"

# Trailing-window lengths (calendar days) accepted by get_correlation_matrix's `horizon` arg.
HORIZON_DAYS: Dict[str, Optional[int]] = {
    "3m": 90,
    "6m": 182,
    "1y": 365,
    "3y": 365 * 3,
    "5y": 365 * 5,
    "all": None,
}


def load_market_data_raw() -> Dict[str, Any]:
    """Return the full market_data.json contents, read fresh from disk every call."""
    with open(_MARKET_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_assumptions() -> Dict[str, Any]:
    """Return the editable model-assumption subset: assets, factor names, caps, exposures."""
    data = load_market_data_raw()
    return {
        "all_assets": data.get("all_assets", []),
        "factor_names": data.get("factor_names", []),
        "market_caps": data.get("market_caps", {}),
        "factor_exposures": data.get("factor_exposures", {}),
    }


def update_assumptions(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge partial ``market_caps`` / ``factor_exposures`` updates into
    market_data.json and persist atomically.

    Args:
        payload: Optional ``market_caps`` (dict[asset, number]) and/or
            ``factor_exposures`` (dict[asset, list[number]]) keys. Only
            assets already present in ``all_assets`` may be updated.

    Returns:
        The refreshed assumptions, equivalent to calling ``get_assumptions()``.

    Raises:
        ValueError: if an asset key is unknown or a value fails validation.
    """
    data = load_market_data_raw()
    all_assets = data.get("all_assets", [])
    factor_names = data.get("factor_names", [])

    market_caps = payload.get("market_caps")
    if market_caps is not None:
        if not isinstance(market_caps, dict):
            raise ValueError("market_caps must be an object mapping asset -> number")
        for asset, value in market_caps.items():
            if asset not in all_assets:
                raise ValueError(f"Unknown asset '{asset}' — not in all_assets")
            try:
                value = float(value)
            except (TypeError, ValueError):
                raise ValueError(f"market_caps['{asset}'] must be a number")
            if value <= 0:
                raise ValueError(f"market_caps['{asset}'] must be positive")
            data["market_caps"][asset] = value

    factor_exposures = payload.get("factor_exposures")
    if factor_exposures is not None:
        if not isinstance(factor_exposures, dict):
            raise ValueError("factor_exposures must be an object mapping asset -> list of numbers")
        n_factors = len(factor_names)
        for asset, row in factor_exposures.items():
            if asset not in all_assets:
                raise ValueError(f"Unknown asset '{asset}' — not in all_assets")
            if not isinstance(row, list) or len(row) != n_factors:
                raise ValueError(f"factor_exposures['{asset}'] must be a list of {n_factors} numbers")
            try:
                row = [float(v) for v in row]
            except (TypeError, ValueError):
                raise ValueError(f"factor_exposures['{asset}'] must contain only numbers")
            data["factor_exposures"][asset] = row

    _write_atomic(data)
    return get_assumptions()


def _write_atomic(data: Dict[str, Any]) -> None:
    """Write *data* to market_data.json via a temp file + os.replace to avoid partial writes."""
    tmp_path = _MARKET_DATA_PATH.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, _MARKET_DATA_PATH)


def refresh_market_caps() -> Dict[str, Any]:
    """
    Stub for refreshing market caps from a live source (e.g. a market data API)
    and persisting them to market_data.json. Not implemented yet — currently a
    no-op that returns the assumptions unchanged.
    """
    return get_assumptions()


def get_correlation_matrix(frequency: int = 252, horizon: str = "all") -> Dict[str, Any]:
    """
    Compute the annualized asset correlation matrix and per-asset annualized
    volatility from real price history, restricted to a trailing window.

    Note: the correlation matrix itself is mathematically invariant to
    ``frequency`` (it cancels out of the covariance-to-correlation
    normalisation) — only ``annualized_volatility`` changes with it.
    ``horizon`` *does* change the correlation matrix, since it changes which
    return observations are included in the sample.

    Args:
        frequency: Periods per year used to annualize (252 daily, 52 weekly, 12 monthly).
        horizon: Trailing window key — one of ``HORIZON_DAYS`` ("3m", "6m",
            "1y", "3y", "5y", "all").

    Returns:
        ``{"assets": [...], "frequency": int, "horizon": str, "correlation": [[...]], "annualized_volatility": {asset: float}}``
    """
    if frequency <= 0:
        raise ValueError("frequency must be positive")
    if horizon not in HORIZON_DAYS:
        raise ValueError(f"horizon must be one of {sorted(HORIZON_DAYS)}, got '{horizon}'")

    # Imported lazily: load_data.py imports this module, so a top-level
    # import here would create a circular import.
    import pandas as pd
    from app.services.price_data.load_data import load_market_data
    from app.services.bl_engine.bl_standalone import sample_cov

    price_df, *_ = load_market_data()

    days = HORIZON_DAYS[horizon]
    if days is not None:
        cutoff = price_df.index.max() - pd.Timedelta(days=days)
        price_df = price_df[price_df.index >= cutoff]

    if len(price_df.pct_change().dropna()) < 2:
        raise ValueError(f"Not enough price history for horizon '{horizon}' to compute covariance")

    cov = sample_cov(price_df, frequency)
    assets = cov.columns.tolist()
    std = np.sqrt(np.diag(cov.values))
    corr = cov.values / np.outer(std, std)
    np.fill_diagonal(corr, 1.0)

    return {
        "assets": assets,
        "frequency": frequency,
        "horizon": horizon,
        "correlation": corr.tolist(),
        "annualized_volatility": dict(zip(assets, std.tolist())),
    }

"""Calculate bounded evidence summaries; the LLM performs no arithmetic."""

import pandas as pd

from app.services.bl_backtest.data_interface.load import ResearchData, check_close
from app.services.bl_backtest.data_interface.query import select_prices
from app.services.bl_backtest.schema import Evidence, ResearchContext, ResearchRequest

LOOKBACKS = (21, 63)
LIMITATIONS = [
    "EPS estimates and 10Y yields are synthetic; prices are exported historical observations.",
    "Observation-date filtering is not publication-time certification. Static metadata is not point-in-time.",
    "Research magnitude is dimensionless strength, not an expected return or a BL input.",
]


def prepare_context(
    data: ResearchData, request: ResearchRequest, price_window: pd.DataFrame | None = None,
) -> ResearchContext:
    prices, observed = select_prices(data, request, price_window)
    eps = data.eps[data.eps["date"].dt.date <= observed]
    rates = data.rates[data.rates["date"].dt.date <= observed].set_index("date")
    evidence: dict[str, Evidence] = {}
    warnings = list(LIMITATIONS)

    def add(
        key: str, series: pd.Series, asset: str | None, source: str,
        columns: list[str], unit: str, synthetic: bool,
        window: int | None = None, applicable: bool = True, rate: bool = False,
    ) -> None:
        count = 1 if window is None else window + 1
        selected = series.iloc[-count:]
        status = "available"
        value = None
        if not applicable:
            status = "not_applicable"
        elif len(selected) < count:
            status = "insufficient_history"
            warnings.append(f"{key}: needs {count} observations; has {len(selected)}")
        elif window is None:
            value = float(selected.iloc[-1])
        elif rate:
            value = float((selected.iloc[-1] - selected.iloc[0]) * 100)
        else:
            value = float(selected.iloc[-1] / selected.iloc[0] - 1)
        evidence[key] = Evidence(
            asset=asset, metric=key.split(".", 1)[1], value=value, unit=unit,
            status=status, source=source, columns=columns,
            start=selected.index[0].date(), end=selected.index[-1].date(),
            observations=len(selected), synthetic=synthetic,
        )

    for asset in request.universe:
        group = eps[eps["ticker"] == asset].set_index("date")
        applicable = bool(group["eps_applicable"].iloc[-1])
        add(f"{asset}.eps_latest", group["eps_estimate_usd"], asset,
            "eps_estimates_revisions.csv", ["eps_estimate_usd"], "USD", True, applicable=applicable)
        add(f"{asset}.price_latest", prices[asset], asset,
            "market_prices.csv", [asset], "USD", False)
        for window in LOOKBACKS:
            add(f"{asset}.eps_change_{window}", group["eps_estimate_usd"], asset,
                "eps_estimates_revisions.csv", ["eps_estimate_usd"], "fraction", True,
                window, applicable)
            add(f"{asset}.return_{window}", prices[asset], asset,
                "market_prices.csv + market_returns.csv", [asset], "fraction", False, window)
            entry = evidence[f"{asset}.return_{window}"]
            if entry.status == "available":
                daily = data.returns.loc[prices.index[-window:], asset]
                check_close(float((1 + daily).prod() - 1), entry.value, f"{asset} return {window}")
    add("macro.yield_10y_latest", rates["yield_10y_pct"], None,
        "rates_10y.csv", ["yield_10y_pct"], "percent", True)
    for window in LOOKBACKS:
        add(f"macro.yield_10y_change_{window}", rates["yield_10y_pct"], None,
            "rates_10y.csv", ["yield_10y_pct"], "basis_points", True, window, rate=True)
    metadata = {
        asset: {
            **data.metadata["asset_metadata"][asset],
            "sector": data.metadata["sector_map"][asset],
        }
        for asset in request.universe
    }
    return ResearchContext(
        request=request, observation_date=observed, metadata=metadata,
        evidence=evidence, warnings=warnings,
    )

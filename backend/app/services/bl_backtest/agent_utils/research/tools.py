"""Plain Python research tools; no LangChain binding or model execution."""

from collections.abc import Callable
from typing import Literal

from app.services.bl_backtest.data_interface.process import LOOKBACKS, summarize_evidence_values
from app.services.bl_backtest.schema import Evidence, ResearchContext

Signal = Literal["eps", "returns", "rates"]
SIGNAL_METRICS = {"eps": "eps_change", "returns": "return", "rates": "yield_10y_change"}


def make_research_tools(
    context: ResearchContext,
) -> dict[str, Callable[..., dict[str, object]]]:
    """Bind a private evidence snapshot; callers cannot choose sources or dates."""
    scoped = context.model_copy(deep=True)
    for entry in scoped.evidence.values():
        if (
            entry.start > entry.end or entry.end > scoped.observation_date
            or entry.end > (scoped.request.as_of or scoped.observation_date)
            or (entry.asset is not None and entry.asset not in scoped.request.universe)
        ):
            raise ValueError("research tools require evidence within the run's universe and cutoff")

    def require_asset(asset: str) -> None:
        if asset not in scoped.request.universe:
            raise ValueError(f"asset {asset!r} is outside the research universe")

    def payload(entries: dict[str, Evidence]) -> dict[str, object]:
        return {
            "observation_date": scoped.observation_date.isoformat(),
            "requested_cutoff": scoped.request.as_of.isoformat() if scoped.request.as_of else None,
            "evidence": {
                reference: entry.model_dump(mode="json") for reference, entry in entries.items()
            },
            "warnings": list(scoped.warnings),
        }

    def query_evidence(
        asset: str, metrics: list[str] | None = None, include_macro: bool = True,
    ) -> dict[str, object]:
        """Return evidence for a selected ticker; asset must never be null.

        To query only macro rates, pass any ticker in the research universe,
        include_macro=True, and metrics such as yield_10y_change_21.
        Macro entries have asset=None in outputs, not in tool arguments.
        """
        require_asset(asset)
        if type(include_macro) is not bool:
            raise ValueError("include_macro must be a boolean")
        entries = {
            key: entry for key, entry in scoped.evidence.items()
            if entry.asset == asset or (include_macro and entry.asset is None)
        }
        if metrics is not None:
            if (
                not isinstance(metrics, list) or not metrics
                or any(not isinstance(metric, str) for metric in metrics)
                or len(set(metrics)) != len(metrics)
            ):
                raise ValueError("metrics must be a nonempty list of unique metric names")
            unknown = set(metrics) - {entry.metric for entry in entries.values()}
            if unknown:
                raise ValueError(f"unavailable metrics for {asset}: {sorted(unknown)}")
            entries = {key: entry for key, entry in entries.items() if entry.metric in metrics}
        if not entries:
            raise ValueError(f"no scoped evidence for {asset}")
        return payload(entries)

    def signal_entry(asset: str, signal: Signal, lookback: int) -> tuple[str, Evidence]:
        require_asset(asset)
        if signal not in SIGNAL_METRICS:
            raise ValueError("signal must be eps, returns, or rates")
        if type(lookback) is not int or lookback not in LOOKBACKS:
            raise ValueError(f"lookback must be one of {LOOKBACKS}")
        scope = "macro" if signal == "rates" else asset
        reference = f"{scope}.{SIGNAL_METRICS[signal]}_{lookback}"
        entry = scoped.evidence.get(reference)
        if entry is None:
            raise ValueError(f"selected context does not contain {reference}")
        expected_asset = None if signal == "rates" else asset
        if entry.asset != expected_asset or entry.metric != reference.split(".", 1)[1]:
            raise ValueError(f"inconsistent evidence identity for {reference}")
        return reference, entry

    def summarize_signal(asset: str, signal: Signal, lookback: int = 63) -> dict[str, object]:
        """Select the existing deterministic 21/63-change summary; no new arithmetic."""
        reference, entry = signal_entry(asset, signal, lookback)
        return payload({reference: entry})

    def compare_signals(
        assets: list[str], signal: Literal["eps", "returns"], lookback: int = 63,
    ) -> dict[str, object]:
        """Compare asset signals and report cross-sectional descriptive statistics."""
        if (
            not isinstance(assets, list) or not assets
            or any(not isinstance(asset, str) for asset in assets)
            or len(set(assets)) != len(assets)
        ):
            raise ValueError("assets must be a nonempty list of unique securities")
        if signal not in ("eps", "returns"):
            raise ValueError("compare_signals supports eps or returns; rates are shared macro evidence")
        entries = dict(signal_entry(asset, signal, lookback) for asset in assets)
        return {
            **payload(entries),
            "statistics": summarize_evidence_values(entries),
        }

    return {
        "query_evidence": query_evidence,
        "summarize_signal": summarize_signal,
        "compare_signals": compare_signals,
    }

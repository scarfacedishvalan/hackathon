"""Hypothesis-driven weights for the existing bt callback; no BL execution."""

from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Literal

import pandas as pd
from pydantic import Field

from app.services.bl_backtest.data_interface.load import ResearchData, load_research_data
from app.services.bl_backtest.data_interface.process import prepare_context
from app.services.bl_backtest.data_interface.query import rebalance_date
from app.services.bl_backtest.research_graph import build_research_graph
from app.services.bl_backtest.schema import ResearchModel, ResearchRequest, ResearchResult, ViewBatch

WeightFn = Callable[[pd.DataFrame, list[str], str, pd.Timestamp], dict[str, float]]
TILT_SCALE = 0.5


class RebalanceRecord(ResearchModel):
    as_of: date
    status: Literal["warmup_equal_weight", "research"]
    hypothesis: str
    weights: dict[str, float]
    research: ResearchResult | None = None
    warnings: list[str] = Field(default_factory=list)


def views_to_weights(batch: ViewBatch, *, universe: list[str] | None = None) -> dict[str, float]:
    """Normalize baseline scores tilted by at most 50% before normalization."""
    signs = {"positive": 1, "negative": -1, "neutral": 0}
    assets = [view.asset for view in batch.views]
    selected = assets if universe is None else universe
    if len(set(assets)) != len(assets) or not selected or len(set(selected)) != len(selected):
        raise ValueError("weight policy requires unique, nonempty views")
    if not set(assets) <= set(selected):
        raise ValueError("weight policy received a view outside the universe")
    scores = dict.fromkeys(selected, 1.0)
    for view in batch.views:
        scores[view.asset] = 1 + TILT_SCALE * signs[view.direction] * view.magnitude * view.confidence
    total = sum(scores.values())
    return {asset: score / total for asset, score in scores.items()}


def make_research_weight_fn(
    *,
    data: ResearchData | None = None,
    llm_client=None,
    db_path: Path | None = None,
    records: list[RebalanceRecord] | None = None,
) -> WeightFn:
    """Load data/compile graph once; retain fresh research state per rebalance."""
    sources = load_research_data() if data is None else data
    graph = build_research_graph(llm_client=llm_client, db_path=db_path)

    def generate_research_weights(
        price_window: pd.DataFrame,
        universe: list[str],
        hypothesis: str,
        as_of: pd.Timestamp,
    ) -> dict[str, float]:
        cutoff = rebalance_date(as_of)
        request = ResearchRequest(hypothesis=hypothesis, universe=universe, as_of=cutoff)
        context = prepare_context(sources, request, price_window)
        warmup = any(
            entry.status == "insufficient_history"
            for key, entry in context.evidence.items() if key.endswith("_63")
        )
        if warmup:
            weights = {asset: 1 / len(universe) for asset in universe}
            record = RebalanceRecord(
                as_of=cutoff, status="warmup_equal_weight",
                hypothesis=hypothesis, weights=weights, warnings=context.warnings,
            )
        else:
            result = graph.invoke({"context": context})["result"]
            weights = views_to_weights(result.views, universe=universe)
            record = RebalanceRecord(
                as_of=cutoff, status="research",
                hypothesis=hypothesis, weights=weights, research=result,
                warnings=[*context.warnings, *result.warnings],
            )
        if records is not None:
            records.append(record)
        return weights

    return generate_research_weights

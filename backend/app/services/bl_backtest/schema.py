"""Research boundary models and deterministic view validation."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ResearchModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResearchRequest(ResearchModel):
    hypothesis: str = Field(min_length=1)
    universe: list[str] = Field(min_length=1)
    as_of: date | None = None

    @model_validator(mode="after")
    def validate_request(self):
        if not self.hypothesis.strip():
            raise ValueError("hypothesis must not be blank")
        if len(set(self.universe)) != len(self.universe):
            raise ValueError("universe must contain unique assets")
        if any(not asset.strip() for asset in self.universe):
            raise ValueError("universe must not contain blank assets")
        return self


class Evidence(ResearchModel):
    asset: str | None
    metric: str
    value: float | None = Field(allow_inf_nan=False)
    unit: str
    status: Literal["available", "not_applicable", "insufficient_history"]
    source: str
    columns: list[str]
    start: date
    end: date
    observations: int = Field(ge=0)
    synthetic: bool

    @model_validator(mode="after")
    def validate_evidence(self):
        if self.start > self.end:
            raise ValueError("evidence start must not exceed end")
        if (self.status == "available") != (self.value is not None):
            raise ValueError("only available evidence may contain a numerical value")
        if self.asset is not None and not self.asset.strip():
            raise ValueError("evidence asset must not be blank")
        return self


class ResearchContext(ResearchModel):
    request: ResearchRequest
    observation_date: date
    metadata: dict[str, dict[str, str]]
    evidence: dict[str, Evidence]
    warnings: list[str]


class AssetView(ResearchModel):
    asset: str
    direction: Literal["positive", "negative", "neutral"]
    magnitude: float = Field(strict=True, ge=0, le=1, allow_inf_nan=False)
    confidence: float = Field(strict=True, ge=0, le=1, allow_inf_nan=False)
    rationale: str = Field(min_length=1)
    evidence_cited: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_view(self):
        if not self.rationale.strip():
            raise ValueError("rationale must not be blank")
        if len(set(self.evidence_cited)) != len(self.evidence_cited):
            raise ValueError("evidence_cited must be unique")
        if (self.direction == "neutral") != (self.magnitude == 0):
            raise ValueError("neutral requires zero magnitude; directional views require > 0")
        return self


class ViewBatch(ResearchModel):
    views: list[AssetView]


class ViewCritique(ResearchModel):
    view_index: int = Field(strict=True, ge=0)
    classification: Literal["SUPPORTED", "WEAK", "CONTRADICTED", "REDUNDANT", "UNCERTAIN"]
    recommendation: Literal["KEEP", "REVISE", "MERGE", "ABANDON"]
    evidence_quality: str = Field(min_length=1)
    contradictions: str = Field(min_length=1)
    materiality: str = Field(min_length=1)
    redundancy: str = Field(min_length=1)
    confidence_assessment: str = Field(min_length=1)
    evidence_cited: list[str]


class CriticBatch(ResearchModel):
    critiques: list[ViewCritique]


class RevisionOutput(ViewBatch):
    needs_review: bool = Field(strict=True)
    summary: str = Field(min_length=1)


class FeedbackCycle(ResearchModel):
    cycle: int
    proposed_views: ViewBatch
    critic: CriticBatch
    revision: RevisionOutput


class ResearchResult(ResearchModel):
    context: ResearchContext
    views: ViewBatch
    stages: list[str]
    original_views: ViewBatch | None = None
    feedback: list[FeedbackCycle] = Field(default_factory=list)
    revision_cycles: int = 0
    revision_limit_reached: bool = False
    warnings: list[str] = Field(default_factory=list)


def validate_views(batch: ViewBatch, context: ResearchContext) -> ViewBatch:
    assets = [view.asset for view in batch.views]
    if len(assets) != len(set(assets)) or not set(assets) <= set(context.request.universe):
        raise ValueError("views must be unique and within the requested universe")
    for view in batch.views:
        available = False
        for reference in view.evidence_cited:
            if reference not in context.evidence:
                raise ValueError(f"{view.asset}: unknown evidence reference {reference}")
            evidence = context.evidence[reference]
            if evidence.asset not in (None, view.asset):
                raise ValueError(f"{view.asset}: evidence reference belongs to another asset")
            if evidence.end > context.observation_date:
                raise ValueError(f"{view.asset}: evidence exceeds observation cutoff")
            available |= evidence.status == "available" and evidence.value is not None
        if view.direction != "neutral" and not available:
            raise ValueError(f"{view.asset}: directional view needs available numerical evidence")
    by_asset = {view.asset: view for view in batch.views}
    return ViewBatch(views=[by_asset[asset] for asset in context.request.universe if asset in by_asset])

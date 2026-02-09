"""Pydantic models for strict semantic recipe validation."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class Optimiser(BaseModel):
    """Optimiser configuration extracted from user instruction."""

    model_config = ConfigDict(extra="forbid")

    name: str
    args: Dict[str, Any]


class SemanticRecipe(BaseModel):
    """Strict semantic recipe schema for backtesting instructions."""

    model_config = ConfigDict(extra="forbid")

    strategy_name: str
    rebalance_freq: str
    select: Optional[str]
    RunAfterDate: Optional[str]
    optimiser: Optimiser

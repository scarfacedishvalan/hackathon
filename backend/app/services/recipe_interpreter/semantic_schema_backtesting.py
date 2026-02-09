"""Pydantic models for strict Backtesting.py semantic recipe validation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class DataConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str | None
    source: str | None
    path: str | None
    start: str | None
    end: str | None


class BacktestConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cash: float | int | None
    commission: float | int | str | None
    margin: float | int | None
    trade_on_close: bool | None
    hedging: bool | None
    exclusive_orders: bool | None


class RulesConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry: str | None
    exit: str | None


class RiskConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stop_loss: float | int | str | None
    take_profit: float | int | str | None
    trailing_stop: float | int | str | None


class OptimizeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str | None
    maximize: bool | None
    constraint: str | None
    params: dict[str, Any] | None


class BacktestingRecipe(BaseModel):
    """Strict schema for Backtesting.py-targeted instructions."""

    model_config = ConfigDict(extra="forbid")

    strategy_name: str | None
    timeframe: str | None
    data: DataConfig
    backtest: BacktestConfig
    strategy_params: dict[str, Any] | None
    rules: RulesConfig
    risk: RiskConfig
    optimize: OptimizeConfig

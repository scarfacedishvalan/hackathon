"""
Black-Litterman Stress Testing Layer

This package provides tools for converting natural language stress testing
requests into structured specifications that can be consumed by an orchestrator.
"""

from app.services.bl_stress.stress_schema import StressSpec
from app.services.bl_stress.stress_defaults import (
    DEFAULT_VIEW_MULTIPLIERS,
    DEFAULT_CONFIDENCE_GRID,
    DEFAULT_FACTOR_SCALE,
    DEFAULT_TAU_MULTIPLIER,
    REGIME_LIBRARY,
)
from app.services.bl_stress.llm_parser import parse_stress_prompt, available_stress_types

__all__ = [
    "StressSpec",
    "DEFAULT_VIEW_MULTIPLIERS",
    "DEFAULT_CONFIDENCE_GRID",
    "DEFAULT_FACTOR_SCALE",
    "DEFAULT_TAU_MULTIPLIER",
    "REGIME_LIBRARY",
    "parse_stress_prompt",
    "available_stress_types",
]

"""
Black-Litterman Portfolio Allocation Engine

A reusable backend module for Black-Litterman portfolio allocation using PyPortfolioOpt.
"""

from .black_litterman import run_black_litterman
from .view_translation import build_P_matrix, build_Q_vector, build_omega
from .metrics import compute_portfolio_metrics
from .chart_formatters import allocation_to_chart, allocation_comparison

__all__ = [
    "run_black_litterman",
    "build_P_matrix",
    "build_Q_vector",
    "build_omega",
    "compute_portfolio_metrics",
    "allocation_to_chart",
    "allocation_comparison",
]

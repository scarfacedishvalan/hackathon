"""
Black-Litterman Portfolio Allocation Engine

A reusable backend module for Black-Litterman portfolio allocation.
Supports both PyPortfolioOpt and standalone (numpy/pandas/scipy only) implementations.
Includes support for top-down factor views via FactorViewTransformer.
"""

from app.services.bl_engine.black_litterman import (
    run_black_litterman_standalone
)
from app.services.bl_engine.view_translation import (
    build_P_matrix,
    build_Q_vector,
    build_omega
)
from app.services.bl_engine.metrics import compute_portfolio_metrics
from app.services.bl_engine.chart_formatters import (
    allocation_to_chart,
    allocation_comparison
)
from app.services.bl_engine.bl_standalone import (
    sample_cov,
    market_implied_prior_returns,
    BlackLittermanModel,
    EfficientFrontier
)
from app.services.bl_engine.factor_views import (
    FactorView,
    FactorViewTransformer
)

__all__ = [
    "run_black_litterman",
    "run_black_litterman_standalone",
    "build_P_matrix",
    "build_Q_vector",
    "build_omega",
    "compute_portfolio_metrics",
    "allocation_to_chart",
    "allocation_comparison",
    "sample_cov",
    "market_implied_prior_returns",
    "BlackLittermanModel",
    "EfficientFrontier",
    "FactorView",
    "FactorViewTransformer",
]

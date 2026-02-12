"""
Black-Litterman Portfolio Allocation Engine

A reusable backend module for Black-Litterman portfolio allocation.
Supports both PyPortfolioOpt and standalone (numpy/pandas/scipy only) implementations.
"""


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
]

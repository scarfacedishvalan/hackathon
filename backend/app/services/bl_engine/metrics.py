"""
Portfolio Metrics Module

Compute portfolio performance metrics from weights, expected returns, and covariance.
"""

import numpy as np
from typing import Dict


def compute_portfolio_metrics(
    weights: Dict[str, float],
    mu: Dict[str, float],
    cov: np.ndarray
) -> Dict[str, float]:
    """
    Compute portfolio performance metrics.
    
    Args:
        weights: Dictionary mapping asset names to portfolio weights
        mu: Dictionary mapping asset names to expected returns
        cov: Covariance matrix (num_assets x num_assets)
    
    Returns:
        Dictionary containing:
            - expected_return: Portfolio expected return
            - volatility: Portfolio standard deviation (risk)
            - sharpe: Sharpe ratio (assuming risk-free rate = 0)
    """
    # Convert dictionaries to arrays in consistent order
    assets = list(weights.keys())
    w = np.array([weights[asset] for asset in assets])
    returns = np.array([mu[asset] for asset in assets])
    
    # Compute expected return: w^T * mu
    expected_return = float(np.dot(w, returns))
    
    # Compute volatility: sqrt(w^T * Sigma * w)
    volatility = float(np.sqrt(np.dot(w, np.dot(cov, w))))
    
    # Compute Sharpe ratio (assuming risk-free rate = 0)
    sharpe = expected_return / volatility if volatility > 0 else 0.0
    
    return {
        "expected_return": expected_return,
        "volatility": volatility,
        "sharpe": sharpe
    }

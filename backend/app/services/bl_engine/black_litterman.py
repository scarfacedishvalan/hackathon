"""
Black-Litterman Portfolio Allocation Module

Core implementation of the Black-Litterman model using PyPortfolioOpt.
"""

import pandas as pd
import numpy as np
from pypfopt import risk_models, black_litterman, EfficientFrontier


def run_black_litterman(
    price_df: pd.DataFrame,
    market_caps: dict,
    P: np.ndarray,
    Q: np.ndarray,
    omega: np.ndarray
) -> dict:
    """
    Run Black-Litterman portfolio allocation.
    
    Args:
        price_df: DataFrame of historical prices with assets as columns
        market_caps: Dictionary mapping asset names to market capitalizations
        P: Pick matrix (views x assets) indicating which assets are involved in each view
        Q: Expected returns vector for the views
        omega: Uncertainty matrix for the views (diagonal covariance)
    
    Returns:
        Dictionary containing:
            - weights: Dictionary of asset weights (sum to 1)
            - posterior_returns: Dictionary of posterior expected returns
    """
    # Step 1: Compute covariance matrix
    cov_matrix = risk_models.sample_cov(price_df)
    
    # Step 2: Compute market-implied prior returns
    market_prior = black_litterman.market_implied_prior_returns(
        market_caps=market_caps,
        risk_aversion=1.0,
        cov_matrix=cov_matrix
    )
    
    # Step 3: Create BlackLittermanModel
    bl = black_litterman.BlackLittermanModel(
        cov_matrix=cov_matrix,
        pi=market_prior,
        P=P,
        Q=Q,
        omega=omega
    )
    
    # Step 4: Compute posterior returns
    posterior_returns = bl.bl_returns()
    
    # Step 5: Run EfficientFrontier to get weights
    ef = EfficientFrontier(posterior_returns, cov_matrix)
    ef.max_sharpe()
    weights = ef.clean_weights()
    
    return {
        "weights": weights,
        "posterior_returns": dict(posterior_returns)
    }

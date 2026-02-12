"""
Black-Litterman Portfolio Allocation Module

Core implementation of the Black-Litterman model using PyPortfolioOpt.
Also includes standalone implementation without pypfopt dependency.
"""

import pandas as pd
import numpy as np
from app.services.bl_engine.bl_standalone import (
    sample_cov as sample_cov_standalone,
    market_implied_prior_returns as market_implied_prior_returns_standalone,
    BlackLittermanModel as BlackLittermanModelStandalone,
    EfficientFrontier as EfficientFrontierStandalone
)


def run_black_litterman_standalone(
    price_df: pd.DataFrame,
    market_caps: dict,
    P: np.ndarray,
    Q: np.ndarray,
    omega: np.ndarray,
    risk_aversion: float = 1.0,
    tau: float = 0.05,
    risk_free_rate: float = 0.02
) -> dict:
    """
    Run Black-Litterman portfolio allocation using standalone implementation.
    
    This version uses only numpy, pandas, and scipy - no pypfopt dependency.
    
    Args:
        price_df: DataFrame of historical prices with assets as columns
        market_caps: Dictionary mapping asset names to market capitalizations
        P: Pick matrix (views x assets) indicating which assets are involved in each view
        Q: Expected returns vector for the views
        omega: Uncertainty matrix for the views (diagonal covariance)
        risk_aversion: Risk aversion parameter (default: 1.0)
                      Higher values (2-4) indicate more risk-averse investors
        tau: Uncertainty in prior estimate (default: 0.05)
             Smaller values (0.025) = more confidence in market equilibrium
        risk_free_rate: Risk-free rate for Sharpe ratio calculation (default: 0.02)
    
    Returns:
        Dictionary containing:
            - weights: Dictionary of asset weights (sum to 1)
            - posterior_returns: Dictionary of posterior expected returns
            - prior_returns: Dictionary of market-implied prior returns
            - posterior_cov: Posterior covariance matrix
    """
    # Step 1: Compute covariance matrix
    cov_matrix = sample_cov_standalone(price_df)
    
    # Step 2: Compute market-implied prior returns
    market_prior = market_implied_prior_returns_standalone(
        market_caps=market_caps,
        risk_aversion=risk_aversion,
        cov_matrix=cov_matrix
    )
    
    # Step 3: Create BlackLittermanModel
    bl = BlackLittermanModelStandalone(
        cov_matrix=cov_matrix,
        pi=market_prior,
        P=P,
        Q=Q,
        omega=omega,
        tau=tau
    )
    
    # Step 4: Compute posterior returns
    posterior_returns = bl.bl_returns()
    posterior_cov = bl.bl_cov()
    
    # Step 5: Run EfficientFrontier to get weights
    ef = EfficientFrontierStandalone(posterior_returns, cov_matrix, risk_free_rate=risk_free_rate)
    ef.max_sharpe()
    weights = ef.clean_weights()
    
    return {
        "weights": weights,
        "posterior_returns": dict(posterior_returns),
        "prior_returns": dict(market_prior),
        "posterior_cov": posterior_cov
    }

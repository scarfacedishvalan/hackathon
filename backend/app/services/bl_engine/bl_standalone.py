"""
Black-Litterman Standalone Implementation

Complete implementation of Black-Litterman model without pypfopt dependency.
Uses only numpy, pandas, and scipy for all calculations.
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize


def sample_cov(price_df: pd.DataFrame, frequency: int = 252) -> pd.DataFrame:
    """
    Calculate the sample covariance matrix of returns.
    
    Args:
        price_df: DataFrame of historical prices with assets as columns
        frequency: Number of periods in a year (252 for daily, 52 for weekly, 12 for monthly)
    
    Returns:
        pd.DataFrame: Annualized covariance matrix
    """
    returns = price_df.pct_change().dropna()
    # Annualize the covariance matrix
    cov_matrix = returns.cov() * frequency
    return cov_matrix


def market_implied_prior_returns(
    market_caps: dict,
    cov_matrix: pd.DataFrame,
    risk_aversion: float = 1.0
) -> pd.Series:
    """
    Calculate market-implied equilibrium returns using reverse optimization.
    
    The Black-Litterman model assumes that market capitalization weights represent
    the equilibrium portfolio. We can back out the implied expected returns using:
    
    π = δ * Σ * w_mkt
    
    Where:
        π = implied equilibrium excess returns
        δ = risk aversion coefficient
        Σ = covariance matrix of returns
        w_mkt = market capitalization weights
    
    Args:
        market_caps: Dictionary mapping asset names to market capitalizations
        cov_matrix: Covariance matrix as pandas DataFrame or numpy array
        risk_aversion: Risk aversion parameter (default: 1.0)
                      Higher values indicate more risk-averse investors
    
    Returns:
        pd.Series: Market-implied prior returns for each asset
    """
    # Convert market caps to weights (normalize by total market cap)
    assets = list(market_caps.keys())
    total_mcap = sum(market_caps.values())
    market_weights = np.array([market_caps[asset] / total_mcap for asset in assets])
    
    # Convert cov_matrix to numpy if it's a DataFrame
    if isinstance(cov_matrix, pd.DataFrame):
        cov_array = cov_matrix.values
    else:
        cov_array = cov_matrix
    
    # Calculate implied returns: π = δ * Σ * w_mkt
    implied_returns = risk_aversion * cov_array @ market_weights
    
    # Return as pandas Series with asset names
    return pd.Series(implied_returns, index=assets)


class BlackLittermanModel:
    """
    Black-Litterman model for combining market equilibrium with investor views.
    
    The Black-Litterman model uses Bayesian updating to blend:
    1. Market-implied equilibrium returns (prior)
    2. Investor views (observations)
    
    To produce posterior expected returns that incorporate both market consensus
    and specific investment views.
    """
    
    def __init__(
        self,
        cov_matrix: pd.DataFrame,
        pi: pd.Series,
        P: np.ndarray,
        Q: np.ndarray,
        omega: np.ndarray = None,
        tau: float = 0.05
    ):
        """
        Initialize the Black-Litterman model.
        
        Args:
            cov_matrix: Covariance matrix of asset returns
            pi: Prior expected returns (market equilibrium)
            P: Pick matrix (k views x n assets) - indicates which assets each view involves
            Q: View returns vector (k views) - expected returns for each view
            omega: View uncertainty matrix (k x k) - covariance of view errors
                   If None, will be calculated as tau * P @ cov_matrix @ P.T
            tau: Scalar uncertainty in prior (typically 0.025-0.05)
        """
        self.cov_matrix = cov_matrix if isinstance(cov_matrix, pd.DataFrame) else pd.DataFrame(cov_matrix)
        self.pi = pi if isinstance(pi, pd.Series) else pd.Series(pi)
        self.P = np.array(P)
        self.Q = np.array(Q)
        self.tau = tau
        
        # Calculate omega if not provided
        if omega is None:
            self.omega = tau * self.P @ self.cov_matrix.values @ self.P.T
        else:
            self.omega = np.array(omega)
        
        self.assets = self.pi.index.tolist()
        self.posterior_returns = None
        self.posterior_cov = None
    
    def bl_returns(self) -> pd.Series:
        """
        Calculate Black-Litterman posterior expected returns.
        
        Formula:
        E[R] = [(τΣ)^(-1) + P'Ω^(-1)P]^(-1) [(τΣ)^(-1)π + P'Ω^(-1)Q]
        
        Returns:
            pd.Series: Posterior expected returns for each asset
        """
        # Convert to numpy arrays
        cov_array = self.cov_matrix.values
        pi_array = self.pi.values.reshape(-1, 1)
        Q_array = self.Q.reshape(-1, 1) if self.Q.ndim == 1 else self.Q
        
        # Step 1: Scaled covariance matrix
        tau_cov = self.tau * cov_array
        
        # Step 2: Inverse of scaled covariance
        tau_cov_inv = np.linalg.inv(tau_cov)
        
        # Step 3: Inverse of omega (view uncertainty)
        omega_inv = np.linalg.inv(self.omega)
        
        # Step 4: Calculate the posterior precision matrix
        # [(τΣ)^(-1) + P'Ω^(-1)P]
        posterior_precision = tau_cov_inv + self.P.T @ omega_inv @ self.P
        
        # Step 5: Calculate the posterior covariance
        self.posterior_cov = np.linalg.inv(posterior_precision)
        
        # Step 6: Calculate the posterior returns
        # E[R] = [(τΣ)^(-1) + P'Ω^(-1)P]^(-1) [(τΣ)^(-1)π + P'Ω^(-1)Q]
        posterior_returns = self.posterior_cov @ (tau_cov_inv @ pi_array + self.P.T @ omega_inv @ Q_array)
        
        # Flatten and return as Series
        self.posterior_returns = pd.Series(posterior_returns.flatten(), index=self.assets)
        return self.posterior_returns
    
    def bl_cov(self) -> pd.DataFrame:
        """
        Calculate Black-Litterman posterior covariance matrix.
        
        Returns:
            pd.DataFrame: Posterior covariance matrix
        """
        if self.posterior_cov is None:
            self.bl_returns()  # Calculate if not already done
        
        return pd.DataFrame(self.posterior_cov, index=self.assets, columns=self.assets)


class EfficientFrontier:
    """
    Efficient Frontier optimizer for portfolio allocation.
    
    Performs mean-variance optimization to find optimal portfolio weights
    that maximize the Sharpe ratio or achieve other objectives.
    """
    
    def __init__(self, expected_returns, cov_matrix, weight_bounds=(0, 1), risk_free_rate=0.02):
        """
        Initialize the EfficientFrontier optimizer.
        
        Args:
            expected_returns: pd.Series or dict of expected returns for each asset
            cov_matrix: pd.DataFrame or np.ndarray covariance matrix of returns
            weight_bounds: tuple (min, max) for portfolio weights, default (0, 1)
            risk_free_rate: risk-free rate for Sharpe ratio calculation
        """
        # Convert expected returns to pandas Series
        if isinstance(expected_returns, dict):
            self.expected_returns = pd.Series(expected_returns)
        elif isinstance(expected_returns, pd.Series):
            self.expected_returns = expected_returns
        else:
            raise TypeError("expected_returns must be a dict or pd.Series")
        
        # Convert covariance matrix to numpy array
        if isinstance(cov_matrix, pd.DataFrame):
            self.cov_matrix = cov_matrix.values
            self.assets = cov_matrix.columns.tolist()
        else:
            self.cov_matrix = np.array(cov_matrix)
            self.assets = self.expected_returns.index.tolist()
        
        self.weight_bounds = weight_bounds
        self.risk_free_rate = risk_free_rate
        self.n_assets = len(self.assets)
        self.weights = None
        
        # Validate dimensions
        assert len(self.expected_returns) == self.n_assets, \
            "Expected returns length must match number of assets"
        assert self.cov_matrix.shape == (self.n_assets, self.n_assets), \
            "Covariance matrix dimensions must match number of assets"
    
    def _portfolio_performance(self, weights):
        """
        Calculate portfolio return and volatility.
        
        Args:
            weights: array of portfolio weights
            
        Returns:
            tuple: (expected_return, volatility)
        """
        portfolio_return = np.dot(weights, self.expected_returns.values)
        portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix, weights)))
        return portfolio_return, portfolio_volatility
    
    def _negative_sharpe(self, weights):
        """
        Calculate negative Sharpe ratio (for minimization).
        
        Args:
            weights: array of portfolio weights
            
        Returns:
            float: negative Sharpe ratio
        """
        portfolio_return, portfolio_volatility = self._portfolio_performance(weights)
        sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_volatility
        return -sharpe_ratio
    
    def _portfolio_variance(self, weights):
        """
        Calculate portfolio variance.
        
        Args:
            weights: array of portfolio weights
            
        Returns:
            float: portfolio variance
        """
        return np.dot(weights.T, np.dot(self.cov_matrix, weights))
    
    def max_sharpe(self, risk_free_rate=None):
        """
        Optimize portfolio to maximize Sharpe ratio.
        
        Args:
            risk_free_rate: override the risk-free rate if provided
            
        Returns:
            dict: optimized portfolio weights
        """
        if risk_free_rate is not None:
            self.risk_free_rate = risk_free_rate
        
        # Initial guess: equal weights
        initial_weights = np.ones(self.n_assets) / self.n_assets
        
        # Constraints: weights sum to 1
        constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        
        # Bounds for each weight
        bounds = tuple(self.weight_bounds for _ in range(self.n_assets))
        
        # Optimize
        result = minimize(
            self._negative_sharpe,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        if not result.success:
            raise ValueError(f"Optimization failed: {result.message}")
        
        self.weights = result.x
        return dict(zip(self.assets, self.weights))
    
    def min_volatility(self):
        """
        Optimize portfolio to minimize volatility.
        
        Returns:
            dict: optimized portfolio weights
        """
        # Initial guess: equal weights
        initial_weights = np.ones(self.n_assets) / self.n_assets
        
        # Constraints: weights sum to 1
        constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        
        # Bounds for each weight
        bounds = tuple(self.weight_bounds for _ in range(self.n_assets))
        
        # Optimize
        result = minimize(
            self._portfolio_variance,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        if not result.success:
            raise ValueError(f"Optimization failed: {result.message}")
        
        self.weights = result.x
        return dict(zip(self.assets, self.weights))
    
    def efficient_return(self, target_return):
        """
        Optimize portfolio to minimize risk for a target return.
        
        Args:
            target_return: desired portfolio return
            
        Returns:
            dict: optimized portfolio weights
        """
        # Initial guess: equal weights
        initial_weights = np.ones(self.n_assets) / self.n_assets
        
        # Constraints: weights sum to 1, target return constraint
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},
            {'type': 'eq', 'fun': lambda w: np.dot(w, self.expected_returns.values) - target_return}
        ]
        
        # Bounds for each weight
        bounds = tuple(self.weight_bounds for _ in range(self.n_assets))
        
        # Optimize
        result = minimize(
            self._portfolio_variance,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        if not result.success:
            raise ValueError(f"Optimization failed: {result.message}")
        
        self.weights = result.x
        return dict(zip(self.assets, self.weights))
    
    def efficient_risk(self, target_volatility):
        """
        Optimize portfolio to maximize return for a target volatility.
        
        Args:
            target_volatility: desired portfolio volatility
            
        Returns:
            dict: optimized portfolio weights
        """
        # Initial guess: equal weights
        initial_weights = np.ones(self.n_assets) / self.n_assets
        
        def portfolio_volatility(w):
            return np.sqrt(np.dot(w.T, np.dot(self.cov_matrix, w)))
        
        # Constraints: weights sum to 1, target volatility constraint
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},
            {'type': 'eq', 'fun': lambda w: portfolio_volatility(w) - target_volatility}
        ]
        
        # Bounds for each weight
        bounds = tuple(self.weight_bounds for _ in range(self.n_assets))
        
        # Maximize return (minimize negative return)
        result = minimize(
            lambda w: -np.dot(w, self.expected_returns.values),
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        if not result.success:
            raise ValueError(f"Optimization failed: {result.message}")
        
        self.weights = result.x
        return dict(zip(self.assets, self.weights))
    
    def clean_weights(self, cutoff=1e-4, rounding=5):
        """
        Clean the optimized weights by removing negligible weights.
        
        Args:
            cutoff: weights below this value are set to zero
            rounding: number of decimal places to round to
            
        Returns:
            dict: cleaned portfolio weights
        """
        if self.weights is None:
            raise ValueError("No weights to clean. Run an optimization method first.")
        
        cleaned = {}
        for asset, weight in zip(self.assets, self.weights):
            if abs(weight) < cutoff:
                cleaned[asset] = 0.0
            else:
                cleaned[asset] = round(weight, rounding)
        
        # Renormalize to ensure weights sum to 1
        total = sum(cleaned.values())
        if total > 0:
            cleaned = {k: v/total for k, v in cleaned.items()}
        
        return cleaned
    
    def portfolio_performance(self, verbose=False):
        """
        Calculate the expected performance of the optimized portfolio.
        
        Args:
            verbose: if True, print the performance metrics
            
        Returns:
            tuple: (expected_return, volatility, sharpe_ratio)
        """
        if self.weights is None:
            raise ValueError("No weights available. Run an optimization method first.")
        
        expected_return, volatility = self._portfolio_performance(self.weights)
        sharpe_ratio = (expected_return - self.risk_free_rate) / volatility
        
        if verbose:
            print(f"Expected annual return: {expected_return:.2%}")
            print(f"Annual volatility: {volatility:.2%}")
            print(f"Sharpe Ratio: {sharpe_ratio:.2f}")
        
        return expected_return, volatility, sharpe_ratio

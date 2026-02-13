"""
Factor View Transformer for Top-Down Black-Litterman

Extends the bottom-up Black-Litterman engine to support top-down macro/factor views.
Converts factor-level views into asset-level P, Q, Omega matrices that can be fed
into the existing BlackLittermanModel class.

Key Concepts:
-------------
- Factor Exposure Matrix B: Maps factor shocks to asset return shifts
  Shape: (n_assets, n_factors)
  Interpretation: Δμ = B @ Δf
  
- Factor Views: Express opinions about factor movements rather than individual assets
  Example: "GDP growth factor will increase by 1%" instead of "AAPL will gain 5%"
  
- Asset-Expanded Approach: Converts factor views into asset-level absolute views
  P = Identity matrix (each asset gets its own view)
  Q = delta_mu (asset return shifts from factor shocks)
  Ω = Scaled diagonal uncertainty matrix based on confidence
"""

from dataclasses import dataclass
import numpy as np
from typing import List


@dataclass
class FactorView:
    """
    Represents a single top-down view on a macro/factor.
    
    Attributes:
        factor_index: Index of the factor in the factor exposure matrix B (0-indexed)
        shock: Expected change in the factor (e.g., 0.01 for 1% increase)
        confidence: Confidence level in the view, range [0, 1]
                   Higher values = more confident = lower uncertainty in Omega
                   Typical values: 0.5 (moderate), 0.7 (high), 0.9 (very high)
    
    Example:
        # View that GDP factor (index 0) will increase by 2% with high confidence
        FactorView(factor_index=0, shock=0.02, confidence=0.8)
    """
    factor_index: int
    shock: float
    confidence: float
    
    def __post_init__(self):
        """Validate factor view parameters."""
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Confidence must be in [0, 1], got {self.confidence}")


class FactorViewTransformer:
    """
    Converts top-down factor views into Black-Litterman matrices (P, Q, Omega).
    
    This transformer allows you to express views at the factor level (e.g., "growth stocks
    will outperform by 2%") and automatically translates them into asset-level views that
    can be consumed by the existing BlackLittermanModel class.
    
    Mathematical Framework:
    ----------------------
    1. Aggregate factor views into factor shock vector:
       Δf[i] = views where factor_index == i
       
    2. Map factor shocks to asset return shifts:
       Δμ = B @ Δf
       Where B is the factor exposure matrix (n_assets × n_factors)
       
    3. Convert to Black-Litterman matrices:
       P = I (identity matrix, size n_assets)
       Q = Δμ (asset return shifts)
       Ω = diag(P @ τΣ @ P.T) / confidence
       
    The confidence parameter scales the uncertainty: higher confidence → lower Ω → views
    have more influence on the posterior.
    
    Design Choice:
    --------------
    We use the asset-expanded approach (P = I) rather than keeping P small with factor-based
    rows. This is simpler and makes the math more transparent, though it results in larger
    matrices. For typical portfolios (<100 assets), this is not a performance concern.
    """
    
    def __init__(self, B: np.ndarray, tau: float, Sigma: np.ndarray):
        """
        Initialize the factor view transformer.
        
        Args:
            B: Factor exposure matrix, shape (n_assets, n_factors)
               Each column represents a factor, each row an asset
               B[i, j] = sensitivity of asset i to factor j
            tau: Uncertainty scalar in the prior estimate (typically 0.025-0.05)
                 Same tau used in BlackLittermanModel
            Sigma: Covariance matrix of asset returns, shape (n_assets, n_assets)
                   Used to scale the uncertainty matrix Omega
        
        Raises:
            ValueError: If dimensions are incompatible
        """
        self.B = np.array(B)
        self.tau = tau
        self.Sigma = np.array(Sigma)
        
        # Validate dimensions
        n_assets, n_factors = self.B.shape
        if self.Sigma.shape != (n_assets, n_assets):
            raise ValueError(
                f"Sigma shape {self.Sigma.shape} incompatible with B shape {self.B.shape}. "
                f"Expected Sigma to be ({n_assets}, {n_assets})"
            )
        
        self.n_assets = n_assets
        self.n_factors = n_factors
    
    def _aggregate_factor_shocks(self, factor_views: List[FactorView]) -> tuple:
        """
        Aggregate multiple factor views into a single factor shock vector.
        
        If multiple views target the same factor, they are combined (summed).
        This allows expressing compound views like "GDP +1% AND inflation -0.5%".
        
        Args:
            factor_views: List of FactorView objects
        
        Returns:
            tuple: (delta_f, confidence_vector)
                delta_f: Factor shock vector, shape (n_factors,)
                confidence_vector: Confidence for each factor, shape (n_factors,)
        
        Note:
            If multiple views reference the same factor, shocks are summed and
            confidences are averaged (simple mean).
        """
        # Initialize accumulators
        delta_f = np.zeros(self.n_factors)
        confidence_sum = np.zeros(self.n_factors)
        confidence_count = np.zeros(self.n_factors)
        
        # Aggregate views
        for view in factor_views:
            if view.factor_index >= self.n_factors:
                raise ValueError(
                    f"factor_index {view.factor_index} exceeds number of factors {self.n_factors}"
                )
            
            delta_f[view.factor_index] += view.shock
            confidence_sum[view.factor_index] += view.confidence
            confidence_count[view.factor_index] += 1
        
        # Compute average confidence for factors with views
        confidence_vector = np.zeros(self.n_factors)
        mask = confidence_count > 0
        confidence_vector[mask] = confidence_sum[mask] / confidence_count[mask]
        
        return delta_f, confidence_vector
    
    def _compute_asset_return_shifts(self, delta_f: np.ndarray) -> np.ndarray:
        """
        Map factor shocks to asset return shifts using the factor exposure matrix.
        
        Formula:
            Δμ = B @ Δf
        
        Args:
            delta_f: Factor shock vector, shape (n_factors,)
        
        Returns:
            np.ndarray: Asset return shifts, shape (n_assets,)
        
        Interpretation:
            Result[i] = expected change in asset i's return due to factor shocks
        """
        delta_mu = self.B @ delta_f
        return delta_mu
    
    def _build_omega_matrix(self, confidence_vector: np.ndarray, delta_f: np.ndarray) -> np.ndarray:
        """
        Build the uncertainty matrix Omega for the asset-level views.
        
        Formula:
            Ω = diag(τΣ) / avg_confidence
            
        Where avg_confidence is weighted by the factor exposure for each asset.
        
        Args:
            confidence_vector: Confidence for each factor, shape (n_factors,)
            delta_f: Factor shock vector, shape (n_factors,)
        
        Returns:
            np.ndarray: Diagonal uncertainty matrix, shape (n_assets, n_assets)
        
        Design Note:
            We compute a per-asset confidence based on which factors affect it.
            Assets driven by high-confidence factors get lower uncertainty.
        """
        # Base uncertainty from tau * Sigma diagonal
        base_uncertainty = self.tau * np.diag(self.Sigma)
        
        # Compute per-asset confidence as a weighted average of factor confidences
        # Weight by absolute factor exposure (assets more exposed to a factor inherit its confidence)
        asset_confidence = np.zeros(self.n_assets)
        
        for i in range(self.n_assets):
            # Get exposures of asset i to all factors
            exposures = np.abs(self.B[i, :])
            
            # Only consider factors that have views (confidence > 0)
            active_factors = confidence_vector > 0
            
            if not np.any(active_factors):
                # No views affect this asset, use default uncertainty
                asset_confidence[i] = 0.5  # moderate default
            else:
                # Weighted average: factors with higher exposure to this asset get more weight
                weights = exposures[active_factors]
                confidences = confidence_vector[active_factors]
                
                if np.sum(weights) > 1e-10:  # avoid division by zero
                    asset_confidence[i] = np.sum(weights * confidences) / np.sum(weights)
                else:
                    asset_confidence[i] = 0.5  # default if no exposure
        
        # Scale base uncertainty by inverse of confidence
        # High confidence → low uncertainty (Omega is small)
        # Low confidence → high uncertainty (Omega is large)
        omega_diagonal = base_uncertainty / (asset_confidence + 1e-10)  # add epsilon to avoid division by zero
        
        # Return as diagonal matrix
        return np.diag(omega_diagonal)
    
    def build_matrices(self, factor_views: List[FactorView]) -> tuple:
        """
        Build Black-Litterman matrices P, Q, Omega from factor views.
        
        This is the main entry point for converting top-down factor views into
        the format required by BlackLittermanModel.
        
        Args:
            factor_views: List of FactorView objects expressing top-down opinions
        
        Returns:
            tuple: (P, Q, Omega)
                P: Pick matrix, shape (n_assets, n_assets) - Identity matrix
                Q: Expected returns vector, shape (n_assets,)
                Omega: Uncertainty matrix, shape (n_assets, n_assets) - Diagonal
        
        Example:
            >>> transformer = FactorViewTransformer(B, tau=0.05, Sigma=cov_matrix)
            >>> views = [
            ...     FactorView(factor_index=0, shock=0.01, confidence=0.7),
            ...     FactorView(factor_index=1, shock=-0.02, confidence=0.8),
            ... ]
            >>> P, Q, Omega = transformer.build_matrices(views)
            >>> # Now use with BlackLittermanModel
            >>> bl = BlackLittermanModel(cov_matrix, pi, P, Q, Omega, tau)
        """
        if not factor_views:
            raise ValueError("Must provide at least one factor view")
        
        # Step 1: Aggregate factor views into factor shock vector
        delta_f, confidence_vector = self._aggregate_factor_shocks(factor_views)
        
        # Step 2: Map factor shocks to asset return shifts
        delta_mu = self._compute_asset_return_shifts(delta_f)
        
        # Step 3: Build matrices using asset-expanded approach
        # P = Identity matrix (each asset is a separate view)
        P = np.eye(self.n_assets)
        
        # Q = Asset return shifts (the "views" are the expected shifts from factors)
        Q = delta_mu
        
        # Omega = Uncertainty matrix (scaled by confidence)
        Omega = self._build_omega_matrix(confidence_vector, delta_f)
        
        return P, Q, Omega
    
    def get_factor_exposures(self, asset_index: int) -> np.ndarray:
        """
        Get the factor exposures for a specific asset.
        
        Utility method for inspecting how factors affect a given asset.
        
        Args:
            asset_index: Index of the asset (0-indexed)
        
        Returns:
            np.ndarray: Factor exposures for the asset, shape (n_factors,)
        """
        if asset_index >= self.n_assets:
            raise ValueError(f"asset_index {asset_index} exceeds number of assets {self.n_assets}")
        
        return self.B[asset_index, :]
    
    def simulate_factor_impact(self, factor_views: List[FactorView]) -> dict:
        """
        Simulate the impact of factor views on asset returns without running BL.
        
        Useful for understanding how factor views translate to expected asset moves
        before committing to the full Black-Litterman posterior calculation.
        
        Args:
            factor_views: List of FactorView objects
        
        Returns:
            dict: Contains:
                - 'delta_f': Factor shock vector
                - 'delta_mu': Asset return shifts
                - 'confidence_vector': Confidence by factor
                - 'asset_confidence': Effective confidence by asset
        """
        delta_f, confidence_vector = self._aggregate_factor_shocks(factor_views)
        delta_mu = self._compute_asset_return_shifts(delta_f)
        
        # Compute per-asset confidence (same logic as in _build_omega_matrix)
        asset_confidence = np.zeros(self.n_assets)
        for i in range(self.n_assets):
            exposures = np.abs(self.B[i, :])
            active_factors = confidence_vector > 0
            
            if not np.any(active_factors):
                asset_confidence[i] = 0.5
            else:
                weights = exposures[active_factors]
                confidences = confidence_vector[active_factors]
                
                if np.sum(weights) > 1e-10:
                    asset_confidence[i] = np.sum(weights * confidences) / np.sum(weights)
                else:
                    asset_confidence[i] = 0.5
        
        return {
            'delta_f': delta_f,
            'delta_mu': delta_mu,
            'confidence_vector': confidence_vector,
            'asset_confidence': asset_confidence
        }

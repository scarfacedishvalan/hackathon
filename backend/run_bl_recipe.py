"""
Black-Litterman Recipe Runner

Implements execution of structured BL recipes that combine:
- Bottom-up views (absolute and relative)
- Top-down factor views
- Portfolio constraints (long-only, per-asset weight bounds)
- Custom estimators for covariance and prior returns

Recipe format supports JSON configuration for repeatable portfolio construction.

Key Features:
- Parses JSON recipe with meta, universe, parameters, constraints, and views
- Builds separate P, Q, Ω matrices for bottom-up and top-down views
- Stacks matrices for unified Black-Litterman inference
- Supports absolute views ("AAPL will return 8%")
- Supports relative views ("AAPL will outperform MSFT by 3%")
- Supports factor shock views ("Growth factor +2%")
- Applies per-asset weight constraints during optimization
- Gracefully handles missing assets by filtering universe

Example Recipe Structure:
{
  "meta": {"name": "...", "description": "..."},
  "universe": {"assets": ["AAPL", "MSFT", ...]},
  "model_parameters": {"tau": 0.05, "risk_aversion": 3.0, "risk_free_rate": 0.02},
  "constraints": {
    "long_only": true,
    "weight_bounds": {"AAPL": [0.0, 0.4], ...}
  },
  "bottom_up_views": [
    {"type": "absolute", "asset": "AAPL", "expected_return": 0.12, "confidence": 0.8},
    {"type": "relative", "assets": ["AAPL", "MSFT"], "weights": [1, -1], 
     "expected_outperformance": 0.03, "confidence": 0.7}
  ],
  "top_down_views": {
    "factor_model": {"factors": ["Growth", "Rates"]},
    "factor_shocks": [
      {"factor": "Growth", "shock": 0.02, "confidence": 0.8}
    ]
  }
}
"""

import sys
import os

# Add backend directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd
from typing import Dict, Callable, List, Tuple
from app.services.bl_engine.bl_standalone import (
    BlackLittermanModel,
    EfficientFrontier,
    sample_cov,
    market_implied_prior_returns
)
from app.services.bl_engine.factor_views import FactorView, FactorViewTransformer
from app.services.price_data.load_data import load_market_data


def run_bl_recipe(
    recipe: dict,
    price_data: pd.DataFrame,
    market_caps: Dict[str, float],
    factor_exposures: np.ndarray,
    factor_index_map: Dict[str, int],
    covariance_estimator: Callable = None,
    return_estimator: Callable = None
) -> dict:
    """
    Execute a Black-Litterman recipe with bottom-up and top-down views.
    
    Args:
        recipe: Recipe dictionary containing:
            - universe: List of assets
            - model_parameters: tau, risk_aversion, risk_free_rate
            - constraints: weight_bounds, long_only
            - bottom_up_views: List of absolute/relative views
            - top_down_views: Factor model and shocks
        price_data: Historical price DataFrame (all assets)
        market_caps: Dictionary of market capitalizations (all assets)
        factor_exposures: Factor exposure matrix B (n_assets x n_factors)
        factor_index_map: Maps factor names to column indices in B
        covariance_estimator: Custom covariance function (default: sample_cov)
        return_estimator: Custom prior return function (default: market_implied_prior_returns)
    
    Returns:
        dict: Portfolio results including weights, returns, and intermediate matrices
    """
    print("\n" + "="*80)
    print(f"RUNNING BLACK-LITTERMAN RECIPE: {recipe['meta']['name']}")
    print("="*80)
    print(f"Description: {recipe['meta']['description']}")
    
    # Extract universe and filter data
    universe = recipe['universe']['assets']
    price_df = price_data[universe].copy()
    filtered_market_caps = {asset: market_caps[asset] for asset in universe}
    
    # Get model parameters
    params = recipe['model_parameters']
    tau = params['tau']
    risk_aversion = params['risk_aversion']
    risk_free_rate = params['risk_free_rate']
    
    print(f"\n📦 Universe: {len(universe)} assets - {', '.join(universe)}")
    print(f"⚙️  Parameters: tau={tau}, risk_aversion={risk_aversion}, rf={risk_free_rate}")
    
    # Compute covariance and prior returns
    if covariance_estimator is None:
        covariance_estimator = sample_cov
    if return_estimator is None:
        return_estimator = market_implied_prior_returns
    
    cov_matrix = covariance_estimator(price_df)
    pi = return_estimator(filtered_market_caps, cov_matrix, risk_aversion)
    Sigma = cov_matrix.values
    n_assets = len(universe)
    
    # Create asset name to index mapping
    asset_to_idx = {asset: idx for idx, asset in enumerate(universe)}
    
    # ==================== BUILD BOTTOM-UP VIEWS ====================
    print("\n" + "="*80)
    print("📊 BOTTOM-UP VIEWS")
    print("="*80)
    
    bottom_up_views = recipe.get('bottom_up_views', [])
    P_bottom_list = []
    Q_bottom_list = []
    omega_bottom_list = []
    
    for i, view in enumerate(bottom_up_views):
        view_type = view['type']
        confidence = view['confidence']
        label = view.get('label', f'View {i+1}')
        
        if view_type == 'absolute':
            # Absolute view: single asset expected return
            asset = view['asset']
            
            # Skip if asset not in universe
            if asset not in asset_to_idx:
                print(f"\n  ⚠ Skipping View {i+1}: Asset {asset} not in universe")
                continue
            
            expected_return = view['expected_return']
            asset_idx = asset_to_idx[asset]
            
            print(f"\n  View {i+1} (Absolute): {label}")
            print(f"    {asset} → {expected_return:.2%} (confidence: {confidence:.2f})")
            
            # P: single row with 1 at asset position
            P_row = np.zeros(n_assets)
            P_row[asset_idx] = 1.0
            P_bottom_list.append(P_row)
            
            # Q: expected return
            Q_bottom_list.append(expected_return)
            
            # Omega: scaled by confidence
            omega_val = tau * Sigma[asset_idx, asset_idx] / confidence
            omega_bottom_list.append(omega_val)
            
        elif view_type == 'relative':
            # Relative view: asset1 outperforms asset2
            assets_in_view = view['assets']
            weights = view['weights']
            expected_outperformance = view['expected_outperformance']
            
            # Skip if any asset not in universe
            if not all(asset in asset_to_idx for asset in assets_in_view):
                missing = [a for a in assets_in_view if a not in asset_to_idx]
                print(f"\n  ⚠ Skipping View {i+1}: Assets {missing} not in universe")
                continue
            
            print(f"\n  View {i+1} (Relative): {label}")
            print(f"    {assets_in_view[0]} vs {assets_in_view[1]} → {expected_outperformance:+.2%} (confidence: {confidence:.2f})")
            
            # P: row with weights at respective positions
            P_row = np.zeros(n_assets)
            for asset, weight in zip(assets_in_view, weights):
                asset_idx = asset_to_idx[asset]
                P_row[asset_idx] = weight
            P_bottom_list.append(P_row)
            
            # Q: expected outperformance
            Q_bottom_list.append(expected_outperformance)
            
            # Omega: variance of the view
            # For relative views: omega = P @ (tau * Sigma) @ P.T / confidence
            view_variance = P_row @ (tau * Sigma) @ P_row.T
            omega_val = view_variance / confidence
            omega_bottom_list.append(omega_val)
    
    # Stack bottom-up matrices
    if P_bottom_list:
        P_bottom = np.array(P_bottom_list)
        Q_bottom = np.array(Q_bottom_list)
        omega_bottom = np.diag(omega_bottom_list)
        
        print(f"\n  ✓ Built {len(P_bottom_list)} bottom-up view(s)")
        print(f"    P_bottom shape: {P_bottom.shape}")
        print(f"    Q_bottom shape: {Q_bottom.shape}")
    else:
        P_bottom = np.zeros((0, n_assets))
        Q_bottom = np.array([])
        omega_bottom = np.zeros((0, 0))
        print(f"\n  ⚠ No bottom-up views defined")
    
    # ==================== BUILD TOP-DOWN VIEWS ====================
    print("\n" + "="*80)
    print("📊 TOP-DOWN FACTOR VIEWS")
    print("="*80)
    
    top_down_config = recipe.get('top_down_views', {})
    factor_shocks = top_down_config.get('factor_shocks', [])
    
    if factor_shocks:
        # Build FactorView objects
        factor_view_objects = []
        for shock_spec in factor_shocks:
            factor_name = shock_spec['factor']
            shock = shock_spec['shock']
            confidence = shock_spec['confidence']
            label = shock_spec.get('label', factor_name)
            
            factor_idx = factor_index_map[factor_name]
            factor_view_objects.append(
                FactorView(factor_index=factor_idx, shock=shock, confidence=confidence)
            )
            
            print(f"\n  Factor View: {label}")
            print(f"    {factor_name} → {shock:+.2%} shock (confidence: {confidence:.2f})")
        
        # Filter factor exposure matrix to universe
        # Assuming factor_exposures is for all assets in original order
        # We need to map universe assets to their rows in factor_exposures
        # For simplicity, assume we can construct B for the universe
        # This requires the caller to provide properly aligned B
        B_universe = factor_exposures[:n_assets, :]  # Assume first n_assets match universe
        
        # Build top-down matrices using FactorViewTransformer
        transformer = FactorViewTransformer(B_universe, tau, Sigma)
        P_top, Q_top, omega_top = transformer.build_matrices(factor_view_objects)
        
        print(f"\n  ✓ Built {len(factor_shocks)} factor view(s)")
        print(f"    P_top shape: {P_top.shape}")
        print(f"    Q_top shape: {Q_top.shape}")
    else:
        P_top = np.zeros((0, n_assets))
        Q_top = np.array([])
        omega_top = np.zeros((0, 0))
        print(f"\n  ⚠ No top-down factor views defined")
    
    # ==================== COMBINE VIEWS ====================
    print("\n" + "="*80)
    print("🔗 COMBINING VIEWS")
    print("="*80)
    
    # Stack all views
    if P_bottom.shape[0] > 0 and P_top.shape[0] > 0:
        P_combined = np.vstack([P_bottom, P_top])
        Q_combined = np.concatenate([Q_bottom, Q_top])
        
        # Block diagonal omega
        n_bottom = P_bottom.shape[0]
        n_top = P_top.shape[0]
        n_total = n_bottom + n_top
        Omega_combined = np.zeros((n_total, n_total))
        Omega_combined[:n_bottom, :n_bottom] = omega_bottom
        Omega_combined[n_bottom:, n_bottom:] = omega_top
        
        print(f"  Combined: {n_bottom} bottom-up + {n_top} top-down = {n_total} total views")
    elif P_bottom.shape[0] > 0:
        P_combined = P_bottom
        Q_combined = Q_bottom
        Omega_combined = omega_bottom
        print(f"  Only bottom-up views: {P_bottom.shape[0]} views")
    elif P_top.shape[0] > 0:
        P_combined = P_top
        Q_combined = Q_top
        Omega_combined = omega_top
        print(f"  Only top-down views: {P_top.shape[0]} views")
    else:
        print(f"\n  ⚠️  WARNING: No views available after filtering")
        print(f"     Proceeding with market equilibrium (no BL adjustment)")
        # Return market equilibrium results
        ef = EfficientFrontier(
            pi, 
            cov_matrix, 
            weight_bounds=(0.0, 1.0),
            risk_free_rate=risk_free_rate
        )
        ef.max_sharpe()
        weights = ef.clean_weights()
        
        return {
            'recipe_name': recipe['meta']['name'],
            'universe': universe,
            'weights': weights,
            'posterior_returns': dict(pi),
            'prior_returns': dict(pi),
            'P': None,
            'Q': None,
            'Omega': None,
            'n_bottom_up_views': 0,
            'n_top_down_views': 0,
            'model_parameters': params,
            'note': 'No views available - using market equilibrium'
        }
    
    print(f"\n  P (Combined): {P_combined.shape}")
    print(f"  Q (Combined): {Q_combined.shape}")
    print(f"  Ω (Combined): {Omega_combined.shape}")
    
    # ==================== RUN BLACK-LITTERMAN ====================
    print("\n" + "="*80)
    print("🧮 BLACK-LITTERMAN POSTERIOR")
    print("="*80)
    
    bl = BlackLittermanModel(
        cov_matrix=cov_matrix,
        pi=pi,
        P=P_combined,
        Q=Q_combined,
        omega=Omega_combined,
        tau=tau
    )
    
    posterior_returns = bl.bl_returns()
    
    print("\n  Posterior Returns:")
    for asset in universe:
        ret = posterior_returns[asset]
        print(f"    {asset:6s}: {ret:7.2%}")
    
    # ==================== PORTFOLIO OPTIMIZATION ====================
    print("\n" + "="*80)
    print("📈 PORTFOLIO OPTIMIZATION")
    print("="*80)
    
    # Extract constraints
    constraints_config = recipe.get('constraints', {})
    long_only = constraints_config.get('long_only', True)
    weight_bounds_config = constraints_config.get('weight_bounds', {})
    
    # Check if we have custom per-asset bounds
    has_custom_bounds = bool(weight_bounds_config) and any(
        asset in weight_bounds_config for asset in universe
    )
    
    if has_custom_bounds:
        # Custom bounds per asset - use manual optimization
        from scipy.optimize import minimize
        
        bounds = []
        custom_count = 0
        for asset in universe:
            if asset in weight_bounds_config:
                bounds.append(tuple(weight_bounds_config[asset]))
                custom_count += 1
            else:
                bounds.append((0.0, 1.0) if long_only else (-1.0, 1.0))
        
        print(f"  Using custom weight bounds for {custom_count} assets")
        
        # Manual optimization
        posterior_returns_array = np.array([posterior_returns[asset] for asset in universe])
        
        def negative_sharpe(weights):
            portfolio_return = np.dot(weights, posterior_returns_array)
            portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(Sigma, weights)))
            return -(portfolio_return - risk_free_rate) / portfolio_volatility
        
        initial_weights = np.ones(n_assets) / n_assets
        constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        
        result = minimize(
            negative_sharpe,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        if not result.success:
            print(f"  ⚠️  Optimization warning: {result.message}")
        
        weights = {asset: weight for asset, weight in zip(universe, result.x)}
        # Clean near-zero weights
        weights = {k: v for k, v in weights.items() if abs(v) > 1e-4}
        
    else:
        # Default bounds - use EfficientFrontier class
        if long_only:
            bounds = (0.0, 1.0)
            print(f"  Using long-only constraint: [0, 1]")
        else:
            bounds = (None, None)
            print(f"  No weight constraints")
        
        # Optimize
        ef = EfficientFrontier(
            posterior_returns, 
            cov_matrix, 
            weight_bounds=bounds,
            risk_free_rate=risk_free_rate
        )
        ef.max_sharpe()
        weights = ef.clean_weights()
    
    print("\n  Optimal Weights:")
    for asset in universe:
        weight = weights.get(asset, 0.0)
        if abs(weight) > 0.001:
            print(f"    {asset:6s}: {weight:7.2%}")
    
    # ==================== RESULTS ====================
    print("\n" + "="*80)
    print("✅ RECIPE EXECUTION COMPLETE")
    print("="*80)
    
    return {
        'recipe_name': recipe['meta']['name'],
        'universe': universe,
        'weights': weights,
        'posterior_returns': dict(posterior_returns),
        'prior_returns': dict(pi),
        'P': P_combined,
        'Q': Q_combined,
        'Omega': Omega_combined,
        'n_bottom_up_views': P_bottom.shape[0],
        'n_top_down_views': P_top.shape[0],
        'model_parameters': params
    }


def example_usage():
    """
    Example: Load and execute a BL recipe.
    """
    import json
    from top_down_bl import create_synthetic_data
    
    print("\n" + "="*80)
    print("BLACK-LITTERMAN RECIPE EXECUTION EXAMPLE")
    print("="*80)
    
    # Load recipe - use absolute path relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    recipe_path = os.path.join(script_dir, 'app', 'services', 'bl_engine', 'bl_recipe.json')
    with open(recipe_path, 'r') as f:
        recipe = json.load(f)
    
    # Create synthetic data (using the same function from top_down_bl)
    price_df_full, market_caps_full, B_full, factor_names, all_assets = load_market_data()
    
    # Build factor index map
    factor_index_map = {name: idx for idx, name in enumerate(factor_names)}
    
    # Filter data to include recipe universe assets
    # Need to ensure we have all recipe assets in our synthetic data
    recipe_assets = recipe['universe']['assets']
    
    # Check if all recipe assets exist in synthetic data
    missing_assets = set(recipe_assets) - set(all_assets)
    if missing_assets:
        print(f"\n⚠️  Warning: Recipe contains assets not in synthetic data: {missing_assets}")
        print(f"   Using only available assets...")
        # For this example, we'll create minimal synthetic data for missing assets
        available_assets = [a for a in recipe_assets if a in all_assets]
        if not available_assets:
            print("   ERROR: No matching assets found!")
            return
        recipe['universe']['assets'] = available_assets
    
    # Run recipe
    results = run_bl_recipe(
        recipe=recipe,
        price_data=price_df_full,
        market_caps=market_caps_full,
        factor_exposures=B_full,
        factor_index_map=factor_index_map,
        covariance_estimator=None,  # Use default
        return_estimator=None  # Use default
    )
    
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    print(f"\nRecipe: {results['recipe_name']}")
    print(f"Views: {results['n_bottom_up_views']} bottom-up + {results['n_top_down_views']} top-down")
    print(f"\nFinal Allocation:")
    for asset, weight in results['weights'].items():
        if abs(weight) > 0.001:
            print(f"  {asset}: {weight:.2%}")


if __name__ == "__main__":
    example_usage()

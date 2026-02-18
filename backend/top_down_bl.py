"""
Combined Bottom-Up and Top-Down Black-Litterman Views

Demonstrates how to combine:
1. Bottom-up asset-level views (e.g., "AAPL will return 8%")
2. Top-down factor views (e.g., "Growth factor +3%")

Into a single stacked P, Q, Omega matrix for unified Black-Litterman inference.
"""
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

from openai import OpenAI

# Add backend directory to path for imports
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

import numpy as np
import pandas as pd
from app.services.bl_engine.bl_standalone import (
    BlackLittermanModel,
    EfficientFrontier,
    sample_cov,
    market_implied_prior_returns
)
from app.services.bl_engine.factor_views import FactorView, FactorViewTransformer


def create_synthetic_data():
    """
    Create synthetic price data and factor exposures for demonstration.
    
    Returns:
        tuple: (price_df, market_caps, factor_exposure_matrix, factor_names, asset_names)
    """
    # Define assets
    assets = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'JPM', 'BAC', 'WMT', 'PG', 'JNJ']
    n_assets = len(assets)
    
    # Generate synthetic price data (252 trading days)
    np.random.seed(42)
    n_days = 252
    
    # Starting prices
    start_prices = np.array([150, 300, 2800, 3300, 700, 140, 35, 145, 140, 165])
    
    # Generate returns with some correlation structure
    mean_returns = np.array([0.0003, 0.0004, 0.0003, 0.0005, 0.0006, 0.0002, 0.0002, 0.0001, 0.0001, 0.0001])
    
    # Correlation matrix (somewhat realistic structure)
    corr = np.eye(n_assets)
    # Tech stocks correlated
    for i in range(5):
        for j in range(5):
            if i != j:
                corr[i, j] = 0.6
    # Banks correlated
    corr[5, 6] = corr[6, 5] = 0.7
    # Consumer goods correlated
    corr[7, 8] = corr[8, 7] = 0.5
    corr[7, 9] = corr[9, 7] = 0.4
    corr[8, 9] = corr[9, 8] = 0.6
    
    volatilities = np.array([0.02, 0.022, 0.023, 0.025, 0.035, 0.018, 0.022, 0.015, 0.013, 0.014])
    
    # Create covariance matrix
    cov = np.outer(volatilities, volatilities) * corr
    
    # Generate returns
    returns = np.random.multivariate_normal(mean_returns, cov, n_days)
    
    # Convert to prices
    prices = np.zeros((n_days, n_assets))
    prices[0] = start_prices
    for t in range(1, n_days):
        prices[t] = prices[t-1] * (1 + returns[t])
    
    price_df = pd.DataFrame(prices, columns=assets)
    
    # Market capitalizations (in billions)
    market_caps = {
        'AAPL': 2800,
        'MSFT': 2400,
        'GOOGL': 1800,
        'AMZN': 1600,
        'TSLA': 800,
        'JPM': 450,
        'BAC': 280,
        'WMT': 400,
        'PG': 360,
        'JNJ': 420
    }
    
    # Define factor exposure matrix B
    # Factors: 0=Tech/Growth, 1=Financial, 2=Defensive/Consumer, 3=Market/Beta
    factor_names = ['Growth', 'Financial', 'Defensive', 'Market']
    n_factors = len(factor_names)
    
    # Factor exposures (n_assets x n_factors)
    # Each row = asset, each column = factor
    B = np.array([
        # AAPL: High growth, low financial, low defensive, high market
        [1.2, 0.0, 0.1, 1.1],
        # MSFT: High growth, low financial, low defensive, high market
        [1.1, 0.0, 0.2, 1.0],
        # GOOGL: High growth, low financial, low defensive, high market
        [1.3, 0.0, 0.1, 1.2],
        # AMZN: Very high growth, low financial, low defensive, high market
        [1.4, 0.0, 0.1, 1.3],
        # TSLA: Extreme growth, low financial, low defensive, very high market
        [1.6, 0.0, 0.0, 1.5],
        # JPM: Low growth, very high financial, low defensive, moderate market
        [0.2, 1.5, 0.2, 0.9],
        # BAC: Low growth, high financial, low defensive, moderate market
        [0.1, 1.3, 0.2, 0.8],
        # WMT: Low growth, low financial, moderate defensive, low market
        [0.3, 0.1, 1.1, 0.7],
        # PG: Low growth, low financial, high defensive, low market
        [0.2, 0.0, 1.3, 0.6],
        # JNJ: Low growth, low financial, very high defensive, low market
        [0.2, 0.0, 1.4, 0.6],
    ])
    
    return price_df, market_caps, B, factor_names, assets


def run_combined_bl(price_df, market_caps, B, asset_view, factor_views, tau=0.05, risk_aversion=2.5):
    """
    Run Black-Litterman with BOTH bottom-up asset views AND top-down factor views.
    
    Stacks the P, Q, and Omega matrices to create a unified view set.
    
    Args:
        price_df: Historical price data
        market_caps: Market capitalizations
        B: Factor exposure matrix
        asset_view: Tuple of (asset_index, expected_return, confidence) for bottom-up view
        factor_views: List of FactorView objects for top-down views
        tau: Uncertainty in prior
        risk_aversion: Risk aversion parameter
    
    Returns:
        dict: Portfolio results with combined views
    """
    print("\n" + "="*70)
    print("COMBINED BLACK-LITTERMAN: Bottom-Up + Top-Down Views")
    print("="*70)
    
    # Compute covariance and prior returns
    cov_matrix = sample_cov(price_df)
    pi = market_implied_prior_returns(market_caps, cov_matrix, risk_aversion)
    Sigma = cov_matrix.values
    assets = price_df.columns.tolist()
    n_assets = len(assets)
    
    # ==================== VIEWS ====================
    print("\n📊 VIEWS:")
    print("─" * 70)
    
    # Bottom-up view
    asset_idx, asset_return, asset_confidence = asset_view
    print(f"\n  Bottom-Up View:")
    print(f"    {assets[asset_idx]} expected return: {asset_return:.2%} (confidence: {asset_confidence:.2f})")
    
    # Top-down factor views
    print(f"\n  Top-Down Factor Views:")
    factor_names = ['Growth', 'Financial', 'Defensive', 'Market']
    for view in factor_views:
        print(f"    {factor_names[view.factor_index]} factor: {view.shock:+.2%} shock (confidence: {view.confidence:.2f})")
    
    # ==================== BUILD BOTTOM-UP MATRICES ====================
    # Bottom-up: single absolute view on one asset
    P_bottom = np.zeros((1, n_assets))
    P_bottom[0, asset_idx] = 1.0
    
    Q_bottom = np.array([asset_return])
    
    # Omega for bottom-up (scaled by confidence)
    omega_bottom = np.diag([tau * Sigma[asset_idx, asset_idx] / asset_confidence])
    
    print("\n" + "="*70)
    print("📐 BOTTOM-UP MATRICES:")
    print("─" * 70)
    print(f"\nP (Bottom-Up) - Shape {P_bottom.shape}:")
    print(P_bottom)
    print(f"\nQ (Bottom-Up) - Shape {Q_bottom.shape}:")
    print(Q_bottom)
    
    # ==================== BUILD TOP-DOWN MATRICES ====================
    transformer = FactorViewTransformer(B, tau, Sigma)
    P_top, Q_top, omega_top = transformer.build_matrices(factor_views)
    
    print("\n" + "="*70)
    print("📐 TOP-DOWN MATRICES:")
    print("─" * 70)
    print(f"\nP (Top-Down) - Shape {P_top.shape}:")
    print(P_top)
    print(f"\nQ (Top-Down) - Shape {Q_top.shape}:")
    print(Q_top)
    
    # ==================== STACK MATRICES ====================
    # Stack P matrices vertically
    P_combined = np.vstack([P_bottom, P_top])
    
    # Stack Q vectors
    Q_combined = np.concatenate([Q_bottom, Q_top])
    
    # Stack Omega matrices (block diagonal)
    n_bottom_views = P_bottom.shape[0]
    n_top_views = P_top.shape[0]
    n_total_views = n_bottom_views + n_top_views
    
    Omega_combined = np.zeros((n_total_views, n_total_views))
    Omega_combined[:n_bottom_views, :n_bottom_views] = omega_bottom
    Omega_combined[n_bottom_views:, n_bottom_views:] = omega_top
    
    print("\n" + "="*70)
    print("📐 COMBINED (STACKED) MATRICES:")
    print("─" * 70)
    print(f"\nP (Combined) - Shape {P_combined.shape}:")
    print(f"  (First {n_bottom_views} row(s): bottom-up, Next {n_top_views} rows: top-down)")
    print(f"\nQ (Combined) - Shape {Q_combined.shape}:")
    print(Q_combined)
    print(f"\nΩ (Combined) - Shape {Omega_combined.shape}:")
    print(f"  (Block diagonal: {n_bottom_views} bottom-up + {n_top_views} top-down views)")
    print(f"  Diagonal elements: {np.diag(Omega_combined)}")
    
    # ==================== RUN BLACK-LITTERMAN ====================
    bl = BlackLittermanModel(
        cov_matrix=cov_matrix,
        pi=pi,
        P=P_combined,
        Q=Q_combined,
        omega=Omega_combined,
        tau=tau
    )
    
    posterior_returns = bl.bl_returns()
    
    print("\n" + "="*70)
    print("📈 POSTERIOR RETURNS (Combined Views):")
    print("─" * 70)
    for asset, ret in posterior_returns.items():
        print(f"  {asset:6s}: {ret:7.2%}")
    
    # ==================== OPTIMIZE PORTFOLIO ====================
    ef = EfficientFrontier(posterior_returns, cov_matrix, risk_free_rate=0.02)
    ef.max_sharpe()
    weights = ef.clean_weights()
    
    print("\n" + "="*70)
    print("💼 FINAL PORTFOLIO ALLOCATION:")
    print("─" * 70)
    for asset, weight in weights.items():
        if weight > 0.001:
            print(f"  {asset:6s}: {weight:7.2%}")
    
    return {
        'weights': weights,
        'posterior_returns': posterior_returns,
        'P_combined': P_combined,
        'Q_combined': Q_combined,
        'Omega_combined': Omega_combined
    }


def main():
    """
    Main execution: demonstrates combining bottom-up and top-down views.
    """
    print("\n" + "="*70)
    print("BLACK-LITTERMAN: COMBINING BOTTOM-UP & TOP-DOWN VIEWS")
    print("="*70)
    print("\nThis demonstrates stacking asset-level and factor-level views")
    print("into a unified P, Q, Ω matrix for Black-Litterman inference.")
    
    # Create synthetic data
    price_df, market_caps, B, factor_names, assets = create_synthetic_data()
    
    print(f"\nPortfolio Setup:")
    print(f"  Assets: {len(assets)} ({', '.join(assets)})")
    print(f"  Factors: {len(factor_names)} ({', '.join(factor_names)})")
    print(f"  Historical days: {len(price_df)}")
    
    # Define bottom-up view: "MSFT will return 12%"
    asset_view = (
        1,      # asset_index for MSFT
        0.12,   # expected return (12%)
        0.7     # confidence
    )
    
    # Define top-down factor views
    factor_views = [
        # Growth factor will increase by 2%
        FactorView(factor_index=0, shock=0.02, confidence=0.8),
        # Financial factor will decrease by 1.5%
        FactorView(factor_index=1, shock=-0.015, confidence=0.6),
    ]
    
    # Run combined Black-Litterman
    results = run_combined_bl(
        price_df, market_caps, B, asset_view, factor_views,
        tau=0.05, risk_aversion=2.5
    )
    
    print("\n" + "="*70)
    print("✓ Successfully combined bottom-up and top-down views!")
    print("="*70)

#  Get yfinance data
def get_price_data():
    from app.services.price_data.data_fetch import read_from_sqlite
    from app.services.price_data.load_csv_to_db import save_to_sqlite, DB_PATH, TABLE_NAME
    df_db = read_from_sqlite()
    #  Drop the column name index
    df_db.drop(columns=['index'], inplace=True)
    save_to_sqlite(df_db, DB_PATH, TABLE_NAME)
    df_db = read_from_sqlite()
    return df_db
 
if __name__ == "__main__":
    # main()
    df_db = get_price_data()
    print(df_db.head())

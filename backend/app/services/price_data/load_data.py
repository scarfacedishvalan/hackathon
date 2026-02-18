"""
Load market data from SQLite and configuration files.

This module provides functions to load actual price data and market configuration
for Black-Litterman portfolio optimization.
"""
import json
from pathlib import Path

import numpy as np

from app.services.price_data.data_fetch import read_from_sqlite

# Backend directory is 4 levels up from this file
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent.parent


def load_market_data(as_dict: bool = False):
    """
    Load actual price data from SQLite and market configuration from JSON.
    
    Returns:
        tuple: (price_df, market_caps, factor_exposure_matrix, factor_names, asset_names)
        - price_df: DataFrame with historical price data (Date index, assets as columns)
        - market_caps: Dict mapping asset symbols to market capitalizations (billions USD)
        - factor_exposure_matrix: numpy array (n_assets x n_factors) with factor exposures
        - factor_names: List of factor names
        - asset_names: List of asset symbols
    """
    # Load market data configuration
    market_data_path = BACKEND_DIR / 'data' / 'market_data.json'
    with open(market_data_path, 'r') as f:
        market_data = json.load(f)
    
    # Get assets and other configuration from JSON
    assets = market_data['all_assets']
    market_caps = market_data['market_caps']
    factor_names = market_data['factor_names']
    factor_exposures = market_data['factor_exposures']
    
    # Build factor exposure matrix B (n_assets x n_factors)
    # Assets are in the order specified in JSON
    B = np.array([factor_exposures[asset] for asset in assets])
    
    # Read actual price data from SQLite
    df_db = read_from_sqlite()
    
    # The database has Date as index/column and tickers as columns
    # Filter for our assets and ensure proper datetime index
    if 'Date' in df_db.columns:
        df_db = df_db.set_index('Date')
    
    # Filter for assets we care about
    available_assets = [asset for asset in assets if asset in df_db.columns]
    
    if len(available_assets) < len(assets):
        missing = set(assets) - set(available_assets)
        print(f"Warning: Missing price data for assets: {missing}")
    
    # Create price dataframe with only our assets
    price_df = df_db[available_assets].copy()
    
    # Remove any NaN values
    price_df = price_df.dropna()
    
    print(f"\n✓ Loaded real price data:")
    print(f"  Assets: {len(available_assets)} ({', '.join(available_assets)})")
    print(f"  Date range: {price_df.index[0]} to {price_df.index[-1]}")
    print(f"  Trading days: {len(price_df)}")
    
    # Update assets list and B matrix to match available assets
    if len(available_assets) < len(assets):
        # Filter B matrix and market_caps for available assets
        asset_indices = [assets.index(asset) for asset in available_assets]
        B = B[asset_indices]
        market_caps = {k: v for k, v in market_caps.items() if k in available_assets}
        assets = available_assets
    if as_dict:
        return {
            'price_df': price_df.to_dict("records"),
            'market_caps': market_caps,
            'factor_exposure_matrix': B.tolist(),
            'factor_names': factor_names,
            'asset_names': assets
        }
    return price_df, market_caps, B, factor_names, assets

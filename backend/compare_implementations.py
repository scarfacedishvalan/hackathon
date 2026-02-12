"""
Comparison script demonstrating both pypfopt and standalone implementations.
"""

import numpy as np
import pandas as pd
from app.services.bl_engine.black_litterman import (
    run_black_litterman_standalone
)
from app.services.bl_engine.view_translation import (
    build_P_matrix,
    build_Q_vector,
    build_omega
)


def main():
    """Compare pypfopt vs standalone implementations."""
    
    # Example data with 5 data points (minimum for stable covariance with 3 assets)
    # Each asset has distinct price movements to ensure non-singular covariance
    price_df = pd.DataFrame({
        "AAPL": [100.0, 102.0, 105.0, 103.0, 107.0],
        "MSFT": [200.0, 198.0, 203.0, 205.0, 201.0],
        "GOOGL": [150.0, 152.0, 155.0, 158.0, 156.0]
    })

    market_caps = {
        "AAPL": 3000.0,
        "MSFT": 2800.0,
        "GOOGL": 1800.0
    }
    # Define views
    views = [
        {
            'type': 'relative',
            'asset_long': 'AAPL',
            'asset_short': 'MSFT',
            'value': 0.05,
            'confidence': 0.7
        }
    ]
    
    # Build matrices
    assets = list(price_df.columns)
    P = build_P_matrix(views, assets)
    Q = build_Q_vector(views)
    omega = build_omega(views)
    
    print("=" * 70)
    print("BLACK-LITTERMAN IMPLEMENTATION COMPARISON")
    print("=" * 70)
    
    # Run pypfopt implementation
    # print("\n--- Using PyPortfolioOpt (Original) ---")
    # try:
    #     result_pypfopt = run_black_litterman(
    #         price_df=price_df,
    #         market_caps=market_caps,
    #         P=P,
    #         Q=Q,
    #         omega=omega
    #     )
    #     print("✓ PyPortfolioOpt implementation successful")
    #     print(f"\nWeights: {result_pypfopt['weights']}")
    #     print(f"Posterior Returns: {result_pypfopt['posterior_returns']}")
    # except Exception as e:
    #     print(f"✗ PyPortfolioOpt implementation failed: {e}")
    #     result_pypfopt = None
    
    # # Run standalone implementation
    # print("\n" + "=" * 70)
    print("--- Using Standalone (No pypfopt) ---")
    try:
        result_standalone = run_black_litterman_standalone(
            price_df=price_df,
            market_caps=market_caps,
            P=P,
            Q=Q,
            omega=omega,
            risk_aversion=1.0,
            tau=0.05,
            risk_free_rate=0.02
        )
        print("✓ Standalone implementation successful")
        print(f"\nWeights: {result_standalone['weights']}")
        print(f"Posterior Returns: {result_standalone['posterior_returns']}")
        print(f"Prior Returns: {result_standalone['prior_returns']}")
    except Exception as e:
        print(f"✗ Standalone implementation failed: {e}")
        import traceback
        traceback.print_exc()
        result_standalone = None
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    main()

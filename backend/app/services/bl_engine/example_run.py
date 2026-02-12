"""
Example Black-Litterman Portfolio Allocation

Demonstrates end-to-end usage of the BL engine with sample data.
"""

import numpy as np
import pandas as pd
from black_litterman import run_black_litterman
from view_translation import build_P_matrix, build_Q_vector, build_omega
from metrics import compute_portfolio_metrics
from chart_formatters import allocation_to_chart, allocation_comparison


def main():
    """Run a complete Black-Litterman example."""
    
    # Set random seed for reproducibility
    np.random.seed(42)
    
    # Define assets
    assets = ["AAPL", "MSFT", "GOOGL", "JNJ"]
    
    # Generate random price data (252 trading days)
    dates = pd.date_range(start="2023-01-01", periods=252, freq="B")
    
    # Simulate price data with random walks
    price_data = {}
    for asset in assets:
        initial_price = 100.0
        returns = np.random.randn(252) * 0.015  # Daily returns ~1.5% std
        prices = initial_price * np.exp(np.cumsum(returns))
        price_data[asset] = prices
    
    price_df = pd.DataFrame(price_data, index=dates)
    
    print("=" * 60)
    print("BLACK-LITTERMAN PORTFOLIO ALLOCATION EXAMPLE")
    print("=" * 60)
    print("\nSample Price Data:")
    print(price_df.head())
    print("\nPrice Statistics:")
    print(price_df.describe())
    
    # Define market capitalizations (in billions)
    market_caps = {
        "AAPL": 3000.0,
        "MSFT": 2800.0,
        "GOOGL": 1800.0,
        "JNJ": 450.0
    }
    
    # Define one relative view: AAPL outperforms MSFT by 5%
    views = [
        {
            "type": "relative",
            "asset_long": "AAPL",
            "asset_short": "MSFT",
            "value": 0.05,  # 5% outperformance
            "confidence": 0.7  # 70% confidence
        }
    ]
    
    # Build P, Q, and omega matrices
    P = build_P_matrix(views, assets)
    Q = build_Q_vector(views)
    omega = build_omega(views)
    
    print("\n" + "=" * 60)
    print("VIEW CONFIGURATION")
    print("=" * 60)
    print(f"\nView: AAPL outperforms MSFT by 5% (confidence: 70%)")
    print(f"\nP Matrix (Pick Matrix):")
    print(P)
    print(f"\nQ Vector (Expected Returns):")
    print(Q)
    print(f"\nOmega Matrix (Uncertainty):")
    print(omega)
    
    # Run Black-Litterman allocation
    print("\n" + "=" * 60)
    print("RUNNING BLACK-LITTERMAN MODEL...")
    print("=" * 60)
    
    result = run_black_litterman(
        price_df=price_df,
        market_caps=market_caps,
        P=P,
        Q=Q,
        omega=omega
    )
    
    # Extract results
    weights = result["weights"]
    posterior_returns = result["posterior_returns"]
    
    # Print weights
    print("\n" + "=" * 60)
    print("OPTIMAL PORTFOLIO WEIGHTS")
    print("=" * 60)
    for asset, weight in weights.items():
        print(f"{asset:10s}: {weight:8.2%}")
    print(f"{'Total':10s}: {sum(weights.values()):8.2%}")
    
    # Print posterior returns
    print("\n" + "=" * 60)
    print("POSTERIOR EXPECTED RETURNS")
    print("=" * 60)
    for asset, ret in posterior_returns.items():
        print(f"{asset:10s}: {ret:8.2%}")
    
    # Compute portfolio metrics
    from pypfopt import risk_models
    cov_matrix = risk_models.sample_cov(price_df)
    
    metrics = compute_portfolio_metrics(
        weights=weights,
        mu=posterior_returns,
        cov=cov_matrix.values
    )
    
    print("\n" + "=" * 60)
    print("PORTFOLIO METRICS")
    print("=" * 60)
    print(f"Expected Return: {metrics['expected_return']:8.2%}")
    print(f"Volatility:      {metrics['volatility']:8.2%}")
    print(f"Sharpe Ratio:    {metrics['sharpe']:8.2f}")
    
    # Format chart data
    chart_data = allocation_to_chart(weights)
    
    print("\n" + "=" * 60)
    print("CHART DATA (Allocation)")
    print("=" * 60)
    for item in chart_data:
        print(f"{item['asset']:10s}: {item['weight']:8.2%}")
    
    # Create a baseline comparison (equal weight)
    baseline_weights = {asset: 1.0 / len(assets) for asset in assets}
    comparison = allocation_comparison(baseline_weights, weights)
    
    print("\n" + "=" * 60)
    print("ALLOCATION COMPARISON (vs Equal Weight)")
    print("=" * 60)
    print(f"{'Asset':10s} {'Baseline':>10s} {'BL':>10s} {'Delta':>10s}")
    print("-" * 60)
    for item in comparison:
        print(f"{item['asset']:10s} {item['baseline']:10.2%} {item['stressed']:10.2%} {item['delta']:+10.2%}")
    
    print("\n" + "=" * 60)
    print("EXAMPLE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()

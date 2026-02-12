"""
Unit tests for the Black-Litterman portfolio allocation engine.
"""

import numpy as np
import pandas as pd
import sys
from pathlib import Path

# Add backend directory to path
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.bl_engine import (
    run_black_litterman,
    build_P_matrix,
    build_Q_vector,
    build_omega,
    compute_portfolio_metrics,
    allocation_to_chart,
    allocation_comparison,
)


def test_view_translation():
    """Test view translation functions."""
    print("Testing view translation...")
    
    assets = ["AAPL", "MSFT", "GOOGL", "JNJ"]
    
    # Test relative view
    views = [
        {
            "type": "relative",
            "asset_long": "AAPL",
            "asset_short": "MSFT",
            "value": 0.05,
            "confidence": 0.7
        },
        {
            "type": "absolute",
            "asset_long": "GOOGL",
            "asset_short": None,
            "value": 0.10,
            "confidence": 0.8
        }
    ]
    
    # Build matrices
    P = build_P_matrix(views, assets)
    Q = build_Q_vector(views)
    omega = build_omega(views)
    
    # Validate P matrix shape and values
    assert P.shape == (2, 4), f"P shape should be (2, 4), got {P.shape}"
    assert P[0, 0] == 1.0, "AAPL should be +1 in first view"
    assert P[0, 1] == -1.0, "MSFT should be -1 in first view"
    assert P[1, 2] == 1.0, "GOOGL should be +1 in second view"
    
    # Validate Q vector
    assert Q.shape == (2,), f"Q shape should be (2,), got {Q.shape}"
    assert Q[0] == 0.05, "First view should be 0.05"
    assert Q[1] == 0.10, "Second view should be 0.10"
    
    # Validate omega matrix
    assert omega.shape == (2, 2), f"Omega shape should be (2, 2), got {omega.shape}"
    assert omega[0, 0] > 0, "Omega diagonal should be positive"
    assert omega[1, 1] > 0, "Omega diagonal should be positive"
    assert omega[0, 1] == 0, "Omega should be diagonal"
    
    print("✓ View translation tests passed")


def test_metrics():
    """Test portfolio metrics computation."""
    print("Testing portfolio metrics...")
    
    # Simple test case
    weights = {"AAPL": 0.5, "MSFT": 0.5}
    mu = {"AAPL": 0.10, "MSFT": 0.08}
    cov = np.array([
        [0.04, 0.01],
        [0.01, 0.03]
    ])
    
    metrics = compute_portfolio_metrics(weights, mu, cov)
    
    # Validate metrics structure
    assert "expected_return" in metrics
    assert "volatility" in metrics
    assert "sharpe" in metrics
    
    # Validate expected return calculation
    expected_return = 0.5 * 0.10 + 0.5 * 0.08
    assert abs(metrics["expected_return"] - expected_return) < 1e-6, "Expected return mismatch"
    
    # Validate volatility is positive
    assert metrics["volatility"] > 0, "Volatility should be positive"
    
    # Validate Sharpe ratio
    assert metrics["sharpe"] > 0, "Sharpe ratio should be positive"
    
    print("✓ Portfolio metrics tests passed")


def test_chart_formatters():
    """Test chart formatting functions."""
    print("Testing chart formatters...")
    
    # Test allocation_to_chart
    weights = {"AAPL": 0.5, "MSFT": 0.3, "GOOGL": 0.2}
    chart_data = allocation_to_chart(weights)
    
    assert len(chart_data) == 3, "Should have 3 items"
    assert chart_data[0]["asset"] == "AAPL", "Should be sorted by weight descending"
    assert chart_data[0]["weight"] == 0.5, "AAPL weight should be 0.5"
    
    # Test allocation_comparison
    baseline = {"AAPL": 0.25, "MSFT": 0.25, "GOOGL": 0.25, "JNJ": 0.25}
    stressed = {"AAPL": 0.5, "MSFT": 0.2, "GOOGL": 0.2, "JNJ": 0.1}
    comparison = allocation_comparison(baseline, stressed)
    
    assert len(comparison) == 4, "Should have 4 items"
    assert "asset" in comparison[0], "Should have asset key"
    assert "baseline" in comparison[0], "Should have baseline key"
    assert "stressed" in comparison[0], "Should have stressed key"
    assert "delta" in comparison[0], "Should have delta key"
    
    # Verify deltas are calculated correctly
    for item in comparison:
        if item["asset"] == "AAPL":
            assert abs(item["delta"] - 0.25) < 1e-6, "AAPL delta should be 0.25"
    
    print("✓ Chart formatter tests passed")


def test_black_litterman_integration():
    """Test the complete Black-Litterman workflow."""
    print("Testing Black-Litterman integration...")
    
    # Set seed for reproducibility
    np.random.seed(42)
    
    # Generate sample data
    assets = ["AAPL", "MSFT", "GOOGL"]
    dates = pd.date_range(start="2023-01-01", periods=100, freq="B")
    
    price_data = {}
    for asset in assets:
        returns = np.random.randn(100) * 0.01
        prices = 100.0 * np.exp(np.cumsum(returns))
        price_data[asset] = prices
    
    price_df = pd.DataFrame(price_data, index=dates)
    
    # Define market caps
    market_caps = {
        "AAPL": 3000.0,
        "MSFT": 2800.0,
        "GOOGL": 1800.0
    }
    
    # Define a simple view
    views = [
        {
            "type": "relative",
            "asset_long": "AAPL",
            "asset_short": "MSFT",
            "value": 0.05,
            "confidence": 0.7
        }
    ]
    
    # Build matrices
    P = build_P_matrix(views, assets)
    Q = build_Q_vector(views)
    omega = build_omega(views)
    
    # Run Black-Litterman
    result = run_black_litterman(
        price_df=price_df,
        market_caps=market_caps,
        P=P,
        Q=Q,
        omega=omega
    )
    
    # Validate results
    assert "weights" in result, "Result should have weights"
    assert "posterior_returns" in result, "Result should have posterior_returns"
    
    weights = result["weights"]
    posterior_returns = result["posterior_returns"]
    
    # Validate weights
    assert len(weights) == 3, "Should have 3 weights"
    total_weight = sum(weights.values())
    assert abs(total_weight - 1.0) < 1e-6, f"Weights should sum to 1, got {total_weight}"
    
    # Validate all weights are non-negative
    for asset, weight in weights.items():
        assert weight >= 0, f"Weight for {asset} should be non-negative, got {weight}"
    
    # Validate posterior returns
    assert len(posterior_returns) == 3, "Should have 3 posterior returns"
    
    print("✓ Black-Litterman integration tests passed")


def test_deterministic_behavior():
    """Test that the engine produces deterministic results."""
    print("Testing deterministic behavior...")
    
    np.random.seed(123)
    
    # Generate sample data
    assets = ["AAPL", "MSFT"]
    dates = pd.date_range(start="2023-01-01", periods=50, freq="B")
    
    price_data = {
        "AAPL": 100.0 * np.exp(np.cumsum(np.random.randn(50) * 0.01)),
        "MSFT": 100.0 * np.exp(np.cumsum(np.random.randn(50) * 0.01))
    }
    price_df = pd.DataFrame(price_data, index=dates)
    
    market_caps = {"AAPL": 3000.0, "MSFT": 2800.0}
    views = [{"type": "absolute", "asset_long": "AAPL", "asset_short": None, "value": 0.08, "confidence": 0.6}]
    
    P = build_P_matrix(views, assets)
    Q = build_Q_vector(views)
    omega = build_omega(views)
    
    # Run twice and compare
    result1 = run_black_litterman(price_df, market_caps, P, Q, omega)
    result2 = run_black_litterman(price_df, market_caps, P, Q, omega)
    
    # Results should be identical
    for asset in assets:
        assert abs(result1["weights"][asset] - result2["weights"][asset]) < 1e-10, \
            f"Weights should be deterministic for {asset}"
        assert abs(result1["posterior_returns"][asset] - result2["posterior_returns"][asset]) < 1e-10, \
            f"Posterior returns should be deterministic for {asset}"
    
    print("✓ Deterministic behavior tests passed")


def main():
    """Run all tests."""
    print("=" * 60)
    print("BLACK-LITTERMAN ENGINE UNIT TESTS")
    print("=" * 60)
    print()
    
    try:
        test_view_translation()
        test_metrics()
        test_chart_formatters()
        test_black_litterman_integration()
        test_deterministic_behavior()
        
        print()
        print("=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"TEST FAILED: {e}")
        print("=" * 60)
        return 1
    except Exception as e:
        print()
        print("=" * 60)
        print(f"ERROR: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

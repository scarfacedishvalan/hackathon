"""
Simple test script for the bt (backtesting) package.
"""
import bt
import pandas as pd
import numpy as np

def main():
    # Create some simple price data
    np.random.seed(42)
    dates = pd.date_range(start="2020-01-01", periods=252, freq="B")
    
    # Simulate two stocks with random walk prices
    data = pd.DataFrame(
        {
            "AAPL": 100 * (1 + np.random.randn(252).cumsum() * 0.02),
            "MSFT": 150 * (1 + np.random.randn(252).cumsum() * 0.02),
        },
        index=dates,
    )
    
    print("Sample price data:")
    print(data.head())
    print()

    # Define a simple equal-weight strategy
    strategy = bt.Strategy(
        "EqualWeight",
        [
            bt.algos.RunMonthly(),          # Rebalance monthly
            bt.algos.SelectAll(),           # Select all securities
            bt.algos.WeighEqually(),        # Equal weight allocation
            bt.algos.Rebalance(),           # Rebalance portfolio
        ],
    )

    # Create a backtest
    backtest = bt.Backtest(strategy, data)

    # Run the backtest
    print("Running backtest...")
    result = bt.run(backtest)

    # Display results
    print("\n=== Backtest Results ===")
    print(result.display())

    print("\n=== Stats ===")
    print(result.stats)

    # Plot if matplotlib is available
    # try:
    #     result.plot(title="Equal Weight Strategy")
    #     print("\nPlot generated (check your display or save it).")
    # except Exception as e:
    #     print(f"\nCould not plot: {e}")

    print("\n✅ bt package is working correctly!")


if __name__ == "__main__":
    main()

"""
Simple test script for the backtesting.py package.
Install with: pip install backtesting
"""
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from backtesting.test import SMA, GOOG  # sample data & indicator


class SmaCross(Strategy):
    """
    Simple Moving Average crossover strategy.
    Buy when fast SMA crosses above slow SMA.
    Sell when fast SMA crosses below slow SMA.
    """
    # Define parameters (can be optimized)
    fast_period = 10
    slow_period = 20

    def init(self):
        # Precompute the two SMAs
        price = self.data.Close
        self.fast_sma = self.I(SMA, price, self.fast_period)
        self.slow_sma = self.I(SMA, price, self.slow_period)

    def next(self):
        # If fast crosses above slow, buy
        if crossover(self.fast_sma, self.slow_sma):
            self.buy()
        # If fast crosses below slow, sell
        elif crossover(self.slow_sma, self.fast_sma):
            self.sell()


def main():
    # GOOG is sample Google stock data included with backtesting.py
    print("Sample data (GOOG):")
    print(GOOG.head())
    print()

    # Create backtest
    bt = Backtest(
        GOOG,
        SmaCross,
        cash=10_000,
        commission=0.002,  # 0.2% commission
        exclusive_orders=True,
    )

    # Run backtest
    print("Running backtest...")
    stats = bt.run()

    # Display results
    print("\n=== Backtest Results ===")
    print(stats)

    # Optimize parameters (optional)
    print("\n=== Optimizing SMA periods ===")
    stats_opt = bt.optimize(
        fast_period=range(5, 15, 2),
        slow_period=range(15, 30, 5),
        maximize="Return [%]",
    )
    print(f"Best params: fast={stats_opt._strategy.fast_period}, slow={stats_opt._strategy.slow_period}")
    print(f"Optimized Return: {stats_opt['Return [%]']:.2f}%")

    # Plot (opens in browser)
    try:
        bt.plot(filename="backtest_result.html", open_browser=False)
        print("\n✅ Plot saved to backtest_result.html")
    except Exception as e:
        print(f"\nCould not generate plot: {e}")

    print("\n✅ backtesting.py package is working correctly!")


if __name__ == "__main__":
    main()

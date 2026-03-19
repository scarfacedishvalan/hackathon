"""
Test script for BuyAndHold strategy fix.
Tests the exact scenario the user reported: BuyAndHold from 2020-01-01 to 2024-01-01 with $25,000 cash.
"""

import logging
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from app.orchestrators.backtest_orchestrator import run_recipe

# Test recipe matching user's request
test_recipe = {
    "strategy_name": "BuyAndHold",
    "data": {
        "symbol": "AAPL",  # Default symbol for testing
        "start": "2020-01-01",
        "end": "2024-01-01"
    },
    "backtest": {
        "cash": 25000.0,
        "commission": 0.001
    }
}

print("=" * 80)
print("Testing BuyAndHold strategy with user's parameters:")
print(f"  Symbol: {test_recipe['data']['symbol']}")
print(f"  Period: {test_recipe['data']['start']} to {test_recipe['data']['end']}")
print(f"  Cash: ${test_recipe['backtest']['cash']:,.2f}")
print("=" * 80)

try:
    result = run_recipe(test_recipe)
    print("\n" + "=" * 80)
    print("SUCCESS! Backtest completed without errors.")
    print("=" * 80)
    print("\nMetrics:")
    for key, value in result["metrics"].items():
        if value is not None:
            print(f"  {key}: {value}")
    print(f"\nEquity curve points: {len(result['equityCurve'])}")
    print(f"Number of trades: {result['metrics']['numTrades']}")
    print("=" * 80)
except Exception as e:
    print("\n" + "=" * 80)
    print(f"ERROR: {type(e).__name__}: {e}")
    print("=" * 80)
    import traceback
    traceback.print_exc()
    sys.exit(1)

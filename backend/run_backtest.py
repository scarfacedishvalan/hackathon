"""
Runner script for portfolio backtesting
Usage: python run_backtest.py
"""
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.services.price_data.data_fetch import PriceData
from app.services.backtest.portfolio_backtest import PortfolioBtest

if __name__ == "__main__":
    pricedata = PriceData()
    chosen_assets = ["NIFTYBEES", "CPSEETF", "JUNIORBEES", "MON100", "MOM100", "CONSUMBEES"]
    bnds = ((0.1, 1), (0.05, 1), (0.05, 0.5), (0.05, 0.5), (0.1, 0.5), (0.05, 1))
    pbtest = PortfolioBtest(pricedata, chosen_assets=chosen_assets, bounds=bnds)
    results = pbtest.run_bt_new()
    print(results)

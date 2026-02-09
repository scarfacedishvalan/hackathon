"""
Runner script for recipe handler
Usage: python run_recipe_handler.py
"""
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.services.recipe_interpreter.recipe_handler import (
    load_json_recipe,
    strategy_runner
)
from app.services.price_data.data_fetch import PriceData

if __name__ == "__main__":
    # Load JSON recipe
    recipe = load_json_recipe(r"C:\Python\portfolio-project\recipe2.json")
    
    # Set up price data
    chosen_assets = ["NIFTYBEES_NS", "CPSEETF_NS", "JUNIORBEES_NS", "MON100_NS", "MOM100_NS", "CONSUMBEES_NS"]

    pricedata = PriceData(asset_list=chosen_assets)
    data = pricedata._dfraw
    
    # Run strategy
    results = strategy_runner(data=data, recipe=recipe)
    print(results)

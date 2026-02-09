"""
Recipe Generator Service
Mock implementation - to be replaced with actual backtesting logic
"""
from typing import List, Dict, Any
import random
from .recipe_interpreter.llm_parser import parse_text_to_json
from .recipe_interpreter.dict_compare import print_comparison_report

def generate_recipe(stocks: List[str], strategy_instruction: str) -> Dict[str, Any]:
    """
    Generate a mock recipe and backtest results.
    
    This is a placeholder function that returns mock data.
    Replace this with actual backtesting implementation later.
    
    Args:
        stocks: List of stock tickers
        strategy_instruction: Natural language strategy description
        
    Returns:
        Dictionary containing recipe, equity curve, and summary statistics
    """
    
    # Parse basic strategy info from instruction (mock parsing)
    recipe = parse_text_to_json(strategy_instruction)
    strategy_name = recipe.get("strategy", "null")
    lookbacks = recipe.get("lookbacks", "null")
    rebalance = recipe.get("rebalance", "yearly")
    # Generate mock equity curve data
    equity_curve = generate_mock_equity_curve()
    
    # Generate mock summary statistics
    summary_stats = generate_mock_summary_stats()
    
    return {
        "recipe": recipe,
        "equity_curve": equity_curve,
        "summary_stats": summary_stats
    }


def generate_mock_equity_curve() -> List[Dict[str, Any]]:
    """Generate mock equity curve data"""
    dates = [
        '2020-01', '2020-04', '2020-07', '2020-10',
        '2021-01', '2021-04', '2021-07', '2021-10',
        '2022-01', '2022-04', '2022-07', '2022-10',
        '2023-01', '2023-04', '2023-07', '2023-10',
        '2024-01', '2024-04', '2024-07', '2024-10',
    ]
    
    equity_curve = []
    base_value = 100000
    
    for i, date in enumerate(dates):
        # Add some randomness to make it more realistic
        growth = 1 + (random.random() * 0.15 - 0.03)  # -3% to +12% per period
        base_value *= growth
        equity_curve.append({
            "date": date,
            "value": round(base_value, 2)
        })
    
    return equity_curve


def generate_mock_summary_stats() -> Dict[str, str]:
    """Generate mock summary statistics"""
    return {
        "cagr": f"{random.uniform(12.0, 25.0):.1f}%",
        "sharpe_ratio": f"{random.uniform(1.0, 2.0):.2f}",
        "max_drawdown": f"-{random.uniform(8.0, 20.0):.1f}%",
        "volatility": f"{random.uniform(12.0, 18.0):.1f}%"
    }


if __name__ == "__main__":
    # Example usage
    stocks = ["AAPL", "MSFT", "GOOGL"]
    instruction = "Run the strategies WeighMeanVar and RiskParity with lookbacks 3y, 2y and 1y with yearly rebalance"
    import json
    test_cases = r"C:\Python\hackathon\backend\app\services\recipe_interpreter\test_cases.json"
    with open(test_cases, 'r') as f:
        test_cases_data = json.load(f)
    test_outputs_dict = {"test_outputs": []}
    for test_case in test_cases_data["test_cases"]:
        instruction = test_case["instruction"]
        result = parse_text_to_json(instruction)
        d = {"instruction": instruction, "result": result}
        test_outputs_dict["test_outputs"].append(d)
        expected_output = test_case["expected_output"]
        print(f"Testing instruction: {instruction}")
        print_comparison_report(result, expected_output)  
        print("-" * 80)
    with open(r"C:\Python\hackathon\backend\app\services\recipe_interpreter\test_outputs.json", 'w') as f:
        json.dump(test_outputs_dict, f, indent=2)
    # result = generate_recipe(stocks, instruction)
    # print(result)
"""
Test script for the Black-Litterman Parser API endpoint.

This script demonstrates how to call the /api/parse-bl-views endpoint
with various investment views and display the structured output.
"""

import requests
import json
from typing import Dict, Any


def test_parse_bl_views(
    investor_text: str,
    assets: list = None,
    factors: list = None,
    use_schema: bool = True,
    base_url: str = "http://localhost:8000"
) -> Dict[str, Any]:
    """
    Test the BL parser endpoint with given parameters.
    
    Args:
        investor_text: Natural language investment views
        assets: Optional list of asset symbols
        factors: Optional list of factor names
        use_schema: Whether to use strict schema validation
        base_url: Base URL of the API server
        
    Returns:
        Parsed views as dictionary
    """
    endpoint = f"{base_url}/api/parse-bl-views"
    
    payload = {
        "investor_text": investor_text,
        "use_schema": use_schema
    }
    
    if assets:
        payload["assets"] = assets
    if factors:
        payload["factors"] = factors
    
    print(f"\n{'='*60}")
    print(f"Testing BL Parser Endpoint")
    print(f"{'='*60}")
    print(f"Investor Text: {investor_text}")
    print(f"Assets: {assets or 'Default'}")
    print(f"Factors: {factors or 'Default'}")
    print(f"\n{'='*60}")
    
    try:
        response = requests.post(endpoint, json=payload)
        response.raise_for_status()
        
        result = response.json()
        
        print("\n✅ Parsing successful!")
        print(f"\nBottom-up views: {len(result['bottom_up_views'])}")
        for i, view in enumerate(result['bottom_up_views'], 1):
            print(f"\n  View {i}:")
            print(f"    Type: {view['type']}")
            print(f"    Label: {view['label']}")
            print(f"    Confidence: {view['confidence']}")
            if view['type'] == 'absolute':
                print(f"    Asset: {view.get('asset')}")
                print(f"    Expected Return: {view.get('expected_return')}")
            else:
                print(f"    Assets: {view.get('assets')}")
                print(f"    Expected Outperformance: {view.get('expected_outperformance')}")
        
        print(f"\nTop-down views (Factor shocks): {len(result['top_down_views']['factor_shocks'])}")
        for i, shock in enumerate(result['top_down_views']['factor_shocks'], 1):
            print(f"\n  Shock {i}:")
            print(f"    Factor: {shock['factor']}")
            print(f"    Shock: {shock['shock']}")
            print(f"    Confidence: {shock['confidence']}")
            print(f"    Label: {shock['label']}")
        
        return result
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to API server.")
        print("Make sure the server is running: uvicorn app.main:app --reload --port 8000")
        return {}
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ HTTP Error: {e}")
        print(f"Response: {response.text}")
        return {}
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return {}


def main():
    """Run test cases for the BL parser endpoint."""
    
    # Test Case 1: Simple tech sector views
    print("\n" + "="*60)
    print("TEST CASE 1: Tech Sector Views")
    print("="*60)
    test_parse_bl_views(
        investor_text="I believe technology stocks will outperform the market by 5% this year. "
                     "Apple should beat Microsoft by 2% due to strong iPhone sales.",
        assets=["AAPL", "MSFT", "GOOGL", "AMZN"],
        factors=["Growth", "Rates", "Momentum", "Value"]
    )
    
    # Test Case 2: Financial sector rotation
    print("\n" + "="*60)
    print("TEST CASE 2: Financial Sector Rotation")
    print("="*60)
    test_parse_bl_views(
        investor_text="I expect banks to underperform due to rising interest rate risk. "
                     "JPMorgan should return -3% over the next quarter. "
                     "Value stocks will see a positive 4% factor shock.",
        assets=["JPM", "BAC", "GS", "AAPL", "MSFT"],
        factors=["Growth", "Rates", "Momentum", "Value"]
    )
    
    # Test Case 3: Multiple views with mixed sentiment
    print("\n" + "="*60)
    print("TEST CASE 3: Mixed Sentiment Views")
    print("="*60)
    test_parse_bl_views(
        investor_text="Growth stocks look overvalued and should see a -2% factor shock. "
                     "Tesla will outperform Amazon by 10% due to EV market expansion. "
                     "Google is expected to return 8% absolute due to AI advantages.",
        assets=["TSLA", "AMZN", "GOOGL", "AAPL"],
        factors=["Growth", "Rates", "Momentum", "Value"]
    )
    
    # Test Case 4: Using default assets and factors
    print("\n" + "="*60)
    print("TEST CASE 4: Default Assets and Factors")
    print("="*60)
    test_parse_bl_views(
        investor_text="I'm bullish on tech mega-caps. AAPL should beat the market by 3%. "
                     "Momentum factor will see a 5% positive shock."
    )
    
    print("\n" + "="*60)
    print("All tests completed!")
    print("="*60)


if __name__ == "__main__":
    main()

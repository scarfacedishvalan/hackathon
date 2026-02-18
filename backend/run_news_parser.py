"""
Example demonstration of article to Black-Litterman view extraction.

This script demonstrates:
1. Loading an example article
2. Calling the parser
3. Displaying structured JSON output

Expected output: A relative view where MSFT outperforms AAPL.
"""

import json
import os
from app.services.news_api.view_parser import parse_article_to_views


# Example article (exact as specified)
EXAMPLE_ARTICLE = """TITLE: Analysts expect Microsoft to outperform Apple
SOURCE: CNBC

CONTENT:
Several analysts raised Microsoft price targets and expect the company
to outperform Apple over the next year."""


def main():
    """
    Run the example article through the view extraction system.
    """
    print("=" * 80)
    print("BLACK-LITTERMAN VIEW EXTRACTION - EXAMPLE RUN")
    print("=" * 80)
    print()
    
    print("INPUT ARTICLE:")
    print("-" * 80)
    print(EXAMPLE_ARTICLE)
    print("-" * 80)
    print()
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable not set")
        print("Please set it before running this example:")
        print("  export OPENAI_API_KEY='your-key-here'  # Unix/Mac")
        print("  $env:OPENAI_API_KEY='your-key-here'    # Windows PowerShell")
        return
    
    print("Calling LLM to extract views...")
    print()
    
    try:
        # Parse article to views
        views = parse_article_to_views(EXAMPLE_ARTICLE)
        
        print("EXTRACTED VIEWS:")
        print("-" * 80)
        print(json.dumps(views, indent=2))
        print("-" * 80)
        print()
        
        # Display summary
        print(f"SUCCESS: Extracted {len(views)} view(s)")
        print()
        
        # Show expected output for comparison
        expected_output = [
            {
                "type": "relative",
                "asset_long": "MSFT",
                "asset_short": "AAPL",
                "factor": None,
                "direction": "positive",
                "confidence": "medium",
                "source": "CNBC"
            }
        ]
        
        print("EXPECTED OUTPUT:")
        print("-" * 80)
        print(json.dumps(expected_output, indent=2))
        print("-" * 80)
        print()
        
        # Compare
        if views == expected_output:
            print("✓ Output matches expected result exactly!")
        else:
            print("⚠ Output differs from expected result")
            print("This may be due to LLM variability, but the structure should be correct.")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

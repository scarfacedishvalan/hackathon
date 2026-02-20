#!/usr/bin/env python3
"""
CLI script for testing the Black-Litterman stress test LLM parser.

This script demonstrates how to use the stress test parser with various
example stress test requests.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

from app.services.bl_stress import parse_stress_prompt, available_stress_types


BACKEND_DIR = Path(__file__).resolve().parent
EXAMPLE_RECIPE_PATH = BACKEND_DIR / "app" / "services" / "bl_stress" / "example_recipe.json"


def load_example_recipe() -> Dict:
    """
    Load the example recipe JSON file.
    
    Returns:
        Dictionary containing the recipe
        
    Raises:
        FileNotFoundError: If example recipe file is not found
    """
    if not EXAMPLE_RECIPE_PATH.exists():
        raise FileNotFoundError(f"Example recipe not found: {EXAMPLE_RECIPE_PATH}")
    
    with open(EXAMPLE_RECIPE_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_recipe_context(recipe: Dict) -> Dict:
    """
    Extract view labels and factors from a recipe for context.
    
    Args:
        recipe: Full recipe dictionary
        
    Returns:
        Dictionary with 'views' and 'factors' lists
    """
    context = {
        "views": [],
        "factors": []
    }
    
    # Extract bottom-up view labels
    if "bottom_up_views" in recipe:
        for view in recipe["bottom_up_views"]:
            if "label" in view:
                context["views"].append(view["label"])
    
    # Extract factors
    if "top_down_views" in recipe:
        top_down = recipe["top_down_views"]
        if "factor_model" in top_down and "factors" in top_down["factor_model"]:
            context["factors"] = top_down["factor_model"]["factors"]
    
    return context


# Predefined test cases
TEST_CASES = [
    {
        "name": "Stress specific view magnitude",
        "request": "I want to stress test how sensitive the portfolio is to the AAPL vs MSFT view with a standard range"
    },
    {
        "name": "Stress all view confidences",
        "request": "What if we're less confident in all our views? Use aggressive range"
    },
    {
        "name": "Amplify momentum factor",
        "request": "Amplify the Momentum factor influence with aggressive scaling"
    },
    {
        "name": "Test tau uncertainty",
        "request": "Test different tau values using a conservative grid"
    },
    {
        "name": "High volatility scenario",
        "request": "Simulate a high volatility environment with standard intensity"
    },
    {
        "name": "Apply crisis regime",
        "request": "Apply the crisis regime template"
    },
    {
        "name": "Joint view stress",
        "request": "Jointly stress both magnitude and confidence for the NVDA outperforms META view, use standard for magnitude and conservative for confidence"
    },
    {
        "name": "Apply high uncertainty regime",
        "request": "Test the portfolio under high uncertainty conditions"
    },
]


def run_single_test(
    request: str,
    recipe_context: Dict,
    verbose: bool = True
) -> bool:
    """
    Run a single stress test parsing request.
    
    Args:
        request: Natural language stress test request
        recipe_context: Recipe context with views and factors
        verbose: If True, print detailed output
        
    Returns:
        True if parsing succeeded, False otherwise
    """
    if verbose:
        print(f"\nRequest: {request}")
        print("-" * 80)
    
    try:
        spec = parse_stress_prompt(request, recipe_context=recipe_context)
        
        if verbose:
            print("✓ Successfully parsed")
            print("\nStressSpec:")
            print(json.dumps(spec.model_dump(), indent=2))
        
        return True
        
    except Exception as e:
        if verbose:
            print(f"✗ Parsing failed: {e}")
        return False


def run_test_suite(recipe_context: Dict) -> int:
    """
    Run all predefined test cases.
    
    Args:
        recipe_context: Recipe context with views and factors
        
    Returns:
        Exit code (0 if all tests passed, 1 otherwise)
    """
    print("=" * 80)
    print("STRESS TEST PARSER - TEST SUITE")
    print("=" * 80)
    
    print(f"\nRecipe context loaded:")
    print(f"  - {len(recipe_context['views'])} views")
    print(f"  - {len(recipe_context['factors'])} factors")
    
    passed = 0
    failed = 0
    
    for i, case in enumerate(TEST_CASES, start=1):
        print(f"\n{'=' * 80}")
        print(f"Test Case {i}/{len(TEST_CASES)}: {case['name']}")
        print(f"{'=' * 80}")
        
        success = run_single_test(case["request"], recipe_context, verbose=True)
        
        if success:
            passed += 1
        else:
            failed += 1
    
    print(f"\n{'=' * 80}")
    print("TEST SUMMARY")
    print(f"{'=' * 80}")
    print(f"Passed: {passed}/{len(TEST_CASES)}")
    print(f"Failed: {failed}/{len(TEST_CASES)}")
    
    return 0 if failed == 0 else 1


def interactive_mode(recipe_context: Dict):
    """
    Run in interactive mode, accepting user input.
    
    Args:
        recipe_context: Recipe context with views and factors
    """
    print("=" * 80)
    print("STRESS TEST PARSER - INTERACTIVE MODE")
    print("=" * 80)
    
    print(f"\nRecipe context:")
    print(f"\nAvailable views:")
    for view in recipe_context["views"]:
        print(f"  - {view}")
    
    print(f"\nAvailable factors:")
    for factor in recipe_context["factors"]:
        print(f"  - {factor}")
    
    print(f"\nAvailable stress types:")
    for stress_type in available_stress_types():
        print(f"  - {stress_type}")
    
    print("\n" + "=" * 80)
    print("Enter your stress test requests (or 'quit' to exit)")
    print("=" * 80 + "\n")
    
    while True:
        try:
            request = input("Request: ").strip()
            
            if request.lower() in ['quit', 'exit', 'q']:
                print("Exiting interactive mode.")
                break
            
            if not request:
                continue
            
            run_single_test(request, recipe_context, verbose=True)
            
        except KeyboardInterrupt:
            print("\n\nExiting interactive mode.")
            break
        except EOFError:
            break


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Test the Black-Litterman stress test LLM parser"
    )
    
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Run in interactive mode"
    )
    
    parser.add_argument(
        "--request",
        "-r",
        type=str,
        help="Single stress test request to parse"
    )
    
    parser.add_argument(
        "--recipe",
        type=str,
        help="Path to custom recipe JSON file (default: example_recipe.json)"
    )
    
    args = parser.parse_args()
    
    # Load recipe
    try:
        if args.recipe:
            recipe_path = Path(args.recipe)
            with open(recipe_path, 'r', encoding='utf-8') as f:
                recipe = json.load(f)
        else:
            recipe = load_example_recipe()
        
        recipe_context = extract_recipe_context(recipe)
        
    except Exception as e:
        print(f"Error loading recipe: {e}", file=sys.stderr)
        return 2
    
    # Run appropriate mode
    if args.interactive:
        interactive_mode(recipe_context)
        return 0
    elif args.request:
        success = run_single_test(args.request, recipe_context, verbose=True)
        return 0 if success else 1
    else:
        # Run full test suite
        return run_test_suite(recipe_context)


if __name__ == "__main__":
    sys.exit(main())

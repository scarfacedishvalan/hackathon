#!/usr/bin/env python3
"""
Scenario Generator Runner for Black-Litterman Stress Testing

This script demonstrates the full pipeline:
1. Load a BL recipe
2. Parse natural language stress test requests into StressSpec
3. Generate concrete numeric scenarios from StressSpec
4. Output scenarios ready for backtest execution

Usage:
    python run_scenario_generator.py                    # Run all test cases
    python run_scenario_generator.py --interactive      # Interactive mode
    python run_scenario_generator.py --request "..."    # Single request
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List
from datetime import datetime

from app.services.bl_stress import (
    parse_stress_prompt,
    available_stress_types,
    generate_scenarios_from_spec,
    StressSpec,
)


BACKEND_DIR = Path(__file__).resolve().parent
EXAMPLE_RECIPE_PATH = BACKEND_DIR / "app" / "services" / "bl_stress" / "example_recipe.json"
OUTPUT_DIR = BACKEND_DIR / "app" / "services" / "bl_stress"


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
        "name": "View magnitude stress - standard grid",
        "request": "Stress test the AAPL vs MSFT view magnitude with a standard range"
    },
    {
        "name": "View magnitude stress - aggressive grid",
        "request": "Stress test NVDA outperforms META view magnitude with aggressive intensity"
    },
    {
        "name": "Confidence scaling - standard",
        "request": "Test different confidence levels with standard grid"
    },
    {
        "name": "Confidence scaling - aggressive",
        "request": "What if we're much less confident in all views? Use aggressive range"
    },
    {
        "name": "Factor amplification - Momentum",
        "request": "Amplify the Momentum factor with standard scaling"
    },
    {
        "name": "Factor amplification - Value",
        "request": "How does dampening the Value factor affect results? Use aggressive grid"
    },
    {
        "name": "Tau shift - conservative",
        "request": "Test different tau values using a conservative grid"
    },
    {
        "name": "Tau shift - standard",
        "request": "Vary tau to see sensitivity to prior vs views, standard intensity"
    },
    {
        "name": "Volatility multiplier - standard",
        "request": "Simulate different volatility regimes with standard grid"
    },
    {
        "name": "Volatility multiplier - aggressive",
        "request": "Test extreme volatility scenarios with aggressive range"
    },
    {
        "name": "Crisis regime template",
        "request": "Apply the crisis regime template"
    },
    {
        "name": "High uncertainty regime",
        "request": "Test the portfolio under high uncertainty conditions"
    },
    {
        "name": "Risk-off regime",
        "request": "Apply the risk_off market regime"
    },
    {
        "name": "Joint view stress - standard/conservative",
        "request": "Jointly stress magnitude and confidence for AAPL outperforms MSFT, standard magnitude and conservative confidence"
    },
]


def run_single_scenario_generation(
    request: str,
    recipe: Dict,
    recipe_context: Dict,
    verbose: bool = True,
    save_output: bool = False
) -> bool:
    """
    Run a single scenario generation from request to concrete scenarios.
    
    Args:
        request: Natural language stress test request
        recipe: Full BL recipe dictionary
        recipe_context: Recipe context with views and factors
        verbose: If True, print detailed output
        save_output: If True, save scenarios to JSON file
        
    Returns:
        True if generation succeeded, False otherwise
    """
    if verbose:
        print(f"\nRequest: {request}")
        print("=" * 80)
    
    try:
        # Step 1: Parse request into StressSpec
        if verbose:
            print("\n[Step 1] Parsing natural language request...")
        
        spec = parse_stress_prompt(request, recipe_context=recipe_context)
        
        if verbose:
            print("✓ Successfully parsed into StressSpec")
            print(f"\nStressSpec:")
            print(json.dumps(spec.model_dump(), indent=2))
        
        # Step 2: Generate concrete scenarios
        if verbose:
            print(f"\n[Step 2] Generating concrete scenarios...")
        
        scenarios = generate_scenarios_from_spec(spec, recipe)
        
        if verbose:
            print(f"✓ Generated {len(scenarios)} scenario(s)")
        
        # Step 3: Display scenarios
        if verbose:
            print(f"\n[Step 3] Concrete Scenarios:")
            print("-" * 80)
            
            for i, scenario in enumerate(scenarios, start=1):
                print(f"\nScenario {i}/{len(scenarios)}:")
                print(json.dumps(scenario.model_dump(), indent=2))
        
        # Step 4: Save to file if requested
        if save_output:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = OUTPUT_DIR / f"scenarios_output_{timestamp}.json"
            
            output_data = {
                "meta": {
                    "timestamp": timestamp,
                    "request": request,
                    "scenario_count": len(scenarios)
                },
                "stress_spec": spec.model_dump(),
                "scenarios": [s.model_dump() for s in scenarios]
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2)
            
            if verbose:
                print(f"\n✓ Scenarios saved to: {output_file}")
        
        return True
        
    except Exception as e:
        if verbose:
            print(f"\n✗ Scenario generation failed: {e}")
            import traceback
            traceback.print_exc()
        return False


def run_test_suite(recipe: Dict, recipe_context: Dict) -> int:
    """
    Run all predefined test cases.
    
    Args:
        recipe: Full BL recipe dictionary
        recipe_context: Recipe context with views and factors
        
    Returns:
        Exit code (0 if all tests passed, 1 otherwise)
    """
    print("=" * 80)
    print("SCENARIO GENERATOR - TEST SUITE")
    print("=" * 80)
    
    print(f"\nRecipe loaded: {EXAMPLE_RECIPE_PATH.name}")
    print(f"  - {len(recipe_context['views'])} views")
    print(f"  - {len(recipe_context['factors'])} factors")
    
    passed = 0
    failed = 0
    
    for i, case in enumerate(TEST_CASES, start=1):
        print(f"\n{'=' * 80}")
        print(f"Test Case {i}/{len(TEST_CASES)}: {case['name']}")
        print(f"{'=' * 80}")
        
        success = run_single_scenario_generation(
            case["request"],
            recipe,
            recipe_context,
            verbose=True,
            save_output=False
        )
        
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


def interactive_mode(recipe: Dict, recipe_context: Dict):
    """
    Run in interactive mode, accepting user input.
    
    Args:
        recipe: Full BL recipe dictionary
        recipe_context: Recipe context with views and factors
    """
    print("=" * 80)
    print("SCENARIO GENERATOR - INTERACTIVE MODE")
    print("=" * 80)
    
    print(f"\nRecipe loaded: {EXAMPLE_RECIPE_PATH.name}")
    
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
    print("Enter stress test requests (or 'quit' to exit)")
    print("Tip: Add '--save' at the end to save scenarios to file")
    print("=" * 80 + "\n")
    
    while True:
        try:
            request = input("Request: ").strip()
            
            if request.lower() in ['quit', 'exit', 'q']:
                print("Exiting interactive mode.")
                break
            
            if not request:
                continue
            
            # Check if user wants to save output
            save_output = False
            if request.endswith("--save"):
                save_output = True
                request = request.replace("--save", "").strip()
            
            run_single_scenario_generation(
                request,
                recipe,
                recipe_context,
                verbose=True,
                save_output=save_output
            )
            
        except KeyboardInterrupt:
            print("\n\nExiting interactive mode.")
            break
        except EOFError:
            break


def demo_mode(recipe: Dict, recipe_context: Dict):
    """
    Run a quick demo with a few representative examples.
    
    Args:
        recipe: Full BL recipe dictionary
        recipe_context: Recipe context with views and factors
    """
    print("=" * 80)
    print("SCENARIO GENERATOR - DEMO MODE")
    print("=" * 80)
    
    demo_cases = [
        "Stress test the AAPL vs MSFT view magnitude with standard range",
        "Test different confidence levels with aggressive grid",
        "Apply the crisis regime template",
    ]
    
    for i, request in enumerate(demo_cases, start=1):
        print(f"\n{'=' * 80}")
        print(f"Demo {i}/{len(demo_cases)}")
        print(f"{'=' * 80}")
        
        run_single_scenario_generation(
            request,
            recipe,
            recipe_context,
            verbose=True,
            save_output=False
        )
    
    print(f"\n{'=' * 80}")
    print("DEMO COMPLETE")
    print(f"{'=' * 80}")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Generate concrete stress test scenarios from natural language requests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Run full test suite
  %(prog)s --demo                       # Run quick demo
  %(prog)s --interactive                # Interactive mode
  %(prog)s --request "stress AAPL view" --save  # Single request with save
  %(prog)s --recipe custom.json         # Use custom recipe
  %(prog)s --stress-spec stress_spec_example1_view_magnitude.json  # Load StressSpec from file
  %(prog)s --stress-spec example.json --save  # Generate and save scenarios
        """
    )
    
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Run in interactive mode"
    )
    
    parser.add_argument(
        "--demo",
        "-d",
        action="store_true",
        help="Run quick demo with a few examples"
    )
    
    parser.add_argument(
        "--request",
        "-r",
        type=str,
        help="Single stress test request to process"
    )
    
    parser.add_argument(
        "--recipe",
        type=str,
        help="Path to custom recipe JSON file (default: example_recipe.json)"
    )
    
    parser.add_argument(
        "--save",
        "-s",
        action="store_true",
        help="Save generated scenarios to JSON file"
    )
    
    parser.add_argument(
        "--stress-spec",
        type=str,
        help="Path to StressSpec JSON file to load and generate scenarios from"
    )
    
    args = parser.parse_args()
    
    # Load recipe
    try:
        if args.recipe:
            recipe_path = Path(args.recipe)
            if not recipe_path.exists():
                print(f"Error: Recipe file not found: {recipe_path}", file=sys.stderr)
                return 2
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
        interactive_mode(recipe, recipe_context)
        return 0
    elif args.demo:
        demo_mode(recipe, recipe_context)
        return 0
    elif args.stress_spec:
        # Load StressSpec from JSON file and generate scenarios
        try:
            spec_path = Path(args.stress_spec)
            if not spec_path.exists():
                print(f"Error: StressSpec file not found: {spec_path}", file=sys.stderr)
                return 2
            
            with open(spec_path, 'r', encoding='utf-8') as f:
                spec_data = json.load(f)
            
            spec = StressSpec(**spec_data)
            
            print("=" * 80)
            print(f"Loaded StressSpec from: {spec_path.name}")
            print("=" * 80)
            print(json.dumps(spec.model_dump(), indent=2))
            print()
            
            print("Generating scenarios...")
            scenarios = generate_scenarios_from_spec(spec, recipe)
            
            print(f"\n✓ Generated {len(scenarios)} scenario(s)")
            print("\nScenarios:")
            print("-" * 80)
            
            for i, scenario in enumerate(scenarios, start=1):
                print(f"\nScenario {i}/{len(scenarios)}:")
                print(json.dumps(scenario.model_dump(), indent=2))
            
            if args.save:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = OUTPUT_DIR / f"scenarios_output_{timestamp}.json"
                
                output_data = {
                    "meta": {
                        "timestamp": timestamp,
                        "source_file": str(spec_path),
                        "scenario_count": len(scenarios)
                    },
                    "stress_spec": spec.model_dump(),
                    "scenarios": [s.model_dump() for s in scenarios]
                }
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, indent=2)
                
                print(f"\n✓ Scenarios saved to: {output_file}")
            
            return 0
            
        except Exception as e:
            print(f"Error processing StressSpec file: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 1
    elif args.request:
        success = run_single_scenario_generation(
            args.request,
            recipe,
            recipe_context,
            verbose=True,
            save_output=args.save
        )
        return 0 if success else 1
    else:
        # Run full test suite
        return run_test_suite(recipe, recipe_context)


if __name__ == "__main__":
    sys.exit(main())

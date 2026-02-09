"""
Test script for recipe interpreter validation.
Loads test cases from test_cases.json and validates LLM output against expected results.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Tuple


def load_test_cases(test_file: str = "test_cases.json") -> List[Dict[str, Any]]:
    """Load test cases from JSON file."""
    test_path = Path(__file__).parent / test_file
    with open(test_path, 'r') as f:
        data = json.load(f)
    return data['test_cases']


def deep_compare(actual: Any, expected: Any, path: str = "root") -> Tuple[bool, List[str]]:
    """
    Recursively compare two objects and return differences.
    
    Args:
        actual: Actual output from LLM
        expected: Expected output from test case
        path: Current path in the object tree (for error reporting)
        
    Returns:
        Tuple of (is_match, list_of_differences)
    """
    differences = []
    
    # Handle None/null cases
    if expected is None and actual is None:
        return True, []
    if expected is None or actual is None:
        differences.append(f"{path}: Expected {expected}, got {actual}")
        return False, differences
    
    # Handle type mismatches
    if type(expected) != type(actual):
        differences.append(f"{path}: Type mismatch - Expected {type(expected).__name__}, got {type(actual).__name__}")
        return False, differences
    
    # Handle dictionaries
    if isinstance(expected, dict):
        # Check for missing keys
        expected_keys = set(expected.keys())
        actual_keys = set(actual.keys())
        
        missing_keys = expected_keys - actual_keys
        extra_keys = actual_keys - expected_keys
        
        if missing_keys:
            differences.append(f"{path}: Missing keys: {missing_keys}")
        if extra_keys:
            differences.append(f"{path}: Extra keys: {extra_keys}")
        
        # Recursively compare common keys
        for key in expected_keys & actual_keys:
            is_match, sub_diffs = deep_compare(
                actual[key], 
                expected[key], 
                f"{path}.{key}"
            )
            if not is_match:
                differences.extend(sub_diffs)
        
        return len(differences) == 0, differences
    
    # Handle lists
    elif isinstance(expected, list):
        if len(expected) != len(actual):
            differences.append(f"{path}: List length mismatch - Expected {len(expected)}, got {len(actual)}")
            return False, differences
        
        for i, (exp_item, act_item) in enumerate(zip(expected, actual)):
            is_match, sub_diffs = deep_compare(
                act_item, 
                exp_item, 
                f"{path}[{i}]"
            )
            if not is_match:
                differences.extend(sub_diffs)
        
        return len(differences) == 0, differences
    
    # Handle primitives
    else:
        if expected != actual:
            differences.append(f"{path}: Expected '{expected}', got '{actual}'")
            return False, differences
        return True, []


def validate_output(actual_output: Dict[str, Any], expected_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate LLM output against expected output.
    
    Args:
        actual_output: The actual output from the LLM
        expected_output: The expected output from test case
        
    Returns:
        Dictionary with validation results
    """
    is_match, differences = deep_compare(actual_output, expected_output)
    
    return {
        "passed": is_match,
        "differences": differences,
        "match_percentage": calculate_match_percentage(actual_output, expected_output)
    }


def calculate_match_percentage(actual: Any, expected: Any) -> float:
    """Calculate approximate match percentage between two objects."""
    if expected is None and actual is None:
        return 100.0
    if expected is None or actual is None:
        return 0.0
    
    if isinstance(expected, dict) and isinstance(actual, dict):
        all_keys = set(expected.keys()) | set(actual.keys())
        if not all_keys:
            return 100.0
        
        matching_keys = 0
        for key in all_keys:
            if key in expected and key in actual:
                if calculate_match_percentage(actual[key], expected[key]) > 50:
                    matching_keys += 1
        
        return (matching_keys / len(all_keys)) * 100
    
    elif isinstance(expected, list) and isinstance(actual, list):
        if len(expected) == 0 and len(actual) == 0:
            return 100.0
        if len(expected) == 0 or len(actual) == 0:
            return 0.0
        
        matches = sum(1 for e, a in zip(expected, actual) if e == a)
        return (matches / max(len(expected), len(actual))) * 100
    
    else:
        return 100.0 if expected == actual else 0.0


def run_tests(llm_outputs: List[Dict[str, Any]] = None):
    """
    Run all test cases and print results.
    
    Args:
        llm_outputs: List of actual LLM outputs corresponding to test cases.
                     If None, this function will just print the test cases.
    """
    test_cases = load_test_cases()
    
    print("=" * 80)
    print("RECIPE INTERPRETER TEST SUITE")
    print("=" * 80)
    print()
    
    if llm_outputs is None:
        print("No LLM outputs provided. Showing test cases only.\n")
        for i, test_case in enumerate(test_cases, 1):
            print(f"Test Case {i}: {test_case['description']}")
            print(f"Instruction: {test_case['instruction']}")
            print(f"Expected Output:")
            print(json.dumps(test_case['expected_output'], indent=2))
            print("-" * 80)
        return
    
    if len(llm_outputs) != len(test_cases):
        print(f"ERROR: Number of outputs ({len(llm_outputs)}) doesn't match number of test cases ({len(test_cases)})")
        return
    
    results = []
    for i, (test_case, actual_output) in enumerate(zip(test_cases, llm_outputs), 1):
        print(f"Test Case {i}: {test_case['description']}")
        print(f"Instruction: {test_case['instruction']}")
        print()
        
        validation = validate_output(actual_output, test_case['expected_output'])
        results.append(validation)
        
        if validation['passed']:
            print("✓ PASSED")
        else:
            print("✗ FAILED")
            print(f"Match Percentage: {validation['match_percentage']:.1f}%")
            print("Differences:")
            for diff in validation['differences']:
                print(f"  - {diff}")
        
        print("-" * 80)
        print()
    
    # Summary
    passed = sum(1 for r in results if r['passed'])
    total = len(results)
    avg_match = sum(r['match_percentage'] for r in results) / total if total > 0 else 0
    
    print("=" * 80)
    print(f"SUMMARY: {passed}/{total} tests passed ({(passed/total*100):.1f}%)")
    print(f"Average Match Percentage: {avg_match:.1f}%")
    print("=" * 80)


if __name__ == "__main__":
    # Example usage - just show test cases
    print("Loading test cases...")
    run_tests()
    
    print("\n\nTo test with actual LLM outputs, call:")
    print("run_tests([output1, output2, output3, output4])")

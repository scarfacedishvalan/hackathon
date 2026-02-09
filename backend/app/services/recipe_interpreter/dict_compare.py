"""
Utility function for comparing nested dictionaries with detailed difference reporting.
"""
from typing import Any, Dict, List, Tuple


def compare_nested_dicts(
    actual: Dict[str, Any], 
    expected: Dict[str, Any], 
    path: str = ""
) -> Tuple[List[str], List[str], List[str]]:
    """
    Compare two nested dictionaries and report differences.
    
    Args:
        actual: The actual dictionary to compare
        expected: The expected dictionary to compare against
        path: Current path in the nested structure (used internally for recursion)
        
    Returns:
        Tuple of three lists:
        - missing_keys: Keys present in expected but not in actual (with paths)
        - extra_keys: Keys present in actual but not in expected (with paths)
        - mismatched_values: Values that don't match (with paths and values)
        
    Example:
        >>> actual = {"a": {"b": 1, "c": 2}}
        >>> expected = {"a": {"b": 1, "c": 3, "d": 4}}
        >>> missing, extra, mismatched = compare_nested_dicts(actual, expected)
        >>> print(missing)
        ['a->d']
        >>> print(mismatched)
        ['a->c: expected 3, got 2']
    """
    missing_keys = []
    extra_keys = []
    mismatched_values = []
    
    # Get all keys from both dictionaries
    expected_keys = set(expected.keys())
    actual_keys = set(actual.keys())
    
    # Find missing keys (in expected but not in actual)
    for key in expected_keys - actual_keys:
        key_path = f"{path}->{key}" if path else key
        missing_keys.append(key_path)
    
    # Find extra keys (in actual but not in expected)
    for key in actual_keys - expected_keys:
        key_path = f"{path}->{key}" if path else key
        extra_keys.append(key_path)
    
    # Compare values for common keys
    for key in expected_keys & actual_keys:
        key_path = f"{path}->{key}" if path else key
        expected_value = expected[key]
        actual_value = actual[key]
        
        # Both are dictionaries - recurse
        if isinstance(expected_value, dict) and isinstance(actual_value, dict):
            sub_missing, sub_extra, sub_mismatched = compare_nested_dicts(
                actual_value, 
                expected_value, 
                key_path
            )
            missing_keys.extend(sub_missing)
            extra_keys.extend(sub_extra)
            mismatched_values.extend(sub_mismatched)
        
        # Both are lists - compare element by element
        elif isinstance(expected_value, list) and isinstance(actual_value, list):
            if len(expected_value) != len(actual_value):
                mismatched_values.append(
                    f"{key_path}: expected list length {len(expected_value)}, got {len(actual_value)}"
                )
            else:
                for i, (exp_item, act_item) in enumerate(zip(expected_value, actual_value)):
                    if isinstance(exp_item, dict) and isinstance(act_item, dict):
                        sub_missing, sub_extra, sub_mismatched = compare_nested_dicts(
                            act_item, 
                            exp_item, 
                            f"{key_path}[{i}]"
                        )
                        missing_keys.extend(sub_missing)
                        extra_keys.extend(sub_extra)
                        mismatched_values.extend(sub_mismatched)
                    elif exp_item != act_item:
                        mismatched_values.append(
                            f"{key_path}[{i}]: expected {repr(exp_item)}, got {repr(act_item)}"
                        )
        
        # Type mismatch
        elif type(expected_value) != type(actual_value):
            mismatched_values.append(
                f"{key_path}: type mismatch - expected {type(expected_value).__name__} ({repr(expected_value)}), "
                f"got {type(actual_value).__name__} ({repr(actual_value)})"
            )
        
        # Simple value comparison
        elif expected_value != actual_value:
            mismatched_values.append(
                f"{key_path}: expected {repr(expected_value)}, got {repr(actual_value)}"
            )
    
    return missing_keys, extra_keys, mismatched_values


def print_comparison_report(
    actual: Dict[str, Any], 
    expected: Dict[str, Any],
    label: str = "Dictionary Comparison"
) -> bool:
    """
    Compare two dictionaries and print a formatted report.
    
    Args:
        actual: The actual dictionary
        expected: The expected dictionary
        label: Label for the comparison report
        
    Returns:
        True if dictionaries match exactly, False otherwise
    """
    missing, extra, mismatched = compare_nested_dicts(actual, expected)
    
    has_differences = bool(missing or extra or mismatched)
    
    print("=" * 80)
    print(f"{label}")
    print("=" * 80)
    
    if not has_differences:
        print("✓ Dictionaries match perfectly!")
    else:
        print("✗ Differences found:\n")
        
        if missing:
            print(f"Missing Keys ({len(missing)}):")
            for key in missing:
                print(f"  - {key}")
            print()
        
        if extra:
            print(f"Extra Keys ({len(extra)}):")
            for key in extra:
                print(f"  + {key}")
            print()
        
        if mismatched:
            print(f"Mismatched Values ({len(mismatched)}):")
            for mismatch in mismatched:
                print(f"  ≠ {mismatch}")
            print()
    
    print("=" * 80)
    
    return not has_differences


# Example usage and tests
if __name__ == "__main__":
    # Test Case 1: Simple differences
    print("Test Case 1: Simple differences")
    actual1 = {
        "name": "John",
        "age": 30,
        "city": "NYC"
    }
    expected1 = {
        "name": "John",
        "age": 31,
        "country": "USA"
    }
    print_comparison_report(actual1, expected1, "Test 1: Simple Dictionary")
    print("\n")
    
    # Test Case 2: Nested differences
    print("Test Case 2: Nested differences")
    actual2 = {
        "user": {
            "name": "Alice",
            "profile": {
                "age": 25,
                "location": "NYC"
            }
        },
        "settings": {
            "theme": "dark"
        }
    }
    expected2 = {
        "user": {
            "name": "Alice",
            "profile": {
                "age": 26,
                "location": "NYC",
                "verified": True
            }
        },
        "settings": {
            "theme": "light",
            "notifications": True
        }
    }
    print_comparison_report(actual2, expected2, "Test 2: Nested Dictionary")
    print("\n")
    
    # Test Case 3: Perfect match
    print("Test Case 3: Perfect match")
    actual3 = {"a": 1, "b": {"c": 2}}
    expected3 = {"a": 1, "b": {"c": 2}}
    print_comparison_report(actual3, expected3, "Test 3: Perfect Match")
    print("\n")
    
    # Test Case 4: List comparisons
    print("Test Case 4: Lists with differences")
    actual4 = {
        "items": [
            {"id": 1, "name": "Item1"},
            {"id": 2, "name": "Item2"}
        ]
    }
    expected4 = {
        "items": [
            {"id": 1, "name": "Item1"},
            {"id": 2, "name": "Item2_Updated", "status": "active"}
        ]
    }
    print_comparison_report(actual4, expected4, "Test 4: Lists with Nested Dicts")

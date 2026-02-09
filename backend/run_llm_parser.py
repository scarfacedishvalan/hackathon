#!/usr/bin/env python3
"""CLI script for text-to-JSON semantic extraction and prompt test cases."""

import argparse
import json
import sys
from pathlib import Path

from app.services.recipe_interpreter.llm_parser import InvalidJSONError, MissingFieldError, ParserError, SchemaMismatchError, parse_text_to_json


BACKEND_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = BACKEND_DIR / "app" / "services" / "recipe_interpreter" / "prompts"

def _is_number(x: object) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


# Function to compare nested dictionaries for testing purposes
def compare_dicts(d1, d2, path=""):
    if isinstance(d1, dict) and isinstance(d2, dict):
        for key in d1:
            if key not in d2:
                print(f"Key '{path + key}' missing in second dict")
                return False
            if not compare_dicts(d1[key], d2[key], path + key + "."):
                return False
        for key in d2:
            if key not in d1:
                print(f"Key '{path + key}' missing in first dict")
                return False
    elif isinstance(d1, list) and isinstance(d2, list):
        if len(d1) != len(d2):
            print(f"List length mismatch at '{path}': {len(d1)} vs {len(d2)}")
            return False
        for i, (item1, item2) in enumerate(zip(d1, d2)):
            if not compare_dicts(item1, item2, path + f"[{i}]."):
                return False
    else:
        if _is_number(d1) and _is_number(d2):
            if abs(float(d1) - float(d2)) > 1e-12:
                print(f"Value mismatch at '{path}': {d1} vs {d2}")
                return False
        elif d1 != d2:
            print(f"Value mismatch at '{path}': {d1} vs {d2}")
            return False
    return True


def run_test_cases(test_cases_path: Path, *, save_extracted_path: Path | None = None) -> int:
    if not test_cases_path.exists():
        print(f"Test cases file not found: {test_cases_path}", file=sys.stderr)
        return 2

    cases = json.loads(test_cases_path.read_text(encoding="utf-8"))
    if not isinstance(cases, list):
        print("Test cases JSON must be a list", file=sys.stderr)
        return 2

    passed = 0
    failed = 0
    extracted_results: list[dict] = []

    for i, case in enumerate(cases, start=1):
        expected_input = case.get("expected_input")
        expected_output = case.get("expected_output")

        if not isinstance(expected_input, str) or not isinstance(expected_output, dict):
            print(f"Case {i}: invalid format (needs expected_input str, expected_output dict)", file=sys.stderr)
            failed += 1
            continue

        print(f"\n=== Case {i} ===")
        print(f"Input: {expected_input}")

        extracted_case: dict[str, object] = {
            "expected_input": expected_input,
            "expected_output": expected_output,
            "extracted_output": None,
            "pass": False,
            "error": None,
        }

        try:
            actual = parse_text_to_json(
                expected_input,
                system_prompt_file="system_prompt_backtesting.txt",
                schema="backtesting",
            )
            extracted_case["extracted_output"] = actual
        except (InvalidJSONError, SchemaMismatchError, MissingFieldError, ParserError) as e:
            print(f"Case {i}: parser error: {e}", file=sys.stderr)
            extracted_case["error"] = str(e)
            extracted_results.append(extracted_case)
            failed += 1
            continue

        ok = compare_dicts(actual, expected_output)
        if ok:
            print(f"Case {i}: PASS")
            extracted_case["pass"] = True
            passed += 1
        else:
            print(f"Case {i}: FAIL")
            print("Actual output:")
            print(json.dumps(actual, indent=2))
            failed += 1

        extracted_results.append(extracted_case)

    if save_extracted_path is not None:
        save_extracted_path.write_text(
            json.dumps(extracted_results, indent=2),
            encoding="utf-8",
        )
        print(f"Saved extracted outputs to: {save_extracted_path}")

    print(f"\nSummary: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the semantic parser or execute Backtesting prompt test cases")
    parser.add_argument(
        "instruction",
        nargs="?",
        default=None,
        help="Instruction text to parse (omit to run tests)",
    )
    parser.add_argument(
        "--tests",
        type=str,
        default=str(PROMPTS_DIR / "backtesting_test_cases.json"),
        help="Path to JSON test cases file",
    )
    parser.add_argument(
        "--save-extracted",
        type=str,
        default=str(PROMPTS_DIR / "backtesting_test_cases_extracted.json"),
        help="Where to save extracted outputs when running tests",
    )

    args = parser.parse_args()

    tests_path = Path(args.tests)
    if not tests_path.is_absolute():
        tests_path = (BACKEND_DIR / tests_path).resolve()

    save_extracted_path = Path(args.save_extracted)
    if not save_extracted_path.is_absolute():
        save_extracted_path = (BACKEND_DIR / save_extracted_path).resolve()

    if args.instruction is None:
        return run_test_cases(
            tests_path,
            save_extracted_path=save_extracted_path,
        )

    try:
        result = parse_text_to_json(
            args.instruction,
            system_prompt_file=str(PROMPTS_DIR / "system_prompt_backtesting.txt"),
            schema="backtesting",
        )
        print(json.dumps(result, indent=2))
        return 0
    except InvalidJSONError as e:
        print(f"Error: Invalid JSON - {e}", file=sys.stderr)
        return 1
    except SchemaMismatchError as e:
        print(f"Error: Schema mismatch - {e}", file=sys.stderr)
        return 1
    except MissingFieldError as e:
        print(f"Error: Missing fields - {e}", file=sys.stderr)
        return 1
    except ParserError as e:
        print(f"Error: Parser error - {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
    

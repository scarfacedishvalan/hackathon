#!/usr/bin/env python3
"""CLI script for text-to-JSON semantic extraction."""

import json
import sys

from llm_parser import (
    InvalidJSONError,
    MissingFieldError,
    ParserError,
    SchemaMismatchError,
    parse_text_to_json,
)


def main() -> int:
    """
    Main entry point for the CLI.

    Usage:
        python run.py "Run the strategy WeighMeanVar with lookbacks 3y, 2y and 1y with yearly rebalance"

    Returns:
        0 on success, 1 on error.
    """
    if len(sys.argv) < 2:
        print("Usage: python run.py <instruction>", file=sys.stderr)
        print('Example: python run.py "Run the strategy WeighMeanVar with lookbacks 3y, 2y and 1y with yearly rebalance"', file=sys.stderr)
        return 1

    instruction = sys.argv[1]

    try:
        result = parse_text_to_json(instruction)
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
    # sys.exit(main())
    INSTRUCTION = "Run the strategy WeighMeanVar with lookbacks 3y, 2y and 1y with yearly rebalance"
    result = parse_text_to_json(INSTRUCTION)
    print(json.dumps(result, indent=2))

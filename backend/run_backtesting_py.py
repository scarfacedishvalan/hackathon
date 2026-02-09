"""Run Backtesting.py strategies from JSON recipes (sample-data friendly).

This is a convenience runner that accepts JSON in the same shape as the
`expected_output` objects in `app/services/recipe_interpreter/prompts/backtesting_test_cases.json`.

By default it uses the built-in sample OHLCV data from backtesting.py (GOOG).

Examples (from repo root):
  python backend/run_backtesting_py.py --recipe backend/app/services/recipe_interpreter/prompts/backtesting_example_expected_output.json
  python backend/run_backtesting_py.py --test-cases backend/app/services/recipe_interpreter/prompts/backtesting_test_cases.json

Notes:
- Requires: `pip install backtesting`
- Plot output requires backtesting's plotting deps (installed automatically with backtesting).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Add backend directory to path (so `app.*` imports work regardless of CWD)
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.recipe_interpreter.backtesting_from_json import run_from_recipe  # noqa: E402


def _slug(text: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in text.strip())
    cleaned = cleaned.strip("_-")
    return cleaned or "plot"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _force_sample_source(recipe: dict[str, Any]) -> dict[str, Any]:
    data = recipe.get("data")
    if not isinstance(data, dict):
        recipe["data"] = {"symbol": None, "source": "sample", "path": None, "start": None, "end": None}
        return recipe

    # If user provided a path, leave it alone.
    if data.get("path"):
        return recipe

    # If user provided a source, respect it.
    if data.get("source") is None:
        data["source"] = "sample"

    # The bundled GOOG sample data won't match arbitrary 2020+ date ranges.
    # Clear date filters so we always have data to run against.
    data["start"] = None
    data["end"] = None

    return recipe


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Backtesting.py from a semantic JSON recipe")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--recipe", type=str, help="Path to a single JSON recipe object")
    g.add_argument(
        "--test-cases",
        type=str,
        help="Path to a JSON list of test cases with expected_output entries",
    )

    parser.add_argument(
        "--plot",
        type=str,
        default=None,
        help="HTML plot output path. If omitted, saves to backend/app/services/plots/ by default.",
    )
    parser.add_argument(
        "--no-plot",
        action="store_true",
        help="Disable saving an HTML plot",
    )
    parser.add_argument("--open-plot", action="store_true", help="Open plot in a browser")
    parser.add_argument(
        "--no-sample",
        action="store_true",
        help="Do not force sample data; respect recipe.data.{path|symbol|source}",
    )

    args = parser.parse_args(argv)

    plots_dir = BACKEND_DIR / "app" / "services" / "plots"
    plot_path: Path | None
    if args.no_plot:
        plot_path = None
    elif args.plot is None:
        plots_dir.mkdir(parents=True, exist_ok=True)
        plot_path = plots_dir / "backtest_result.html"
    else:
        plot_path = Path(args.plot)

    if args.recipe:
        recipe_path = Path(args.recipe)
        recipe = _load_json(recipe_path)
        if not isinstance(recipe, dict):
            print("Recipe JSON must be an object", file=sys.stderr)
            return 2

        if not args.no_sample:
            recipe = _force_sample_source(recipe)

        run_from_recipe(recipe, plot_path=plot_path, open_plot=bool(args.open_plot))
        return 0

    test_cases_path = Path(args.test_cases)
    cases = _load_json(test_cases_path)
    if not isinstance(cases, list):
        print("Test cases JSON must be a list", file=sys.stderr)
        return 2

    failures = 0
    for i, case in enumerate(cases, start=1):
        recipe = case.get("expected_output") if isinstance(case, dict) else None
        if not isinstance(recipe, dict):
            print(f"Case {i}: missing expected_output object", file=sys.stderr)
            failures += 1
            continue

        if not args.no_sample:
            recipe = _force_sample_source(recipe)

        print(f"\n=== Running case {i}: {recipe.get('strategy_name')} ===")
        try:
            case_plot_path = plot_path
            if plot_path is not None and args.plot is None:
                plots_dir.mkdir(parents=True, exist_ok=True)
                strategy = _slug(str(recipe.get("strategy_name") or "strategy"))
                symbol = _slug(str((recipe.get("data") or {}).get("symbol") or "data"))
                case_plot_path = plots_dir / f"case_{i:02d}_{strategy}_{symbol}.html"

            run_from_recipe(recipe, plot_path=case_plot_path, open_plot=bool(args.open_plot))
        except Exception as exc:
            print(f"Case {i}: ERROR: {exc}", file=sys.stderr)
            failures += 1

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    # Convenience: allow running from VS Code without passing args.
    # If no CLI args were provided, default to the example expected-output recipe.
    if len(sys.argv) == 1:
        default_recipe = (
            BACKEND_DIR
            / "app"
            / "services"
            / "recipe_interpreter"
            / "prompts"
            / "backtesting_example_expected_output.json"
        )
        raise SystemExit(main(["--recipe", str(default_recipe)]))

    raise SystemExit(main())

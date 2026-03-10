from pathlib import Path
import sys
import json

from app.orchestrators.view_orchestrator import parse_view, load_recipe
from app.orchestrators.bl_orchestrator import run_black_litterman
from app.services.price_data.load_data import load_market_data

_CURRENT_RECIPE_PATH = Path(__file__).resolve().parent / "data" / "bl_recipes" / "current.json"


def load_current_recipe() -> dict:
    """Load the recipe from data/bl_recipes/current.json."""
    if not _CURRENT_RECIPE_PATH.exists():
        raise FileNotFoundError(
            f"current.json not found at {_CURRENT_RECIPE_PATH}. "
            "Run a view parse first or create the file manually."
        )
    return load_recipe("current")

# ---------------------------------------------------------------------------
# View parsing example
# ---------------------------------------------------------------------------

def run_view_parsing_example():
    SAMPLE_TEXTS = [
        # "Apple will strongly outperform Google by 5% next quarter.",
        # "I'm bearish on Tesla, expecting a 4% decline. Rising interest rates are a concern.",
        # "Microsoft looks neutral; no strong view.",
        "Technology sector will outperform by 4%. AI adoption driving growth across the sector."
    ]

    for sample in SAMPLE_TEXTS:
        print(f"\n{'=' * 60}")
        print(f"Input : {sample}")
        print("-" * 60)
        try:
            views = parse_view(sample)  # uses DEFAULT_ASSETS / DEFAULT_FACTORS
            if views:
                for i, view in enumerate(views, 1):
                    print(f"  View {i}: {json.dumps(view, indent=4)}")
            else:
                print("  (no views extracted)")
        except Exception as exc:
            print(f"  ERROR: {exc}")

    print(f"\n{'=' * 60}")


# ---------------------------------------------------------------------------
# BL orchestrator example
# ---------------------------------------------------------------------------


def run_bl_example():
    print("\n" + "=" * 60)
    print("BL ORCHESTRATOR EXAMPLE")
    print("=" * 60)

    recipe = load_current_recipe()
    print(f"Loaded recipe: {recipe.get('meta', {}).get('name', 'current.json')}")

    # Load price data (metadata loaded internally by orchestrator)
    price_df, _caps, _B, _factor_names, _assets = load_market_data()

    results = run_black_litterman(recipe, price_df)

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Recipe : {results['recipe_name']}")
    print(
        f"Views  : {results['n_bottom_up_views']} bottom-up + "
        f"{results['n_top_down_views']} top-down"
    )
    print("\nOptimal weights:")
    for asset, weight in sorted(results["weights"].items(), key=lambda x: -x[1]):
        if abs(weight) > 0.001:
            print(f"  {asset:6s}  {weight:7.2%}")

    print("\nPosterior vs prior returns:")
    print(f"  {'Asset':6s}  {'Posterior':>10s}  {'Prior':>8s}  {'Δ':>8s}")
    for asset in results["universe"]:
        post = results["posterior_returns"].get(asset, 0.0)
        prior = results["prior_returns"].get(asset, 0.0)
        print(f"  {asset:6s}  {post:10.2%}  {prior:8.2%}  {post - prior:+8.2%}")

    print("=" * 60)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Allow running this module directly.
    # Inserts backend/ into sys.path so that `app.*` imports resolve correctly.

    import argparse

    parser = argparse.ArgumentParser(description="Run orchestrator examples")
    parser.add_argument(
        "--example",
        choices=["views", "bl", "all"],
        default="bl",
        help="Which example to run (default: bl)",
    )
    args = parser.parse_args()

    if args.example in ("views", "all"):
        run_view_parsing_example()

    if args.example in ("bl", "all"):
        run_bl_example()
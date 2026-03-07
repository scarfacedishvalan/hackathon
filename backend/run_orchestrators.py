from pathlib import Path
import sys
from app.orchestrators.view_orchestrator import parse_view
import json
# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Allow running this module directly (python -m or python view_orchestrator.py).
    # Inserts backend/ into sys.path so that `app.*` imports resolve correctly.

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
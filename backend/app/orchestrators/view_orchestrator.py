"""
View Orchestrator

Orchestration layer for parsing natural language investment views into
structured Black-Litterman views. Contains orchestration logic only —
no FastAPI routes.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.bl_llm_parser.parser import BlackLittermanLLMParser

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_SERVICES_DIR = Path(__file__).resolve().parent.parent / "services"
_PARSER_DIR = _SERVICES_DIR / "bl_llm_parser"
_PROMPT_DIR = _PARSER_DIR / "prompts"
_METADATA_PATH = _PARSER_DIR / "sector_metadata.json"

# Recipes are stored in backend/data/bl_recipes/
_RECIPES_DIR = Path(__file__).resolve().parents[2] / "data" / "bl_recipes"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_ASSETS: List[str] = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA"]
DEFAULT_FACTORS: List[str] = ["Rates", "Growth", "Value", "Momentum"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_asset_metadata() -> Dict[str, Any]:
    """Load sector/factor metadata for the default asset universe."""
    try:
        with open(_METADATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


# ---------------------------------------------------------------------------
# Recipe persistence
# ---------------------------------------------------------------------------


def _recipe_path(name: str) -> Path:
    """Return the file path for a recipe named *name*."""
    # Sanitise name: keep only alphanumerics, hyphens, underscores
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    return _RECIPES_DIR / f"{safe}.json"


def save_current_views(views: List[Dict[str, Any]]) -> Path:
    """
    Overwrite ``current.json`` with a frontend-supplied list of active views.

    Called when the UI syncs its full active-views state to the server
    (e.g. after a delete or after appending a newly-parsed view).

    Args:
        views: List of ``ActiveView``-shaped dicts sent from the frontend.

    Returns:
        Path to the saved file.
    """
    _RECIPES_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "name": "current",
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "raw_result": None,  # not available for frontend-driven syncs
        "normalised_views": views,
    }
    path = _recipe_path("current")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return path


def save_recipe(
    raw_result: Dict[str, Any],
    normalised: List[Dict[str, Any]],
    name: str = "current",
) -> Path:
    """
    Persist a parse result to ``backend/data/bl_recipes/<name>.json``.

    ``current.json`` is always overwritten.  Any other *name* creates a
    named snapshot that can be retrieved later.

    Args:
        raw_result:  Raw parser output from ``BlackLittermanLLMParser``.
        normalised:  Normalised view list produced by ``parse_view``.
        name:        Recipe name (default ``"current"``).

    Returns:
        Path to the saved file.
    """
    _RECIPES_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "name": name,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "raw_result": raw_result,
        "normalised_views": normalised,
    }
    path = _recipe_path(name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return path


def load_recipe(name: str = "current") -> Dict[str, Any]:
    """
    Load a previously saved recipe by name.

    Args:
        name: Recipe name (default ``"current"``).

    Returns:
        Dict with keys ``name``, ``saved_at``, ``raw_result``,
        ``normalised_views``.

    Raises:
        FileNotFoundError: If no recipe with that name exists.
    """
    path = _recipe_path(name)
    if not path.exists():
        raise FileNotFoundError(f"No recipe named '{name}' found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_recipes() -> List[str]:
    """
    Return the names of all saved recipes (without the ``.json`` extension).

    ``"current"`` is always listed first when present.
    """
    if not _RECIPES_DIR.exists():
        return []
    names = [p.stem for p in sorted(_RECIPES_DIR.glob("*.json"))]
    # Float "current" to the top
    if "current" in names:
        names = ["current"] + [n for n in names if n != "current"]
    return names


def _normalize_view(raw_view: Dict[str, Any], view_category: str) -> Dict[str, Any]:
    """
    Convert a single raw parser view into a normalised dictionary.

    Args:
        raw_view: A single view dict from the parser output.
        view_category: Either ``"bottom_up"`` or ``"top_down"``.

    Returns:
        Normalised view dict with consistent keys.

    Bottom-up relative example::

        {
            "type": "relative",
            "asset_long": "AAPL",
            "asset_short": "GOOGL",
            "alpha": 0.05,
            "confidence": 0.6,
            "label": "AAPL outperforms GOOGL"
        }

    Bottom-up absolute example::

        {
            "type": "absolute",
            "asset": "TSLA",
            "alpha": -0.05,
            "confidence": 0.6,
            "label": "Bearish view on Tesla"
        }

    Top-down factor example::

        {
            "type": "factor",
            "factor": "Rates",
            "alpha": -0.02,
            "confidence": 0.5,
            "label": "Rising rates concern"
        }
    """
    if view_category == "top_down":
        return {
            "type": "factor",
            "factor": raw_view.get("factor"),
            "alpha": raw_view.get("shock"),
            "confidence": raw_view.get("confidence"),
            "label": raw_view.get("label"),
        }

    view_type = raw_view.get("type")

    if view_type == "relative":
        assets: List[str] = raw_view.get("assets", [])
        weights: List[float] = raw_view.get("weights", [1, -1])

        # Identify long / short leg from weights (positive weight → long).
        if len(assets) == 2 and len(weights) == 2:
            if weights[0] >= 0:
                asset_long, asset_short = assets[0], assets[1]
            else:
                asset_long, asset_short = assets[1], assets[0]
        else:
            asset_long = assets[0] if len(assets) > 0 else None
            asset_short = assets[1] if len(assets) > 1 else None

        return {
            "type": "relative",
            "asset_long": asset_long,
            "asset_short": asset_short,
            "alpha": raw_view.get("expected_outperformance"),
            "confidence": raw_view.get("confidence"),
            "label": raw_view.get("label"),
        }

    # absolute (default)
    return {
        "type": "absolute",
        "asset": raw_view.get("asset"),
        "alpha": raw_view.get("expected_return"),
        "confidence": raw_view.get("confidence"),
        "label": raw_view.get("label"),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_view(
    text: str,
    assets: Optional[List[str]] = None,
    factors: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Parse a natural language investment view into normalised BL view dicts.

    Calls the LLM parser (``BlackLittermanLLMParser``) and converts every
    bottom-up and top-down view in the response into a uniform dictionary
    format suitable for downstream Black-Litterman processing.

    Args:
        text: Natural language investment view string, e.g.
            ``"Apple will outperform Google by 5% next quarter."``.
        assets: Asset universe to use. Defaults to :data:`DEFAULT_ASSETS`.
        factors: Factor universe to use. Defaults to :data:`DEFAULT_FACTORS`.

    Returns:
        List of normalised view dicts. Each dict always contains ``type``,
        ``alpha``, ``confidence``, and ``label``.  Additional keys depend on
        view type:

        * ``"relative"`` — ``asset_long``, ``asset_short``
        * ``"absolute"`` — ``asset``
        * ``"factor"``   — ``factor``

    Raises:
        ValueError: If the LLM returns an invalid or malformed JSON response.
        FileNotFoundError: If prompt templates cannot be located.
    """
    assets = assets or DEFAULT_ASSETS
    factors = factors or DEFAULT_FACTORS

    asset_metadata = _load_asset_metadata()

    parser = BlackLittermanLLMParser(
        prompt_dir=str(_PROMPT_DIR),
        use_schema=True,
    )

    raw_result = parser.parse(
        assets=assets,
        factors=factors,
        investor_text=text,
        asset_metadata=asset_metadata if asset_metadata else None,
    )

    normalised: List[Dict[str, Any]] = []

    for view in raw_result.get("bottom_up_views", []):
        normalised.append(_normalize_view(view, "bottom_up"))

    for shock in raw_result.get("top_down_views", {}).get("factor_shocks", []):
        normalised.append(_normalize_view(shock, "top_down"))

    # Always persist the latest result so the UI can consume it
    save_recipe(raw_result, normalised, name="current")

    return normalised


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Allow running this module directly (python -m or python view_orchestrator.py).
    # Inserts backend/ into sys.path so that `app.*` imports resolve correctly.
    _BACKEND_DIR = Path(__file__).resolve().parents[2]
    if str(_BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(_BACKEND_DIR))
        SAMPLE_TEXTS = [
            "Apple will strongly outperform Google by 5% next quarter.",
            "I'm bearish on Tesla, expecting a 4% decline. Rising interest rates are a concern.",
            "Microsoft looks neutral; no strong view.",
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

"""
Views Router

Thin FastAPI router exposing view-parsing and current-recipe endpoints.
Orchestration is delegated entirely to view_orchestrator.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from app.orchestrators import view_orchestrator

router = APIRouter(prefix="/views", tags=["views"])


# ---------------------------------------------------------------------------
# Adaptor helpers
# ---------------------------------------------------------------------------

def _adapt_views(recipe: Dict[str, Any]) -> Dict[str, List[Dict]]:
    """
    Transform the ``bottom_up_views`` and ``top_down_views`` keys from a
    raw recipe dict (current.json format) into the frontend BottomUpView /
    TopDownView shapes.

    All other keys in *recipe* are intentionally ignored.
    """
    bottom_up_raw: List[Dict] = recipe.get("bottom_up_views", [])
    factor_shocks: List[Dict] = (
        recipe.get("top_down_views", {}).get("factor_shocks", [])
    )

    bottom_up: List[Dict] = []
    for i, v in enumerate(bottom_up_raw):
        if v.get("type") == "absolute":
            bottom_up.append(
                {
                    "id": f"bu-{i}",
                    "type": "absolute",
                    "asset": v.get("asset"),
                    "value": v.get("expected_return", 0),
                    "confidence": v.get("confidence", 0),
                    "label": v.get("label"),
                }
            )
        else:  # relative
            assets = v.get("assets", [])
            bottom_up.append(
                {
                    "id": f"bu-{i}",
                    "type": "relative",
                    "asset_long": assets[0] if len(assets) > 0 else None,
                    "asset_short": assets[1] if len(assets) > 1 else None,
                    "value": v.get("expected_outperformance", 0),
                    "confidence": v.get("confidence", 0),
                    "label": v.get("label"),
                }
            )

    top_down: List[Dict] = [
        {
            "id": f"td-{i}",
            "factor": v.get("factor"),
            "shock": v.get("shock", 0),
            "confidence": v.get("confidence", 0),
            "label": v.get("label"),
        }
        for i, v in enumerate(factor_shocks)
    ]

    return {"bottom_up": bottom_up, "top_down": top_down}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/parse")
async def parse_view(body: dict):
    """Parse a natural language view and auto-save as the current recipe."""
    text = body["text"]
    parsed_view = view_orchestrator.parse_view(text)
    return {"view": parsed_view}


@router.get("/current")
async def get_current_views():
    """
    Read ``current.json`` and return the views adapted for the frontend.

    Response shape::

        {
          "bottom_up": [ BottomUpView, ... ],
          "top_down":  [ TopDownView,  ... ]
        }

    Returns empty lists when ``current.json`` does not exist yet.
    """
    try:
        recipe = view_orchestrator.load_recipe("current")
    except FileNotFoundError:
        return {"bottom_up": [], "top_down": []}
    return _adapt_views(recipe)


@router.get("/model_parameters")
async def get_model_parameters():
    """Return the model_parameters block from current.json."""
    return view_orchestrator.get_model_parameters()


@router.put("/model_parameters")
async def update_model_parameters(body: dict):
    """
    Update model_parameters in current.json.

    Accepted keys: ``tau``, ``risk_aversion``, ``risk_free_rate``.
    Returns the saved parameters.
    """
    view_orchestrator.update_model_parameters(body)
    return view_orchestrator.get_model_parameters()


@router.delete("/bottom_up/{index}", status_code=204)
async def delete_bottom_up_view(index: int):
    """
    Delete the bottom-up view at array position *index* from ``current.json``.

    The index matches the numeric suffix in the frontend row id
    (e.g. ``bu-1`` → ``index=1``).
    """
    try:
        view_orchestrator.delete_bottom_up_view(index)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except IndexError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.delete("/top_down/{index}", status_code=204)
async def delete_top_down_view(index: int):
    """
    Delete the factor shock at array position *index* from ``current.json``.

    The index matches the numeric suffix in the frontend row id
    (e.g. ``td-0`` → ``index=0``).
    """
    try:
        view_orchestrator.delete_top_down_view(index)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except IndexError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

"""
Views Router

Thin FastAPI router exposing view-parsing functionality.
Orchestration is delegated entirely to view_orchestrator.
"""

from fastapi import APIRouter, HTTPException
from app.orchestrators import view_orchestrator

router = APIRouter(prefix="/views", tags=["views"])


@router.post("/parse")
async def parse_view(body: dict):
    """Parse a natural language view and auto-save as the current recipe."""
    text = body["text"]
    parsed_view = view_orchestrator.parse_view(text)
    return {"view": parsed_view}


# ---------------------------------------------------------------------------
# Recipe endpoints
# ---------------------------------------------------------------------------


@router.get("/recipes")
async def list_recipes():
    """Return the names of all saved recipes."""
    return {"recipes": view_orchestrator.list_recipes()}


@router.get("/recipes/{name}")
async def get_recipe(name: str):
    """Load a saved recipe by name (use ``current`` for the latest parse)."""
    try:
        return view_orchestrator.load_recipe(name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.put("/current")
async def sync_current_views(body: dict):
    """
    Overwrite ``current.json`` with the full active-views list from the UI.

    The frontend calls this after every add or delete so the server always
    mirrors the complete view table shown to the user.

    Expected body: ``{ "views": [ ...ActiveView objects... ] }``
    """
    views = body.get("views", [])
    path = view_orchestrator.save_current_views(views)
    return {"synced": True, "count": len(views), "path": str(path)}


@router.post("/recipes/{name}")
async def save_recipe(name: str):
    """
    Snapshot the current parse result as a named recipe.

    Reads ``current.json`` and copies it under the given *name* so it is
    preserved before the next ``/parse`` call overwrites it.
    """
    try:
        current = view_orchestrator.load_recipe("current")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"No current result to save: {exc}")

    path = view_orchestrator.save_recipe(
        raw_result=current["raw_result"],
        normalised=current["normalised_views"],
        name=name,
    )
    return {"saved": name, "path": str(path)}

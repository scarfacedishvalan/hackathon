"""
Views Router

Thin FastAPI router exposing view-parsing functionality.
Orchestration is delegated entirely to view_orchestrator.
"""

from fastapi import APIRouter
from app.orchestrators import view_orchestrator

router = APIRouter(prefix="/views", tags=["views"])


@router.post("/parse")
async def parse_view(body: dict):
    text = body["text"]
    parsed_view = view_orchestrator.parse_view(text)
    return {"view": parsed_view}

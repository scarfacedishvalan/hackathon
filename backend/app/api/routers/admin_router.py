"""
Admin Console Router

GET  /admin/console           -> full payload (LLM usage + agent usage, tare-filtered)
GET  /admin/llm-usage         -> LLM-only data (tare-filtered)
GET  /admin/agent-usage       -> agent-only data (tare-filtered)
POST /admin/tare              -> set tare point (resets display cost counter)
POST /admin/tare/reset        -> remove active tare (show all history again)
GET  /admin/tare/history      -> list past tare events
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from app.orchestrators.admin_console_orchestrator import (
    get_admin_console_data,
    get_llm_usage_data,
    get_agent_usage_data,
    tare,
    reset_tare,
    get_tare_history,
    get_active_tare,
)


class TareRequest(BaseModel):
    note: Optional[str] = ""


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/console")
async def admin_console(
    llm_recent_limit: int = Query(50, ge=1, le=500, description="Max recent LLM calls to return"),
    agent_recent_limit: int = Query(100, ge=1, le=500, description="Max recent agent steps to return"),
):
    """Return the full admin console payload: LLM usage + agent usage + grand total cost."""
    try:
        return get_admin_console_data(
            llm_recent_limit=llm_recent_limit,
            agent_recent_limit=agent_recent_limit,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/llm-usage")
async def llm_usage(
    recent_limit: int = Query(50, ge=1, le=500),
):
    """Return only the LLM (chat_and_record) usage data."""
    try:
        return get_llm_usage_data(recent_limit=recent_limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/agent-usage")
async def agent_usage(
    recent_limit: int = Query(100, ge=1, le=500),
):
    """Return only the agentic (chat_with_history) cost data."""
    try:
        return get_agent_usage_data(recent_limit=recent_limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Tare endpoints
# ---------------------------------------------------------------------------


@router.post("/tare")
async def tare_costs(body: TareRequest = TareRequest()):
    """
    Set a new tare point.

    All dashboard queries will now only count data *after* this timestamp.
    Historical data in the underlying databases is never modified or deleted.

    Returns: { tare_ts, note, previous_tare_ts }
    """
    try:
        return tare(note=body.note or "")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/tare/reset")
async def reset_tare_costs():
    """
    Remove the active tare so all historical data is shown in the dashboard.
    The tare_log history is preserved.

    Returns: { removed_tare_ts }
    """
    try:
        return reset_tare()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/tare/history")
async def tare_history(limit: int = Query(20, ge=1, le=100)):
    """Return the tare event log (most recent first)."""
    try:
        return {"history": get_tare_history(limit=limit)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/tare/active")
async def active_tare():
    """Return the currently active tare record, or null if none is set."""
    try:
        return {"active_tare": get_active_tare()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


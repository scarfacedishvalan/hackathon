"""
Admin Console Router

GET  /admin/console           -> full payload (LLM usage + agent usage, tare-filtered)
GET  /admin/llm-usage         -> LLM-only data (tare-filtered)
GET  /admin/agent-usage       -> agent-only data (tare-filtered)
POST /admin/tare              -> set tare point (resets display cost counter)
POST /admin/tare/reset        -> remove active tare (show all history again)
GET  /admin/tare/history      -> list past tare events
"""

import logging
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

logger = logging.getLogger(__name__)


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
        active_tare = get_active_tare()
        if active_tare:
            logger.info(f"Admin console data filtered by tare: {active_tare['tare_ts']}")
        return get_admin_console_data(
            llm_recent_limit=llm_recent_limit,
            agent_recent_limit=agent_recent_limit,
        )
    except Exception as exc:
        logger.error(f"Error getting admin console data: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/llm-usage")
async def llm_usage(
    recent_limit: int = Query(50, ge=1, le=500),
):
    """Return only the LLM (chat_and_record) usage data, filtered by active tare."""
    try:
        active_tare = get_active_tare()
        since = active_tare["tare_ts"] if active_tare else None
        return get_llm_usage_data(recent_limit=recent_limit, since=since)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/agent-usage")
async def agent_usage(
    recent_limit: int = Query(100, ge=1, le=500),
):
    """Return only the agentic (chat_with_history) cost data, filtered by active tare."""
    try:
        active_tare = get_active_tare()
        since = active_tare["tare_ts"] if active_tare else None
        return get_agent_usage_data(recent_limit=recent_limit, since=since)
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
sult = tare(note=body.note or "")
        logger.info(f"Tare set: {result['tare_ts']}, note: {result.get('note', '')}")
        return result
    except Exception as exc:
        logger.error(f"Error setting tare: {exc}", exc_info=True), previous_tare_ts }
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


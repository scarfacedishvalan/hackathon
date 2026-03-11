"""
Agent Router

Endpoints for the agentic Black-Litterman analysis feature.

GET  /agent/recipes          -- list available thesis names (bl_recipes/*.json)
POST /agent/run              -- run agent on a named thesis
GET  /agent/audits           -- list past agent audit summaries
GET  /agent/audits/{audit_id} -- load a specific audit record
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.orchestrators.bl_agent_orchestrator import (
    run_agent,
    list_audits,
    load_audit,
    AGENT_AUDITS_DIR,
)

router = APIRouter(prefix="/agent", tags=["agent"])

_RECIPES_DIR = Path(__file__).resolve().parents[3] / "data" / "bl_recipes"

# ---------------------------------------------------------------------------
# Running state — simple in-process dict (fine for single-user hackathon)
# ---------------------------------------------------------------------------
_running: Dict[str, str] = {}  # audit_id -> "running" | "done" | "error"


# ---------------------------------------------------------------------------
# GET /agent/recipes
# ---------------------------------------------------------------------------

@router.get("/recipes")
async def list_recipes() -> List[str]:
    """Return the names of all saved BL recipes (stems of *.json files)."""
    if not _RECIPES_DIR.exists():
        return []
    return sorted(
        p.stem for p in _RECIPES_DIR.glob("*.json")
    )


# ---------------------------------------------------------------------------
# POST /agent/run
# ---------------------------------------------------------------------------

class AgentRunRequest(BaseModel):
    thesis_name: str
    goal: str = (
        "Stress-test all views by varying confidence and find an allocation "
        "for a moderate-risk investor with max 25% per position."
    )
    max_steps: int = 8


class AgentRunResponse(BaseModel):
    audit_id: str


def _do_run(thesis_name: str, goal: str, max_steps: int, audit_id_holder: list):
    """Blocking worker executed in a thread pool."""
    import uuid, json
    audit_id = str(uuid.uuid4())
    audit_id_holder.append(audit_id)
    _running[audit_id] = "running"
    try:
        # patch run_agent to use our pre-assigned audit_id
        from app.orchestrators import bl_agent_orchestrator as _mod
        import uuid as _uuid
        _orig_uuid4 = _uuid.uuid4
        _uuid.uuid4 = lambda: audit_id  # type: ignore[assignment]
        try:
            run_agent(thesis_name=thesis_name, goal=goal, max_steps=max_steps)
        finally:
            _uuid.uuid4 = _orig_uuid4
        _running[audit_id] = "done"
    except Exception as exc:
        _running[audit_id] = f"error: {exc}"


@router.post("/run")
async def start_agent_run(
    request: AgentRunRequest,
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    """
    Start an agent run in the background.

    Returns immediately with ``audit_id`` and ``status: "running"``.
    Poll ``GET /agent/audits/{audit_id}`` until the file appears on disk.
    """
    import uuid
    audit_id = str(uuid.uuid4())
    _running[audit_id] = "running"

    loop = asyncio.get_event_loop()

    async def _run_in_thread():
        try:
            await loop.run_in_executor(
                None,
                lambda: _exec_run(audit_id, request.thesis_name, request.goal, request.max_steps),
            )
        except Exception:
            pass

    background_tasks.add_task(_run_in_thread)
    return {"audit_id": audit_id, "status": "running"}


def _exec_run(audit_id: str, thesis_name: str, goal: str, max_steps: int):
    """Block the executor thread; writes audit JSON to disk when done."""
    import uuid as _uuid_mod
    _original = _uuid_mod.uuid4

    # Force the orchestrator to use our pre-generated audit_id
    call_count = [0]
    def _patched():
        call_count[0] += 1
        if call_count[0] == 1:
            # Return an object whose str() == audit_id
            class _Fixed:
                def __str__(self): return audit_id
                def __format__(self, _): return audit_id
            return _Fixed()
        return _original()

    _uuid_mod.uuid4 = _patched  # type: ignore[assignment]
    try:
        run_agent(thesis_name=thesis_name, goal=goal, max_steps=max_steps)
        _running[audit_id] = "done"
    except Exception as exc:
        _running[audit_id] = f"error: {exc}"
    finally:
        _uuid_mod.uuid4 = _original


# ---------------------------------------------------------------------------
# GET /agent/audits
# ---------------------------------------------------------------------------

@router.get("/audits")
async def get_audit_list(limit: int = 50) -> List[Dict[str, Any]]:
    """Return past audit summaries from agent_costs.db, newest first."""
    try:
        return list_audits(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /agent/audits/{audit_id}
# ---------------------------------------------------------------------------

@router.get("/audits/{audit_id}")
async def get_audit(audit_id: str) -> Dict[str, Any]:
    """
    Return a full audit record.

    While the run is still in progress, returns ``{"status": "running"}``.
    On error, returns ``{"status": "error", "detail": "..."}``.
    """
    status = _running.get(audit_id)
    if status == "running":
        return {"status": "running", "audit_id": audit_id}
    if status and status.startswith("error"):
        return {"status": "error", "audit_id": audit_id, "detail": status}

    try:
        audit = load_audit(audit_id)
        return {"status": "done", **audit}
    except FileNotFoundError:
        # Not started by this process — check disk anyway (previous run)
        try:
            audit = load_audit(audit_id)
            return {"status": "done", **audit}
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Audit '{audit_id}' not found.")

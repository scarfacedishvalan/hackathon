"""
Admin Console Orchestrator
==========================

Provides all data needed by the Admin Console tab:

  - **LLM Usage** (``llm_usage.db``)
      Regular ``chat_and_record`` calls.

  - **Agent Costs** (``agent_costs.db``)
      Agentic ReAct-loop calls.

  - **Tare** (``admin_meta.db``)
      Records a tare timestamp.  All display queries filter
      ``WHERE timestamp >= tare_ts`` so history is never deleted.

Public API
----------
    get_active_tare()           -> dict | None
    get_tare_history()          -> list[dict]
    tare(note)                  -> dict
    reset_tare()                -> dict
    get_llm_usage_data()        -> dict
    get_agent_usage_data()      -> dict
    get_admin_console_data()    -> dict
"""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"

LLM_USAGE_DB:     Path = _DATA_DIR / "llm_usage.db"
AGENT_COSTS_DB:   Path = _DATA_DIR / "agent_costs.db"
AGENT_AUDITS_DIR: Path = _DATA_DIR / "agent_audits"
ADMIN_META_DB:    Path = _DATA_DIR / "admin_meta.db"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


@contextmanager
def _connect(db_path: Path, write: bool = False):
    """Yield a sqlite3 connection. Falls back to :memory: if DB missing and read-only."""
    if not db_path.exists() and not write:
        conn = sqlite3.connect(":memory:")
    else:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _rows(db_path: Path, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Execute *sql* and return list of dicts, empty on missing table."""
    with _connect(db_path) as conn:
        try:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
        except sqlite3.OperationalError:
            return []


# ---------------------------------------------------------------------------
# Tare store  (admin_meta.db -> tare_log)
# ---------------------------------------------------------------------------


def _ensure_tare_table() -> None:
    with _connect(ADMIN_META_DB, write=True) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tare_log (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                tare_ts  TEXT NOT NULL,
                note     TEXT NOT NULL DEFAULT ''
            )
            """
        )
        conn.commit()


def get_active_tare() -> Optional[Dict[str, Any]]:
    """Return the most recent tare row, or None if no tare has been set."""
    _ensure_tare_table()
    rows = _rows(ADMIN_META_DB, "SELECT * FROM tare_log ORDER BY id DESC LIMIT 1")
    return rows[0] if rows else None


def get_tare_history(limit: int = 20) -> List[Dict[str, Any]]:
    """Return all tare events, most recent first."""
    _ensure_tare_table()
    return _rows(ADMIN_META_DB,
                 "SELECT * FROM tare_log ORDER BY id DESC LIMIT ?", (limit,))


def tare(note: str = "") -> Dict[str, Any]:
    """
    Record a new tare point at the current UTC time.

    All subsequent display queries will only count data from this timestamp
    onwards. Historical data in llm_usage.db / agent_costs.db is never deleted.

    Returns the new tare record plus the previous tare timestamp (if any).
    """
    _ensure_tare_table()
    previous = get_active_tare()
    # Use naive local time to match what llm_calls / agent_costs stores
    # (both recording services use datetime.now() with no timezone).
    ts = datetime.now().isoformat()
    with _connect(ADMIN_META_DB, write=True) as conn:
        conn.execute(
            "INSERT INTO tare_log (tare_ts, note) VALUES (?, ?)", (ts, note)
        )
        conn.commit()
    return {
        "tare_ts":          ts,
        "note":             note,
        "previous_tare_ts": previous["tare_ts"] if previous else None,
    }


def reset_tare() -> Dict[str, Any]:
    """
    Remove the active tare so all historical data is shown again.
    The tare_log history rows are preserved.
    Returns the removed tare timestamp (if any).
    """
    _ensure_tare_table()
    previous = get_active_tare()
    if previous:
        with _connect(ADMIN_META_DB, write=True) as conn:
            conn.execute("DELETE FROM tare_log WHERE id = ?", (previous["id"],))
            conn.commit()
    return {"removed_tare_ts": previous["tare_ts"] if previous else None}


# ---------------------------------------------------------------------------
# Agent audit JSON enrichment
# ---------------------------------------------------------------------------


def _load_agent_audit_index() -> Dict[str, Dict[str, str]]:
    """Return audit_id -> {goal, run_timestamp, thesis_name, model} from JSON files."""
    index: Dict[str, Dict[str, str]] = {}
    if not AGENT_AUDITS_DIR.exists():
        return index
    for jf in AGENT_AUDITS_DIR.glob("*.json"):
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
            aid = data.get("audit_id")
            if aid:
                index[aid] = {
                    "goal":          data.get("goal", ""),
                    "run_timestamp": data.get("run_timestamp", ""),
                    "thesis_name":   data.get("thesis_name", ""),
                    "model":         data.get("model", ""),
                }
        except Exception:
            pass
    return index


# ---------------------------------------------------------------------------
# LLM Usage (llm_usage.db -> llm_calls)
# ---------------------------------------------------------------------------


def get_llm_usage_data(
    recent_limit: int = 50,
    since: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Return all data for the LLM Calls section.

    Parameters
    ----------
    since : ISO-8601 timestamp string (inclusive lower bound).
            When None all rows are included.

    Keys: summary, by_service, by_model, recent_calls
    """
    db     = LLM_USAGE_DB
    where  = "WHERE timestamp >= ?" if since else "WHERE 1=1"
    params: tuple = (since,) if since else ()
    
    if since:
        logger.info(f"Filtering LLM usage data with tare timestamp: {since}")
    else:
        logger.debug("Loading all LLM usage data (no tare filter)")

    summary_rows = _rows(db, f"""
        SELECT
            COUNT(*)                                     AS total_calls,
            SUM(CASE WHEN success=1 THEN 1 ELSE 0 END)  AS successful_calls,
            SUM(CASE WHEN success=0 THEN 1 ELSE 0 END)  AS failed_calls,
            COALESCE(SUM(prompt_tokens), 0)              AS total_prompt_tokens,
            COALESCE(SUM(completion_tokens), 0)          AS total_completion_tokens,
            COALESCE(SUM(total_tokens), 0)               AS total_tokens,
            COALESCE(SUM(cost_usd), 0.0)                 AS total_cost_usd,
            COALESCE(AVG(latency_ms), 0.0)               AS avg_latency_ms
        FROM llm_calls {where}
    """, params)
    summary = summary_rows[0] if summary_rows else {
        "total_calls": 0, "successful_calls": 0, "failed_calls": 0,
        "total_prompt_tokens": 0, "total_completion_tokens": 0,
        "total_tokens": 0, "total_cost_usd": 0.0, "avg_latency_ms": 0.0,
    }

    by_service = _rows(db, f"""
        SELECT
            service, operation,
            COUNT(*)                                               AS calls,
            COALESCE(SUM(total_tokens), 0)                        AS total_tokens,
            COALESCE(SUM(prompt_tokens), 0)                       AS prompt_tokens,
            COALESCE(SUM(completion_tokens), 0)                   AS completion_tokens,
            COALESCE(SUM(cost_usd), 0.0)                          AS cost_usd,
            COALESCE(AVG(latency_ms), 0.0)                        AS avg_latency_ms,
            COALESCE(
                1.0 * SUM(CASE WHEN success=1 THEN 1 ELSE 0 END)
                    / COUNT(*), 0.0
            )                                                     AS success_rate
        FROM llm_calls {where}
        GROUP BY service, operation
        ORDER BY cost_usd DESC
    """, params)

    by_model = _rows(db, f"""
        SELECT
            model,
            COUNT(*)                               AS calls,
            COALESCE(SUM(total_tokens), 0)         AS total_tokens,
            COALESCE(SUM(prompt_tokens), 0)        AS prompt_tokens,
            COALESCE(SUM(completion_tokens), 0)    AS completion_tokens,
            COALESCE(SUM(cost_usd), 0.0)           AS cost_usd,
            COALESCE(AVG(latency_ms), 0.0)         AS avg_latency_ms
        FROM llm_calls {where}
        GROUP BY model
        ORDER BY cost_usd DESC
    """, params)

    recent_calls = _rows(db, f"""
        SELECT call_id, timestamp, service, operation, model,
               prompt_tokens, completion_tokens, total_tokens,
               cost_usd, latency_ms, success, error_message
        FROM llm_calls {where}
        ORDER BY timestamp DESC
        LIMIT ?
    """, params + (recent_limit,))
    for row in recent_calls:
        row["success"] = bool(row.get("success"))

    return {
        "summary":      dict(summary),
        "by_service":   by_service,
        "by_model":     by_model,
        "recent_calls": recent_calls,
    }


# ---------------------------------------------------------------------------
# Agent Costs (agent_costs.db -> agent_costs)
# ---------------------------------------------------------------------------


def get_agent_usage_data(
    recent_limit: int = 100,
    since: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Return all data for the Agent Runs section.

    Parameters
    ----------
    since : ISO-8601 timestamp string (inclusive lower bound).

    Keys: summary, by_run, by_thesis, by_tool
    
    if since:
        logger.info(f"Filtering agent usage data with tare timestamp: {since}")
    else:
        logger.debug("Loading all agent usage data (no tare filter)"), by_model, recent_steps
    """
    db          = AGENT_COSTS_DB
    audit_index = _load_agent_audit_index()
    where  = "WHERE timestamp >= ?" if since else "WHERE 1=1"
    params: tuple = (since,) if since else ()

    summary_rows = _rows(db, f"""
        SELECT
            COUNT(DISTINCT audit_id)               AS total_runs,
            COUNT(*)                               AS total_steps,
            COALESCE(SUM(total_tokens), 0)         AS total_tokens,
            COALESCE(SUM(cost_usd), 0.0)           AS total_cost_usd
        FROM agent_costs {where}
    """, params)
    raw         = summary_rows[0] if summary_rows else {}
    total_runs  = raw.get("total_runs")  or 0
    total_cost  = raw.get("total_cost_usd") or 0.0
    total_steps = raw.get("total_steps") or 0
    summary = {
        "total_runs":        total_runs,
        "total_steps":       total_steps,
        "total_tokens":      raw.get("total_tokens") or 0,
        "total_cost_usd":    total_cost,
        "avg_cost_per_run":  (total_cost  / total_runs)  if total_runs  else 0.0,
        "avg_steps_per_run": (total_steps / total_runs)  if total_runs  else 0.0,
    }

    by_run_raw = _rows(db, f"""
        SELECT
            audit_id, thesis_name,
            MIN(timestamp)                  AS first_timestamp,
            COUNT(*)                        AS steps,
            COALESCE(SUM(total_tokens), 0)  AS total_tokens,
            COALESCE(SUM(cost_usd), 0.0)    AS cost_usd
        FROM agent_costs {where}
        GROUP BY audit_id
        ORDER BY first_timestamp DESC
    """, params)
    by_run: List[Dict[str, Any]] = []
    for row in by_run_raw:
        aid  = row["audit_id"]
        meta = audit_index.get(aid, {})
        by_run.append({
            "audit_id":      aid,
            "thesis_name":   row.get("thesis_name", meta.get("thesis_name", "")),
            "goal":          meta.get("goal", ""),
            "run_timestamp": meta.get("run_timestamp", row.get("first_timestamp", "")),
            "steps":         row.get("steps", 0),
            "total_tokens":  row.get("total_tokens", 0),
            "cost_usd":      row.get("cost_usd", 0.0),
            "model":         meta.get("model", ""),
        })

    by_thesis = _rows(db, f"""
        SELECT
            thesis_name,
            COUNT(DISTINCT audit_id)        AS runs,
            COUNT(*)                        AS steps,
            COALESCE(SUM(total_tokens), 0)  AS total_tokens,
            COALESCE(SUM(cost_usd), 0.0)    AS cost_usd
        FROM agent_costs {where}
        GROUP BY thesis_name
        ORDER BY cost_usd DESC
    """, params)

    by_tool = _rows(db, f"""
        SELECT
            COALESCE(tool_called, 'synthesis / planning') AS tool_called,
            COUNT(*)                                        AS calls,
            COALESCE(SUM(total_tokens), 0)                 AS total_tokens,
            COALESCE(SUM(cost_usd), 0.0)                   AS cost_usd,
            COALESCE(AVG(latency_ms), 0.0)                 AS avg_latency_ms
        FROM agent_costs {where}
        GROUP BY COALESCE(tool_called, 'synthesis / planning')
        ORDER BY cost_usd DESC
    """, params)

    by_model = _rows(db, f"""
        SELECT
            model,
            COUNT(*)                        AS steps,
            COALESCE(SUM(total_tokens), 0)  AS total_tokens,
            COALESCE(SUM(cost_usd), 0.0)    AS cost_usd
        FROM agent_costs {where}
        GROUP BY model
        ORDER BY cost_usd DESC
    """, params)

    recent_steps = _rows(db, f"""
        SELECT audit_id, timestamp, thesis_name, step, tool_called,
               model, prompt_tokens, completion_tokens, total_tokens,
               cost_usd, latency_ms, success
        FROM agent_costs {where}
        ORDER BY timestamp DESC
        LIMIT ?
    """, params + (recent_limit,))
    for row in recent_steps:
        row["success"] = bool(row.get("success"))

    return {
        "summary":      summary,
        "by_run":       by_run,
        "by_thesis":    by_thesis,
        "by_tool":      by_tool,
        "by_model":     by_model,
        "recent_steps": recent_steps,
    }


# ---------------------------------------------------------------------------
# Combined entry point
# ---------------------------------------------------------------------------


def get_admin_console_data(
    llm_recent_limit: int = 50,
    agent_recent_limit: int = 100,
) -> Dict[str, Any]:
    """
    Full payload for the Admin Console tab.

    Automatically applies the active tare timestamp as a lower bound on
    all queries.  Full historical data is never touched.

    Keys: grand_total_cost_usd, tare_info, llm_usage, agent_usage
    """
    active_tare = get_active_tare()
    since       = active_tare["tare_ts"] if active_tare else None

    llm_data   = get_llm_usage_data(recent_limit=llm_recent_limit,    since=since)
    agent_data = get_agent_usage_data(recent_limit=agent_recent_limit, since=since)

    llm_cost   = (llm_data.get("summary")   or {}).get("total_cost_usd", 0.0) or 0.0
    agent_cost = (agent_data.get("summary") or {}).get("total_cost_usd", 0.0) or 0.0

    return {
        "grand_total_cost_usd": round(llm_cost + agent_cost, 6),
        "tare_info": {
            "active_tare_ts": since,
            "tare_history":   get_tare_history(limit=10),
        },
        "llm_usage":   llm_data,
        "agent_usage": agent_data,
    }

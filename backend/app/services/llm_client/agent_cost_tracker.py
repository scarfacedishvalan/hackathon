"""
Agent Cost Tracker

Tracks per-step costs for agentic (multi-turn, tool-calling) BL orchestration
runs. Stored in a separate SQLite DB (agent_costs.db) so that agent audit data
is not mixed with the per-call llm_usage.db records.

Schema (agent_costs table):
    audit_id        TEXT  -- uuid, groups all steps for one agent run
    timestamp       TEXT  -- ISO-8601 start time of this step
    thesis_name     TEXT  -- name of the BL recipe / thesis
    step            INT   -- 0-based step number within the ReAct loop
    tool_called     TEXT  -- tool name called by the LLM (null on synthesis)
    model           TEXT  -- LLM model used
    prompt_tokens   INT
    completion_tokens INT
    total_tokens    INT
    cost_usd        REAL
    latency_ms      INT
    success         BOOL
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional


DEFAULT_AGENT_COSTS_DB = (
    Path(__file__).resolve().parents[3] / "data" / "agent_costs.db"
)


@dataclass
class AgentStepRecord:
    """One ReAct-loop step (LLM call + optional tool call)."""

    audit_id: str
    timestamp: datetime
    thesis_name: str
    step: int
    tool_called: Optional[str]
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    latency_ms: int
    success: bool


class AgentCostTracker:
    """Writes per-step agent cost records to a dedicated SQLite database."""

    def __init__(self, db_path: Optional[str | Path] = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_AGENT_COSTS_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_costs (
                    audit_id          TEXT NOT NULL,
                    timestamp         TEXT NOT NULL,
                    thesis_name       TEXT NOT NULL,
                    step              INTEGER NOT NULL,
                    tool_called       TEXT,
                    model             TEXT NOT NULL,
                    prompt_tokens     INTEGER NOT NULL,
                    completion_tokens INTEGER NOT NULL,
                    total_tokens      INTEGER NOT NULL,
                    cost_usd          REAL NOT NULL,
                    latency_ms        INTEGER NOT NULL,
                    success           INTEGER NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_audit
                ON agent_costs (audit_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_thesis
                ON agent_costs (thesis_name)
            """)
            conn.commit()

    # ------------------------------------------------------------------
    # Connection helper
    # ------------------------------------------------------------------

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def record_step(self, record: AgentStepRecord) -> None:
        """Insert one step record."""
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO agent_costs
                  (audit_id, timestamp, thesis_name, step, tool_called,
                   model, prompt_tokens, completion_tokens, total_tokens,
                   cost_usd, latency_ms, success)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.audit_id,
                    record.timestamp.isoformat(),
                    record.thesis_name,
                    record.step,
                    record.tool_called,
                    record.model,
                    record.prompt_tokens,
                    record.completion_tokens,
                    record.total_tokens,
                    record.cost_usd,
                    record.latency_ms,
                    int(record.success),
                ),
            )
            conn.commit()

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_audit_steps(self, audit_id: str) -> List[dict]:
        """Return all step rows for *audit_id*, ordered by step number."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM agent_costs WHERE audit_id = ? ORDER BY step",
                (audit_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_audit_cost(self, audit_id: str) -> dict:
        """
        Return aggregate cost/token summary for a single audit run.

        Returns
        -------
        dict with keys: total_cost_usd, total_tokens, steps, success_steps
        """
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*)           AS steps,
                    SUM(total_tokens)  AS total_tokens,
                    SUM(cost_usd)      AS total_cost_usd,
                    SUM(success)       AS success_steps
                FROM agent_costs
                WHERE audit_id = ?
                """,
                (audit_id,),
            ).fetchone()
        return dict(row) if row else {}

    def list_audit_summaries(self, limit: int = 50) -> List[dict]:
        """
        Return one summary row per audit run, most-recent first.

        Columns: audit_id, thesis_name, first_timestamp, steps,
                 total_tokens, total_cost_usd
        """
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT
                    audit_id,
                    thesis_name,
                    MIN(timestamp)     AS first_timestamp,
                    COUNT(*)           AS steps,
                    SUM(total_tokens)  AS total_tokens,
                    SUM(cost_usd)      AS total_cost_usd
                FROM agent_costs
                GROUP BY audit_id
                ORDER BY first_timestamp DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

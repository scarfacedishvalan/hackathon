"""
SQLite-based LLM Usage Tracker

Tracks all LLM API calls with token usage, costs, and performance metrics.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from contextlib import contextmanager


@dataclass
class LLMCallRecord:
    """Record of a single LLM API call."""
    call_id: str
    timestamp: datetime
    service: str  # e.g., "recipe_interpreter", "bl_llm_parser", "news_api"
    operation: str  # e.g., "parse_strategy", "parse_bl_views", "extract_views"
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    input_length: int  # characters in user prompt
    output_length: int  # characters in response
    temperature: float
    max_tokens: int
    success: bool
    error_message: Optional[str] = None
    latency_ms: int = 0  # API call duration
    cost_usd: float = 0.0  # Calculated cost


class LLMUsageTracker:
    """Tracks LLM API usage in SQLite database."""
    
    def __init__(self, db_path: str = "llm_usage.db"):
        """
        Initialize the usage tracker.
        
        Args:
            db_path: Path to SQLite database file (created if doesn't exist)
        """
        self.db_path = Path(db_path)
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize SQLite database with tables and indexes."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS llm_calls (
                    call_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    service TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    model TEXT NOT NULL,
                    prompt_tokens INTEGER NOT NULL,
                    completion_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    input_length INTEGER NOT NULL,
                    output_length INTEGER NOT NULL,
                    temperature REAL NOT NULL,
                    max_tokens INTEGER NOT NULL,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    latency_ms INTEGER NOT NULL,
                    cost_usd REAL NOT NULL
                )
            """)
            
            # Create indexes for common queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON llm_calls(timestamp DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_service 
                ON llm_calls(service)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_success 
                ON llm_calls(success)
            """)
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def record_call(self, record: LLMCallRecord) -> None:
        """
        Save an LLM call record to the database.
        
        Args:
            record: LLMCallRecord instance to save
        """
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO llm_calls VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                record.call_id,
                record.timestamp.isoformat(),
                record.service,
                record.operation,
                record.model,
                record.prompt_tokens,
                record.completion_tokens,
                record.total_tokens,
                record.input_length,
                record.output_length,
                record.temperature,
                record.max_tokens,
                record.success,
                record.error_message,
                record.latency_ms,
                record.cost_usd,
            ))
            conn.commit()
    
    def get_usage_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        service: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get aggregated usage statistics.
        
        Args:
            start_date: Filter calls after this date
            end_date: Filter calls before this date
            service: Filter by service name
            
        Returns:
            Dictionary with aggregated statistics
        """
        query = """
            SELECT 
                COUNT(*) as total_calls,
                SUM(prompt_tokens) as total_prompt_tokens,
                SUM(completion_tokens) as total_completion_tokens,
                SUM(total_tokens) as total_tokens,
                SUM(cost_usd) as total_cost,
                AVG(latency_ms) as avg_latency_ms,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_calls,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_calls
            FROM llm_calls
            WHERE 1=1
        """
        params = []
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.isoformat())
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date.isoformat())
        if service:
            query += " AND service = ?"
            params.append(service)
        
        with self._get_connection() as conn:
            result = conn.execute(query, params).fetchone()
            return dict(result) if result else {}
    
    def get_usage_by_service(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get usage breakdown by service.
        
        Args:
            start_date: Filter calls after this date
            end_date: Filter calls before this date
            
        Returns:
            List of dictionaries with per-service statistics
        """
        query = """
            SELECT 
                service,
                COUNT(*) as calls,
                SUM(total_tokens) as tokens,
                SUM(cost_usd) as cost,
                AVG(latency_ms) as avg_latency_ms
            FROM llm_calls
            WHERE 1=1
        """
        params = []
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.isoformat())
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date.isoformat())
        
        query += " GROUP BY service ORDER BY cost DESC"
        
        with self._get_connection() as conn:
            results = conn.execute(query, params).fetchall()
            return [dict(row) for row in results]
    
    def get_recent_calls(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get most recent LLM calls.
        
        Args:
            limit: Maximum number of calls to return
            
        Returns:
            List of call records, most recent first
        """
        with self._get_connection() as conn:
            results = conn.execute("""
                SELECT * FROM llm_calls
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(row) for row in results]
    
    def get_failed_calls(
        self,
        start_date: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get failed LLM calls for debugging.
        
        Args:
            start_date: Filter calls after this date
            limit: Maximum number of failed calls to return
            
        Returns:
            List of failed call records
        """
        query = """
            SELECT * FROM llm_calls
            WHERE success = 0
        """
        params = []
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.isoformat())
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        with self._get_connection() as conn:
            results = conn.execute(query, params).fetchall()
            return [dict(row) for row in results]
    
    def get_total_cost(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> float:
        """
        Get total cost across all calls in date range.
        
        Args:
            start_date: Filter calls after this date
            end_date: Filter calls before this date
            
        Returns:
            Total cost in USD
        """
        query = "SELECT SUM(cost_usd) as total FROM llm_calls WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.isoformat())
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date.isoformat())
        
        with self._get_connection() as conn:
            result = conn.execute(query, params).fetchone()
            return result['total'] if result and result['total'] else 0.0

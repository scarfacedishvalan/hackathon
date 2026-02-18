"""
LLM Client with Usage Tracking

This module provides centralized LLM API call utilities with automatic
usage tracking to SQLite database.
"""

from app.services.llm_client.tracker import LLMUsageTracker, LLMCallRecord
from app.services.llm_client.utils import (
    chat_and_record,
    OpenAIClientWrapper,
    DEFAULT_DB_PATH,
)

__all__ = [
    "chat_and_record",
    "LLMUsageTracker",
    "LLMCallRecord",
    "OpenAIClientWrapper",
    "DEFAULT_DB_PATH",
]
"""
Utility functions for LLM calls with automatic tracking.

Provides standalone functions that work with any LLM client object
and automatically track usage to SQLite database.
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union

from openai import OpenAI

from app.services.llm_client.tracker import LLMUsageTracker, LLMCallRecord
from app.services.model_settings import PRICING


# Default database location: backend/data/llm_usage.db
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent.parent / "data" / "llm_usage.db"


class OpenAIClientWrapper:
    """
    Default OpenAI client wrapper with consistent .chat() interface.
    Used when no client is provided to chat_and_record().
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize the OpenAI client.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model to use (default: gpt-4o-mini)
        """
        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                    "or pass api_key parameter."
                )
        
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.last_prompt_tokens = 0
        self.last_completion_tokens = 0
    
    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Optional[Dict[str, Any]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> str:
        """
        Make a chat completion request.
        
        Args:
            system_prompt: System message
            user_prompt: User message
            schema: Optional JSON schema (not directly used by OpenAI)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Response text from the model
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Store token counts for tracking
        self.last_prompt_tokens = response.usage.prompt_tokens
        self.last_completion_tokens = response.usage.completion_tokens
        
        return response.choices[0].message.content


def chat_and_record(
    system_prompt: str,
    user_prompt: str,
    service: str,
    operation: str,
    llm_client=None,
    schema: Optional[Dict[str, Any]] = None,
    temperature: float = 0.7,
    max_tokens: int = 4000,
    model: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> str:
    """
    Make an LLM chat call and automatically record usage to SQLite.
    
    This is a standalone function that works with any LLM client object
    that has a .chat() method. If no client is provided, uses default OpenAI client.
    
    Args:
        system_prompt: System instructions
        user_prompt: User message
        service: Service name (e.g., "bl_llm_parser", "recipe_interpreter")
        operation: Operation name (e.g., "parse_views", "parse_strategy")
        llm_client: Any LLM client with chat(system_prompt, user_prompt, schema) method.
                    If None, uses default OpenAI client (gpt-4o-mini)
        schema: Optional JSON schema for structured output
        temperature: Sampling temperature
        max_tokens: Maximum response tokens
        model: Model name (if None, tries to get from llm_client.model)
        db_path: Path to SQLite database. If None, uses backend/data/llm_usage.db
        
    Returns:
        Raw LLM response text (usually JSON string)
        
    Raises:
        Re-raises any exceptions from the LLM client after recording the failure
        
    Example:
        >>> # Using default OpenAI client and default DB path
        >>> response = chat_and_record(
        ...     system_prompt="You are a helpful assistant",
        ...     user_prompt="What is 2+2?",
        ...     service="test_service",
        ...     operation="test_operation"
        ... )
        >>>
        >>> # Using custom client and custom DB path
        >>> client = MyCustomClient()
        >>> response = chat_and_record(
        ...     system_prompt="You are a helpful assistant",
        ...     user_prompt="What is 2+2?",
        ...     service="test_service",
        ...     operation="test_operation",
        ...     llm_client=client,
        ...     db_path="custom/path/usage.db"
        ... )
    """
    # Use default OpenAI client if none provided
    if llm_client is None:
        llm_client = OpenAIClientWrapper(model=model or "gpt-4o-mini")
    
    # Use default DB path if none provided
    if db_path is None:
        db_path = DEFAULT_DB_PATH
        # Ensure the data directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize tracker
    tracker = LLMUsageTracker(str(db_path))
    
    # Generate unique call ID
    call_id = str(uuid.uuid4())
    start_time = datetime.now()
    
    # Try to get model from client if not provided
    if model is None:
        model = getattr(llm_client, 'model', 'unknown')
    
    try:
        # Make the actual LLM call
        response = llm_client.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=schema
        )
        
        # Calculate metrics
        end_time = datetime.now()
        latency_ms = int((end_time - start_time).total_seconds() * 1000)
        
        # Try to extract token counts from response or client
        prompt_tokens = getattr(llm_client, 'last_prompt_tokens', 0)
        completion_tokens = getattr(llm_client, 'last_completion_tokens', 0)
        
        # Fallback: estimate tokens if client doesn't provide them
        if prompt_tokens == 0:
            prompt_tokens = _estimate_tokens(system_prompt + user_prompt)
        if completion_tokens == 0:
            completion_tokens = _estimate_tokens(response)
        
        total_tokens = prompt_tokens + completion_tokens
        
        # Calculate cost
        cost = _calculate_cost(model, prompt_tokens, completion_tokens)
        
        # Record successful call
        record = LLMCallRecord(
            call_id=call_id,
            timestamp=start_time,
            service=service,
            operation=operation,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            input_length=len(system_prompt) + len(user_prompt),
            output_length=len(response),
            temperature=temperature,
            max_tokens=max_tokens,
            success=True,
            latency_ms=latency_ms,
            cost_usd=cost,
        )
        tracker.record_call(record)
        
        return response
        
    except Exception as e:
        # Record failed call
        end_time = datetime.now()
        latency_ms = int((end_time - start_time).total_seconds() * 1000)
        
        record = LLMCallRecord(
            call_id=call_id,
            timestamp=start_time,
            service=service,
            operation=operation,
            model=model,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            input_length=len(system_prompt) + len(user_prompt),
            output_length=0,
            temperature=temperature,
            max_tokens=max_tokens,
            success=False,
            error_message=str(e),
            latency_ms=latency_ms,
            cost_usd=0.0,
        )
        tracker.record_call(record)
        
        # Re-raise the exception
        raise


def chat_with_history(
    messages: list[dict],
    service: str,
    operation: str,
    tools: Optional[list[dict]] = None,
    model: str = "gpt-4o",
    temperature: float = 0.2,
    db_path: Optional[Union[str, Path]] = None,
    agent_cost_db_path: Optional[Union[str, Path]] = None,
    agent_metadata: Optional[Dict[str, Any]] = None,
) -> tuple[Optional[str], Optional[list]]:
    """
    Multi-turn LLM call that supports tool-use (function calling).

    Designed for agentic ReAct loops where the caller accumulates the
    ``messages`` list across steps.  Each call:

    * Sends the full ``messages`` history to the model.
    * Optionally includes ``tools`` (OpenAI function-calling schema).
    * Writes a token/cost record to ``llm_usage.db`` (always).
    * If ``agent_cost_db_path`` is supplied, also writes a step record
      to ``agent_costs.db`` with richer audit metadata.

    Parameters
    ----------
    messages:
        Accumulated conversation history.
        e.g. [{"role": "system", ...}, {"role": "user", ...}, ...]
    service, operation:
        Tracking labels (same as ``chat_and_record``).
    tools:
        Optional list of OpenAI tool schemas.
    model:
        Model name (default: gpt-4o).
    temperature:
        Sampling temperature (default: 0.2 for agent determinism).
    db_path:
        Path to ``llm_usage.db``; defaults to ``DEFAULT_DB_PATH``.
    agent_cost_db_path:
        Path to ``agent_costs.db``; required for per-step audit tracking.
    agent_metadata:
        Extra context written to ``agent_costs.db``.
        Expected keys: ``audit_id``, ``thesis_name``, ``step``, ``tool_called``.

    Returns
    -------
    (content, tool_calls)
        ``content`` is the text reply (None if the model chose to call a tool).
        ``tool_calls`` is a list of OpenAI tool-call objects (None if no tools).
    """
    from app.services.llm_client.agent_cost_tracker import (
        AgentCostTracker,
        AgentStepRecord,
    )

    # Resolve database paths
    if db_path is None:
        db_path = DEFAULT_DB_PATH
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    tracker = LLMUsageTracker(str(db_path))
    call_id = str(uuid.uuid4())
    start_time = datetime.now()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set.")
    client = OpenAI(api_key=api_key)

    try:
        kwargs: Dict[str, Any] = dict(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = client.chat.completions.create(**kwargs)

        end_time = datetime.now()
        latency_ms = int((end_time - start_time).total_seconds() * 1000)

        usage = response.usage
        prompt_tokens = usage.prompt_tokens
        completion_tokens = usage.completion_tokens
        total_tokens = usage.total_tokens
        cost = _calculate_cost(model, prompt_tokens, completion_tokens)

        choice = response.choices[0]
        content: Optional[str] = choice.message.content
        tool_calls = choice.message.tool_calls  # list[ChatCompletionMessageToolCall] | None

        # ---- write to llm_usage.db ----------------------------------------
        record = LLMCallRecord(
            call_id=call_id,
            timestamp=start_time,
            service=service,
            operation=operation,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            input_length=sum(len(m.get("content") or "") for m in messages),
            output_length=len(content or ""),
            temperature=temperature,
            max_tokens=0,
            success=True,
            latency_ms=latency_ms,
            cost_usd=cost,
        )
        tracker.record_call(record)

        # ---- write to agent_costs.db (if path supplied) --------------------
        if agent_cost_db_path and agent_metadata:
            act = AgentCostTracker(agent_cost_db_path)
            step_record = AgentStepRecord(
                audit_id=agent_metadata.get("audit_id", call_id),
                timestamp=start_time,
                thesis_name=agent_metadata.get("thesis_name", "unknown"),
                step=agent_metadata.get("step", 0),
                tool_called=agent_metadata.get("tool_called"),
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost,
                latency_ms=latency_ms,
                success=True,
            )
            act.record_step(step_record)

        return content, tool_calls

    except Exception as exc:
        end_time = datetime.now()
        latency_ms = int((end_time - start_time).total_seconds() * 1000)

        record = LLMCallRecord(
            call_id=call_id,
            timestamp=start_time,
            service=service,
            operation=operation,
            model=model,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            input_length=sum(len(m.get("content") or "") for m in messages),
            output_length=0,
            temperature=temperature,
            max_tokens=0,
            success=False,
            error_message=str(exc),
            latency_ms=latency_ms,
            cost_usd=0.0,
        )
        tracker.record_call(record)

        if agent_cost_db_path and agent_metadata:
            act = AgentCostTracker(agent_cost_db_path)
            step_record = AgentStepRecord(
                audit_id=agent_metadata.get("audit_id", call_id),
                timestamp=start_time,
                thesis_name=agent_metadata.get("thesis_name", "unknown"),
                step=agent_metadata.get("step", 0),
                tool_called=agent_metadata.get("tool_called"),
                model=model,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_usd=0.0,
                latency_ms=latency_ms,
                success=False,
            )
            act.record_step(step_record)

        raise


def _estimate_tokens(text: str) -> int:
    """
    Rough estimate: ~4 chars per token for English text.
    
    This is a fallback when the LLM client doesn't provide token counts.
    For more accurate counting, use tiktoken library.
    
    Args:
        text: Input text
        
    Returns:
        Estimated token count
    """
    return len(text) // 4


def _calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Calculate cost in USD based on token usage.
    
    Pricing is per 1M tokens as of February 2026.
    Update these values in model_settings/chat_and_record_metadata.py as pricing changes.
    
    Args:
        model: Model name
        prompt_tokens: Number of input tokens
        completion_tokens: Number of output tokens
        
    Returns:
        Total cost in USD
    """
    # Default pricing for unknown models
    pricing = PRICING.get(model, {"input": 0, "output": 0})
    
    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]
    
    return input_cost + output_cost

"""
LLM-based article to Black-Litterman view parser.

This module handles the extraction of structured BL views from article text
using an LLM (OpenAI). It performs strict semantic extraction without inference.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional

from openai import OpenAI
from pydantic import ValidationError
from app.services.llm_client import chat_and_record
from app.services.model_settings import CHAT_AND_RECORD_METADATA
from app.services.news_api.view_schema import View, ViewList


def load_prompt(filename: str) -> str:
    """
    Load a prompt template from the prompts directory.
    
    Args:
        filename: Name of the prompt file (e.g., "system_prompt.txt")
    
    Returns:
        The prompt text as a string
    
    Raises:
        FileNotFoundError: If the prompt file doesn't exist
    """
    prompts_dir = Path(__file__).parent / "prompts"
    prompt_path = prompts_dir / filename
    
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    
    return prompt_path.read_text(encoding="utf-8")


def parse_article_to_views(article_text: str, api_key: Optional[str] = None, model: str = "gpt-4o") -> List[Dict]:
    """
    Parse an article into structured Black-Litterman views using an LLM.
    
    This function:
    1. Loads system and user prompts
    2. Inserts article text into user prompt
    3. Calls OpenAI chat completion
    4. Parses and validates JSON output
    5. Returns validated views as dict list
    
    Args:
        article_text: The article content to parse
        api_key: OpenAI API key (if None, reads from OPENAI_API_KEY env var)
        model: OpenAI model to use (default: gpt-4o)
    
    Returns:
        List of validated view dictionaries
    
    Raises:
        ValueError: If LLM output is not valid JSON or fails validation
        RuntimeError: If LLM call fails
    """
    # Load prompts
    system_prompt = load_prompt("system_prompt.txt")
    user_prompt_template = load_prompt("user_prompt.txt")
    
    # Insert article text into user prompt
    user_prompt = user_prompt_template.replace("{ARTICLE_TEXT}", article_text)
    
    # Validate API key if provided
    if api_key is None and not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OpenAI API key not provided and OPENAI_API_KEY env var not set")
    
    # Call LLM with automatic tracking
    metadata = CHAT_AND_RECORD_METADATA["news_api"]["parse_article_views"]
    try:
        llm_output = chat_and_record(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            service=metadata["service"],
            operation=metadata["operation"],
            model=model or metadata["model"],  # Allow override via parameter
            temperature=metadata["temperature"]
        )
        
        if not llm_output:
            raise RuntimeError("LLM returned empty response")
            
    except Exception as e:
        raise RuntimeError(f"LLM call failed: {e}") from e
    
    # Parse JSON
    try:
        parsed_json = json.loads(llm_output)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM output is not valid JSON: {e}\nOutput: {llm_output}") from e
    
    # Handle both direct list and wrapped in a key
    if isinstance(parsed_json, dict):
        # Try common keys that might wrap the list
        for key in ["views", "results", "data", "output"]:
            if key in parsed_json and isinstance(parsed_json[key], list):
                parsed_json = parsed_json[key]
                break
        else:
            # If it's still a dict, it might be a single view or an error
            if parsed_json:
                raise ValueError(f"Expected a list of views, got dict: {parsed_json}")
            else:
                parsed_json = []
    
    if not isinstance(parsed_json, list):
        raise ValueError(f"Expected a list of views, got: {type(parsed_json)}")
    
    # Validate using Pydantic schema
    try:
        view_list = ViewList(parsed_json)
        return view_list.to_list()
    except ValidationError as e:
        raise ValueError(f"LLM output failed validation: {e}\nOutput: {parsed_json}") from e


def parse_article_to_views_safe(article_text: str, api_key: Optional[str] = None, model: str = "gpt-4o") -> tuple[List[Dict], Optional[str]]:
    """
    Safe version of parse_article_to_views that catches errors.
    
    Args:
        article_text: The article content to parse
        api_key: OpenAI API key (if None, reads from OPENAI_API_KEY env var)
        model: OpenAI model to use
    
    Returns:
        Tuple of (views, error_message)
        - If successful: (list of views, None)
        - If failed: ([], error message string)
    """
    try:
        views = parse_article_to_views(article_text, api_key, model)
        return views, None
    except Exception as e:
        return [], str(e)

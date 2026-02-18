"""LLM parser module for text-to-JSON semantic extraction."""

import json
from pathlib import Path

from openai import OpenAI

from app.services.llm_client import chat_and_record
from app.services.model_settings import CHAT_AND_RECORD_METADATA


class ParserError(Exception):
    """Base exception for parser errors."""

    pass


class InvalidJSONError(ParserError):
    """Raised when LLM output is not valid JSON."""

    pass


class SchemaMismatchError(ParserError):
    """Raised when JSON does not match the selected schema."""

    pass


class MissingFieldError(ParserError):
    """Raised when required fields are missing."""

    pass


def _load_prompt(filename: str) -> str:
    """Load a prompt file from the prompts directory."""
    prompts_dir = Path(__file__).parent / "prompts"
    prompt_path = prompts_dir / filename
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def _extract_json_from_response(content: str) -> str:
    """Extract JSON from LLM response, handling markdown code blocks."""
    content = content.strip()
    
    # Handle markdown code blocks
    if content.startswith("```"):
        lines = content.split("\n")
        # Remove first line (```json or ```)
        lines = lines[1:]
        # Remove last line (```)
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines)
    
    return content.strip()


def parse_text_to_json(
    text: str,
    *,
    system_prompt_file: str = "system_prompt_backtesting.txt",
    user_prompt_file: str = "user_prompt.txt",
    schema: str = "backtesting",
    validate: bool = True,
) -> dict:
    """
    Parse user instruction text into validated JSON.

    Args:
        text: The user instruction in natural language.

    Returns:
        A validated dictionary matching the SemanticRecipe schema.

    Raises:
        InvalidJSONError: If LLM output is not valid JSON.
        SchemaMismatchError: If JSON does not match schema.
        MissingFieldError: If required fields are missing.
    """
    # Load prompts
    system_prompt = _load_prompt(system_prompt_file)
    user_prompt_template = _load_prompt(user_prompt_file)

    # Inject user text into user prompt
    user_prompt = user_prompt_template.replace("{USER_INPUT}", text)

    # Call LLM with automatic tracking
    metadata = CHAT_AND_RECORD_METADATA["recipe_interpreter_bt"]["parse_strategy"]
    raw_output = chat_and_record(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        service=metadata["service"],
        operation=metadata["operation"],
        model=metadata["model"],
        temperature=metadata["temperature"]
    )
    
    if raw_output is None:
        raise InvalidJSONError("LLM returned empty response")

    # Extract JSON from response
    json_str = _extract_json_from_response(raw_output)

    # Parse JSON
    try:
        parsed_data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise InvalidJSONError(f"Invalid JSON from LLM: {e}") from e

    return parsed_data
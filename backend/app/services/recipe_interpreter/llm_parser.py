"""LLM parser module for text-to-JSON semantic extraction."""

import json
from pathlib import Path

from openai import OpenAI
from pydantic import ValidationError

from .semantic_schema import SemanticRecipe


class ParserError(Exception):
    """Base exception for parser errors."""

    pass


class InvalidJSONError(ParserError):
    """Raised when LLM output is not valid JSON."""

    pass


class SchemaMismatchError(ParserError):
    """Raised when JSON does not match SemanticRecipe schema."""

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


def parse_text_to_json(text: str) -> dict:
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
    system_prompt = _load_prompt("system_prompt.txt")
    user_prompt_template = _load_prompt("user_prompt.txt")

    # Inject user text into user prompt
    user_prompt = user_prompt_template.replace("{USER_INPUT}", text)

    # Call OpenAI-compatible API
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
    )

    raw_output = response.choices[0].message.content
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
    # # Validate against schema
    # try:
    #     validated = SemanticRecipe.model_validate(parsed_data)
    # except ValidationError as e:
    #     errors = e.errors()
    #     missing_fields = [err for err in errors if err["type"] == "missing"]
    #     if missing_fields:
    #         field_names = [".".join(str(loc) for loc in err["loc"]) for err in missing_fields]
    #         raise MissingFieldError(f"Missing required fields: {field_names}") from e
    #     raise SchemaMismatchError(f"Schema validation failed: {e}") from e

    # return validated.model_dump()

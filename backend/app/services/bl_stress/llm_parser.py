"""
Black-Litterman Stress Test LLM Parser

Production-ready parser for converting natural language stress test requests
into structured StressSpec objects using an LLM.
"""

import os
import json
from typing import List, Dict, Optional

from app.services.llm_client import chat_and_record
from app.services.model_settings import CHAT_AND_RECORD_METADATA
from app.services.bl_stress.stress_schema import StressSpec


def available_stress_types() -> List[str]:
    """
    Get list of all available stress test types.
    
    Returns:
        List of valid stress_type values
    """
    return [
        "view_magnitude",
        "confidence_scale",
        "factor_amplification",
        "tau_shift",
        "volatility_multiplier",
        "regime_template",
        "view_joint"
    ]


class StressTestLLMParser:
    """
    Parser that orchestrates LLM-based extraction of stress test specifications.
    
    This class loads prompt templates, injects recipe context, calls an LLM,
    and validates the response into a StressSpec object.
    """
    
    def __init__(self, prompt_dir: str):
        """
        Initialize the parser.
        
        Args:
            prompt_dir: Directory path containing system_prompt.txt and user_prompt.txt
        """
        self.prompt_dir = prompt_dir
        
    def _load_file(self, path: str) -> str:
        """
        Load and return the contents of a text file.
        
        Args:
            path: Absolute or relative file path
            
        Returns:
            File contents as string
            
        Raises:
            FileNotFoundError: If the file does not exist
            IOError: If the file cannot be read
        """
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _build_user_prompt(
        self,
        template: str,
        view_labels: List[str],
        factors: List[str],
        stress_request: str
    ) -> str:
        """
        Build the user prompt by replacing template placeholders.
        
        Args:
            template: User prompt template with placeholders
            view_labels: List of available view labels from recipe
            factors: List of available factor names from recipe
            stress_request: User's natural language stress test request
            
        Returns:
            Formatted user prompt string
        """
        # Format view labels
        if view_labels:
            view_labels_str = "\n".join([f"  - {label}" for label in view_labels])
        else:
            view_labels_str = "  (No views available in recipe)"
        
        # Format factors
        if factors:
            factors_str = "\n".join([f"  - {factor}" for factor in factors])
        else:
            factors_str = "  (No factors available in recipe)"
        
        # Replace placeholders
        prompt = template.replace("{VIEW_LABELS}", view_labels_str)
        prompt = prompt.replace("{FACTORS}", factors_str)
        prompt = prompt.replace("{STRESS_REQUEST}", stress_request)
        
        return prompt
    
    def _extract_json_from_response(self, content: str) -> str:
        """
        Extract JSON from LLM response, handling markdown code blocks.
        
        Args:
            content: Raw LLM response string
            
        Returns:
            Cleaned JSON string
        """
        content = content.strip()
        
        # Handle markdown code blocks (```json ... ``` or ``` ... ```)
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first line (```json or ```)
            lines = lines[1:]
            # Remove last line (```)
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)
        
        return content.strip()
    
    def parse(
        self,
        user_request: str,
        recipe_context: Optional[Dict] = None
    ) -> StressSpec:
        """
        Parse a natural language stress test request into a StressSpec.
        
        This is the main entry point for the parser. It orchestrates:
        1. Loading prompt templates
        2. Building the formatted user prompt with recipe context
        3. Calling the LLM
        4. Parsing and validating the JSON response into a StressSpec
        
        Args:
            user_request: Natural language description of desired stress test
            recipe_context: Optional dictionary with:
                - views: List of available view labels
                - factors: List of available factor names
                This helps the LLM use exact labels from the recipe
        
        Returns:
            Validated StressSpec object
            
        Raises:
            ValueError: If JSON is invalid or fails StressSpec validation
            FileNotFoundError: If prompt files cannot be found
        """
        # Load system prompt
        system_prompt_path = os.path.join(self.prompt_dir, "system_prompt.txt")
        system_prompt = self._load_file(system_prompt_path)
        
        # Load user prompt template
        user_prompt_path = os.path.join(self.prompt_dir, "user_prompt.txt")
        user_prompt_template = self._load_file(user_prompt_path)
        
        # Extract recipe context
        view_labels = []
        factors = []
        if recipe_context:
            view_labels = recipe_context.get("views", [])
            factors = recipe_context.get("factors", [])
        
        # Build formatted user prompt
        user_prompt = self._build_user_prompt(
            template=user_prompt_template,
            view_labels=view_labels,
            factors=factors,
            stress_request=user_request
        )
        
        # Call LLM with automatic tracking
        metadata = CHAT_AND_RECORD_METADATA["bl_stress_parser"]["parse_stress_request"]
        response = chat_and_record(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            service=metadata["service"],
            operation=metadata["operation"],
            model=metadata["model"],
            temperature=metadata["temperature"],
            schema=None  # No schema enforcement, rely on prompt engineering
        )
        
        # Extract JSON from response (handles markdown code blocks)
        cleaned_response = self._extract_json_from_response(response)
        
        # Parse JSON response
        try:
            result = json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON returned by LLM: {e}\n\n"
                f"Raw Response: {response}\n\n"
                f"Cleaned Response: {cleaned_response}"
            )
        
        # Validate using Pydantic model
        # This will automatically check required fields and run validators
        try:
            stress_spec = StressSpec(**result)
        except Exception as e:
            raise ValueError(f"Invalid StressSpec: {e}\n\nParsed JSON: {result}")
        
        return stress_spec


def parse_stress_prompt(
    user_request: str,
    recipe_context: Optional[Dict] = None,
    prompt_dir: Optional[str] = None
) -> StressSpec:
    """
    Convenience function to parse a stress test request.
    
    Args:
        user_request: Natural language stress test request
        recipe_context: Optional dict with 'views' and 'factors' lists
        prompt_dir: Optional custom prompt directory path
                   If None, uses default location
    
    Returns:
        Validated StressSpec object
        
    Example:
        >>> spec = parse_stress_prompt(
        ...     "I want to stress test how sensitive we are to the AAPL view",
        ...     recipe_context={
        ...         "views": ["AAPL outperforms MSFT", "Tech leads market"],
        ...         "factors": ["Momentum", "Value", "Growth"]
        ...     }
        ... )
        >>> print(spec.stress_type)
        view_magnitude
        >>> print(spec.target_label)
        AAPL outperforms MSFT
    """
    if prompt_dir is None:
        # Default to prompts directory in this package
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_dir = os.path.join(current_dir, "prompts")
    
    parser = StressTestLLMParser(prompt_dir)
    return parser.parse(user_request, recipe_context)

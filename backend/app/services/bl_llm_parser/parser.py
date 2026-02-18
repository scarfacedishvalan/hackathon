"""
Black-Litterman LLM Parser

Production-ready parser for converting natural language investment views
into structured Black-Litterman format using an LLM.
"""

import os
import json
from typing import List, Dict, Optional

from app.services.llm_client import chat_and_record
from app.services.model_settings import CHAT_AND_RECORD_METADATA


class BlackLittermanLLMParser:
    """
    Parser that orchestrates LLM-based extraction of investment views.
    
    This class loads prompt templates, injects dynamic content, calls an LLM,
    and validates the structured response.
    """
    
    def __init__(
        self,
        prompt_dir: str,
        use_schema: bool = False
    ):
        """
        Initialize the parser.
        
        Args:
            prompt_dir: Directory path containing system_prompt.txt and user_prompt.txt
            use_schema: If True, loads and passes output_schema.json to the LLM client
        """
        self.prompt_dir = prompt_dir
        self.use_schema = use_schema
        
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
        assets: List[str],
        factors: List[str],
        text: str,
        asset_metadata: Optional[Dict] = None
    ) -> str:
        """
        Build the user prompt by replacing template placeholders.
        
        Args:
            template: User prompt template with placeholders
            assets: List of asset symbols
            factors: List of factor names
            text: Investor's natural language text
            asset_metadata: Optional dict with asset sector/factor metadata
            
        Returns:
            Formatted user prompt string
        """
        # Format assets and factors as JSON arrays
        asset_list = json.dumps(assets, indent=2)
        factor_list = json.dumps(factors, indent=2)
        
        # Format asset metadata
        if asset_metadata:
            # Filter metadata to only include assets in the universe
            filtered_metadata = {k: v for k, v in asset_metadata.items() if k in assets}
            metadata_str = json.dumps(filtered_metadata, indent=2)
        else:
            metadata_str = "No asset metadata provided"
        
        # Replace placeholders
        prompt = template.replace("{ASSET_LIST}", asset_list)
        prompt = prompt.replace("{FACTOR_LIST}", factor_list)
        prompt = prompt.replace("{ASSET_METADATA}", metadata_str)
        prompt = prompt.replace("{INVESTOR_TEXT}", text)
        
        return prompt
    
    def parse(
        self,
        assets: List[str],
        factors: List[str],
        investor_text: str,
        asset_metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Parse investor text into structured Black-Litterman views.
        
        This is the main entry point for the parser. It orchestrates:
        1. Loading prompt templates
        2. Building the formatted user prompt with asset metadata
        3. Calling the LLM with optional schema
        4. Parsing and validating the JSON response
        
        Args:
            assets: List of allowed asset symbols (e.g., ["AAPL", "MSFT"])
            factors: List of allowed factor names (e.g., ["Rates", "Growth"])
            investor_text: Natural language investment views
            asset_metadata: Optional dict mapping assets to sector/factor data
                Example: {"AAPL": {"sector": "Technology", "factor_exposures": {...}}}
                If None, parser works without sector context
            
        Returns:
            Dictionary containing:
                - bottom_up_views: List of bottom-up investment views
                - top_down_views: Dictionary with factor_shocks list
                
        Raises:
            ValueError: If JSON is invalid or required keys are missing
            FileNotFoundError: If prompt files cannot be found
        """
        # Load system prompt
        system_prompt_path = os.path.join(self.prompt_dir, "system_prompt.txt")
        system_prompt = self._load_file(system_prompt_path)
        
        # Load user prompt template
        user_prompt_path = os.path.join(self.prompt_dir, "user_prompt.txt")
        user_prompt_template = self._load_file(user_prompt_path)
        
        # Build formatted user prompt
        user_prompt = self._build_user_prompt(
            template=user_prompt_template,
            assets=assets,
            factors=factors,
            text=investor_text,
            asset_metadata=asset_metadata
        )
        
        # Load schema if enabled
        schema: Optional[Dict] = None
        if self.use_schema:
            schema_path = os.path.join(
                os.path.dirname(self.prompt_dir),
                "output_schema.json"
            )
            schema_content = self._load_file(schema_path)
            schema = json.loads(schema_content)
        
        # Call LLM with automatic tracking
        metadata = CHAT_AND_RECORD_METADATA["black_litterman_parser"]["parse_views"]
        response = chat_and_record(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            service=metadata["service"],
            operation=metadata["operation"],
            model=metadata["model"],
            temperature=metadata["temperature"],
            schema=schema
        )
        
        # Parse JSON response
        try:
            result = json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON returned by LLM: {e}")
        
        # Validate required top-level keys
        required_keys = {"bottom_up_views", "top_down_views"}
        missing_keys = required_keys - set(result.keys())
        
        if missing_keys:
            raise ValueError(
                f"Malformed output structure: missing keys {missing_keys}"
            )
        
        return result

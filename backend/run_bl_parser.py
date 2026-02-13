"""
Black-Litterman LLM Parser Runner

Demonstrates the BL parser by processing natural language investment views
and converting them into structured JSON format for Black-Litterman models.

This runner script:
- Uses a mock LLM client for demonstration (can be replaced with real LLM)
- Loads prompts from the bl_llm_parser/prompts directory
- Shows how to parse investor text into bottom-up and top-down views
- Validates the structured output format
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

from openai import OpenAI

# Add backend directory to path for imports
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.bl_llm_parser.parser import BlackLittermanLLMParser


def load_asset_metadata() -> dict:
    """
    Load asset metadata from sector_metadata.json.
    
    Returns:
        Dictionary mapping asset symbols to sector/factor metadata
    """
    metadata_path = BACKEND_DIR / "app" / "services" / "bl_llm_parser" / "sector_metadata.json"
    
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"\u26a0\ufe0f  Warning: Asset metadata file not found at {metadata_path}")
        return {}
    except json.JSONDecodeError as e:
        print(f"\u26a0\ufe0f  Warning: Could not parse metadata file: {e}")
        return {}


class OpenAIClient:
    """
    OpenAI client wrapper for the Black-Litterman parser.
    
    Uses OpenAI Python SDK 5.2+ with chat completions API.
    Supports optional structured outputs via response_format parameter.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.1
    ):
        """
        Initialize OpenAI client.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model name to use (default: gpt-4o-mini)
            temperature: Sampling temperature (default: 0.1 for consistent parsing)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.temperature = temperature
    
    def _add_additional_properties(self, schema: dict) -> dict:
        """
        Recursively add 'additionalProperties': false to all objects in schema.
        
        This is required by OpenAI's structured output strict mode.
        
        Args:
            schema: JSON schema dictionary
            
        Returns:
            Modified schema with additionalProperties set
        """
        import copy
        schema = copy.deepcopy(schema)
        
        def process_schema(obj):
            if isinstance(obj, dict):
                # Add additionalProperties: false to all objects
                if obj.get("type") == "object":
                    obj["additionalProperties"] = False
                
                # Recursively process all values
                for key, value in obj.items():
                    obj[key] = process_schema(value)
            elif isinstance(obj, list):
                return [process_schema(item) for item in obj]
            
            return obj
        
        return process_schema(schema)
    
    def chat(self, system_prompt: str, user_prompt: str, schema: Optional[dict] = None) -> str:
        """
        Call OpenAI chat completion API.
        
        Args:
            system_prompt: System prompt text
            user_prompt: User prompt text
            schema: Optional JSON schema for structured output
            
        Returns:
            Response content as string (JSON if schema provided)
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Prepare API call parameters
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature
        }
        
        # Add structured output if schema provided (requires compatible model)
        if schema:
            # Use json_object mode for more flexible schema support
            # Strict mode requires all properties to be required, which doesn't
            # work well with our optional fields (asset vs assets, etc.)
            kwargs["response_format"] = {"type": "json_object"}
        
        # Call API
        response = self.client.chat.completions.create(**kwargs)
        
        # Extract and return content
        return response.choices[0].message.content


# COMMENTED OUT - SimpleMockLLMClient (kept for reference)
# class SimpleMockLLMClient:
#     """
#     Simple mock LLM client for demonstration purposes.
#     
#     In production, replace this with:
#     - OpenAI GPT client
#     - Azure OpenAI client
#     - Anthropic Claude client
#     - Local LLM via LangChain
#     """
#     
#     def chat(self, system_prompt: str, user_prompt: str, schema: Optional[dict] = None) -> str:
#         """
#         Mock chat that returns a hardcoded valid BL structure.
#         
#         In a real implementation, this would:
#         1. Send system_prompt and user_prompt to the LLM
#         2. Optionally enforce the schema if provided
#         3. Return the LLM's JSON response as a string
#         """
#         # Parse out investor text for basic mock response
#         if "outperform" in user_prompt.lower() and "microsoft" in user_prompt.lower():
#             return json.dumps({
#                 "bottom_up_views": [
#                     {
#                         "type": "relative",
#                         "assets": ["AAPL", "MSFT"],
#                         "weights": [1, -1],
#                         "expected_outperformance": 0.03,
#                         "confidence": 0.85,
#                         "label": "Apple to strongly outperform Microsoft by 3%"
#                     }
#                 ],
#                 "top_down_views": {
#                     "factor_shocks": []
#                 }
#             })
#         elif "decline" in user_prompt.lower() or "bearish" in user_prompt.lower():
#             return json.dumps({
#                 "bottom_up_views": [
#                     {
#                         "type": "absolute",
#                         "asset": "TSLA",
#                         "expected_return": -0.05,
#                         "confidence": 0.70,
#                         "label": "Tesla expected to decline"
#                     }
#                 ],
#                 "top_down_views": {
#                     "factor_shocks": [
#                         {
#                             "factor": "Rates",
#                             "shock": 0.025,
#                             "confidence": 0.75,
#                             "label": "Rising interest rate environment"
#                         }
#                     ]
#                 }
#             })
#         else:
#             # Generic response
#             return json.dumps({
#                 "bottom_up_views": [],
#                 "top_down_views": {
#                     "factor_shocks": []
#                 }
#             })


def print_section(title: str):
    """Print formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_views(result: dict):
    """Pretty print the parsed views."""
    
    # Print bottom-up views
    bottom_up = result.get("bottom_up_views", [])
    print(f"\n📊 Bottom-Up Views: {len(bottom_up)}")
    
    if bottom_up:
        for i, view in enumerate(bottom_up, 1):
            view_type = view.get("type", "unknown")
            label = view.get("label", "No label")
            confidence = float(view.get("confidence", 0))
            
            print(f"\n  [{i}] {label}")
            print(f"      Type: {view_type}")
            print(f"      Confidence: {confidence:.2f}")
            
            if view_type == "relative":
                assets = view.get("assets", [])
                weights = view.get("weights", [])
                outperformance = float(view.get("expected_outperformance", 0))
                print(f"      Assets: {' vs '.join(assets)}")
                print(f"      Weights: {weights}")
                print(f"      Expected Outperformance: {outperformance:+.2%}")
            elif view_type == "absolute":
                asset = view.get("asset", "")
                expected_return = float(view.get("expected_return", 0))
                print(f"      Asset: {asset}")
                print(f"      Expected Return: {expected_return:+.2%}")
    else:
        print("  (none)")
    
    # Print top-down views
    top_down = result.get("top_down_views", {})
    factor_shocks = top_down.get("factor_shocks", [])
    
    print(f"\n🌍 Top-Down Factor Views: {len(factor_shocks)}")
    
    if factor_shocks:
        for i, shock in enumerate(factor_shocks, 1):
            factor = shock.get("factor", "")
            shock_value = float(shock.get("shock", 0))
            confidence = float(shock.get("confidence", 0))
            label = shock.get("label", "No label")
            
            print(f"\n  [{i}] {label}")
            print(f"      Factor: {factor}")
            print(f"      Shock: {shock_value:+.3f}")
            print(f"      Confidence: {confidence:.2f}")
    else:
        print("  (none)")


def run_example(
    investor_text: str,
    assets: list,
    factors: list,
    use_schema: bool = False,
    title: str = "Example",
    output_file: Optional[str] = None,
    asset_metadata: Optional[dict] = None
):
    """Run a single parsing example."""
    
    print_section(title)
    
    # Display inputs
    print(f"\n📝 Investor Text:")
    print(f'   "{investor_text}"')
    print(f"\n📈 Universe: {', '.join(assets)}")
    print(f"🔍 Factors: {', '.join(factors)}")
    print(f"⚙️  Schema Enforcement: {'Enabled' if use_schema else 'Disabled'}")
    
    # Show if metadata is being used
    if asset_metadata:
        available_assets = [a for a in assets if a in asset_metadata]
        print(f"📊 Asset Metadata: Available for {len(available_assets)}/{len(assets)} assets")
    
    # Initialize parser with OpenAI client
    prompt_dir = BACKEND_DIR / "app" / "services" / "bl_llm_parser" / "prompts"
    
    try:
        llm_client = OpenAIClient(model="gpt-4o-mini", temperature=0.1)
    except ValueError as e:
        print(f"\n❌ {e}")
        print("\nTo use OpenAI, set your API key:")
        print("  export OPENAI_API_KEY='your-api-key'  # Linux/Mac")
        print("  $env:OPENAI_API_KEY='your-api-key'   # Windows PowerShell")
        return None
    
    parser = BlackLittermanLLMParser(
        llm_client=llm_client,
        prompt_dir=str(prompt_dir),
        use_schema=use_schema
    )
    
    # Parse
    try:
        result = parser.parse(
            assets=assets,
            factors=factors,
            investor_text=investor_text,
            asset_metadata=asset_metadata
        )
        
        # Save to JSON file first (before printing in case printing fails)
        if output_file:
            output_path = BACKEND_DIR / output_file
            output_data = {
                "input": {
                    "investor_text": investor_text,
                    "assets": assets,
                    "factors": factors,
                    "use_schema": use_schema
                },
                "output": result
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Saved to: {output_file}")
        
        # Display results (may fail if LLM returns bad types)
        try:
            print_views(result)
        except (ValueError, TypeError) as e:
            print(f"\n⚠️  Warning: Could not format output for display: {e}")
            print(f"    Raw output saved to JSON file.")
        
        print("\n✅ Parsing successful")
        return result
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return None


def run_interactive_mode():
    """Run interactive mode where user can enter text."""
    print_section("Interactive Mode")
    print("\nEnter your investment views in natural language.")
    print("Type 'quit' or 'exit' to stop.\n")
    
    # Load asset metadata
    asset_metadata = load_asset_metadata()
    
    # Default universe
    assets = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA"]
    factors = ["Rates", "Growth", "Value", "Momentum"]
    
    print(f"Universe: {', '.join(assets)}")
    print(f"Factors: {', '.join(factors)}")
    if asset_metadata:
        available = [a for a in assets if a in asset_metadata]
        print(f"Metadata: Available for {len(available)}/{len(assets)} assets")
    print()
    
    prompt_dir = BACKEND_DIR / "app" / "services" / "bl_llm_parser" / "prompts"
    
    try:
        llm_client = OpenAIClient(model="gpt-4o-mini", temperature=0.1)
    except ValueError as e:
        print(f"\n❌ {e}")
        print("\nTo use OpenAI, set your API key:")
        print("  export OPENAI_API_KEY='your-api-key'  # Linux/Mac")
        print("  $env:OPENAI_API_KEY='your-api-key'   # Windows PowerShell")
        return
    
    parser = BlackLittermanLLMParser(
        llm_client=llm_client,
        prompt_dir=str(prompt_dir),
        use_schema=True
    )
    
    while True:
        try:
            investor_text = input("\n💭 Your view: ").strip()
            
            if investor_text.lower() in ("quit", "exit", "q"):
                print("\nGoodbye! 👋")
                break
                
            if not investor_text:
                continue
            
            result = parser.parse(
                assets=assets,
                factors=factors,
                investor_text=investor_text,
                asset_metadata=asset_metadata
            )
            
            print_views(result)
            
        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run Black-Litterman LLM Parser examples",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_bl_parser.py                    # Run demo examples
  python run_bl_parser.py --interactive      # Interactive mode
  python run_bl_parser.py --text "AAPL will outperform MSFT by 5%%"
        """
    )
    
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode"
    )
    
    parser.add_argument(
        "--text", "-t",
        type=str,
        help="Parse specific investor text"
    )
    
    parser.add_argument(
        "--assets",
        type=str,
        default="AAPL,MSFT,GOOGL,AMZN,TSLA",
        help="Comma-separated list of assets (default: AAPL,MSFT,GOOGL,AMZN,TSLA)"
    )
    
    parser.add_argument(
        "--factors",
        type=str,
        default="Rates,Growth,Value,Momentum",
        help="Comma-separated list of factors (default: Rates,Growth,Value,Momentum)"
    )
    
    parser.add_argument(
        "--schema",
        action="store_true",
        help="Enable schema enforcement"
    )
    
    args = parser.parse_args()
    
    # Load asset metadata
    asset_metadata = load_asset_metadata()
    if asset_metadata:
        print(f"\n✓ Loaded metadata for {len(asset_metadata)} assets")
    
    # Parse assets and factors
    assets = [a.strip() for a in args.assets.split(",")]
    factors = [f.strip() for f in args.factors.split(",")]
    
    if args.interactive:
        run_interactive_mode()
    elif args.text:
        # Generate output filename from timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"bl_parser_output_{timestamp}.json"
        
        run_example(
            investor_text=args.text,
            assets=assets,
            factors=factors,
            use_schema=args.schema,
            title="Custom Input",
            output_file=output_file,
            asset_metadata=asset_metadata
        )
    else:
        # Run demo examples
        print("\n" + "*" * 70)
        print("  BLACK-LITTERMAN LLM PARSER DEMONSTRATION")
        print("*" * 70)
        print("\nThis script demonstrates parsing natural language investment views")
        print("into structured JSON format for Black-Litterman portfolio models.")
        
        # Example 1: Relative view
        run_example(
            investor_text="Apple will strongly outperform Microsoft by 3% this quarter.",
            assets=["AAPL", "MSFT", "GOOGL", "AMZN"],
            factors=["Rates", "Growth"],
            use_schema=True,
            title="Example 1: Relative View",
            output_file="bl_parser_example1_relative.json",
            asset_metadata=asset_metadata
        )
        
        # Example 2: Absolute view with macro factor
        run_example(
            investor_text="I'm bearish on Tesla. Expecting 5% decline. Rising rates are a concern.",
            assets=["TSLA", "NVDA", "AMD"],
            factors=["Rates", "Growth", "Momentum"],
            use_schema=True,
            title="Example 2: Absolute View + Macro Factor",
            output_file="bl_parser_example2_absolute_macro.json",
            asset_metadata=asset_metadata
        )
        
        # Example 3: Neutral (no views)
        run_example(
            investor_text="The market looks uncertain. No strong opinion.",
            assets=["AAPL", "MSFT"],
            factors=["Rates"],
            use_schema=False,
            title="Example 3: Neutral View",
            output_file="bl_parser_example3_neutral.json",
            asset_metadata=asset_metadata
        )

        run_example(
            investor_text="TSLA will outperform MSFT by 2%. Rates are expected to rise by 0.5%, which will impact growth stocks negatively. Momentum in tech sector is strong.",
            assets=["AAPL", "MSFT", "TSLA"],
            factors=["Rates", "Growth", "Momentum"],
            use_schema=False,
            title="Example 4: Mixed View",
            output_file="bl_parser_example4_mixed.json",
            asset_metadata=asset_metadata
        )
        
        print("\n" + "=" * 70)
        print("\n💡 Using OpenAI API (gpt-4o-mini)")
        print("   Set OPENAI_API_KEY environment variable to use.")
        print("\n   Alternative LLM options:")
        print("   - Azure OpenAI client")
        print("   - Anthropic Claude client")
        print("   - Local LLM via LangChain/Ollama")
        print("\n" + "=" * 70)


if __name__ == "__main__":
    main()

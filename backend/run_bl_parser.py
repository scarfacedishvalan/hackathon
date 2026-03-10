import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.bl_llm_parser.parser import BlackLittermanLLMParser


ASSETS = ["AAPL", "AMZN", "BAC", "BND", "GLD", "GOOG", "GOOGL", "JNJ", "JPM", "MSFT", "PG", "TSLA", "VNQ", "WMT"]
FACTORS = ["Growth", "Financial", "Defensive", "Market", "Rates"]

INVESTOR_TEXT = (
    "Rising rates will strongly benefit financials and slightly hurt defensives."
)


def main():
    prompt_dir = BACKEND_DIR / "app" / "services" / "bl_llm_parser" / "prompts"

    parser = BlackLittermanLLMParser(prompt_dir=str(prompt_dir), use_schema=True)

    result = parser.parse(
        assets=ASSETS,
        factors=FACTORS,
        investor_text=INVESTOR_TEXT,
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

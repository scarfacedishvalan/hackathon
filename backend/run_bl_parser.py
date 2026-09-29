import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.bl_llm_parser.parser import BlackLittermanLLMParser

_MARKET_DATA_PATH = BACKEND_DIR / "data" / "market_data.json"

def _load_market_defaults():
    with open(_MARKET_DATA_PATH, "r", encoding="utf-8") as f:
        md = json.load(f)
    return md["all_assets"], md["factor_names"]

ASSETS, FACTORS = _load_market_defaults()

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

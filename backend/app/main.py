from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.services.recipe_interpreter.backtesting_from_json import run_from_recipe

try:
    # Optional: only used if you want to parse natural language into a recipe.
    from app.services.recipe_interpreter.llm_parser import parse_text_to_json
except Exception:  # pragma: no cover
    parse_text_to_json = None  # type: ignore[assignment]

app = FastAPI(title="Portfolio Backtesting API", version="1.0.0")

APP_DIR = Path(__file__).resolve().parent
PLOTS_DIR = APP_DIR / "services" / "plots"
PROMPTS_DIR = APP_DIR / "services" / "recipe_interpreter" / "prompts"

# Ensure plots dir exists before mounting static files
PLOTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/plots", StaticFiles(directory=str(PLOTS_DIR)), name="plots")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    # Allow local dev frontends on any port (Vite can change ports, and it may use 127.0.0.1).
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RecipeRequest(BaseModel):
    stocks: List[str]
    strategy_instruction: str


class RecipeResponse(BaseModel):
    recipe: Dict[str, Any]
    equity_curve: List[Dict[str, Any]]
    summary_stats: Dict[str, Any]
    plot_url: Optional[str] = None


def _load_example_recipe() -> Dict[str, Any]:
    path = PROMPTS_DIR / "backtesting_example_expected_output.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _can_import_yfinance() -> bool:
    try:
        import yfinance  # noqa: F401
    except Exception:
        return False
    return True


def _force_sample_source(recipe: Dict[str, Any]) -> Dict[str, Any]:
    data = recipe.get("data")
    if not isinstance(data, dict):
        recipe["data"] = {"symbol": None, "source": "sample", "path": None, "start": None, "end": None}
        return recipe

    if data.get("path"):
        return recipe

    data["source"] = "sample"
    # Clear date filters so the bundled sample dataset always has enough bars.
    data["start"] = None
    data["end"] = None
    return recipe


def _slug(text: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in text.strip())
    cleaned = cleaned.strip("_-")
    return cleaned or "plot"


def _stats_to_api_payload(stats: Any) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Convert Backtesting.py stats to JSON-friendly structures."""

    equity_curve: List[Dict[str, Any]] = []
    summary: Dict[str, Any] = {}

    # Backtesting.py returns a pandas Series-like object.
    if hasattr(stats, "to_dict"):
        as_dict = stats.to_dict()  # type: ignore[attr-defined]
    elif isinstance(stats, dict):
        as_dict = stats
    else:
        as_dict = {"stats": str(stats)}

    eq = as_dict.get("_equity_curve")
    if isinstance(eq, pd.DataFrame) and not eq.empty:
        eq_df = eq.copy()
        if isinstance(eq_df.index, pd.DatetimeIndex):
            eq_df = eq_df.reset_index().rename(columns={"index": "Date"})
        if "Date" in eq_df.columns:
            eq_df["Date"] = pd.to_datetime(eq_df["Date"]).dt.strftime("%Y-%m-%d")
        equity_curve = jsonable_encoder(eq_df.to_dict(orient="records"))

    # Keep only non-private keys for summary.
    for key, value in as_dict.items():
        if str(key).startswith("_"):
            continue
        # jsonable_encoder handles numpy/pandas scalars reasonably well.
        summary[str(key)] = jsonable_encoder(value)

    return equity_curve, summary


@app.get("/")
def read_root():
    return {"message": "Portfolio Backtesting API", "status": "running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/api/generate-recipe", response_model=RecipeResponse)
async def generate_recipe_endpoint(request: RecipeRequest):
    """
    Generate a recipe based on selected stocks and strategy instruction.
    Currently returns mock data - to be replaced with actual implementation.
    """
    try:
        # 1) Build/parse a recipe
        print("Generating recipe for instruction:", request.strategy_instruction)
        recipe: Dict[str, Any]
        if parse_text_to_json is not None and request.strategy_instruction.strip():
            # Best-effort LLM parse. If it fails, we fall back to the example recipe.
            try:
                recipe = parse_text_to_json(request.strategy_instruction)
            except Exception:
                print("LLM parsing failed, falling back to example recipe.")
                recipe = _load_example_recipe()
        else:
            print("No strategy instruction provided, using example recipe.")
            recipe = _load_example_recipe()

        # 2) Apply selected stock(s). The Backtesting.py runner supports a single symbol.
        if request.stocks:
            recipe.setdefault("data", {})
            if isinstance(recipe["data"], dict):
                recipe["data"]["symbol"] = request.stocks[0]
                recipe["data"].setdefault("path", None)
                recipe["data"].setdefault("source", None)

        # 3) Ensure data source is runnable in typical dev envs.
        # If yfinance isn't available and no data.path is provided, fall back to sample.
        data = recipe.get("data")
        print("Using recipe data source:", data)
        if isinstance(data, dict) and not data.get("path"):
            wants_symbol = bool(data.get("symbol"))
            if wants_symbol and not _can_import_yfinance():
                recipe = _force_sample_source(recipe)
            elif data.get("source") is None and not wants_symbol:
                recipe = _force_sample_source(recipe)

        # 4) Run backtest and save plot by default.
        print("Running backtest from recipe...")
        strategy = _slug(str(recipe.get("strategy_name") or "strategy"))
        symbol = _slug(str((recipe.get("data") or {}).get("symbol") or "data"))
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        plot_filename = f"backtest_{ts}_{strategy}_{symbol}.html"
        plot_path = PLOTS_DIR / plot_filename

        try:
            stats = run_from_recipe(recipe, plot_path=plot_path, open_plot=False)
        except NotImplementedError as exc:
            # LLM/user may request a strategy we don't support in the Backtesting.py runner.
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        equity_curve, summary_stats = _stats_to_api_payload(stats)

        return {
            "recipe": jsonable_encoder(recipe),
            "equity_curve": equity_curve,
            "summary_stats": summary_stats,
            "plot_url": f"/plots/{plot_filename}",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recipe/backtest: {str(e)}")

"""
Simulated Financial News Generator

Uses an LLM to generate realistic but entirely fictional news articles about
a given stock ticker, optionally guided by keywords/themes.

The output format is identical to fetch_news_for_stock so the rest of the
news pipeline (view_parser → bl_llm_parser) works without modification.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from app.services.llm_client import chat_and_record
from app.services.model_settings import CHAT_AND_RECORD_METADATA

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(filename: str) -> str:
    return (_PROMPTS_DIR / filename).read_text(encoding="utf-8")


def _fake_url(ticker: str, title: str) -> str:
    """Stable deterministic URL so the deduplication ID is consistent."""
    h = hashlib.md5(f"{ticker}:{title}".encode()).hexdigest()[:10]
    return f"https://simulation.example.com/{ticker.lower()}/{h}"


def generate_simulated_articles(
    ticker: str,
    keywords: Optional[List[str]] = None,
    limit: int = 5,
) -> List[Dict]:
    """
    Generate *limit* realistic but fictional financial news articles about *ticker*.

    Args:
        ticker:   Stock ticker symbol (e.g. 'AAPL')
        keywords: Optional themes to weave into the articles
                  (e.g. ['earnings beat', 'rate sensitivity'])
        limit:    Number of articles to generate (1–10 recommended)

    Returns:
        List of article dicts with keys:
            title, source, url, description, published_at, author, content
        Identical shape to the output of fetch_news_for_stock.

    Raises:
        RuntimeError: If the LLM call fails.
        ValueError:   If the LLM returns invalid JSON.
    """
    keywords = keywords or []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    system_prompt = _load_prompt("generate_system_prompt.txt")
    user_prompt = (
        _load_prompt("generate_user_prompt.txt")
        .replace("{TICKER}", ticker)
        .replace("{KEYWORDS}", ", ".join(keywords) if keywords else "general market outlook")
        .replace("{LIMIT}", str(limit))
        .replace("{TODAY}", today)
    )

    metadata = CHAT_AND_RECORD_METADATA["news_api"]["generate_article"]
    try:
        raw = chat_and_record(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            **metadata,
        )
    except Exception as exc:
        raise RuntimeError(f"LLM article generation failed for {ticker}: {exc}") from exc

    # Parse JSON — strip markdown fences if the model added them
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        articles_raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"LLM returned invalid JSON for {ticker}: {exc}\nRaw output: {raw[:400]}"
        ) from exc

    # Normalise: accept {"articles": [...]} wrapper or bare list
    if isinstance(articles_raw, dict):
        articles_raw = articles_raw.get("articles", articles_raw.get("items", []))

    now_iso = datetime.now(timezone.utc).isoformat()
    articles: List[Dict] = []
    for item in articles_raw[:limit]:
        title = item.get("title", f"Simulated {ticker} News")
        articles.append({
            "title": title,
            "source": item.get("source", "Simulated News"),
            "url": _fake_url(ticker, title),
            "description": item.get("description", ""),
            "published_at": item.get("published_at", now_iso),
            "author": item.get("author", "AI Correspondent"),
            "content": item.get("content") or item.get("description", ""),
        })

    return articles

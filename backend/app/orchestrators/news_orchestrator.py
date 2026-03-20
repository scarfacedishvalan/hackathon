"""
News Orchestrator

Fetches news articles, converts them to natural-language BL view summaries
(translatedView), and stores them in backend/data/news.json.

When the user clicks "+ Active Views", the stored translatedView string is
sent through the existing bl_llm_parser pipeline which produces properly
quantified bottom_up_views / factor_shocks and appends them to current.json.
"""

import hashlib
import json
import random
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.news_api.fetch_news import fetch_news_for_stock
from app.services.news_api.view_parser import parse_article_to_views_safe
from app.services.bl_llm_parser.parser import BlackLittermanLLMParser
from app.orchestrators import view_orchestrator

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
_NEWS_PATH = _DATA_DIR / "news.json"
_PARSER_PROMPTS = Path(__file__).resolve().parent.parent / "services" / "bl_llm_parser" / "prompts"

# ---------------------------------------------------------------------------
# Defaults  (kept in sync with market_data.json)
# ---------------------------------------------------------------------------

DEFAULT_ASSETS: List[str] = [
    "AAPL", "AMZN", "BAC", "BND", "GLD", "GOOG", "GOOGL",
    "JNJ", "JPM", "MSFT", "PG", "TSLA", "VNQ", "WMT",
]
DEFAULT_FACTORS: List[str] = ["Growth", "Financial", "Defensive", "Market", "Rates"]

# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


def load_news() -> List[Dict[str, Any]]:
    """Return the list of news items from news.json, or [] if absent."""
    if not _NEWS_PATH.exists():
        return []
    try:
        with open(_NEWS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("items", [])
    except (json.JSONDecodeError, OSError):
        return []


def save_news(items: List[Dict[str, Any]]) -> None:
    """Persist *items* to news.json, overwriting the existing file."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(_NEWS_PATH, "w", encoding="utf-8") as f:
        json.dump({"items": items}, f, indent=2, ensure_ascii=False)


def _fuzzy_match(text: str, keyword: str, threshold: float = 0.6) -> bool:
    """
    Check if keyword fuzzy-matches text using SequenceMatcher.
    
    Args:
        text: Text to search in
        keyword: Keyword to search for
        threshold: Similarity threshold (0.0 to 1.0, default 0.6)
    
    Returns:
        True if keyword matches text with similarity >= threshold
    """
    text_lower = text.lower()
    keyword_lower = keyword.lower()
    
    # Exact substring match (fast path)
    if keyword_lower in text_lower:
        return True
    
    # Fuzzy match on whole text
    ratio = SequenceMatcher(None, text_lower, keyword_lower).ratio()
    if ratio >= threshold:
        return True
    
    # Fuzzy match on individual words
    words = text_lower.split()
    for word in words:
        ratio = SequenceMatcher(None, word, keyword_lower).ratio()
        if ratio >= threshold:
            return True
    
    return False


def get_random_news(keyword: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Return random news items from news.json, optionally filtered by keyword.
    
    Uses fuzzy matching to find articles where the keyword appears in:
    - heading
    - translatedView
    - ticker symbol
    
    Args:
        keyword: Optional keyword to filter by (fuzzy matching with 60% threshold)
        limit:   Maximum number of items to return (default: 5)
    
    Returns:
        List of random news items (up to *limit* items)
    """
    all_items = load_news()
    
    # Filter by keyword if provided
    if keyword:
        filtered = [
            item for item in all_items
            if (_fuzzy_match(item.get("heading", ""), keyword) or
                _fuzzy_match(item.get("translatedView", ""), keyword) or
                _fuzzy_match(item.get("ticker", ""), keyword))
        ]
    else:
        filtered = all_items
    
    # Return random sample
    if len(filtered) <= limit:
        return filtered
    return random.sample(filtered, limit)


def count_news(keyword: Optional[str] = None) -> int:
    """
    Count total news items, optionally filtered by keyword.
    
    Args:
        keyword: Optional keyword to filter by (fuzzy matching)
    
    Returns:
        Count of matching items
    """
    all_items = load_news()
    
    if not keyword:
        return len(all_items)
    
    return sum(
        1 for item in all_items
        if (_fuzzy_match(item.get("heading", ""), keyword) or
            _fuzzy_match(item.get("translatedView", ""), keyword) or
            _fuzzy_match(item.get("ticker", ""), keyword))
    )


# ---------------------------------------------------------------------------
# Article → translatedView conversion
# ---------------------------------------------------------------------------


def _stable_id(url: str) -> str:
    """Return a stable 12-char hex ID derived from the article URL."""
    return hashlib.md5(url.encode()).hexdigest()[:12]


def _views_to_translated(views: List[Dict[str, Any]], ticker: str, title: str) -> str:
    """
    Convert the raw view_schema.View objects returned by news_api/view_parser
    into a single natural-language sentence suitable as bl_llm_parser input.
    """
    if not views:
        # Fall back to the article title as a minimal investor statement
        return title

    parts = []
    for v in views:
        view_type = v.get("type")
        direction = v.get("direction", "positive")
        confidence = v.get("confidence", "medium")
        asset_long = v.get("asset_long") or ticker
        asset_short = v.get("asset_short")
        factor = v.get("factor")

        dir_word = "positive" if direction == "positive" else "negative"
        conf_word = {"high": "strongly", "medium": "moderately", "low": "slightly"}.get(confidence, "moderately")

        if view_type == "relative" and asset_short:
            parts.append(
                f"{asset_long} is expected to {conf_word} outperform {asset_short}."
                if direction == "positive"
                else f"{asset_long} is expected to {conf_word} underperform {asset_short}."
            )
        elif view_type == "absolute":
            parts.append(
                f"{asset_long} is expected to have a {conf_word} {dir_word} return."
            )
        elif view_type == "factor" and factor:
            parts.append(
                f"The {factor} factor is expected to deliver a {conf_word} {dir_word} premium."
            )

    return " ".join(parts) if parts else title


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_and_parse(
    tickers: Optional[List[str]] = None,
    limit_per_ticker: int = 5,
    keywords: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Generate simulated news for each ticker, extract a translatedView summary
    via news_api/view_parser, and persist new items to news.json.

    Existing items (matched by content hash) are NOT overwritten.

    Args:
        tickers:          Tickers to generate articles for (defaults to DEFAULT_ASSETS)
        limit_per_ticker: Articles per ticker
        keywords:         Optional themes to weave into every generated article

    Returns:
        The full updated list of news items.
    """
    if tickers is None:
        tickers = DEFAULT_ASSETS

    existing = load_news()
    existing_ids = {item["id"] for item in existing}
    new_items: List[Dict[str, Any]] = []

    for ticker in tickers:
        try:
            articles = fetch_news_for_stock(ticker, limit=limit_per_ticker, keywords=keywords)
        except Exception as exc:
            print(f"[news_orchestrator] fetch failed for {ticker}: {exc}")
            continue

        for article in articles:
            url = article.get("url", "")
            item_id = _stable_id(url)

            if item_id in existing_ids:
                continue  # deduplicate

            title = article.get("title", "") or ""
            description = article.get("description", "") or ""
            source = article.get("source", "") or ""
            article_text = f"{title}. {description}".strip()

            views, _err = parse_article_to_views_safe(article_text)
            translated_view = _views_to_translated(views, ticker, title)

            item: Dict[str, Any] = {
                "id": item_id,
                "heading": title,
                "translatedView": translated_view,
                "link": url,
                "source": source,
                "ticker": ticker,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            new_items.append(item)
            existing_ids.add(item_id)

    merged = new_items + existing  # new items at top
    save_news(merged)
    return merged


def add_view_to_recipe(
    item_id: str,
    assets: Optional[List[str]] = None,
    factors: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Find the news item by *item_id*, send its translatedView through the
    bl_llm_parser pipeline, and append the result to current.json.

    Returns:
        The raw parse result dict (bottom_up_views + top_down_views).

    Raises:
        KeyError: If no item with *item_id* exists in news.json.
    """
    if assets is None:
        assets = DEFAULT_ASSETS
    if factors is None:
        factors = DEFAULT_FACTORS

    items = load_news()
    item = next((i for i in items if i["id"] == item_id), None)
    if item is None:
        raise KeyError(f"No news item with id '{item_id}'")

    investor_text: str = item["translatedView"]

    parser = BlackLittermanLLMParser(
        prompt_dir=str(_PARSER_PROMPTS),
        use_schema=True,
    )
    result = parser.parse(
        assets=assets,
        factors=factors,
        investor_text=investor_text,
    )

    view_orchestrator._append_views_to_current(result)
    return result

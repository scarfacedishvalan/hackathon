"""
News Router

Exposes three endpoints for the Analyst Suggestions feature:
  GET  /news              — return cached news items from news.json
  POST /news/fetch        — fetch fresh articles and generate translatedViews
  POST /news/{id}/add-view — parse translatedView and append to current.json
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from app.orchestrators import news_orchestrator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/news", tags=["news"])


class FetchNewsRequest(BaseModel):
    tickers: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    limit_per_ticker: int = 5


@router.get("")
async def get_news(
    keyword: Optional[str] = Query(None, description="Filter news by keyword (fuzzy searches heading, translatedView, ticker)"),
    limit: int = Query(5, ge=1, le=50, description="Number of random items to return")
):
    """
    Return random news items from news.json, optionally filtered by keyword.

    Uses fuzzy matching (75% similarity threshold) to find articles where the
    keyword appears in heading, translatedView, or ticker symbol.

    Query params:
      - keyword: Filter articles by keyword with fuzzy matching
      - limit: Number of random items to return (default: 5, max: 50)

    Response shape::

        {
          "items": [
            {
              "id": str,
              "heading": str,
              "translatedView": str,
              "link": str,
              "source": str,
              "ticker": str,
              "fetched_at": str
            },
            ...
          ],
          "total_available": int,
          "returned": int
        }
    
    Examples:
      - GET /news               → 5 random articles
      - GET /news?limit=10      → 10 random articles
      - GET /news?keyword=AAPL  → 5 random AAPL articles
      - GET /news?keyword=bullish&limit=3  → 3 random bullish articles
    """
    logger.info(f"GET /news - Request: keyword='{keyword}', limit={limit}")
    
    items = news_orchestrator.get_random_news(keyword=keyword, limit=limit)
    total = news_orchestrator.count_news(keyword=keyword)
    
    response = {
        "items": items,
        "total_available": total,
        "returned": len(items)
    }
    
    logger.info(
        f"GET /news - Response: returned {len(items)} items, "
        f"total_available={total}, "
        f"keyword_filter={'YES' if keyword else 'NO'}"
    )
    
    if items:
        # Log first item preview for debugging
        first_item = items[0]
        logger.debug(
            f"GET /news - First item: id={first_item['id'][:12]}..., "
            f"ticker={first_item['ticker']}, "
            f"heading='{first_item['heading'][:50]}...'"
        )
    
    return response


@router.post("/fetch")
async def fetch_news(body: FetchNewsRequest = FetchNewsRequest()):
    """
    Generate fresh simulated news articles for the given tickers (defaults to
    the full universe), optionally guided by *keywords* / themes.  A natural-
    language translatedView is extracted for each article and cached in
    news.json.  Existing items (by content hash) are skipped.

    Request body (all optional)::

        {
          "tickers":          ["AAPL", "JPM"],  // default: all universe assets
          "keywords":         ["rate hike", "earnings beat"],
          "limit_per_ticker": 5
        }

    Response shape::

        { "count": int, "items": [...] }
    """
    try:
        items = news_orchestrator.fetch_and_parse(
            tickers=body.tickers,
            limit_per_ticker=body.limit_per_ticker,
            keywords=body.keywords,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"News generation failed: {exc}")
    return {"count": len(items), "items": items}


@router.post("/{item_id}/add-view", status_code=204)
async def add_view(item_id: str):
    """
    Send the stored ``translatedView`` for *item_id* through the
    bl_llm_parser pipeline and append the resulting views to current.json.

    Returns 204 No Content on success.
    Returns 404 if no item with *item_id* exists.
    Returns 500 if the BL parser fails.
    """
    try:
        news_orchestrator.add_view_to_recipe(item_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"View parsing failed: {exc}")

"""
News Router

Exposes three endpoints for the Analyst Suggestions feature:
  GET  /news              — return cached news items from news.json
  POST /news/fetch        — fetch fresh articles and generate translatedViews
  POST /news/{id}/add-view — parse translatedView and append to current.json
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.orchestrators import news_orchestrator

router = APIRouter(prefix="/news", tags=["news"])


class FetchNewsRequest(BaseModel):
    tickers: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    limit_per_ticker: int = 5


@router.get("")
async def get_news():
    """
    Return all cached news items from news.json.

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
          ]
        }
    """
    items = news_orchestrator.load_news()
    return {"items": items}


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

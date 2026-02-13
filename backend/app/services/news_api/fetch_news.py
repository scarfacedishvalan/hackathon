NEWS_API_KEY = "17de61727fb84d01b208a2a5d100194e"

# pip install requests pandas

import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd

BASE_URL = "https://newsapi.org/v2/everything"


def fetch_news_for_stock(
    ticker: str,
    limit: int = 5,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    sort_by: str = "publishedAt"
) -> List[Dict]:
    """
    Fetch recent news articles related to a stock ticker.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')
        limit: Maximum number of articles to fetch (max 100 per request)
        from_date: Start date in YYYY-MM-DD format (default: 30 days ago)
        to_date: End date in YYYY-MM-DD format (default: today)
        sort_by: Sort order - 'publishedAt', 'relevancy', or 'popularity'
    
    Returns:
        List of article dictionaries with title, source, url, description, published_at, author, content
    """
    # Default date range: last 30 days
    if to_date is None:
        to_date = datetime.now().strftime("%Y-%m-%d")
    if from_date is None:
        from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    query = f"{ticker} OR {ticker} stock OR {ticker} analyst OR {ticker} earnings OR {ticker} outlook"

    params = {
        "q": query,
        "language": "en",
        "sortBy": sort_by,
        "pageSize": min(limit, 100),  # API max is 100 per request
        "from": from_date,
        "to": to_date,
        "apiKey": NEWS_API_KEY,
    }

    response = requests.get(BASE_URL, params=params)
    response.raise_for_status()

    data = response.json()

    articles = []
    for article in data.get("articles", []):
        articles.append({
            "title": article.get("title", ""),
            "source": article.get("source", {}).get("name", ""),
            "url": article.get("url", ""),
            "description": article.get("description", ""),
            "published_at": article.get("publishedAt", ""),
            "author": article.get("author", ""),
            "content": article.get("content", "")
        })

    return articles


def fetch_news_for_multiple_stocks(
    tickers: List[str],
    limit_per_stock: int = 10,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> Dict[str, List[Dict]]:
    """
    Fetch news for multiple stock tickers.
    
    Args:
        tickers: List of stock ticker symbols
        limit_per_stock: Maximum articles per ticker
        from_date: Start date in YYYY-MM-DD format
        to_date: End date in YYYY-MM-DD format
    
    Returns:
        Dictionary mapping ticker -> list of articles
    """
    results = {}
    for ticker in tickers:
        print(f"Fetching news for {ticker}...")
        try:
            articles = fetch_news_for_stock(ticker, limit_per_stock, from_date, to_date)
            results[ticker] = articles
            print(f"  ✓ Found {len(articles)} articles")
        except Exception as e:
            print(f"  ✗ Error fetching news for {ticker}: {e}")
            results[ticker] = []
    return results


def news_to_dataframe(news_dict: Dict[str, List[Dict]]) -> pd.DataFrame:
    """
    Convert news dictionary to a pandas DataFrame for analysis.
    
    Args:
        news_dict: Dictionary from fetch_news_for_multiple_stocks
    
    Returns:
        DataFrame with columns: ticker, title, source, url, description, published_at, author, content
    """
    rows = []
    for ticker, articles in news_dict.items():
        for article in articles:
            row = {"ticker": ticker}
            row.update(article)
            rows.append(row)
    
    df = pd.DataFrame(rows)
    if not df.empty and "published_at" in df.columns:
        df["published_at"] = pd.to_datetime(df["published_at"])
        df = df.sort_values("published_at", ascending=False)
    
    return df


def fetch_comprehensive_news_dump(
    tickers: List[str],
    days_back: int = 30,
    articles_per_ticker: int = 50
) -> pd.DataFrame:
    """
    Fetch a comprehensive dump of news articles for multiple stocks.
    
    Args:
        tickers: List of stock ticker symbols
        days_back: Number of days to look back (default: 30)
        articles_per_ticker: Number of articles per ticker (default: 50, max: 100)
    
    Returns:
        DataFrame with all articles sorted by date
    """
    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    print(f"Fetching news from {from_date} to {to_date}")
    print(f"Tickers: {', '.join(tickers)}")
    print(f"Articles per ticker: {articles_per_ticker}")
    print("=" * 60)
    
    news_dict = fetch_news_for_multiple_stocks(
        tickers,
        limit_per_stock=articles_per_ticker,
        from_date=from_date,
        to_date=to_date
    )
    
    df = news_to_dataframe(news_dict)
    
    print("\n" + "=" * 60)
    print(f"Total articles fetched: {len(df)}")
    if not df.empty:
        print(f"Date range: {df['published_at'].min()} to {df['published_at'].max()}")
        print(f"\nArticles per ticker:")
        for ticker, count in df['ticker'].value_counts().items():
            print(f"  {ticker}: {count}")
    
    return df


if __name__ == "__main__":
    # Example 1: Simple fetch for one stock
    print("=" * 60)
    print("EXAMPLE 1: Fetch recent news for AAPL")
    print("=" * 60)
    articles = fetch_news_for_stock("AAPL", limit=5)
    for a in articles:
        print(f"\n{a['published_at']}: {a['title']}")
        print(f"Source: {a['source']}")
    
    # Example 2: Comprehensive dump for multiple stocks
    print("\n\n" + "=" * 60)
    print("EXAMPLE 2: Comprehensive news dump")
    print("=" * 60)
    stocks = ["AAPL", "GOOGL", "MSFT"]
    df = fetch_comprehensive_news_dump(stocks, days_back=7, articles_per_ticker=20)
    
    if not df.empty:
        print("\n--- Sample of fetched articles ---")
        print(df[['ticker', 'published_at', 'title', 'source']].head(10).to_string())
        
        # Save to CSV
        output_file = "news_dump.csv"
        df.to_csv(output_file, index=False)
        print(f"\n✓ Full news dump saved to: {output_file}")
        
        # Group by date
        print("\n--- Articles by Date ---")
        df['date'] = df['published_at'].dt.date
        date_counts = df.groupby('date').size().sort_index(ascending=False)
        print(date_counts.to_string())

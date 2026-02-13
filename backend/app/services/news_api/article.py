import requests
from bs4 import BeautifulSoup
from typing import Optional
import pandas as pd

def fetch_full_article(url: str, timeout: int = 10) -> Optional[str]:
    """
    Fetch full article text from a URL using BeautifulSoup.
    
    Args:
        url: Article URL
        timeout: Request timeout in seconds
    
    Returns:
        Extracted article text or None if failed
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            script.decompose()
        
        # Try to find article content
        article_selectors = [
            'article',
            '[class*="article"]',
            '[class*="content"]',
            '[class*="post"]',
            'main'
        ]
        
        article_text = None
        for selector in article_selectors:
            article_elem = soup.select_one(selector)
            if article_elem:
                article_text = article_elem.get_text(separator='\n', strip=True)
                if len(article_text) > 200:  # Ensure we got substantial content
                    break
        
        # Fallback to body if no article found
        if not article_text or len(article_text) < 200:
            article_text = soup.body.get_text(separator='\n', strip=True) if soup.body else ""
        
        # Clean up extra whitespace
        lines = [line.strip() for line in article_text.split('\n') if line.strip()]
        article_text = '\n'.join(lines)
        
        return article_text
    
    except Exception as e:
        print(f"Error fetching article from {url}: {e}")
        return None


# Option 3: Using newspaper4k (maintained fork, better than newspaper3k)
# Install: pip install newspaper4k
def fetch_full_article_newspaper4k(url: str) -> Optional[str]:
    """
    Fetch article using newspaper4k (maintained fork).
    Requires: pip install newspaper4k
    """
    try:
        from newspaper import Article
        article = Article(url)
        article.download()
        article.parse()
        return article.text
    except ImportError:
        print("newspaper4k not installed. Run: pip install newspaper4k")
        return None
    except Exception as e:
        print(f"Error with newspaper4k: {e}")
        return None


# Example usage
if __name__ == "__main__":
    url = "https://www.globenewswire.com/news-release/2026/02/11/3236163/0/en/4K-Display-Resolution-Market-Size-to-Grow-USD-1331-84-Billion-by-2035-Research-by-SNS-Insider.html"
    
    print("Fetching article with BeautifulSoup...")
    data_dump = r"C:\Python\hackathon\news_dump.csv"
    df_dump = pd.read_csv(data_dump)
    for index, row in df_dump.iterrows():
        print(f"\nArticle {index+1}: {row['title']}")
        text = fetch_full_article(row['url'])
        if text:
            print(f"Extracted {len(text)} characters")
            print(f"First 500 characters:\n{text[:500]}")
        else:
            print(f"Failed to fetch article for: {row['url']}")

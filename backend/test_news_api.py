"""
Quick test script for the new news API with fuzzy matching
"""
from app.orchestrators import news_orchestrator

print("=" * 60)
print("Testing News API with Fuzzy Matching")
print("=" * 60)

# Test 1: Get all news count
total = news_orchestrator.count_news()
print(f"\n1. Total news items: {total}")

# Test 2: Get 5 random news (no filter)
random_news = news_orchestrator.get_random_news(limit=5)
print(f"\n2. Random 5 news items:")
for item in random_news:
    print(f"   - [{item['ticker']}] {item['heading'][:60]}...")

# Test 3: Filter by keyword "AAPL"
aapl_count = news_orchestrator.count_news(keyword="AAPL")
aapl_news = news_orchestrator.get_random_news(keyword="AAPL", limit=3)
print(f"\n3. AAPL news (total: {aapl_count}, showing 3):")
for item in aapl_news:
    print(f"   - [{item['ticker']}] {item['heading'][:60]}...")

# Test 4: Filter by keyword "bullish" (fuzzy match)
bullish_count = news_orchestrator.count_news(keyword="bullish")
bullish_news = news_orchestrator.get_random_news(keyword="bullish", limit=3)
print(f"\n4. Bullish news (total: {bullish_count}, showing 3):")
for item in bullish_news:
    print(f"   - [{item['ticker']}] {item['heading'][:60]}...")

# Test 5: Filter by partial match "market"
market_count = news_orchestrator.count_news(keyword="market")
market_news = news_orchestrator.get_random_news(keyword="market", limit=5)
print(f"\n5. Market news (total: {market_count}, showing 5):")
for item in market_news:
    print(f"   - [{item['ticker']}] {item['heading'][:60]}...")

# Test 6: Typo test with fuzzy matching "Amazn" -> should match "AMZN"
fuzzy_count = news_orchestrator.count_news(keyword="Amazn")
fuzzy_news = news_orchestrator.get_random_news(keyword="Amazn", limit=2)
print(f"\n6. Fuzzy match 'Amazn' (total: {fuzzy_count}, showing 2):")
for item in fuzzy_news:
    print(f"   - [{item['ticker']}] {item['heading'][:60]}...")

print("\n" + "=" * 60)
print("All tests completed!")
print("=" * 60)

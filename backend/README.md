# Backend - Portfolio Backtesting & Black-Litterman API

FastAPI backend service for portfolio backtesting, Black-Litterman portfolio optimization, and natural language strategy interpretation.

## Overview

This backend provides a comprehensive portfolio management and analysis platform with multiple integrated services:
- **Portfolio Backtesting**: Test trading strategies using the Backtesting.py library
- **Black-Litterman Optimization**: Generate optimal portfolio allocations incorporating market views
- **Natural Language Processing**: Convert plain text investment strategies and news into structured data
- **Market Data Integration**: Fetch and process price data and financial news

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI application and routes
│   ├── api/
│   │   └── routers/                     # API route handlers
│   ├── db/
│   │   └── database.py                  # Database connections and models
│   ├── orchestrators/                   # Business logic orchestration
│   │   ├── view_orchestrator.py         # View parsing and recipe management
│   │   ├── bl_orchestrator.py           # Black-Litterman optimization runner
│   │   ├── bl_agent_orchestrator.py     # Agentic BL analysis with tool calling
│   │   ├── news_orchestrator.py         # News fetching and view conversion
│   │   ├── backtest_orchestrator.py     # Backtesting workflow coordination
│   │   └── admin_console_orchestrator.py # LLM usage and cost tracking
│   └── services/
│       ├── backtest/                    # Portfolio backtesting and optimization
│       │   ├── algo_optimiser.py        # Custom algorithms for bt library
│       │   └── portfolio_optimizer.py   # Mean-variance portfolio optimization
│       │
│       ├── bl_engine/                   # Black-Litterman portfolio allocation
│       │   ├── black_litterman.py       # Core BL model implementation
│       │   ├── view_translation.py      # Convert views to matrix format
│       │   ├── metrics.py               # Portfolio performance metrics
│       │   ├── chart_formatters.py      # Format data for UI charts
│       │   └── factor_views.py          # Factor-based view construction
│       │
│       ├── bl_llm_parser/               # LLM-based Black-Litterman parser
│       │   ├── parser.py                # Convert natural language to BL views
│       │   ├── output_schema.json       # JSON schema for BL output
│       │   ├── sector_metadata.json     # Sector and ticker metadata
│       │   └── prompts/                 # LLM prompt templates
│       │
│       ├── bl_stress/                   # Stress testing and sensitivity analysis
│       │   └── stress_tester.py         # Vary parameters and analyze impact
│       │
│       ├── news_api/                    # Financial news integration
│       │   ├── fetch_news.py            # Fetch and simulate news articles
│       │   ├── article.py               # Article data structures
│       │   └── view_parser.py           # Parse articles into BL views
│       │
│       ├── price_data/                  # Market data management
│       │   └── load_data.py             # Load price data and market metadata
│       │
│       ├── llm_client/                  # LLM integration utilities
│       │   ├── client.py                # Unified LLM client with cost tracking
│       │   └── cost_tracker.py          # Track token usage and costs
│       │
│       └── plots/                       # Generated backtest charts
│
├── data/
│   ├── news.json                        # News articles with BL-formatted views
│   ├── market_data.json                 # Historical prices and factor exposures
│   ├── bl_recipes/                      # Saved BL view recipes
│   └── agent_audits/                    # Agent execution logs and audits
│
├── requirements.txt
└── README.md
```

## Service Modules

### 🎯 **orchestrators/**
Business logic layer coordinating multiple services for complex workflows.
- **view_orchestrator.py**: Manages view parsing from natural language and recipe file operations (load, save, append views)
- **bl_orchestrator.py**: Coordinates Black-Litterman model execution with price data loading and result formatting
- **bl_agent_orchestrator.py**: Agentic workflow with LLM-powered tool calling for stress testing, sensitivity analysis, and scenario exploration
- **news_orchestrator.py**: Fetches news articles, converts them to BL-formatted views, and integrates with the view pipeline
- **backtest_orchestrator.py**: Coordinates backtesting workflow from recipe creation to execution and result generation
- **admin_console_orchestrator.py**: Aggregates LLM usage statistics, token costs, and agent execution audits from tracking databases

### 🔬 **backtest/**
Portfolio backtesting and optimization using the bt library and custom algorithms.
- **algo_optimiser.py**: Custom algorithm implementations for the bt backtesting framework, including mean-variance optimization with multiple lookback periods
- **portfolio_optimizer.py**: Implements portfolio optimization methods including mean-variance, minimum variance, and risk parity using scipy optimization

### 📊 **bl_engine/**
Black-Litterman portfolio allocation engine using PyPortfolioOpt.
- **black_litterman.py**: Core implementation of the Black-Litterman model for combining market equilibrium with investor views
- **view_translation.py**: Converts human-readable investment views into the mathematical matrices (P, Q, Ω) required by the BL model
- **metrics.py**: Calculates portfolio performance metrics including returns, volatility, Sharpe ratio, and risk contributions
- **chart_formatters.py**: Formats portfolio allocation and performance data into UI-ready structures for visualization
- **factor_views.py**: Constructs factor-based views (e.g., sector rotation, style tilts) for the BL model

### 🤖 **bl_llm_parser/**
LLM-based parser for converting natural language investment views into structured Black-Litterman format.
- **parser.py**: Orchestrates LLM calls to extract structured investment views from natural language text using prompt engineering
- **output_schema.json**: Defines the JSON schema for validated Black-Litterman output (tickers, view types, confidence levels)
- **sector_metadata.json**: Metadata mapping for stock tickers to sectors/industries for view validation

### 🧪 **bl_stress/**
Stress testing and sensitivity analysis for Black-Litterman portfolios.
- **stress_tester.py**: Systematically varies confidence levels, factor shocks, and view parameters to analyze portfolio sensitivity

### 📰 **news_api/**
Financial news integration with BL-formatted view generation.
- **fetch_news.py**: Fetches and simulates news articles for stock tickers with market sentiment
- **article.py**: Data structures representing news articles with metadata (title, source, publication date, ticker)
- **view_parser.py**: Converts news article text into structured Black-Litterman views with confidence levels and expected returns

### 💹 **price_data/**
Market data management and historical price loading.
- **load_data.py**: Loads historical price data, market caps, and factor exposure matrices from market_data.json

### 🤖 **llm_client/**
Centralized LLM integration with cost tracking.
- **client.py**: Unified client for OpenAI API calls with automatic token counting and cost calculation
- **cost_tracker.py**: Persistent tracking of LLM usage per service/operation with SQLite storage

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
```

2. Activate the virtual environment:
```bash
# Windows
.\venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Server

Development mode with auto-reload:
```bash
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

### `GET /`
Health check endpoint
- Returns: `{"message": "Portfolio Backtesting API", "status": "running"}`

### `GET /health`
Health status
- Returns: `{"status": "healthy"}`

### `POST /api/bl/parse-views`
Parse natural language investment views into structured Black-Litterman format

**Request Body:**
```json
{
  "investor_text": "I believe tech stocks will outperform by 5% this year. Apple should beat Microsoft by 2%.",
  "assets": ["AAPL", "MSFT", "GOOGL", "AMZN"],
  "factors": ["Growth", "Rates", "Momentum", "Value"]
}
```

**Response:**
```json
{
  "bottom_up_views": [
    {
      "type": "relative",
      "asset": "AAPL",
      "expected_return": 0.02,
      "confidence": 0.7,
      "label": "Apple expected to outperform Microsoft by 2%"
    }
  ],
  "top_down_views": {
    "factor_shocks": [
      {
        "factor": "Growth",
        "shock": 0.05,
        "confidence": 0.8,
        "label": "Tech sector expected to grow by 5%"
      }
    ]
  }
}
```

### `GET /api/news?keyword={keyword}&limit={limit}`
Fetch random news articles with BL-formatted views, optionally filtered by keyword

**Query Parameters:**
- `keyword` (optional): Fuzzy search keyword for filtering (searches heading, translatedView, ticker)
- `limit` (optional): Maximum number of items to return (default: 5)

**Response:**
```json
{
  "items": [
    {
      "id": "abc123",
      "heading": "TSLA Analysts Bullish on Growth",
      "translatedView": "Medium confidence: TSLA expected absolute return of +7% (bullish view).",
      "ticker": "TSLA",
      "source": "Bloomberg",
      "link": "https://...",
      "fetched_at": "2026-03-15T10:00:00Z"
    }
  ],
  "total_available": 10,
  "returned": 5
}
```

### `POST /api/news/{item_id}/add-to-recipe`
Add a news article's translatedView to the current BL recipe by parsing it through the LLM

**Response:**
```json
{
  "bottom_up_views": [...],
  "top_down_views": {...}
}
```

## Development Notes

- CORS is configured to allow requests from the frontend (localhost:5173 and production deployment)
- News articles stored in `data/news.json` with BL-formatted `translatedView` fields
- Market data (prices, caps, factor exposures) loaded from `data/market_data.json`
- BL recipes saved in `data/bl_recipes/` directory, `current.json` is the active recipe
- LLM integration requires OpenAI API key in environment variables
- LLM usage and costs tracked in SQLite databases (`llm_usage.db`, `agent_costs.db`)
- Agent execution audits saved to `data/agent_audits/` as JSON files

## Testing

Run orchestrator examples:
```bash
# Test news API (random selection, keyword search, fuzzy matching)
python run_orchestrators.py --example news

# Test news → active views integration (LLM parsing)
python run_orchestrators.py --example news_views

# Test BL model execution
python run_orchestrators.py --example bl

# Test agentic BL orchestrator
python run_orchestrators.py --example agent

# Test admin console (LLM costs and usage)
python run_orchestrators.py --example admin

# Run all tests
python run_orchestrators.py --example all
```

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
│       │   ├── factor_views.py          # Factor-based view construction
│       │   └── bl_standalone.py         # Standalone BL runner
│       │
│       ├── bl_llm_parser/               # LLM-based Black-Litterman parser
│       │   ├── parser.py                # Convert natural language to BL views
│       │   ├── output_schema.json       # JSON schema for BL output
│       │   ├── sector_metadata.json     # Sector and ticker metadata
│       │   └── prompts/                 # LLM prompt templates
│       │
│       ├── news_api/                    # Financial news integration
│       │   ├── fetch_news.py            # Fetch news from NewsAPI
│       │   ├── article.py               # Article data structures
│       │   ├── view_parser.py           # Parse articles into BL views
│       │   └── view_schema.py           # Pydantic schemas for views
│       │
│       ├── price_data/                  # Market data management
│       │   ├── data_fetch.py            # Price data fetching and processing
│       │   └── load_csv_to_db.py        # Load CSV data to SQLite
│       │
│       ├── recipe_interpreter/          # Natural language strategy parser
│       │   ├── llm_parser.py            # Parse text to JSON recipe
│       │   ├── backtesting_from_json.py # Execute backtest from recipe
│       │   ├── semantic_schema_backtesting.py  # Recipe schema definitions
│       │   └── get_bt_classes.py        # Backtesting.py class utilities
│       │
│       └── plots/                       # Generated backtest charts
│
├── requirements.txt
├── failed_requirements.txt
└── README.md
```

## Service Modules

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

### 📰 **news_api/**
Financial news integration and analysis using NewsAPI.
- **fetch_news.py**: Fetches recent news articles for specified stock tickers from NewsAPI
- **article.py**: Data structures representing news articles with metadata (title, source, publication date, content)
- **view_parser.py**: LLM-based extraction of structured Black-Litterman views from news article text
- **view_schema.py**: Pydantic models for validating extracted investment views from news

### 💹 **price_data/**
Market data management and historical price fetching.
- **data_fetch.py**: Core module for fetching historical price data from multiple sources (Excel, SQLite, synthetic data)
- **load_csv_to_db.py**: Utility to load CSV price data into SQLite database for efficient querying

### 📝 **recipe_interpreter/**
Natural language strategy interpretation and execution.
- **llm_parser.py**: Converts plain text trading strategy descriptions into structured JSON recipes using LLM
- **backtesting_from_json.py**: Executes backtests based on JSON recipe specifications, supporting various strategy types
- **semantic_schema_backtesting.py**: Defines the semantic schema for backtest recipes (strategy parameters, indicators, rules)
- **get_bt_classes.py**: Utility functions for dynamically accessing Backtesting.py classes and methods

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

### `POST /api/generate-recipe`
Generate a portfolio recipe and backtest results

**Request Body:**
```json
{
  "stocks": ["AAPL", "MSFT", "GOOGL"],
  "strategy_instruction": "Run the strategy WeighMeanVar with lookbacks 3y, 2y and 1y with yearly rebalance"
}
```

**Response:**
```json
{
  "recipe": {
    "strategy": "WeighMeanVar",
    "lookbacks": ["3y", "2y", "1y"],
    "rebalance": "yearly",
    "stocks": ["AAPL", "MSFT", "GOOGL"],
    "start_date": "2020-01-01",
    "end_date": "2024-12-31",
    "initial_capital": 100000,
    "risk_model": {
      "covariance_method": "sample",
      "expected_returns": "mean_historical_return"
    }
  },
  "equity_curve": [...],
  "summary_stats": {
    "cagr": "18.4%",
    "sharpe_ratio": "1.42",
    "max_drawdown": "-12.8%",
    "volatility": "15.2%"
  }
}
```

### `POST /api/parse-bl-views`
Parse natural language investment views into structured Black-Litterman format

**Request Body:**
```json
{
  "investor_text": "I believe tech stocks will outperform by 5% this year. Apple should beat Microsoft by 2%.",
  "assets": ["AAPL", "MSFT", "GOOGL", "AMZN"],
  "factors": ["Growth", "Rates", "Momentum", "Value"],
  "use_schema": true
}
```

**Note:** `assets` and `factors` are optional. If omitted, defaults to a predefined list of major stocks and common factors.

**Response:**
```json
{
  "bottom_up_views": [
    {
      "type": "relative",
      "assets": ["AAPL", "MSFT"],
      "weights": [1.0, -1.0],
      "expected_outperformance": 0.02,
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

## Development Notes

- CORS is configured to allow requests from the frontend (localhost:5173 and 127.0.0.1)
- Generated backtest charts are served from `/plots` endpoint
- LLM integration requires OpenAI API key in environment variables
- NewsAPI integration requires API key configured in `news_api/fetch_news.py`

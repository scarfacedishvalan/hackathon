# Backend - Portfolio Backtesting API

FastAPI backend service for portfolio backtesting and recipe generation.

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

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application and routes
│   └── services/
│       ├── __init__.py
│       └── recipe_generator.py  # Recipe generation logic (mock for now)
├── requirements.txt
└── README.md
```

## Development Notes

- The `recipe_generator.py` currently contains mock implementations
- Replace the mock functions with actual backtesting logic later
- CORS is configured to allow requests from the frontend (localhost:5173)

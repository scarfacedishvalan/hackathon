# Black-Litterman Portfolio Allocation Engine

A clean backend implementation of a Black-Litterman portfolio allocation engine using PyPortfolioOpt.

## Overview

This module provides deterministic functions for portfolio allocation using the Black-Litterman model, designed to be called from APIs or UI dashboards.

## Module Structure

```
app/services/bl_engine/
├── __init__.py              # Package exports
├── black_litterman.py       # Core BL engine
├── view_translation.py      # View to matrix conversion
├── metrics.py               # Portfolio metrics calculation
├── chart_formatters.py      # UI-ready data formatters
└── example_run.py           # Complete example
```

## Dependencies

- Python 3.12+
- PyPortfolioOpt
- pandas
- numpy

## Usage

### Basic Example

```python
from app.services.bl_engine import (
    run_black_litterman,
    build_P_matrix,
    build_Q_vector,
    build_omega,
    compute_portfolio_metrics,
    allocation_to_chart
)
import pandas as pd
import numpy as np

# Prepare price data
price_df = pd.DataFrame({
    "AAPL": [...],  # Historical prices
    "MSFT": [...],
    "GOOGL": [...]
})

# Define market capitalizations
market_caps = {
    "AAPL": 3000.0,
    "MSFT": 2800.0,
    "GOOGL": 1800.0
}

# Define views
views = [
    {
        "type": "relative",
        "asset_long": "AAPL",
        "asset_short": "MSFT",
        "value": 0.05,      # 5% outperformance
        "confidence": 0.7    # 70% confidence
    }
]

# Build matrices
assets = list(price_df.columns)
P = build_P_matrix(views, assets)
Q = build_Q_vector(views)
omega = build_omega(views)

# Run Black-Litterman
result = run_black_litterman(
    price_df=price_df,
    market_caps=market_caps,
    P=P,
    Q=Q,
    omega=omega
)

# Extract results
weights = result["weights"]
posterior_returns = result["posterior_returns"]

# Compute metrics
from pypfopt import risk_models
cov_matrix = risk_models.sample_cov(price_df)
metrics = compute_portfolio_metrics(weights, posterior_returns, cov_matrix.values)

print(f"Expected Return: {metrics['expected_return']:.2%}")
print(f"Volatility: {metrics['volatility']:.2%}")
print(f"Sharpe Ratio: {metrics['sharpe']:.2f}")

# Format for charts
chart_data = allocation_to_chart(weights)
```

## View Types

### Relative View
Expresses that one asset will outperform another:
```python
{
    "type": "relative",
    "asset_long": "AAPL",    # Asset expected to outperform
    "asset_short": "MSFT",   # Asset expected to underperform
    "value": 0.05,            # Expected outperformance (5%)
    "confidence": 0.7         # Confidence level (0-1)
}
```

### Absolute View
Expresses the expected return for a single asset:
```python
{
    "type": "absolute",
    "asset_long": "GOOGL",   # Asset name
    "asset_short": None,      # Not used for absolute views
    "value": 0.10,            # Expected return (10%)
    "confidence": 0.8         # Confidence level (0-1)
}
```

## API Reference

### `run_black_litterman(price_df, market_caps, P, Q, omega)`
Run the complete Black-Litterman model.

**Returns:**
```python
{
    "weights": {
        "AAPL": 0.5,
        "MSFT": 0.3,
        "GOOGL": 0.2
    },
    "posterior_returns": {
        "AAPL": 0.08,
        "MSFT": 0.06,
        "GOOGL": 0.07
    }
}
```

### `build_P_matrix(views, assets)`
Build the pick matrix from structured views.

**Returns:** numpy.ndarray of shape (num_views, num_assets)

### `build_Q_vector(views)`
Build the expected returns vector from views.

**Returns:** numpy.ndarray of shape (num_views,)

### `build_omega(views)`
Build the uncertainty matrix from view confidences.

**Returns:** numpy.ndarray of shape (num_views, num_views)

### `compute_portfolio_metrics(weights, mu, cov)`
Compute portfolio performance metrics.

**Returns:**
```python
{
    "expected_return": 0.08,
    "volatility": 0.15,
    "sharpe": 0.53
}
```

### `allocation_to_chart(weights)`
Format weights for chart display.

**Returns:** List of dicts sorted by weight descending

### `allocation_comparison(baseline, stressed)`
Compare two allocations side-by-side.

**Returns:** List of dicts with delta calculations

## Running the Example

```bash
cd backend/app/services/bl_engine
python example_run.py
```

## Running Tests

```bash
cd backend
python test_bl_engine.py
```

## Features

- ✅ Type hints on all functions
- ✅ Comprehensive docstrings
- ✅ Deterministic behavior
- ✅ No global state
- ✅ Weights always sum to 1
- ✅ Full unit test coverage
- ✅ Security validated (CodeQL)

## Notes

- The engine uses a risk aversion parameter of 1.0 for market-implied returns
- Uncertainty scaling factor is set to 0.01 (adjustable via `UNCERTAINTY_SCALE` constant)
- All portfolio weights are non-negative (long-only)

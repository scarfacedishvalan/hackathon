# API Endpoint Reference — BL Main

**Backend:** `http://localhost:8000`  
**Frontend proxy:** Vite rewrites `/api/*` → backend root, so use `/api/<path>` in `apiClient` calls.  
**Source:** `backend/app/api/routers/` + `backend/app/main.py`

---

## Views  (`/views`)

| Method | Path | Status | What it does |
|--------|------|--------|--------------|
| `GET` | `/views/current` | 200 | Returns active bottom-up and top-down views from `current.json` |
| `POST` | `/views/parse` | 200 | Parses a natural-language string into a view and appends it to `current.json` |
| `GET` | `/views/model_parameters` | 200 | Returns the `model_parameters` block from `current.json` |
| `PUT` | `/views/model_parameters` | 200 | Merges `tau`, `risk_aversion`, `risk_free_rate` into `current.json`; returns saved params |
| `GET` | `/views/constraints` | 200 | Returns `long_only` and `weight_bounds` from `current.json` |
| `PUT` | `/views/constraints` | 200 | Overwrites constraints in `current.json`; validates bounds |
| `POST` | `/views/thesis` | 201 | Saves a named copy of `current.json`; auto-generates description if omitted |
| `GET` | `/views/universe` | 200 | Returns `universe.assets` list from `current.json` |
| `PUT` | `/views/universe` | 200 | Overwrites `universe.assets` in `current.json` |
| `PATCH` | `/views/bottom_up/{index}` | 200 | Updates `value` / `confidence` of a single bottom-up view; returns refreshed views |
| `PATCH` | `/views/top_down/{index}` | 200 | Updates `shock` / `confidence` of a single factor shock; returns refreshed views |
| `DELETE` | `/views/bottom_up/{index}` | 204 | Removes a bottom-up view by index |
| `DELETE` | `/views/top_down/{index}` | 204 | Removes a factor shock by index |

### `GET /views/current` response
```json
{
  "bottom_up": [
    { "id": "bu-0", "type": "absolute",  "asset": "AAPL", "value": 0.05, "confidence": 0.6, "label": "..." },
    { "id": "bu-1", "type": "relative", "asset_long": "AAPL", "asset_short": "GOOGL", "value": 0.03, "confidence": 0.7, "label": "..." }
  ],
  "top_down": [
    { "id": "td-0", "factor": "Rates", "shock": 0.02, "confidence": 0.7, "label": "..." }
  ]
}
```

### `POST /views/parse` request / response
```json
// request
{ "text": "AAPL will moderately outperform MSFT" }

// response — list of normalised view dicts appended to current.json
{ "view": [ { "type": "relative", "asset_long": "AAPL", "asset_short": "MSFT", "alpha": 0.03, "confidence": 0.6, "label": "..." } ] }
```

### `PUT /views/model_parameters` request
```json
{ "tau": 0.05, "risk_aversion": 2.5, "risk_free_rate": 0.03 }
```

### `PUT /views/constraints` request / response
```json
// request
{ "long_only": true, "weight_bounds": [0.0, 0.25] }

// response
{ "long_only": true, "weight_bounds": [0.0, 0.25] }
```

### `POST /views/thesis` request / response
```json
// request  (description is optional; a default is generated if omitted)
{ "name": "Q2 Bullish Tech", "description": "Optional free-text note" }

// response
{ "name": "q2_bullish_tech" }
```
When `description` is omitted the saved recipe receives a description like:
`"2 bottom-up views, 1 factor shock — saved May 05, 2026"`

### `PATCH /views/bottom_up/{index}` request
```json
{ "value": 0.07, "confidence": 0.8 }
```

### `PATCH /views/top_down/{index}` request
```json
{ "shock": -0.03, "confidence": 0.6 }
```

---

## Black-Litterman  (`/bl`)

| Method | Path | Status | What it does |
|--------|------|--------|--------------|
| `POST` | `/bl/run` | 200 | Runs the full BL pipeline from `current.json` and returns chart data |
| `GET` | `/bl/price-history` | 200 | Returns full historical daily close prices for all universe assets |

### `POST /bl/run` response
```json
{
  "efficientFrontier": {
    "curve": [{ "vol": 0.12, "ret": 0.08 }],
    "prior":     { "vol": 0.14, "ret": 0.07 },
    "posterior": { "vol": 0.13, "ret": 0.09 }
  },
  "allocation": [
    { "ticker": "AAPL", "priorWeight": 0.10, "blWeight": 0.13 }
  ],
  "topDownContribution": [
    { "sector": "Financial", "returnContribution": 0.02, "riskContribution": 0.01 }
  ],
  "portfolioStats": {
    "prior":     { "ret": 0.07, "vol": 0.14, "sharpe": 0.50, "var95": -0.09 },
    "posterior": { "ret": 0.09, "vol": 0.13, "sharpe": 0.69, "var95": -0.07 }
  },
  "calculationSteps": [{ "title": "Prior Returns", "latex": "\\Pi = ..." }],
  "weights":           { "AAPL": 0.13 },
  "posterior_returns": { "AAPL": 0.09 },
  "prior_returns":     { "AAPL": 0.07 },
  "n_bottom_up_views": 2,
  "n_top_down_views":  1
}
```

### `GET /bl/price-history` response
```json
{
  "dates":  ["2020-01-02", "2020-01-03"],
  "prices": { "AAPL": [300.0, 301.5], "MSFT": [170.0, 171.2] }
}
```

---

## News / Analyst Suggestions  (`/news`)

| Method | Path | Status | What it does |
|--------|------|--------|--------------|
| `GET` | `/news` | 200 | Returns random cached news items; supports `keyword` fuzzy filter and `limit` |
| `POST` | `/news/fetch` | 200 | Generates new articles via LLM and caches them in `news.json` |
| `POST` | `/news/{item_id}/add-view` | 204 | Parses the article's `translatedView` and appends resulting views to `current.json` |

### `GET /news` query params
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `keyword` | string | — | Fuzzy-match filter against heading, translatedView, and ticker (75% threshold) |
| `limit` | int 1-50 | 5 | Number of random items to return |

### `GET /news` response
```json
{
  "items": [
    {
      "id": "a3f1b2c4d5e6",
      "heading": "JPM Beats Q1 Estimates on Rising Net Interest Income",
      "translatedView": "JPM is expected to moderately outperform due to positive Financial factor.",
      "link": "https://simulation.example.com/jpm/...",
      "source": "Reuters Mock",
      "ticker": "JPM",
      "fetched_at": "2026-03-10T09:00:00+00:00"
    }
  ],
  "total_available": 42,
  "returned": 5
}
```

### `POST /news/fetch` request / response
```json
// request (all fields optional)
{
  "tickers": ["AAPL", "JPM"],
  "keywords": ["rate hike", "earnings beat"],
  "limit_per_ticker": 5
}

// response
{ "count": 10, "items": [ { } ] }
```

---

## Backtesting  (`/backtest`)

| Method | Path | Status | What it does |
|--------|------|--------|--------------|
| `POST` | `/backtest/parse` | 200 | Converts natural-language description into a validated backtest recipe JSON |
| `POST` | `/backtest/run` | 200 | Executes a backtest recipe and returns metrics + equity curve |
| `GET` | `/backtest/theses` | 200 | Lists saved BL thesis names available for portfolio backtesting |
| `POST` | `/backtest/run-portfolio` | 200 | Runs a thesis-driven equal-weight portfolio backtest |

### `POST /backtest/parse` request / response
```json
// request
{ "text": "Backtest SmaCross on AAPL daily from 2021-01-01" }

// response
{
  "strategy_name": "SmaCross",
  "timeframe": "daily",
  "data": { "symbol": "AAPL", "start": "2021-01-01" },
  "backtest": { "cash": 10000 },
  "strategy_params": { "fast": 20, "slow": 50 },
  "rules": { "entry": "...", "exit": "..." },
  "risk": {},
  "optimize": {}
}
```

### `POST /backtest/run` request / response
```json
// request
{ "recipe": { } }

// response
{
  "recipe":      { "strategy_name": "SmaCross" },
  "metrics":     { "returnPct": 12.4, "sharpeRatio": 1.1, "maxDrawdownPct": -8.2 },
  "equityCurve": [{ "date": "2021-01-04", "equity": 10120.0 }],
  "trades":      [{ "entryTime": "...", "exitTime": "...", "pnl": 120.0 }]
}
```

### `POST /backtest/run-portfolio` request
```json
{
  "thesis_name": "q2_bullish_tech",
  "strategy_name": "SmaCross",
  "strategy_params": { "fast": 10, "slow": 30 },
  "start": "2022-01-01",
  "end": "2023-12-31",
  "cash": 10000.0,
  "commission": 0.001
}
```

---

## Portfolios  (`/portfolios`)

| Method | Path | Status | What it does |
|--------|------|--------|--------------|
| `GET` | `/portfolios` | 200 | Lists all saved portfolios |
| `POST` | `/portfolios` | 201 | Creates a new portfolio; 409 if id already exists |
| `GET` | `/portfolios/{id}` | 200 | Returns a single portfolio |
| `DELETE` | `/portfolios/{id}` | 204 | Deletes a portfolio |

### Portfolio shape
```json
{
  "id": "uuid-or-custom-id",
  "name": "My Portfolio",
  "holdings": [
    { "ticker": "AAPL", "weight": 0.40 },
    { "ticker": "MSFT", "weight": 0.60 }
  ]
}
```

---

## Agent  (`/agent`)

| Method | Path | Status | What it does |
|--------|------|--------|--------------|
| `GET` | `/agent/recipes` | 200 | Lists available BL thesis names (stems of `data/bl_recipes/*.json`) |
| `POST` | `/agent/run` | 200 | Starts a background ReAct agent run; returns `audit_id` immediately |
| `GET` | `/agent/audits` | 200 | Lists past agent audit summaries from `agent_costs.db` |
| `GET` | `/agent/audits/{audit_id}` | 200 | Returns full audit record, or polling status if still running |

### `POST /agent/run` request / response
```json
// request
{
  "thesis_name": "q2_bullish_tech",
  "goal": "Stress-test all views and find allocation for a conservative investor with max 15% per position.",
  "max_steps": 8
}

// response — immediate; poll audits/{audit_id} until done
{ "audit_id": "uuid", "status": "running" }
```

### `GET /agent/audits/{audit_id}` response variants
```json
// still running
{ "status": "running", "audit_id": "uuid" }

// failed — full traceback included for debugging
{ "status": "error", "audit_id": "uuid", "detail": "FileNotFoundError: ...", "traceback": "Traceback (most recent call last):\n  ..." }

// completed
{
  "status": "done",
  "audit_id": "uuid",
  "thesis_name": "q2_bullish_tech",
  "goal": "...",
  "run_timestamp": "2026-05-05T10:00:00",
  "model": "gpt-4o",
  "base_result_summary": { "weights": {}, "sharpe": 0.0 },
  "steps": [ { "step": 0, "tool": "get_recipe_summary", "args": {}, "result": {} } ],
  "diagnostics": { "view_importance": [], "view_fragility": [], "factor_transmission": [], "allocation_envelope": [] },
  "synthesis": { "narrative": "...", "recommended_weights": { "AAPL": 0.15 }, "risk_flags": [], "done": true },
  "run_errors": [ { "step": 2, "tool": "run_bl_scenario", "error": "..." } ],
  "final_weights": { "AAPL": 0.15 },
  "weight_delta_vs_base": { "AAPL": 0.03 },
  "cost_breakdown": { "total_cost_usd": 0.042, "total_tokens": 12000 },
  "step_costs": []
}
```

### `GET /agent/audits` query params
| Param | Default | Description |
|-------|---------|-------------|
| `limit` | 50 | Max number of audit summaries to return |

---

## Admin / Cost Console  (`/admin`)

| Method | Path | Status | What it does |
|--------|------|--------|--------------|
| `GET` | `/admin/console` | 200 | Full payload: LLM usage + agent usage + grand total, filtered by active tare |
| `GET` | `/admin/llm-usage` | 200 | LLM-only usage data, filtered by active tare |
| `GET` | `/admin/agent-usage` | 200 | Agent-only cost data, filtered by active tare |
| `POST` | `/admin/tare` | 200 | Sets a new tare point; all dashboard queries count only data after this timestamp |
| `POST` | `/admin/tare/reset` | 200 | Removes the active tare (shows all history); tare log is preserved |
| `GET` | `/admin/tare/history` | 200 | Returns the tare event log, most recent first |
| `GET` | `/admin/tare/active` | 200 | Returns the currently active tare record, or `null` |

### `GET /admin/console` query params
| Param | Default | Range | Description |
|-------|---------|-------|-------------|
| `llm_recent_limit` | 50 | 1-500 | Max recent LLM calls to return |
| `agent_recent_limit` | 100 | 1-500 | Max recent agent steps to return |

### `POST /admin/tare` request
```json
{ "note": "Before hackathon demo" }
```

---

## Frontend service files

| Service | File |
|---------|------|
| Views + BL run | `blMainService.ts` → `blService`, `viewService` |
| Portfolios | `blMainService.ts` → `portfolioService` |
| News | `blMainService.ts` → `newsService` |
| Agent | `features/agent/services/agentService.ts` |
| Base HTTP client | `src/services/apiClient.ts` |
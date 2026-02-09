# API ↔ Frontend Endpoint Map (Layman-Friendly)

This document explains **which backend URLs exist**, **which frontend UI actions call them**, and **what data is sent/returned**.

---

## Quick mental model

- The **frontend (React/Vite)** runs in your browser (usually `http://localhost:5173`).
- The **backend (FastAPI)** runs as a local web server (usually `http://localhost:8000`).
- When you click **Run Backtest** in the UI, the browser makes an HTTP request to FastAPI.
- The backend responds with **JSON** (data for the UI) and also saves an **HTML report** file that the UI can open.

---

## Main mapping table (what users do → what gets called)

| User action in UI | Frontend file/module | Backend endpoint called | Backend file/module | What it does (simple) |
|---|---|---|---|---|
| Select stocks in the dropdown | `frontend/src/app/components/StockSelector.tsx` | *(no call)* | *(n/a)* | Updates local UI state (which tickers are selected). |
| Type into “Strategy Instruction” textarea | `frontend/src/app/App.tsx` | *(no call)* | *(n/a)* | Updates local UI state (instruction text). |
| Click an example “copy” button | `frontend/src/app/App.tsx` | *(no call)* | *(n/a)* | Copies example text to clipboard and fills the textarea. |
| Click **Run Backtest** | `frontend/src/app/App.tsx` | `POST /api/generate-recipe` | `backend/app/main.py` | Runs a backtest from a “recipe”, returns JSON for the chart/cards, and saves an HTML plot file. |
| Click **Open HTML plot** link | `frontend/src/app/App.tsx` | `GET /plots/<file>.html` | `backend/app/main.py` (static mount) | Downloads/opens the generated HTML report in a new tab. |

---

## Backend endpoints (what exists)

### 1) `GET /`

| Item | Details |
|---|---|
| Backend code location | `backend/app/main.py` (`read_root`) |
| Frontend usage | Not directly used (but handy to confirm the server is alive). |
| Response format | JSON object |
| Example response | `{ "message": "Portfolio Backtesting API", "status": "running" }` |

---

### 2) `GET /health`

| Item | Details |
|---|---|
| Backend code location | `backend/app/main.py` (`health_check`) |
| Frontend usage | Not directly used (but useful for monitoring / scripts). |
| Response format | JSON object |
| Example response | `{ "status": "healthy" }` |

---

### 3) `POST /api/generate-recipe`

This is the **main** endpoint used by the UI.

| Item | Details |
|---|---|
| Backend code location | `backend/app/main.py` (`generate_recipe_endpoint`) |
| Frontend caller | `frontend/src/app/App.tsx` (`handleGenerateRecipe`) |
| Request format | JSON body |
| Response format | JSON body |

#### What the frontend sends (request JSON)

| Field | Type | Example | Meaning |
|---|---|---|---|
| `stocks` | `string[]` | `["SPY", "AAPL"]` | Selected tickers. **Note:** backend currently uses only the **first** one (`stocks[0]`). |
| `strategy_instruction` | `string` | `"Run SmaCross on SPY ..."` | Optional natural-language instruction. If blank, backend uses a built-in example recipe. |

#### What the backend returns (response JSON)

| Field | Type | What it’s used for |
|---|---|---|
| `recipe` | `object` | Shown in the “Backtesting recipe” collapsible JSON section. |
| `equity_curve` | `array<object>` | Used to build the line chart. Backend typically returns rows with keys like `Date` and `Equity`. |
| `summary_stats` | `object` | Used to fill the 4 metric cards (CAGR, Sharpe, Max Drawdown, Volatility). Keys come from Backtesting.py stats and may include `%` in the key name. |
| `plot_url` | `string` (or `null`) | Link to the generated HTML report (served from `/plots/...`). |

#### How the equity curve gets into the chart (important)

- Backend (`backend/app/main.py`) extracts `_equity_curve` from Backtesting.py results and returns it as `equity_curve`.
- Frontend (`frontend/src/app/App.tsx`) **normalizes** each row into `{ date, value }`:
  - `date` is taken from `row.date` or `row.Date` (etc.)
  - `value` is taken from `row.value` or `row.Equity` (etc.)

This is why the chart is configured as:
- `XAxis dataKey="date"`
- `Line dataKey="value"`

#### Where the recipe comes from

The backend chooses a recipe like this:

1) If `strategy_instruction` is blank → load the example recipe JSON from:
   - `backend/app/services/recipe_interpreter/prompts/backtesting_example_expected_output.json`

2) If `strategy_instruction` is not blank → backend may try to parse it using the optional LLM parser:
   - `backend/app/services/recipe_interpreter/llm_parser.py`

If the parser fails, it falls back to the example recipe.

#### What strategies are supported

The Backtesting.py runner supports only a small set of strategies. If an instruction/recipe requests an unsupported strategy, the backend returns **HTTP 400** with a clear message.

Supported (as of now):
- `SmaCross`
- `EmaCross`
- `RsiReversion`
- `BuyAndHold`

Implementation is in:
- `backend/app/services/recipe_interpreter/backtesting_from_json.py`

---

### 4) `GET /plots/<file>.html`

This endpoint serves the **HTML report file** created by Backtesting.py.

| Item | Details |
|---|---|
| Backend code location | `backend/app/main.py` (`app.mount("/plots", StaticFiles(...))`) |
| Frontend usage | The “Open HTML plot” link opens it in a new browser tab. |
| Response format | HTML (`text/html`) |
| Where files are stored on disk | `backend/app/services/plots/` |

#### What’s actually being “passed” here

The HTML plot is **not returned inside the JSON**.

Instead:
1) Backend runs the backtest.
2) Backtesting.py writes an HTML file into `backend/app/services/plots/`.
3) Backend returns `plot_url` (a string like `/plots/backtest_...html`).
4) Frontend displays that URL as a clickable link.

---

## CORS (why OPTIONS requests happen)

Browsers often send an **OPTIONS “preflight” request** before the real POST when you call the backend from a different origin (different port).

- Frontend origin: `http://localhost:5173`
- Backend origin: `http://localhost:8000`

CORS is configured in:
- `backend/app/main.py` (FastAPI `CORSMiddleware`)

The current setup allows local dev origins on both `localhost` and `127.0.0.1` for any port.

---

## Helpful test script

There is a lightweight script that tests:
- `GET /`
- `GET /health`
- `POST /api/generate-recipe`
- and that the returned `plot_url` is fetchable

File:
- `backend/test_api_endpoints.py`

Example (tests running server):

```bash
python backend/test_api_endpoints.py --base-url http://localhost:8000
```

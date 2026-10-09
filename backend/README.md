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

Run the commands below from the `backend` directory with Python installed.
`requirements.txt` lists unversioned top-level packages for the API, portfolio
analysis, backtesting, charts, LLM integration, and news extraction. Pip installs
their transitive dependencies automatically; Python and its standard-library
modules (including SQLite) are not pip dependencies. Unpinned versions simplify
setup but do not guarantee compatibility or reproducible installations.

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
python -m pip install -r requirements.txt
```

## Hypothesis-driven research example

Research-role code is grouped under
[agent_utils/research](app/services/bl_backtest/agent_utils/research/):

```text
agent_utils/
|-- prompts.py          # Critic/revision prompts; compatible research re-exports
`-- research/
    |-- __init__.py
    |-- prompts.py      # Research instructions and context formatting
    `-- tools.py        # Plain Python functions, NOT bound to an LLM
```

`make_research_tools(context)` creates scope-restricted callables over a private
copy of the already selected evidence:

- `query_evidence(asset, metrics=None, include_macro=True)` selects asset/shared
  evidence with original references and coverage information.
- `summarize_signal(asset, signal, lookback=63)` retrieves existing EPS, return,
  or shared-rate summaries; lookbacks are restricted to 21 or 63 observations.
- `compare_signals(assets, signal, lookback=63)` compares EPS/return values using
  deterministic mean, minimum, maximum, and population standard deviation.
  Missing/non-applicable entries are explicitly reported and excluded, not
  treated as zeros.

```python
from app.services.bl_backtest.agent_utils.research import make_research_tools

tools = make_research_tools(context)
comparison = tools["compare_signals"](["AAPL", "MSFT"], "eps", 63)
```

Tools accept no dataset path, SQL, code, or cutoff override. Unknown assets,
metrics, and unsupported windows raise explicit errors. Calculations remain in
the data interface. Returned entries preserve the existing evidence IDs,
units, source dates, synthetic-data labels, and warnings; comparison statistics
are descriptive summaries, not newly citable evidence or forecasts.
The production graph has no tool binding or dispatcher. For a standalone
LangChain demonstration, open
[tool_agent_walkthrough.ipynb](app/services/bl_backtest/agent_utils/research/tool_agent_walkthrough.ipynb).
It uses `ChatOpenAI.bind_tools`, prints model-selected tool calls and results,
limits retrieval to four rounds, and validates structured views against retrieved
evidence. Final synthesis receives a fresh message containing only
retrieved evidence and an explicit citation allowlist, not the initial catalog
or intermediate model assessments. Deterministic validation still rejects
unretrieved or invented citations. Retrieving a non-applicable coverage entry
is required before citing it as a reason for abstention.
Tool argument errors are printed and sent back for correction within the same
round budget; no successful retrieval means synthesis stops explicitly.
Responses requesting more than eight calls are rejected as a whole, with an
error response for every call ID so the model can retry a smaller batch.
The execution limits are not silently increased or bypassed.
For macro-only evidence, `query_evidence` still requires a selected ticker
(not `None`), `include_macro=True`, and macro metric names.
Install the backend dependencies and set `OPENAI_API_KEY` in the kernel
environment before manually running its live cell (OpenAI requests incur charges
and bypass application cost tracking). The notebook is saved unexecuted.
Production research/critic/revision behavior and portfolio construction are unchanged.

For the feedback-loop version, open
[research_feedback_walkthrough.ipynb](app/services/bl_backtest/research_feedback_walkthrough.ipynb),
an unexecuted copy of the single-date walkthrough. It uses the same research
implementation and unchanged BL node, prints the expanded conditional graph,
and displays original proposals, per-cycle criticism/revisions, validated final
views, and prior-versus-BL allocations.

The shared research graph now defaults to:

```text
prepare_research_context -> analyze_available_evidence -> generate_investment_views
    -> critic_agent -> revision_agent -> validate_structured_views
           ^                |
           +----------------+  needs_review and cycle count below limit
```

The analyst may return zero or more supported views; it need not cover every
security. The existing `AssetView` fields and deterministic citation/score
validation are preserved. Final views must be unique per asset and within the
requested universe. The critic independently evaluates every proposal's
evidence quality, contradictions, materiality, redundancy, and confidence.
Revision receives the original/current proposals, same evidence, and critique.
It can abstain or merge same-asset theses without inventing evidence.

`max_revision_cycles` accepts 1 or 2 (default 2). One cycle costs three LLM
calls (analyst, critic, revision); a second costs two more. The revision's
`needs_review` flag requests another cycle. At the hard limit, remaining
concerns are explicitly reported through `revision_limit_reached` and warnings;
deterministic validation still runs before any portfolio node. Empty final
views are valid and use the existing BL engine's equilibrium allocation.
For the earlier one-call behavior, use
`build_research_graph(feedback_enabled=False)` in the same implementation.
Existing notebooks use the updated default when rerun; their previously saved
outputs are not fresh feedback-loop results.

For a minimal single-date example without a backtest, open
[research_walkthrough.ipynb](app/services/bl_backtest/research_walkthrough.ipynb).
It shows explicit LangGraph state/node/edge construction, prints the expanded
compiled graph, and ends with validated views and Black-Litterman optimized
weights using the application's existing recipe runner. The
`research_views -> generate_weights_bl -> END` path uses an explicit
`MAX_ANNUAL_ALPHA = 0.05` illustrative annual prior-relative return calibration,
omits neutral/zero-confidence views, and shows the same `priorWeight`/`blWeight`
comparison as the application's allocation chart. Model defaults and long-only
constraints are reused; this is not an empirically calibrated forecasting model.
Graph invocation uses the shared bounded feedback loop, then deterministic BL optimization.
It reuses the same setup and credentials described below. The monthly backtest
notebook below still uses research-strength tilts, not BL.

Open [the research notebook](app/services/bl_backtest/run_example.ipynb) using
the repository Python environment. Install this backend's requirements and
set `OPENAI_API_KEY` in your environment or a local `.env`; do not put keys
in notebook cells. The notebook loads `.env` from the backend/repository root.

Edit `RESEARCH_HYPOTHESIS`, `START_DATE`, and `END_DATE` in the setup cell,
then run all cells. The default short range (2021-03-19 through 2021-09-30)
limits live calls. There is one bounded research/critic/revision sequence per monthly rebalance once
the required 64 observations exist. Before that, explicitly recorded warm-up
rebalances use equal weights and make no LLM call.

The [LangGraph workflow](app/services/bl_backtest/research_graph.py)
receives selected evidence, returns strict views, and checks citations in
Python. EPS/rate signals come from the existing synthetic CSVs; prices/returns
are existing historical exports. The agent receives no raw DataFrame or
database access.

The callback produces **research-strength tilts, not Black-Litterman weights**:

```text
score_i = 1 + 0.5 * sign(direction_i) * magnitude_i * confidence_i
weight_i = score_i / sum(scores)
```

Scores range from 0.5 to 1.5 before normalization. Neutral views retain a
baseline score of 1; omitted securities also retain that baseline score
without creating fabricated research views. Negative views reduce allocation without shorting.
Magnitude is not an expected return. There is no new backtest engine,
BL execution, or return calibration in this example.

Inspect `rebalance_records` and the notebook's audit tables for hypotheses,
cutoffs, validated views, evidence references, warnings, and weights.
Provider/refusal/parsing/validation failures stop execution; they do not
silently fall back to the mock. Token usage uses the existing LLM usage recorder.
Do not treat results as publication-time-safe research or demonstrated
investment performance: EPS/rates are synthetic, metadata is static, and an
LLM may already know later events.

Commands from the backend directory:

```powershell
# Existing mock example (no live research calls)
python -m app.services.bl_backtest.run_example

# One-shot research with no backtest
python -m app.services.bl_backtest.run_example --research-only --as-of 2021-09-30 --universe AAPL MSFT JPM --hypothesis "Use EPS revisions as the primary signal."

# Explicit live hypothesis-driven rebalances, using the existing bt engine
python -m app.services.bl_backtest.run_example --research-backtest --start-date 2021-03-19 --end-date 2021-09-30 --universe AAPL MSFT JPM

# Offline tests: fake LLM, real graph/bt execution, temporary usage database
python -m unittest test_research_graph -v
```

`AgenticViewWeighTarget.weight_fn` now receives
`(price_window, universe, hypothesis, as_of)`. Update any custom callbacks
to accept the fourth positional rebalance timestamp. The default mock
still supports its old three-argument direct invocation.

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

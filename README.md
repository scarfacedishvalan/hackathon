# Portfolio Research Dashboard

This project is a researcher-facing dashboard for turning investment ideas into structured portfolio views, Black-Litterman allocations, and backtest results.

At a high level, it helps answer four practical questions:

- What is my current market prior?
- How do my bottom-up and top-down views change that prior?
- What portfolio does the model recommend after blending those views?
- How would a related strategy or thesis have behaved historically?

## What the dashboard does

The dashboard combines three workflows in one place:

- Natural-language thesis input: analysts can describe asset or factor views in plain English and save them into a working recipe.
- Black-Litterman portfolio construction: the app combines market priors, user views, and portfolio constraints to produce posterior returns and optimized weights.
- Historical backtesting: users can parse a strategy description, review the generated recipe, and run either a single-strategy or thesis-driven portfolio backtest.

The working state is stored in `backend/data/bl_recipes/current.json`, which acts as the live thesis/recipe the UI edits and the backend executes.

## Key features

- Black-Litterman allocation dashboard with prior vs posterior weights, efficient frontier, sector contribution views, and calculation steps.
- Natural-language view parser for bottom-up asset views and top-down factor shocks.
- Editable model controls for `tau`, risk aversion, risk-free rate, and global weight bounds.
- Thesis management using named recipe snapshots saved from the current working recipe.
- Portfolio backtesting flow: describe strategy -> review parsed recipe -> run -> inspect metrics, equity curve, and trades.
- Agent-driven portfolio analysis that can stress-test a thesis and produce an auditable recommendation.

## Very brief math background

The Black-Litterman model starts from a market-implied equilibrium return vector,

$$
\pi = \delta \Sigma w_{mkt}
$$

where $\delta$ is risk aversion, $\Sigma$ is the covariance matrix, and $w_{mkt}$ is the market-cap-weighted portfolio.

Investor views are then blended with that prior to produce posterior expected returns. In plain terms: the model starts from “what the market already implies” and then tilts that baseline using explicit research views with confidence levels, instead of replacing the prior entirely.

## Architecture at a glance

### Frontend

The main dashboard lives in `frontend/port_optim`.

- Feature modules hold UI, types, hooks, and service clients.
- `useBLMain` is the main state hook for the Black-Litterman screen: it loads current views, runs the optimization, and refreshes the charts.
- The backtest page uses a simpler page-local flow for parse -> review -> run.
- Service files call FastAPI endpoints and keep API details out of components.

### Backend

The API lives in `backend/app`.

- Routers expose HTTP endpoints such as `/views`, `/bl`, `/backtest`, and `/agent`.
- Orchestrators coordinate multi-step workflows without mixing them into route handlers.
- Services contain the lower-level logic: LLM parsing, BL math, price data loading, and backtesting execution.
- The database layer is lightweight and mainly supports app state and seeded data.

### Orchestrator roles

- `view_orchestrator.py`: manages the live recipe, parses natural-language views, and persists the evolving thesis.
- `bl_orchestrator.py`: loads market metadata, runs the Black-Litterman pipeline, and shapes chart-ready outputs for the UI.
- `backtest_orchestrator.py`: parses strategy text and runs serialized backtests for both single strategies and thesis portfolios.

## Agent Orchestrator

The project also includes an agentic analysis layer for Black-Litterman research. This is not just a chat wrapper. It is an orchestrated workflow that loads a thesis, applies goal constraints, runs a base scenario, explores alternatives with tools, and then writes out a final recommendation with an audit trail.

In practice, this means a researcher can give the system a goal such as “find a more conservative allocation with a 15% max position size,” and the agent can:

- inspect the current recipe,
- run the baseline BL allocation,
- test alternative scenarios and stress cases,
- compare how allocations and risk metrics move,
- and synthesize a final narrative with recommended weights.

The agent logic lives primarily in `backend/app/orchestrators/bl_agent_orchestrator.py`, with supporting tools in `bl_agent_tools.py`. It follows a ReAct-style loop: reason about the current state, call the next useful tool, inspect the result, and repeat until it has enough evidence to synthesize an answer.

The supporting toolset includes scenario runs, stress sweeps, scenario comparison, and diagnostics such as view fragility and allocation envelope analysis. That makes the agent useful for more than one-shot optimization. It is effectively a structured research assistant for portfolio investigation.

An important practical feature is traceability. Each agent run can persist an audit record containing the recipe snapshot, the sequence of tool calls, scenario summaries, final synthesis, and cost usage. That gives researchers a reproducible path from question -> exploration -> recommendation instead of an opaque black-box answer.

## Why this helps a researcher

Without a tool like this, the research loop is fragmented across notes, spreadsheets, notebooks, and manual model updates. This dashboard reduces that friction by giving the researcher one place to:

- translate qualitative views into structured inputs,
- inspect how those views affect allocations,
- compare prior and posterior portfolios,
- test related strategies quickly,
- and keep the current thesis reproducible through saved JSON recipes.

The result is not just faster iteration. It is also a cleaner audit trail from idea -> model input -> portfolio recommendation -> historical test.
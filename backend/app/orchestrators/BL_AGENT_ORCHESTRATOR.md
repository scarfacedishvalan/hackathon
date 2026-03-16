# BL Agent Orchestrator Documentation

## Overview

The BL Agent Orchestrator is an autonomous portfolio analysis system that uses GPT-4o with tool-calling to explore, stress-test, and optimize Black-Litterman portfolio recipes. It operates via a **ReAct (Reason + Act) loop**, making iterative decisions based on tool results until it synthesizes final recommendations.

**Primary Use Case**: Given a BL recipe and a natural-language goal (e.g., "Find an allocation for a conservative investor with max 15% per position"), the agent autonomously stress-tests views, explores parameter sensitivity, and produces an actionable narrative with weight recommendations.

---

## Architecture

### Core Components

```
bl_agent_orchestrator.py         # Main orchestration & ReAct loop
├── bl_agent_tools.py            # Tool definitions & dispatch logic
├── bl_orchestrator.py           # BL calculation engine
├── view_orchestrator.py         # Recipe loading/management
├── llm_client.py                # LLM interaction & cost tracking
└── price_data/load_data.py      # Market data loading
```

### Data Flow

```
User Request (thesis_name, goal)
    ↓
Load Recipe + Extract Goal Constraints
    ↓
Run Base BL Scenario (benchmark)
    ↓
┌─────────────────────────────────┐
│   ReAct Loop (max 8 steps)      │
│  ┌──────────────────────────┐  │
│  │ GPT-4o analyzes state    │  │
│  │ Selects tool to call     │  │
│  └──────────────────────────┘  │
│            ↓                    │
│  ┌──────────────────────────┐  │
│  │ Core Tools:              │  │
│  │ - get_recipe_summary     │  │
│  │ - run_bl_scenario        │  │
│  │ - run_stress_sweep       │  │
│  │ - compare_scenarios      │  │
│  │ - synthesise             │  │
│  │                          │  │
│  │ Diagnostic Tools:        │  │
│  │ - view_importance_test   │  │
│  │ - view_fragility_scan    │  │
│  │ - factor_shock_scan      │  │
│  │ - allocation_envelope    │  │
│  └──────────────────────────┘  │
│            ↓                    │
│  Tool result → conversation     │
│  history → next iteration       │
└─────────────────────────────────┘
    ↓
Synthesis Output (narrative + weights)
    ↓
Audit Record Saved (JSON + SQLite costs)
```

---

## Public API

### `run_agent(thesis_name, goal, max_steps=8) -> dict`

**Execute a full agentic analysis run.**

**Parameters:**
- `thesis_name` (str): Name of BL recipe in `data/bl_recipes/<name>.json`
- `goal` (str): Natural-language objective (e.g., "Maximize Sharpe with max 20% position caps")
- `max_steps` (int): Hard cap on ReAct iterations (default: 8)

**Returns:**
- `audit` (dict): Complete audit record including:
  - `audit_id`: Unique UUID for this run
  - `base_recipe_snapshot`: Original recipe JSON
  - `base_result_summary`: Benchmark allocation stats
  - `steps`: List of tool calls with args/results
  - `scenarios_run`: All stress-test scenarios executed
  - `synthesis`: Final narrative + risk flags
  - `final_weights`: Recommended portfolio allocation
  - `weight_delta_vs_base`: Position changes from benchmark
  - `cost_breakdown`: Total tokens/USD spent
  - `step_costs`: Per-step cost breakdown

**Side Effects:**
- Writes audit JSON to `data/agent_audits/<audit_id>.json`
- Logs cost metrics to `data/agent_costs.db`

**Example:**
```python
from app.orchestrators.bl_agent_orchestrator import run_agent

audit = run_agent(
    thesis_name="current",
    goal="Stress-test all views and find allocation for max 15% per position"
)

print(audit["synthesis"]["narrative"])
print(audit["final_weights"])
```

---

### `list_audits(limit=50) -> list[dict]`

**Query past agent runs from the cost database.**

**Returns:**
- List of summary dicts with fields:
  - `audit_id`, `thesis_name`, `first_timestamp`
  - `steps`, `total_tokens`, `total_cost_usd`

---

### `load_audit(audit_id) -> dict`

**Load a previously-saved full audit record from disk.**

**Raises:**
- `FileNotFoundError` if audit does not exist

---

## The ReAct Loop

### System Prompt

Defines agent behavior via `AGENT_SYSTEM_PROMPT`:
- **Role**: Expert quantitative portfolio analyst
- **Task**: Systematically explore recipe, stress-test assumptions, find suitable allocations
- **Rules**:
  - Must call `get_recipe_summary` first to understand recipe structure
  - Run base scenario to establish benchmark
  - Execute ≥3 stress scenarios before synthesizing (unless trivial recipe)
  - Follow hard constraints from goal (e.g., position caps)
  - Populate `recommended_weights` in synthesis with allocation that best satisfies goal

### Loop Mechanics

1. **Initialization**:
   - Extract goal constraints via `_extract_goal_mutations(goal)`
     - Uses GPT-4o-mini to parse constraints like "max 20% per asset"
     - Falls back to regex if LLM fails
   - Run base scenario with goal constraints applied
   - Initialize conversation history with system prompt + base summary

2. **Iteration** (up to `max_steps`):
   - Call `chat_with_history()` with tools enabled
   - If no tool calls → treat as implicit synthesis, terminate
   - For each tool call:
     - Parse arguments
     - Dispatch via `dispatch_tool()` (from `bl_agent_tools.py`)
     - Append result to conversation history
     - Log to audit trail
   - If `synthesise` tool called with `done: true` → terminate

3. **Termination**:
   - Compute final weights (from synthesis or last scenario)
   - Calculate weight delta vs base
   - Aggregate cost breakdown from SQLite
   - Save full audit JSON to disk

---

## Helper Modules

### `bl_agent_tools.py`

**Purpose**: Define agent tools and orchestrate their execution.

**Key Exports**:
- `TOOLS` (list): OpenAI tool schema definitions for function calling
- `dispatch_tool(tool_name, tool_args, base_recipe, run_cache, price_df, goal_mutations)`: Router function

**Available Tools**:

| Tool | Purpose | Key Arguments |
|------|---------|---------------|
| `get_recipe_summary` | Inspect recipe structure | None |
| `run_bl_scenario` | Execute BL with mutations | `label`, `mutations` |
| `run_stress_sweep` | Parameter grid search | `sweep_parameter`, `sweep_values` |
| `compare_scenarios` | Side-by-side analysis | `scenario_labels` |
| `synthesise` | Terminate with narrative | `narrative`, `recommended_weights` |

**Diagnostic Tools** (Advanced Portfolio Analysis):

| Tool | Purpose | Key Arguments | Performance Limit |
|------|---------|---------------|------------------|
| `view_importance_test` | Identify critical views by removal | `views` (optional), `scenario_prefix` | N/A |
| `view_fragility_scan` | Test portfolio sensitivity to view magnitude | `view_label`, `magnitude_values`, `scenario_prefix` | Max 5 points |
| `factor_shock_scan` | Simulate macro factor shocks | `factor`, `shock_values`, `scenario_prefix` | Max 5 points |
| `allocation_envelope` | Compute min/max weight ranges across scenarios | `scenario_labels` (optional) | N/A |

**Diagnostic Tool Details**:

1. **`view_importance_test`**: Systematically removes each view one at a time and measures:
   - Sharpe change (how much performance degrades)
   - Allocation shift (sum of absolute weight changes)
   - Results sorted by allocation shift (descending) to highlight most impactful views
   - Use this **early** in analysis to focus subsequent testing on critical views

2. **`view_fragility_scan`**: Tests how portfolio weights change as a single view's magnitude varies:
   - Useful for identifying non-linear sensitivities
   - Example: Test AAPL expected return at [+5%, +10%, +15%, +20%, +25%]
   - Each scenario saved in run_cache with label: `{prefix}_{view_label}_{magnitude}`
   - Returns fragility scan with weights, Sharpe, volatility at each magnitude point

3. **`factor_shock_scan`**: Simulates macro factor shocks (e.g., interest rate changes):
   - Tests portfolio response to different shock magnitudes
   - Example: Test "rates" factor at [-2%, -1%, 0%, +1%, +2%]
   - Each scenario saved in run_cache with label: `{prefix}_{factor}_{shock}`
   - Returns portfolio return, volatility, weights, Sharpe at each shock level

4. **`allocation_envelope`**: Computes stability metrics across all scenarios:
   - For each asset: min weight, max weight, range
   - Results sorted by range (descending) to highlight most variable allocations
   - Helps assess robustness: narrow ranges = stable allocation
   - Use this **late** in analysis after running multiple scenarios

**Recommended Diagnostic Workflow**:
1. `get_recipe_summary` (understand recipe structure)
2. `view_importance_test` (identify top 2-3 critical views)
3. `view_fragility_scan` (test sensitivity of important views)
4. `factor_shock_scan` (if factor exposures exist in recipe)
5. `allocation_envelope` (summarize stability across all scenarios)
6. `synthesise` (final narrative with insights)

**Internal Utilities**:
- `_apply_mutations(recipe, mutations)`: Deep-merge recipe overrides
- `_summarise_result(bl_result, recipe)`: Extract key stats (weights, Sharpe, vol, etc.)
- `_weight_delta(w1, w2)`: Compute position-level changes
- `_apply_view_override(recipe, label, magnitude)`: Override view magnitude
- `_apply_factor_shock_override(recipe, factor, shock)`: Override factor shock
- `_compute_weight_shift(base_weights, scenario_weights)`: Sum of absolute weight changes

---

### `bl_orchestrator.py`

**Purpose**: Execute Black-Litterman optimization.

**Key Function**:
```python
run_black_litterman(recipe, price_data) -> dict
```

**Returns**:
- `efficientFrontier`: Risk-return curve points
- `allocation`: Optimal portfolio weights
- `portfolioStats`: Expected return, volatility, Sharpe ratio
- `calculationSteps`: LaTeX-formatted BL math (6 sections)
- `topDownContribution`: Sector exposure breakdown

**Used By**: Agent tools call this repeatedly with mutated recipes to explore scenarios.

---

### `view_orchestrator.py`

**Purpose**: Load and validate BL recipes from disk.

**Key Function**:
```python
load_recipe(thesis_name) -> dict
```

**Recipe Structure**:
- `meta`: Name, description, version
- `universe`: List of tickers
- `market_context`: Embedded market caps, factor exposures, sectors
- `model_parameters`: tau, risk_aversion, risk_free_rate
- `constraints`: long_only, weight_bounds
- `bottom_up_views`: Asset-level views (absolute/relative)
- `top_down_views`: Factor shock views

---

### `llm_client.py`

**Purpose**: Manage OpenAI API interactions and cost tracking.

**Key Classes/Functions**:

#### `chat_with_history(messages, service, operation, tools=None, model, temperature, agent_cost_db_path, agent_metadata) -> (content, tool_calls)`

**Responsibilities**:
- Call OpenAI chat completion API
- Parse response (text content or tool calls)
- Log usage metrics to SQLite

**Agent-Specific Behavior**:
- When `agent_cost_db_path` provided, logs to `agent_costs` table
- Records: audit_id, step, tool_called, model, tokens, cost_usd, timestamp

#### `AgentCostTracker(db_path)`

**Methods**:
- `log_cost(audit_id, step, service, operation, ...)`: Write cost record
- `get_audit_cost(audit_id)`: Aggregate total for an audit
- `get_audit_steps(audit_id)`: Per-step breakdown
- `list_audit_summaries(limit)`: Query all past runs

**Database Schema** (`agent_costs` table):
```sql
CREATE TABLE agent_costs (
    id INTEGER PRIMARY KEY,
    audit_id TEXT,
    step INTEGER,
    service TEXT,
    operation TEXT,
    tool_called TEXT,
    model TEXT,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    cost_usd REAL,
    timestamp TEXT
)
```

---

### `price_data/load_data.py`

**Purpose**: Load historical price data for backtesting/optimization.

**Key Function**:
```python
load_market_data() -> (price_df, ...)
```

**Returns**:
- `price_df`: Daily price time series (DatetimeIndex × ticker columns)
- Used to compute covariance matrices and implied equilibrium returns

**Agent Usage**: Loaded once at start of `run_agent()`, passed to all BL runs.

---

## Scenario Caching

**Run Cache** (`run_cache: Dict[str, dict]`):
- In-memory store of scenario results within a single agent run
- Key: scenario label (e.g., `"base"`, `"high_confidence_sweep_0.8"`)
- Value: Summarized result dict with `weights`, `sharpe_ratio`, `volatility`, etc.

**Purpose**:
- Avoid redundant BL calculations
- Enable `compare_scenarios` tool to reference past runs
- Provide agent with memory of explored scenarios

**Lifecycle**: Exists only for duration of `run_agent()` call

---

## Cost Tracking

### Why Track Costs?

Agent runs can make 10+ LLM calls (ReAct steps + tool reasoning). Cost visibility enables:
- Budget monitoring for production deployments
- Per-recipe complexity analysis
- Model comparison (GPT-4o vs GPT-4o-mini)

### Cost Flow

1. **Per-Call Logging**:
   - Every `chat_with_history()` call extracts `usage` from OpenAI response
   - Computes USD cost via pricing table (e.g., GPT-4o: $5/1M input tokens)
   - Writes to `agent_costs.db` with audit_id + step metadata

2. **Audit Aggregation**:
   - At end of `run_agent()`, queries SQLite for all records matching audit_id
   - Sums tokens/cost across steps
   - Includes breakdown by operation type (e.g., `react_step`, `extract_goal_constraints`)

3. **Persistence**:
   - Cost data survives in SQLite even if audit JSON is deleted
   - Enables historical cost analysis via `list_audits()`

---

## Audit System

### Audit Record Structure

Each `run_agent()` call produces a comprehensive JSON audit:

```json
{
  "audit_id": "uuid-v4",
  "thesis_name": "current",
  "goal": "Find allocation for max 15% position caps",
  "run_timestamp": "2026-03-16T14:23:01",
  "model": "gpt-4o",
  "base_recipe_snapshot": { ... },
  "base_result_summary": {
    "weights": { "AAPL": 0.20, ... },
    "sharpe_ratio": 0.85,
    "volatility": 0.18
  },
  "steps": [
    {
      "step": 0,
      "tool": "get_recipe_summary",
      "args": {},
      "result": { ... }
    },
    ...
  ],
  "scenarios_run": {
    "tech_bear": { "weights": {...}, "sharpe_ratio": 0.72 }
  },
  "diagnostics": {
    "view_fragility": [
      {
        "view_label": "AAPL_bullish",
        "fragility_scan": [
          { "magnitude": 0.10, "weights": {...}, "sharpe": 0.82, "volatility": 0.17 },
          { "magnitude": 0.15, "weights": {...}, "sharpe": 0.88, "volatility": 0.18 }
        ]
      }
    ],
    "factor_transmission": [
      {
        "factor": "rates",
        "shock_results": [
          { "shock": -0.02, "portfolio_return": 0.14, "volatility": 0.16, "weights": {...} }
        ]
      }
    ],
    "view_importance": [
      {
        "view_importance": [
          { "view": "AAPL_bullish", "sharpe_change": -0.12, "allocation_shift": 0.35 },
          { "view": "tech_tilt", "sharpe_change": -0.05, "allocation_shift": 0.18 }
        ]
      }
    ],
    "allocation_envelope": [
      {
        "allocation_envelope": {
          "AAPL": { "min": 0.15, "max": 0.28, "range": 0.13 },
          "MSFT": { "min": 0.12, "max": 0.20, "range": 0.08 }
        },
        "scenarios_analyzed": 12
      }
    ]
  },
  "synthesis": {
    "narrative": "...",
    "risk_flags": ["..."],
    "recommended_weights": { ... },
    "done": true
  },
  "final_weights": { ... },
  "weight_delta_vs_base": { "AAPL": -0.05, ... },
  "cost_breakdown": {
    "total_tokens": 45230,
    "total_cost_usd": 0.52
  },
  "step_costs": [ ... ]
}
```

**Diagnostics Field**: Automatically populated when diagnostic tools are used during the agent run. Contains:
- `view_fragility`: Results from `view_fragility_scan` calls
- `factor_transmission`: Results from `factor_shock_scan` calls  
- `view_importance`: Results from `view_importance_test` calls
- `allocation_envelope`: Results from `allocation_envelope` calls

Each diagnostic tool result includes full scan data (weights, metrics) for offline analysis.

### Storage

- **Location**: `backend/data/agent_audits/<audit_id>.json`
- **Retention**: Indefinite (manual cleanup required)
- **Size**: Typically 50-200 KB per audit (larger with diagnostics: 100-500 KB)

### Use Cases

- **Reproducibility**: Re-load past analyses via `load_audit()`
- **Debugging**: Inspect exact tool call sequence that led to recommendations
- **Compliance**: Audit trail for portfolio decision-making
- **Training**: Generate datasets for fine-tuning or prompt engineering

---

## Goal Constraint Extraction

### Problem

Users phrase portfolio constraints in natural language:
- "Max 20% per asset"
- "Conservative investor, no single name above 15%"
- "Keep each position under a quarter"

### Solution: `_extract_goal_mutations(goal)`

**Two-Stage Approach**:

1. **LLM Extraction** (GPT-4o-mini):
   - Send goal to specialized constraint-parsing prompt
   - Parse JSON response for `weight_bounds`, `risk_aversion`, `long_only`
   - Strips markdown code fences if model adds them

2. **Regex Fallback**:
   - If LLM fails, regex searches for patterns like `max 20%`
   - Converts to `weight_bounds: [0.0, 0.20]`

**Integration**:
- Extracted mutations applied to **every** BL scenario run
- Agent cannot violate goal-level constraints
- Ensures final recommendations are feasible

---

## Configuration

### Tunables

| Parameter | Location | Default | Purpose |
|-----------|----------|---------|---------|
| `MAX_STEPS` | `bl_agent_orchestrator.py` | 8 | Max ReAct iterations |
| `AGENT_MODEL` | `bl_agent_orchestrator.py` | `"gpt-4o"` | LLM for reasoning |
| `AGENT_COSTS_DB` | `bl_agent_orchestrator.py` | `data/agent_costs.db` | SQLite path |
| `AGENT_AUDITS_DIR` | `bl_agent_orchestrator.py` | `data/agent_audits/` | Audit JSON dir |

### Paths

```
backend/
├── data/
│   ├── agent_costs.db          # SQLite cost tracking
│   ├── agent_audits/           # Audit JSON files
│   │   └── <uuid>.json
│   ├── bl_recipes/             # Recipe library
│   │   ├── current.json
│   │   └── alpha_tilt.json
│   └── market_data.json        # Global market metadata
└── app/
    ├── orchestrators/
    │   ├── bl_agent_orchestrator.py   # This module
    │   ├── bl_agent_tools.py
    │   ├── bl_orchestrator.py
    │   └── view_orchestrator.py
    └── services/
        ├── llm_client/
        └── price_data/
```

---

## Tool Usage Patterns

### Typical Agent Workflow

1. **Discovery** (`get_recipe_summary`):
   - Understand universe, views, parameters
   - Identify sweepable confidence parameters

2. **Baseline** (implicit via base run):
   - Already computed before ReAct loop starts
   - Cached in `run_cache["base"]`

3. **Stress Testing**:
   - **Confidence sweep**: `run_stress_sweep` with `sweep_parameter: "View Label"`, `sweep_values: [0.4, 0.6, 0.8]`
   - **Return assumptions**: `run_bl_scenario` with `mutations: {override_expected_return: {AAPL: 0.08}}`
   - **Risk aversion**: `run_stress_sweep` with `sweep_parameter: "risk_aversion"`

4. **Comparison** (`compare_scenarios`):
   - Side-by-side stats for selected labels
   - Identify which mutation best satisfies goal

5. **Synthesis** (`synthesise`):
   - Narrative summary of findings
   - Risk flags (e.g., "High position concentration", "Low diversification")
   - Recommended weights (must be from a named scenario)

### Critical Rules

- **Constraint Enforcement**: Every mutation must include `goal_mutations`
- **Named Scenarios**: `run_stress_sweep` generates grid summaries but doesn't save weights; must follow with `run_bl_scenario` to capture exact weights
- **Recommended Weights**: Must pass best allocation to `synthesise` — evaluated relative to goal metric (Sharpe, vol, diversification, etc.)

---

## Error Handling

### Recipe Errors

- **Missing recipe**: `load_recipe()` raises `FileNotFoundError`
- **Invalid JSON**: Parsing errors logged, agent receives error summary

### BL Calculation Errors

- **Singular matrices**: Optimizer failures caught, returned as `{"error": "..."}`
- **Constraint violations**: Warnings added to result (e.g., `"constraint_warning": "All weights equal to cap"`)

### LLM Errors

- **API failures**: Retries handled by `llm_client`, logged as error steps
- **Malformed tool calls**: JSON parsing errors → empty `tool_args`
- **Max steps reached**: Agent terminates with partial synthesis

---

## Performance Characteristics

### Typical Run Metrics

- **Steps**: 5-8 tool calls
- **Duration**: 30-90 seconds (network latency dominant)
- **Tokens**: 30k-60k total
- **Cost**: $0.30-$0.70 per run (GPT-4o pricing)

### Optimization Tips

1. **Reduce max_steps**: Lower to 5 for simple recipes
2. **Use GPT-4o-mini**: Switch model for non-critical runs (10x cheaper)
3. **Cache aggressive**: Expand `run_cache` to persist across runs
4. **Batch sweeps**: Use `run_stress_sweep` instead of multiple `run_bl_scenario` calls

---

## Extension Points

### Adding New Tools

1. Define tool schema in `bl_agent_tools.py` → `TOOLS` list
2. Implement handler function (prefix: `_handle_*`)
3. Add dispatch case in `dispatch_tool()`
4. Update system prompt with usage guidance

**Example**: Add `export_weights` tool to save allocation to CSV:

```python
TOOLS.append({
    "type": "function",
    "function": {
        "name": "export_weights",
        "description": "Save scenario weights to CSV file",
        "parameters": {
            "type": "object",
            "properties": {
                "scenario_label": {"type": "string"},
                "output_path": {"type": "string"}
            },
            "required": ["scenario_label", "output_path"]
        }
    }
})

def _handle_export_weights(args, run_cache, **_):
    label = args["scenario_label"]
    if label not in run_cache:
        return {"error": f"Scenario '{label}' not found"}
    
    weights = run_cache[label]["weights"]
    import pandas as pd
    pd.Series(weights).to_csv(args["output_path"])
    return {"status": "exported", "path": args["output_path"]}
```

### Custom Cost Tracking

Extend `AgentCostTracker` to:
- Alert on budget thresholds
- Track per-user spend quotas
- Export cost reports to BI tools

---

## Troubleshooting

### "All weights equal to weight_bounds cap"

**Symptom**: Agent reports constraint warning, allocation shows equal weights at cap.

**Cause**: Position caps too restrictive given number of assets (e.g., 5 assets with 15% cap = 75% < 100%).

**Fix**:
- Increase cap in goal (e.g., "max 25% per position")
- Reduce universe size in recipe

### "Max steps reached without synthesis"

**Symptom**: Agent terminates without final narrative.

**Cause**: Agent stuck in exploration loop, not calling `synthesise`.

**Fix**:
- Increase `max_steps` to 12
- Add explicit termination trigger in system prompt (e.g., "After 5 scenarios, synthesise")

### "Scenario not found in run_cache"

**Symptom**: `compare_scenarios` fails with missing label.

**Cause**: Agent referencing a sweep result (not saved as named scenario).

**Fix**: Update system prompt to clarify sweep results → must call `run_bl_scenario` to save weights.

---

## Best Practices

1. **Goal Clarity**: Phrase goals with explicit constraints ("max 20% per asset, minimize volatility")
2. **Recipe Quality**: Ensure views are economically sensible; agent can't fix bad inputs
3. **Monitor Costs**: Run `list_audits()` periodically to track spend
4. **Audit Review**: Inspect `steps` log for debugging unexpected recommendations
5. **Iterative Refinement**: Use saved audits to improve system prompts and tool descriptions

---

## Future Enhancements

- **Multi-Recipe Analysis**: Compare allocations across different recipe families
- **Live Data**: Integrate real-time market data instead of static price_df
- **Interactive Mode**: Allow user mid-run feedback (e.g., "explore tech sector more")
- **Visualization Export**: Auto-generate charts from scenarios (efficient frontier overlays)
- **Fine-Tuned Model**: Train specialized LLM on portfolio analysis tasks to reduce costs

---

## Summary

The BL Agent Orchestrator transforms natural-language portfolio requests into systematic quantitative analyses via:

1. **ReAct Loop**: GPT-4o iteratively selects tools based on prior results
2. **Tool Ecosystem**: 5 specialized functions for exploration, stress-testing, comparison, synthesis
3. **Cost Tracking**: SQLite-backed ledger for production budget monitoring
4. **Audit Trail**: Complete JSON records for reproducibility and compliance
5. **Constraint-Aware**: Automatically parses and enforces goal-level portfolio limits

By combining LLM reasoning with rigorous BL optimization, the agent delivers actionable portfolio recommendations with full transparency into the analysis process.

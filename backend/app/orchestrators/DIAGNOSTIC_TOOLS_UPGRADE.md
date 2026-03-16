# BL Agent Diagnostic Tools Upgrade

## Overview

The BL Agent infrastructure has been upgraded to support **advanced portfolio diagnostics**, transforming it from a basic parameter sweeper into a comprehensive **portfolio diagnostics engine**.

## New Capabilities

The agent can now identify:

- **Fragile views**: Views that cause disproportionate allocation shifts
- **Macro sensitivity**: Portfolio response to factor shocks
- **View importance**: Which views drive the allocation
- **Allocation stability**: Weight ranges across stress scenarios

## New Diagnostic Tools

### 1. `view_importance_test`

**Purpose**: Systematically identify which views are critical to the allocation.

**How it works**:
- Removes each view one at a time from the recipe
- Runs BL optimization without that view
- Measures:
  - Sharpe change (performance impact)
  - Allocation shift (sum of absolute weight changes)

**When to use**: **Early** in the diagnostic workflow to focus subsequent testing on important views.

**Example**:
```json
{
  "tool": "view_importance_test",
  "args": {
    "views": ["AAPL_bullish", "tech_tilt", "value_rotation"],
    "scenario_prefix": "view_removed"
  }
}
```

**Output**:
```json
{
  "view_importance": [
    {
      "view": "AAPL_bullish",
      "sharpe_change": -0.12,
      "allocation_shift": 0.35,
      "sharpe_without_view": 0.73
    },
    {
      "view": "tech_tilt",
      "sharpe_change": -0.05,
      "allocation_shift": 0.18,
      "sharpe_without_view": 0.80
    },
    {
      "view": "value_rotation",
      "sharpe_change": -0.01,
      "allocation_shift": 0.05,
      "sharpe_without_view": 0.84
    }
  ]
}
```

**Interpretation**:
- `AAPL_bullish` is the most critical view (highest allocation shift)
- Removing it causes 35% of portfolio weights to change
- Sharpe drops by 0.12 without this view

---

### 2. `view_fragility_scan`

**Purpose**: Test how portfolio weights change as a view's magnitude varies.

**How it works**:
- Overrides a single view's expected return/outperformance
- Runs BL at multiple magnitude values
- Captures weights, Sharpe, volatility at each point

**When to use**: After `view_importance_test` to focus on top 1-2 critical views.

**Performance limit**: Max 5 magnitude points.

**Example**:
```json
{
  "tool": "view_fragility_scan",
  "args": {
    "view_label": "AAPL_bullish",
    "magnitude_values": [0.05, 0.10, 0.15, 0.20, 0.25],
    "scenario_prefix": "fragility"
  }
}
```

**Output**:
```json
{
  "view_label": "AAPL_bullish",
  "fragility_scan": [
    {
      "magnitude": 0.05,
      "weights": {"AAPL": 0.18, "MSFT": 0.16, ...},
      "sharpe": 0.78,
      "volatility": 0.17
    },
    {
      "magnitude": 0.10,
      "weights": {"AAPL": 0.22, "MSFT": 0.14, ...},
      "sharpe": 0.82,
      "volatility": 0.18
    },
    ...
  ]
}
```

**Interpretation**:
- AAPL weight increases from 18% to 22% as expected return increases from 5% to 10%
- Non-linear response indicates potential fragility
- Use this to set confidence intervals on view magnitudes

---

### 3. `factor_shock_scan`

**Purpose**: Simulate macro factor shocks and observe portfolio response.

**How it works**:
- Overrides a factor shock magnitude in `top_down_views.factor_shocks`
- Runs BL at multiple shock levels
- Captures portfolio return, volatility, weights at each shock

**When to use**: When recipe includes factor exposures (e.g., interest rates, inflation).

**Performance limit**: Max 5 shock points.

**Example**:
```json
{
  "tool": "factor_shock_scan",
  "args": {
    "factor": "rates",
    "shock_values": [-0.02, -0.01, 0.0, 0.01, 0.02],
    "scenario_prefix": "factor"
  }
}
```

**Output**:
```json
{
  "factor": "rates",
  "shock_results": [
    {
      "shock": -0.02,
      "portfolio_return": 0.14,
      "volatility": 0.16,
      "weights": {"AAPL": 0.20, ...},
      "sharpe": 0.88
    },
    {
      "shock": 0.02,
      "portfolio_return": 0.10,
      "volatility": 0.19,
      "weights": {"AAPL": 0.18, ...},
      "sharpe": 0.53
    }
  ]
}
```

**Interpretation**:
- Portfolio return drops from 14% to 10% as rates increase 2%
- Sharpe deteriorates significantly under rate shock
- Use this to assess macro risk exposure

---

### 4. `allocation_envelope`

**Purpose**: Compute min/max weight ranges across all previously executed scenarios.

**How it works**:
- Aggregates weights from all scenarios in `run_cache`
- Computes per-asset: min, max, range
- Sorts by range (descending) to highlight variable allocations

**When to use**: **Late** in the workflow to summarize allocation stability.

**Example**:
```json
{
  "tool": "allocation_envelope",
  "args": {
    "scenario_labels": ["base", "fragility_AAPL_0.10", "fragility_AAPL_0.20", "factor_rates_0.02"]
  }
}
```

**Output**:
```json
{
  "allocation_envelope": {
    "AAPL": {
      "min": 0.15,
      "max": 0.28,
      "range": 0.13
    },
    "MSFT": {
      "min": 0.12,
      "max": 0.20,
      "range": 0.08
    },
    "AMZN": {
      "min": 0.10,
      "max": 0.12,
      "range": 0.02
    }
  },
  "scenarios_analyzed": 4
}
```

**Interpretation**:
- AAPL weight varies by 13% across scenarios (most variable)
- AMZN weight is stable (range = 2%)
- Narrow ranges indicate robust allocations

---

## Recommended Diagnostic Workflow

1. **`get_recipe_summary`** - Understand recipe structure
2. **`view_importance_test`** - Identify top 2-3 critical views
3. **`view_fragility_scan`** - Test sensitivity of important views (max 5 points each)
4. **`factor_shock_scan`** - Test macro factor sensitivity (if factor exposures exist)
5. **`allocation_envelope`** - Summarize stability across all scenarios
6. **`synthesise`** - Final narrative with insights and recommended weights

## System Prompt Enhancements

The agent's system prompt now guides it to:

- **Diagnose which views drive the allocation** before stress-testing parameters
- **Explore fragility of important views** using targeted magnitude scans
- **Test macro factor shocks** when factor exposures exist in the recipe
- **Evaluate whether allocations remain stable** across scenarios using envelope analysis

The agent is instructed to prefer structured diagnostics over ad-hoc parameter sweeps.

## Audit Record Enhancements

The audit record now includes a `diagnostics` field:

```json
{
  "diagnostics": {
    "view_fragility": [...],
    "factor_transmission": [...],
    "view_importance": [...],
    "allocation_envelope": [...]
  }
}
```

This field is automatically populated when diagnostic tools are used and persisted to:
- `backend/data/agent_audits/<audit_id>.json`

## Performance Safeguards

To prevent excessive API costs:

- **`view_fragility_scan`**: Max 5 magnitude points
- **`factor_shock_scan`**: Max 5 shock points
- Larger sweeps are rejected with an error message

Use `run_stress_sweep` for broader parameter exploration if needed.

## Goal Constraint Preservation

All diagnostic tools respect `goal_mutations`:

- Position caps (e.g., `weight_bounds: [0.0, 0.15]`)
- Risk aversion overrides
- Long-only constraints

Every scenario run automatically merges goal constraints with local mutations.

## Scenario Naming Convention

All diagnostic scenarios follow predictable naming:

- Fragility scans: `fragility_<view_label>_<magnitude>`
- Factor scans: `factor_<factor>_<shock>`
- View removal: `view_removed_<view_label>`

This keeps `run_cache` interpretable and enables `compare_scenarios` to reference diagnostic results.

## Backward Compatibility

**No breaking changes**:

- Existing `run_agent()` signature unchanged
- All original tools (`run_bl_scenario`, `run_stress_sweep`, etc.) unchanged
- Cost tracking system unchanged
- Audit storage structure extended (new `diagnostics` field is optional)

Agents that don't use diagnostic tools will function identically to before.

## Example Agent Run with Diagnostics

```python
from app.orchestrators.bl_agent_orchestrator import run_agent

audit = run_agent(
    thesis_name="current",
    goal="Identify fragile views and find robust allocation with max 15% per position",
    max_steps=10
)

# Access diagnostic results
print(audit["diagnostics"]["view_importance"])
print(audit["diagnostics"]["allocation_envelope"])
print(audit["synthesis"]["narrative"])
```

Expected agent behavior:
1. Calls `get_recipe_summary`
2. Calls `view_importance_test` to identify critical views
3. Calls `view_fragility_scan` on top 2 important views
4. Calls `factor_shock_scan` if factor shocks exist
5. Runs targeted `run_bl_scenario` calls for goal-specific testing
6. Calls `allocation_envelope` to assess stability
7. Calls `synthesise` with comprehensive narrative highlighting fragile views and recommended weights

## Implementation Details

### Files Modified

1. **`bl_agent_tools.py`**:
   - Added 4 new tool schemas to `TOOLS` list
   - Added helper functions: `_apply_view_override`, `_apply_factor_shock_override`, `_compute_weight_shift`
   - Added dispatch handlers for all 4 diagnostic tools
   - Updated module docstring

2. **`bl_agent_orchestrator.py`**:
   - Extended `AGENT_SYSTEM_PROMPT` with diagnostic workflow guidance
   - Added diagnostic extraction logic before audit assembly
   - Added `diagnostics` field to audit record

3. **`BL_AGENT_ORCHESTRATOR.md`**:
   - Added diagnostic tools table
   - Added detailed documentation for each diagnostic tool
   - Updated audit record structure example
   - Added recommended workflow section

### Lines of Code Added

- `bl_agent_tools.py`: ~250 lines (helpers + tool schemas + dispatch handlers)
- `bl_agent_orchestrator.py`: ~50 lines (prompt updates + diagnostics extraction)
- `BL_AGENT_ORCHESTRATOR.md`: ~100 lines (documentation)

Total: **~400 lines** of production code + documentation.

## Testing Recommendations

1. **Unit test**: Each diagnostic tool with sample recipes
2. **Integration test**: Full agent run with diagnostic workflow
3. **Performance test**: Verify 5-point limit enforcement
4. **Edge case test**: Empty views, missing factors, constraint conflicts

## Future Enhancements

Potential extensions (not implemented):

- **View correlation analysis**: Identify redundant views
- **Robust optimization**: Multi-scenario optimization with worst-case constraints
- **Monte Carlo simulation**: Bootstrap confidence intervals for allocations
- **Factor attribution**: Decompose portfolio return by factor contribution
- **Constraint relaxation**: Identify binding constraints and suggest relaxations

These can be added as additional diagnostic tools following the same pattern.

---

**Upgrade completed**: March 16, 2026  
**Backward compatible**: ✅  
**Production ready**: ✅  
**Documentation complete**: ✅

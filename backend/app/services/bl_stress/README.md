# Black-Litterman Stress Testing Layer

Production-ready stress test specification layer for Black-Litterman portfolio optimization.

## Overview

This module provides tools for converting natural language stress testing requests into structured specifications that can be consumed by an orchestrator. The layer focuses on **intent interpretation** and **specification generation**, not on execution or numeric computation.

## Architecture

```
bl_stress/
├── __init__.py                    # Package exports
├── stress_schema.py               # Pydantic models for StressSpec
├── stress_defaults.py             # Deterministic default grids
├── llm_parser.py                  # LLM-based parser
├── example_recipe.json            # Example recipe for testing
└── prompts/
    └── stress_prompt.txt          # System prompt for LLM
```

## Components

### 1. `stress_schema.py`

Defines the `StressSpec` Pydantic model with:

- **7 stress types**: view_magnitude, confidence_scale, factor_amplification, tau_shift, volatility_multiplier, regime_template, view_joint
- **Field validation**: Ensures required fields are present based on stress_type
- **Type safety**: All fields are properly typed and validated

### 2. `stress_defaults.py`

Provides deterministic default grids:

- `DEFAULT_VIEW_MULTIPLIERS`: Grid for view magnitude stress tests
- `DEFAULT_CONFIDENCE_GRID`: Grid for confidence scaling
- `DEFAULT_FACTOR_SCALE`: Grid for factor amplification
- `DEFAULT_TAU_MULTIPLIER`: Grid for tau uncertainty
- `DEFAULT_VOLATILITY_MULTIPLIER`: Grid for volatility stress
- `REGIME_LIBRARY`: Predefined market regime templates

All grids come in three levels: **conservative**, **standard**, **aggressive**.

### 3. `llm_parser.py`

LLM-based parser following the same pattern as `bl_llm_parser`:

- Uses `chat_and_record` for LLM calls with automatic tracking
- Loads system prompt from `prompts/stress_prompt.txt`
- Accepts optional recipe context (view labels, factors)
- Returns validated `StressSpec` object
- Main function: `parse_stress_prompt(user_request, recipe_context)`

### 4. `prompts/stress_prompt.txt`

System prompt that:

- Instructs LLM to output only valid JSON
- Lists all allowed stress types and their required fields
- Explicitly forbids numeric hallucination
- Enforces use of grid_level labels instead of numeric ranges
- Requires exact matching of view labels and factor names

## Usage

### Basic Usage

```python
from app.services.bl_stress import parse_stress_prompt

# Simple request without recipe context
spec = parse_stress_prompt(
    "Test different tau values with conservative range"
)

print(spec.stress_type)  # "tau_shift"
print(spec.grid_level)   # "conservative"
```

### With Recipe Context

```python
import json
from app.services.bl_stress import parse_stress_prompt

# Load recipe
with open("example_recipe.json") as f:
    recipe = json.load(f)

# Extract context
context = {
    "views": [v["label"] for v in recipe["bottom_up_views"]],
    "factors": recipe["top_down_views"]["factor_model"]["factors"]
}

# Parse request with context
spec = parse_stress_prompt(
    "Stress test the AAPL vs MSFT view with aggressive range",
    recipe_context=context
)

print(spec.stress_type)    # "view_magnitude"
print(spec.target_label)   # "AAPL outperforms MSFT"
print(spec.grid_level)     # "aggressive"
```

### Accessing Default Grids

```python
from app.services.bl_stress import (
    DEFAULT_VIEW_MULTIPLIERS,
    get_grid_for_stress_type,
    get_regime_template,
    list_available_regimes
)

# Get a specific grid
grid = DEFAULT_VIEW_MULTIPLIERS["standard"]
print(grid)  # [-2, -1, 0, 1, 2]

# Get grid by stress type
grid = get_grid_for_stress_type("confidence_scale", "aggressive")
print(grid)  # [0.2, 0.4, 0.6, 0.8, 1.0]

# Get regime template
regime = get_regime_template("high_uncertainty")
print(regime)
# {
#   "description": "Market regime with elevated uncertainty and volatility",
#   "tau_multiplier": 2.0,
#   "confidence_scale": 0.7,
#   "volatility_multiplier": 1.3
# }

# List all available regimes
regimes = list_available_regimes()
print(regimes)  # ["high_uncertainty", "risk_off", "risk_on", "crisis", "low_vol"]
```

## Testing

Use the provided test script:

```bash
# Run full test suite
python run_stress_parser.py

# Interactive mode
python run_stress_parser.py --interactive

# Single request
python run_stress_parser.py --request "Stress the momentum factor with aggressive range"

# Custom recipe
python run_stress_parser.py --recipe path/to/custom_recipe.json
```

## Stress Types

### 1. view_magnitude
Stress the magnitude of a specific view's expected outperformance.

**Required fields**: `target_label`, `grid_level`
**Optional fields**: `mode`

### 2. confidence_scale
Scale the confidence levels of views.

**Required fields**: `grid_level`
**Optional fields**: `target_label` (for specific view)

### 3. factor_amplification
Amplify or dampen a specific factor's influence.

**Required fields**: `factor`, `grid_level`

### 4. tau_shift
Stress the tau uncertainty parameter.

**Required fields**: `grid_level`

### 5. volatility_multiplier
Scale the covariance matrix volatility.

**Required fields**: `grid_level`

### 6. regime_template
Apply a predefined market regime template.

**Required fields**: `template_name`

Available templates: `high_uncertainty`, `risk_off`, `risk_on`, `crisis`, `low_vol`

### 7. view_joint
Jointly stress both magnitude and confidence of a specific view.

**Required fields**: `target_label`, `magnitude_grid_level`, `confidence_grid_level`

## Design Principles

1. **Clean Separation**: This layer only generates specifications, does not execute stress tests
2. **No Numeric Hallucination**: LLM outputs symbolic labels (grid_level), not numeric ranges
3. **Type Safety**: Pydantic ensures all specs are valid before use
4. **Deterministic Defaults**: All numeric grids are predefined, no LLM involvement
5. **Future-Proof**: StressSpec can be extended without breaking existing code

## Integration

This layer is designed to feed into a future orchestrator:

```python
# Future usage pattern
from app.services.bl_stress import parse_stress_prompt
from app.services.bl_orchestrator import run_stress_test

# Parse user request
spec = parse_stress_prompt(
    "Test sensitivity to AAPL view",
    recipe_context=context
)

# Run stress test (orchestrator layer, not yet implemented)
results = run_stress_test(base_recipe, spec)
```

## Error Handling

The parser raises clear errors:

- `ValueError`: Invalid JSON from LLM
- `ValidationError`: StressSpec validation failed (missing required fields)
- `FileNotFoundError`: Prompt file not found

All errors include diagnostic information to help debug issues.

## Metadata Configuration

LLM calls are tracked in `app/services/model_settings/chat_and_record_metadata.py`:

```python
"bl_stress_parser": {
    "parse_stress_request": {
        "service": "bl_stress_parser",
        "operation": "parse_stress_request",
        "model": "gpt-4o",
        "temperature": 0  # Deterministic
    }
}
```

## Example StressSpec Outputs

```json
{
  "stress_type": "view_magnitude",
  "target_label": "AAPL outperforms MSFT",
  "grid_level": "standard",
  "mode": "relative_to_base"
}
```

```json
{
  "stress_type": "factor_amplification",
  "factor": "Momentum",
  "grid_level": "aggressive"
}
```

```json
{
  "stress_type": "regime_template",
  "template_name": "high_uncertainty"
}
```

```json
{
  "stress_type": "view_joint",
  "target_label": "NVDA outperforms META",
  "magnitude_grid_level": "standard",
  "confidence_grid_level": "conservative"
}
```

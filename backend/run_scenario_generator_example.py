#!/usr/bin/env python3
"""
Simple Example Runner for generate_scenarios_from_spec

This script demonstrates how to use generate_scenarios_from_spec with a single
StressSpec and example recipe. No argparse - just clear inputs and outputs.

Usage:
    python run_scenario_generator_example.py
"""

import json
from pathlib import Path
from app.services.bl_stress import (
    StressSpec,
    generate_scenarios_from_spec,
)


def main():
    """
    Main function demonstrating generate_scenarios_from_spec usage.
    """
    backend_dir = Path(__file__).resolve().parent
    bl_stress_dir = backend_dir / "app" / "services" / "bl_stress"
    
    spec_file = bl_stress_dir / "stress_spec_example1_view_magnitude.json"
    recipe_file = bl_stress_dir / "example_recipe.json"
    
    with open(spec_file, 'r', encoding='utf-8') as f:
        spec_data = json.load(f)
    spec = StressSpec(**spec_data)
    
    with open(recipe_file, 'r', encoding='utf-8') as f:
        recipe = json.load(f)
    
    scenarios = generate_scenarios_from_spec(spec, recipe)
    
    output = {
        "inputs": {
            "spec_file": spec_file.name,
            "recipe_file": recipe_file.name,
            "stress_spec": spec_data
        },
        "scenario_count": len(scenarios),
        "scenarios": [scenario.model_dump() for scenario in scenarios]
    }
    
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()

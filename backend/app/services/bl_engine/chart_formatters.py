"""
Chart Formatters Module

Format portfolio data into structures ready for UI consumption.
"""

from typing import Dict, List, Any


def allocation_to_chart(weights: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    Convert portfolio weights to a chart-ready format.
    
    Args:
        weights: Dictionary mapping asset names to portfolio weights
    
    Returns:
        List of dictionaries with 'asset' and 'weight' keys, sorted by weight descending
    """
    chart_data = [
        {"asset": asset, "weight": weight}
        for asset, weight in weights.items()
    ]
    # Sort by weight descending
    chart_data.sort(key=lambda x: x["weight"], reverse=True)
    return chart_data


def allocation_comparison(
    baseline: Dict[str, float],
    stressed: Dict[str, float]
) -> List[Dict[str, Any]]:
    """
    Compare two portfolio allocations side-by-side.
    
    Args:
        baseline: Dictionary of baseline portfolio weights
        stressed: Dictionary of stressed/alternative portfolio weights
    
    Returns:
        List of dictionaries with 'asset', 'baseline', 'stressed', and 'delta' keys
    """
    # Get all unique assets from both portfolios
    all_assets = set(baseline.keys()) | set(stressed.keys())
    
    comparison_data = []
    for asset in sorted(all_assets):
        baseline_weight = baseline.get(asset, 0.0)
        stressed_weight = stressed.get(asset, 0.0)
        delta = stressed_weight - baseline_weight
        
        comparison_data.append({
            "asset": asset,
            "baseline": baseline_weight,
            "stressed": stressed_weight,
            "delta": delta
        })
    
    # Sort by absolute delta descending
    comparison_data.sort(key=lambda x: abs(x["delta"]), reverse=True)
    return comparison_data

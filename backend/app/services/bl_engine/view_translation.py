"""
View Translation Module

Utilities for converting structured views into Black-Litterman matrices (P, Q, omega).
"""

import numpy as np
from typing import List, Dict, Any


def build_P_matrix(views: List[Dict[str, Any]], assets: List[str]) -> np.ndarray:
    """
    Build the pick matrix P from structured views.
    
    Args:
        views: List of view dictionaries with keys:
            - type: "absolute" or "relative"
            - asset_long: Asset name to go long
            - asset_short: Asset name to short (None for absolute views)
            - value: Expected return or outperformance
            - confidence: Confidence level (0-1)
        assets: List of asset names in the portfolio
    
    Returns:
        P matrix (num_views x num_assets) where each row represents a view
    """
    num_views = len(views)
    num_assets = len(assets)
    P = np.zeros((num_views, num_assets))
    
    asset_index = {asset: i for i, asset in enumerate(assets)}
    
    for i, view in enumerate(views):
        if view["type"] == "relative":
            # Relative view: asset_long outperforms asset_short
            long_idx = asset_index[view["asset_long"]]
            short_idx = asset_index[view["asset_short"]]
            P[i, long_idx] = 1.0
            P[i, short_idx] = -1.0
        elif view["type"] == "absolute":
            # Absolute view: single asset expected return
            asset_idx = asset_index[view["asset_long"]]
            P[i, asset_idx] = 1.0
    
    return P


def build_Q_vector(views: List[Dict[str, Any]]) -> np.ndarray:
    """
    Build the expected returns vector Q from structured views.
    
    Args:
        views: List of view dictionaries with keys:
            - value: Expected return or outperformance
    
    Returns:
        Q vector (num_views,) containing expected returns for each view
    """
    Q = np.array([view["value"] for view in views])
    return Q


def build_omega(views: List[Dict[str, Any]]) -> np.ndarray:
    """
    Build the uncertainty matrix omega from view confidences.
    
    Args:
        views: List of view dictionaries with keys:
            - confidence: Confidence level (0-1), higher = more confident
    
    Returns:
        Diagonal omega matrix (num_views x num_views) representing view uncertainties
    """
    num_views = len(views)
    omega = np.zeros((num_views, num_views))
    
    for i, view in enumerate(views):
        # Higher confidence -> lower uncertainty
        # Using a simple inverse relationship: uncertainty = (1 - confidence)
        uncertainty = (1.0 - view["confidence"]) * 0.01
        omega[i, i] = uncertainty
    
    return omega

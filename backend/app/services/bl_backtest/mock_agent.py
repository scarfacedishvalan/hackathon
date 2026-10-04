"""
Placeholder stand-in for the real agentic view-generation + Black-Litterman
pipeline described in AGENTIC_BL_BACKTEST_ARCHITECTURE.md.

Swap ``mock_generate_agent_weights`` for a function with the same signature
that, for real:
    1. computes point-in-time EPS features (eps_features.compute_eps_features);
    2. calls the LangChain view agent (eps_view_agent.generate_views) to get
       a validated ViewBatch;
    3. assembles a BL recipe from those views and calls
       bl_orchestrator.run_black_litterman() to get posterior weights.

Nothing in agent_weigh_algo.py needs to change when that swap happens --
only the ``weight_fn`` passed to ``AgenticViewWeighTarget`` changes.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def mock_generate_agent_weights(
    price_window: pd.DataFrame,
    universe: list[str],
    hypothesis: str,
) -> dict[str, float]:
    """
    Mock agent: returns an equal-weight baseline tilted by a small random
    perturbation, seeded by the as-of date so a given rebalance date always
    produces the same mock output (reproducible, not a real signal).

    Args:
        price_window: Price history for ``universe``, already sliced to
            everything available up to (and including) the current
            rebalance date -- this is the point-in-time boundary the real
            agent's tools must also respect.
        universe: Tickers selected for this rebalance.
        hypothesis: Natural-language research hypothesis (unused by the mock,
            but the real agent will consume it exactly as received here).

    Returns:
        dict mapping ticker -> raw (not necessarily normalised) weight.
    """
    if not universe:
        return {}
    if price_window.empty:
        return {asset: 1.0 / len(universe) for asset in universe}

    # Deterministic per-date seed so re-running the backtest is reproducible.
    as_of = price_window.index[-1]
    seed = int(pd.Timestamp(as_of).strftime("%Y%m%d"))
    rng = np.random.default_rng(seed)

    base = 1.0 / len(universe)
    tilts = rng.uniform(-0.3, 0.3, size=len(universe)) * base
    return {asset: max(base + tilt, 0.0) for asset, tilt in zip(universe, tilts)}

"""
Custom ``bt`` Algo that delegates target-weight selection at each rebalance
to an agent (LLM-driven view generation + Black-Litterman, per
AGENTIC_BL_BACKTEST_ARCHITECTURE.md). See ``mock_agent.py`` for the
placeholder implementation that this class calls today.

Follows the same subclassing pattern as the existing
``app.services.backtest.algo_optimiser.MPTOptimiser``: a ``bt.core.Algo``
that reads ``target.temp["selected"]`` and ``target.universe``, and sets
``target.temp["weights"]`` for the downstream ``Rebalance()`` algo to apply.
"""

from __future__ import annotations

from typing import Callable, Optional

import pandas as pd
from bt.core import Algo

from app.services.bl_backtest.mock_agent import mock_generate_agent_weights

WeightFn = Callable[[pd.DataFrame, list, str], dict]


class AgenticViewWeighTarget(Algo):
    """
    Sets ``target.temp["weights"]`` from an agent-generated view pipeline.

    Args:
        hypothesis: Natural-language research hypothesis passed verbatim to
            the agent on every call (see agent_plan.md section 6).
        weight_fn: ``(price_window, universe, hypothesis) -> {ticker: weight}``.
            Defaults to the mock agent. Swap this for the real pipeline
            (EPS features -> LangChain view agent -> run_black_litterman)
            without changing this class or the Strategy wiring.
        lookback: How much price history before ``target.now`` to hand the
            agent as its point-in-time price window.

    Requires:
        * selected

    Sets:
        * weights
    """

    def __init__(
        self,
        hypothesis: str,
        weight_fn: Optional[WeightFn] = None,
        lookback: pd.DateOffset = pd.DateOffset(months=6),
    ):
        super(AgenticViewWeighTarget, self).__init__()
        self.hypothesis = hypothesis
        self.weight_fn = weight_fn or mock_generate_agent_weights
        self.lookback = lookback

    def __call__(self, target) -> bool:
        selected = target.temp["selected"]

        if len(selected) == 0:
            target.temp["weights"] = {}
            return True

        # target.universe is already date-indexed; slicing to target.now is
        # the point-in-time boundary -- the agent never sees future prices.
        t0 = target.now
        price_window = target.universe.loc[t0 - self.lookback : t0, selected]

        weights = self.weight_fn(price_window, selected, self.hypothesis)

        total = sum(weights.values())
        if total > 0:
            weights = {ticker: w / total for ticker, w in weights.items()}

        target.temp["weights"] = weights
        return True

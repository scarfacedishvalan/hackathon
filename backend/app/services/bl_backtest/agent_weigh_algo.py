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

import math
from numbers import Real
from typing import Callable, Optional

import pandas as pd
from bt.core import Algo

from app.services.bl_backtest.mock_agent import mock_generate_agent_weights

WeightFn = Callable[[pd.DataFrame, list[str], str, pd.Timestamp], dict[str, float]]


class AgenticViewWeighTarget(Algo):
    """
    Sets ``target.temp["weights"]`` from an agent-generated view pipeline.

    Args:
        hypothesis: Natural-language research hypothesis passed verbatim to
            the agent on every call (see agent_plan.md section 6).
        weight_fn: ``(price_window, universe, hypothesis, as_of) -> {ticker: weight}``.
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
        # bt prepends one all-NaN initialization row, not a market observation.
        if (
            not price_window.empty
            and price_window.index[0] == target.universe.index[0]
            and price_window.iloc[0].isna().all()
        ):
            price_window = price_window.iloc[1:]

        weights = self.weight_fn(price_window, selected, self.hypothesis, pd.Timestamp(t0))
        if set(weights) != set(selected):
            raise ValueError("weight_fn must return exactly the selected assets")
        if any(
            isinstance(value, bool) or not isinstance(value, Real)
            or not math.isfinite(value) or value < 0
            for value in weights.values()
        ):
            raise ValueError("weight_fn must return finite, nonnegative numeric weights")

        total = sum(weights.values())
        if not math.isfinite(total) or total <= 0:
            raise ValueError("weight_fn must return a finite, strictly positive total weight")
        weights = {ticker: w / total for ticker, w in weights.items()}

        target.temp["weights"] = weights
        return True

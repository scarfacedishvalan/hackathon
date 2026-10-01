"""
Example: wiring AgenticViewWeighTarget (with the mocked agent) into a real
``bt`` Strategy/Backtest pipeline, using actual price data from this
repo's price_data.db.

Run from backend/:
    python -m app.services.bl_backtest.run_example
"""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[3]  # backend/
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import bt  # noqa: E402

from app.services.price_data.load_data import load_market_data  # noqa: E402
from app.services.bl_backtest.agent_weigh_algo import AgenticViewWeighTarget  # noqa: E402

# Example hypothesis text, per agent_plan.md section 6.
HYPOTHESIS = (
    "Use earnings estimate revisions as the primary signal. Focus on the "
    "direction and magnitude of revisions over the past three months. "
    "Generate positive views for stocks with materially improving earnings "
    "expectations, negative views for materially deteriorating expectations, "
    "and remain neutral when the signal is weak or ambiguous. Be more "
    "confident when revisions are large and consistent across time. Do not "
    "overreact to small one-off revisions."
)

# ETFs in market_data.json have no EPS/earnings concept -- equities only.
_NON_EQUITY_ASSETS = {"BND", "GLD", "VNQ"}


def build_agentic_strategy(universe: list[str], hypothesis: str) -> bt.Strategy:
    """Monthly-rebalanced strategy whose weights come from the (mocked) agent."""
    return bt.Strategy(
        "AgenticBL",
        [
            bt.algos.RunMonthly(),
            bt.algos.SelectThese(universe),
            AgenticViewWeighTarget(hypothesis=hypothesis),
            bt.algos.Rebalance(),
        ],
    )


def build_equal_weight_strategy(universe: list[str]) -> bt.Strategy:
    """Baseline: same rebalance cadence and universe, naive equal weighting."""
    return bt.Strategy(
        "EqualWeight",
        [
            bt.algos.RunMonthly(),
            bt.algos.SelectThese(universe),
            bt.algos.WeighEqually(),
            bt.algos.Rebalance(),
        ],
    )


def main() -> None:
    price_df, _market_caps, _B, _factor_names, all_assets = load_market_data()
    universe = [a for a in all_assets if a not in _NON_EQUITY_ASSETS]

    agentic_bt = bt.Backtest(build_agentic_strategy(universe, HYPOTHESIS), price_df[universe])
    equal_weight_bt = bt.Backtest(build_equal_weight_strategy(universe), price_df[universe])

    result = bt.run(agentic_bt, equal_weight_bt)

    print(result.display())
    print("\n=== Stats ===")
    print(result.stats)


if __name__ == "__main__":
    main()

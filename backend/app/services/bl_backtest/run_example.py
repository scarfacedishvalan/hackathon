"""
Examples using the existing bt engine: default mock backtest, research-only,
and explicitly selected hypothesis-driven research-strength backtest.

Run from backend/:
    python -m app.services.bl_backtest.run_example
    python -m app.services.bl_backtest.run_example --research-only
    python -m app.services.bl_backtest.run_example --research-backtest
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

_BACKEND_DIR = Path(__file__).resolve().parents[3]  # backend/
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

if TYPE_CHECKING:
    import bt
    from app.services.bl_backtest.agent_weigh_algo import WeightFn

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


def build_agentic_strategy(
    universe: list[str], hypothesis: str, *, weight_fn: WeightFn | None = None,
    name: str = "AgenticBL",
) -> bt.Strategy:
    """Monthly rebalances; default mock is retained unless a callback is injected."""
    import bt
    from app.services.bl_backtest.agent_weigh_algo import AgenticViewWeighTarget

    return bt.Strategy(
        name,
        [
            bt.algos.RunMonthly(),
            bt.algos.SelectThese(universe),
            AgenticViewWeighTarget(hypothesis=hypothesis, weight_fn=weight_fn),
            bt.algos.Rebalance(),
        ],
    )


def build_equal_weight_strategy(universe: list[str]) -> bt.Strategy:
    """Baseline: same rebalance cadence and universe, naive equal weighting."""
    import bt

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
    parser = argparse.ArgumentParser(description="Mock backtest or one-shot hypothesis research")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--research-only", action="store_true")
    modes.add_argument("--research-backtest", action="store_true")
    parser.add_argument("--hypothesis", default=HYPOTHESIS)
    parser.add_argument("--universe", nargs="+")
    parser.add_argument("--as-of")
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    args = parser.parse_args()

    if args.research_only or args.research_backtest:
        from dotenv import load_dotenv
        from app.services.bl_backtest.data_interface.load import load_research_data
        from app.services.bl_backtest.data_interface.process import prepare_context
        from app.services.bl_backtest.schema import ResearchRequest

        load_dotenv(_BACKEND_DIR / ".env")
        load_dotenv(_BACKEND_DIR.parent / ".env")
        data = load_research_data()
        universe = args.universe or [
            asset for asset in data.metadata["all_assets"] if asset not in _NON_EQUITY_ASSETS
        ]
        request = ResearchRequest(hypothesis=args.hypothesis, universe=universe, as_of=args.as_of)
        if args.research_only:
            from app.services.bl_backtest.research_graph import run_research

            result = run_research(prepare_context(data, request))
            print(result.model_dump_json(indent=2))
            return
        if args.as_of:
            parser.error("--as-of is for --research-only; use --start-date/--end-date for a backtest")
        import bt
        import pandas as pd
        from app.services.bl_backtest.research_weights import make_research_weight_fn

        context = prepare_context(data, request)
        start = pd.Timestamp(args.start_date) if args.start_date else data.prices.index[0]
        end = pd.Timestamp(args.end_date) if args.end_date else data.prices.index[-1]
        if pd.isna(start) or pd.isna(end) or start.tzinfo or end.tzinfo:
            raise ValueError("backtest dates require valid timezone-naive timestamps")
        if not data.prices.index[0] <= start <= end <= data.prices.index[-1]:
            raise ValueError("backtest dates must be ordered and inside evidence coverage")
        prices = data.prices.loc[start:end, universe]
        if prices.empty:
            raise ValueError("backtest date range has no observations")
        records = []
        weight_fn = make_research_weight_fn(data=data, records=records)
        agentic_bt = bt.Backtest(
            build_agentic_strategy(universe, args.hypothesis, weight_fn=weight_fn, name="AgenticResearch"),
            prices,
        )
        baseline = bt.Backtest(build_equal_weight_strategy(universe), prices)
        print("Research-strength tilts, NOT Black-Litterman. Live model calls at eligible rebalances.")
        print("\n".join(context.warnings))
        result = bt.run(agentic_bt, baseline)
        print(result.stats)
        print(json.dumps([record.model_dump(mode="json") for record in records], indent=2))
        return

    import bt
    from app.services.price_data.load_data import load_market_data

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

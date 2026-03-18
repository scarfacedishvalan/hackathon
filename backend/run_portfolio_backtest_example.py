"""Example: thesis-driven equal-weight portfolio backtest.

Parses a natural-language strategy description into a recipe, then runs
``run_portfolio_recipe`` using the thesis universe directly.

Usage:
    python backend/run_portfolio_backtest_example.py

Requires the backend venv to be active and the SQLite DB to be populated.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure ``app.*`` imports resolve regardless of CWD.
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))


def run_example() -> None:
    from app.orchestrators.backtest_orchestrator import parse_strategy, run_portfolio_recipe

    # ── 1. Natural-language input ──────────────────────────────────────────
    # The LLM extracts strategy name, params, dates, cash and commission.
    # thesis_name is specified separately — the LLM has no concept of it.
    nl_text = (
        "Run SmaCross with fast=10 and slow=30 "
        "from 2021-01-01 to 2023-12-31 "
        "with $50,000 cash and 0.1% commission."
    )
    thesis_name = "current"   # stem of any file under backend/data/bl_recipes/

    print("── Step 1: Parse natural-language description ─────────────────")
    print(f"Input : {nl_text!r}")
    print(f"Thesis: {thesis_name}")
    print()

    recipe = parse_strategy(nl_text)

    print("Parsed recipe:")
    print(json.dumps(recipe, indent=2, default=str))
    print()

    # ── 2. Extract fields from parsed recipe ──────────────────────────────
    strategy_name   = recipe.get("strategy_name")
    strategy_params = recipe.get("strategy_params")
    data            = recipe.get("data") or {}
    bt_cfg          = recipe.get("backtest") or {}

    start      = data.get("start")
    end        = data.get("end")
    cash       = float(bt_cfg.get("cash") or 10_000.0)
    commission = bt_cfg.get("commission")

    if not strategy_name:
        raise ValueError("LLM parser did not return a strategy_name — check the input text.")

    print("── Step 2: Run portfolio backtest ─────────────────────────────")
    print(f"Strategy : {strategy_name}  params={strategy_params}")
    print(f"Window   : {start} → {end}")
    print(f"Cash     : ${cash:,.0f}   commission: {commission}")
    print()

    result = run_portfolio_recipe(
        thesis_name=thesis_name,
        strategy_name=strategy_name,
        strategy_params=strategy_params,
        start=start,
        end=end,
        cash=cash,
        commission=commission,
    )

    # ── 3. Portfolio summary ───────────────────────────────────────────────
    assets  = result["recipe"]["assets"]
    weights = result["weights"]
    metrics = result["metrics"]

    print("\n── Portfolio ──────────────────────────────────────────────────")
    print(f"Assets : {assets}")
    print(f"Weights: { {a: f'{w:.1%}' for a, w in weights.items()} }")
    print()

    m_rows = [
        ("Total Return",    f"{metrics.get('returnPct', 'N/A'):.2f}%"),
        ("Ann. Return",     f"{metrics.get('annualReturnPct', 'N/A'):.2f}%"),
        ("Ann. Volatility", f"{metrics.get('annualVolatilityPct', 'N/A'):.2f}%"),
        ("Sharpe Ratio",    f"{metrics.get('sharpeRatio', 'N/A'):.4f}"),
        ("Max Drawdown",    f"{metrics.get('maxDrawdownPct', 'N/A'):.2f}%"),
        ("Equity Final",    f"${metrics.get('equityFinal', 0):,.2f}"),
        ("Equity Peak",     f"${metrics.get('equityPeak',  0):,.2f}"),
        ("Start",           metrics.get("start", "N/A")),
        ("End",             metrics.get("end",   "N/A")),
    ]
    col = max(len(k) for k, _ in m_rows) + 2
    for label, value in m_rows:
        print(f"  {label:<{col}}{value}")

    # ── 4. Per-asset trade counts ──────────────────────────────────────────
    print("\n── Per-asset trades ───────────────────────────────────────────")
    for asset in assets:
        n_trades = len(result["trades"].get(asset, []))
        n_points = len(result["assetCurves"].get(asset, []))
        print(f"  {asset:<8} {n_trades:>4} trades   {n_points} equity points")

    # ── 5. Equity curve sample ─────────────────────────────────────────────
    ec = result["equityCurve"]
    if ec:
        print(f"\n── Portfolio equity curve ({len(ec)} points) ─────────────────")
        sample = ec[:5] + (["..."] if len(ec) > 10 else []) + ec[-5:]
        for pt in sample:
            if isinstance(pt, dict):
                print(f"  {pt['date']}  ${pt['equity']:>12,.2f}")
            else:
                print(f"  {pt}")

    # ── 6. Write full result to JSON ───────────────────────────────────────
    out_path = BACKEND_DIR / "portfolio_backtest_result.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\nFull result written to: {out_path}")


if __name__ == "__main__":
    run_example()


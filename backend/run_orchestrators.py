from pathlib import Path
import sys
import json

from app.orchestrators.view_orchestrator import parse_view, load_recipe
from app.orchestrators.bl_orchestrator import run_black_litterman
from app.orchestrators.news_orchestrator import fetch_and_parse, load_news, add_view_to_recipe
from app.services.price_data.load_data import load_market_data

_CURRENT_RECIPE_PATH = Path(__file__).resolve().parent / "data" / "bl_recipes" / "current.json"


def load_current_recipe() -> dict:
    """Load the recipe from data/bl_recipes/current.json."""
    if not _CURRENT_RECIPE_PATH.exists():
        raise FileNotFoundError(
            f"current.json not found at {_CURRENT_RECIPE_PATH}. "
            "Run a view parse first or create the file manually."
        )
    return load_recipe("current")

# ---------------------------------------------------------------------------
# Agent orchestrator example
# ---------------------------------------------------------------------------


def run_agent_example(
    thesis_name: str = "current",
    goal: str = (
        "Stress-test all views by varying confidence from 0.2 to 0.9 and "
        "analyse the allocation for a moderate-risk investor with max 25% per position."
    ),
    max_steps: int = 8,
):
    """Run the agentic BL orchestrator on a named recipe."""
    from app.orchestrators.bl_agent_orchestrator import run_agent, list_audits

    print("\n" + "=" * 60)
    print("BL AGENT ORCHESTRATOR")
    print("=" * 60)
    print(f"Thesis : {thesis_name}")
    print(f"Goal   : {goal}")
    print(f"Max steps: {max_steps}")
    print("-" * 60)

    audit = run_agent(thesis_name=thesis_name, goal=goal, max_steps=max_steps)

    print(f"Audit ID      : {audit['audit_id']}")
    print(f"Tool calls    : {len(audit['steps'])}")
    print(f"LLM iterations: {audit.get('cost_breakdown', {}).get('steps', '?')}")

    cost = audit.get("cost_breakdown", {})
    print(f"Total cost: ${cost.get('total_cost_usd', 0):.4f} USD")
    print(f"Total tokens: {cost.get('total_tokens', 0):,}")

    print("\n" + "-" * 60)
    print("STEP LOG")
    for s in audit["steps"]:
        tool = s.get("tool", s.get("type", "?"))
        args_preview = ""
        if "args" in s:
            args_preview = " | label=" + s["args"].get("label", "")
        print(f"  step {s['step']:2d}: {tool}{args_preview}")

    print("\n" + "-" * 60)
    print("SYNTHESIS")
    synthesis = audit.get("synthesis", {})
    print(synthesis.get("narrative", "(none)"))

    if synthesis.get("risk_flags"):
        print("\nRisk flags:")
        for flag in synthesis["risk_flags"]:
            print(f"  - {flag}")

    if audit.get("weight_delta_vs_base"):
        print("\nWeight delta vs base:")
        for asset, delta in sorted(
            audit["weight_delta_vs_base"].items(), key=lambda x: abs(x[1]), reverse=True
        ):
            if abs(delta) > 0.0001:
                print(f"  {asset:6s}  {delta:+.2%}")

    print("\n" + "-" * 60)
    print("Recent audits:")
    for row in list_audits(limit=5):
        print(
            f"  {row['audit_id'][:8]}...  "
            f"{row['thesis_name']:12s}  "
            f"{row['first_timestamp'][:19]}  "
            f"steps={row['steps']}  "
            f"${row['total_cost_usd']:.4f}"
        )

    print("=" * 60)
    return audit


# ---------------------------------------------------------------------------
# News API example
# ---------------------------------------------------------------------------


def run_news_example():
    TICKERS = ["AAPL", "MSFT", "JPM"]
    KEYWORDS = ["interest rates", "earnings beat", "analyst upgrade"]
    LIMIT = 3  # articles per ticker

    print("\n" + "=" * 60)
    print("NEWS ORCHESTRATOR EXAMPLE  (simulated LLM articles)")
    print("=" * 60)

    # ── Step 1: generate & parse articles into news.json ──────────────────
    print(f"\nGenerating up to {LIMIT} articles each for: {', '.join(TICKERS)}")
    print(f"Keywords: {', '.join(KEYWORDS)}")
    print("(Skips articles already cached in data/news.json)")
    items = fetch_and_parse(tickers=TICKERS, limit_per_ticker=LIMIT, keywords=KEYWORDS)
    print(f"\nTotal items in news.json after generation: {len(items)}")

    if not items:
        print("No news items returned — check your OPENAI_API_KEY and model availability.")
        return

    # ── Step 2: display the first few items ────────────────────────────────
    print("\nLatest news items (first 5):")
    print("-" * 60)
    for item in items[:5]:
        print(f"  [{item['ticker']}]  {item['heading'][:70]}")
        print(f"           → {item['translatedView']}")
        print()

    # ── Step 3: add the first item's view to current.json ──────────────────
    first_id = items[0]["id"]
    print(f"Adding view for item id='{first_id}' to current.json ...")
    try:
        result = add_view_to_recipe(first_id)
        bottom_up = result.get("bottom_up_views", [])
        factor_shocks = result.get("top_down_views", {}).get("factor_shocks", [])
        print(f"  → {len(bottom_up)} bottom-up view(s), {len(factor_shocks)} factor shock(s) appended")
        if bottom_up:
            print(f"     bottom-up: {json.dumps(bottom_up[0], indent=6)}")
        if factor_shocks:
            print(f"     top-down:  {json.dumps(factor_shocks[0], indent=6)}")
    except Exception as exc:
        print(f"  ERROR adding view: {exc}")

    print("=" * 60)


# ---------------------------------------------------------------------------
# View parsing example
# ---------------------------------------------------------------------------

def run_view_parsing_example():
    SAMPLE_TEXTS = [
        # "Apple will strongly outperform Google by 5% next quarter.",
        # "I'm bearish on Tesla, expecting a 4% decline. Rising interest rates are a concern.",
        # "Microsoft looks neutral; no strong view.",
        "Technology sector will outperform by 4%. AI adoption driving growth across the sector."
    ]

    for sample in SAMPLE_TEXTS:
        print(f"\n{'=' * 60}")
        print(f"Input : {sample}")
        print("-" * 60)
        try:
            views = parse_view(sample)  # uses DEFAULT_ASSETS / DEFAULT_FACTORS
            if views:
                for i, view in enumerate(views, 1):
                    print(f"  View {i}: {json.dumps(view, indent=4)}")
            else:
                print("  (no views extracted)")
        except Exception as exc:
            print(f"  ERROR: {exc}")

    print(f"\n{'=' * 60}")


# ---------------------------------------------------------------------------
# BL orchestrator example
# ---------------------------------------------------------------------------


def run_bl_example():
    print("\n" + "=" * 60)
    print("BL ORCHESTRATOR EXAMPLE")
    print("=" * 60)

    recipe = load_current_recipe()
    print(f"Loaded recipe: {recipe.get('meta', {}).get('name', 'current.json')}")

    # Load price data (metadata loaded internally by orchestrator)
    price_df, _caps, _B, _factor_names, _assets = load_market_data()

    results = run_black_litterman(recipe, price_df)

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Recipe : {results['recipe_name']}")
    print(
        f"Views  : {results['n_bottom_up_views']} bottom-up + "
        f"{results['n_top_down_views']} top-down"
    )
    print("\nOptimal weights:")
    for asset, weight in sorted(results["weights"].items(), key=lambda x: -x[1]):
        if abs(weight) > 0.001:
            print(f"  {asset:6s}  {weight:7.2%}")

    print("\nPosterior vs prior returns:")
    print(f"  {'Asset':6s}  {'Posterior':>10s}  {'Prior':>8s}  {'Δ':>8s}")
    for asset in results["universe"]:
        post = results["posterior_returns"].get(asset, 0.0)
        prior = results["prior_returns"].get(asset, 0.0)
        print(f"  {asset:6s}  {post:10.2%}  {prior:8.2%}  {post - prior:+8.2%}")

    print("=" * 60)


# ---------------------------------------------------------------------------
# Admin Console example
# ---------------------------------------------------------------------------


def run_admin_console_example():
    """Print a summary of LLM usage and agent costs from the tracking databases."""
    from app.orchestrators.admin_console_orchestrator import get_admin_console_data

    print("\n" + "=" * 60)
    print("ADMIN CONSOLE — TOKEN BUDGET & COST SUMMARY")
    print("=" * 60)

    data = get_admin_console_data(llm_recent_limit=10, agent_recent_limit=20)

    print(f"\n  Grand total spend : ${data['grand_total_cost_usd']:.6f} USD")

    # ── LLM Usage ────────────────────────────────────────────────────────────
    llm = data["llm_usage"]
    s   = llm["summary"]
    print("\n" + "-" * 60)
    print("LLM CALLS  (chat_and_record / llm_usage.db)")
    print("-" * 60)
    print(f"  Total calls     : {s['total_calls']}  "
          f"(ok={s['successful_calls']}  fail={s['failed_calls']})")
    print(f"  Prompt tokens   : {s['total_prompt_tokens']:,}")
    print(f"  Completion tkns : {s['total_completion_tokens']:,}")
    print(f"  Total tokens    : {s['total_tokens']:,}")
    print(f"  Total cost      : ${s['total_cost_usd']:.6f} USD")
    print(f"  Avg latency     : {s['avg_latency_ms']:.0f} ms")

    if llm["by_service"]:
        print("\n  By service / operation:")
        print(f"  {'Service':<30}  {'Op':<22}  {'Calls':>5}  {'Tokens':>8}  {'Cost':>10}  {'OK%':>6}")
        print("  " + "-" * 86)
        for row in llm["by_service"]:
            print(
                f"  {row['service']:<30}  {row['operation']:<22}  "
                f"{row['calls']:>5}  {row['total_tokens']:>8,}  "
                f"${row['cost_usd']:>9.6f}  {row['success_rate']*100:>5.1f}%"
            )

    if llm["by_model"]:
        print("\n  By model:")
        print(f"  {'Model':<25}  {'Calls':>5}  {'Tokens':>9}  {'Cost':>10}")
        print("  " + "-" * 56)
        for row in llm["by_model"]:
            print(
                f"  {row['model']:<25}  {row['calls']:>5}  "
                f"{row['total_tokens']:>9,}  ${row['cost_usd']:>9.6f}"
            )

    if llm["recent_calls"]:
        print(f"\n  Most recent {len(llm['recent_calls'])} calls:")
        print(f"  {'Timestamp':<20}  {'Service':<25}  {'Model':<18}  {'Tokens':>7}  {'Cost':>10}  {'OK'}")
        print("  " + "-" * 94)
        for c in llm["recent_calls"]:
            ok = "✓" if c["success"] else "✗"
            print(
                f"  {c['timestamp'][:19]:<20}  {c['service']:<25}  {c['model']:<18}  "
                f"{c['total_tokens']:>7,}  ${c['cost_usd']:>9.6f}  {ok}"
            )

    # ── Agent Costs ──────────────────────────────────────────────────────────
    ag = data["agent_usage"]
    s  = ag["summary"]
    print("\n" + "-" * 60)
    print("AGENT RUNS  (chat_with_history / agent_costs.db)")
    print("-" * 60)
    print(f"  Total runs      : {s['total_runs']}")
    print(f"  Total steps     : {s['total_steps']}  (avg {s['avg_steps_per_run']:.1f} / run)")
    print(f"  Total tokens    : {s['total_tokens']:,}")
    print(f"  Total cost      : ${s['total_cost_usd']:.6f} USD  "
          f"(avg ${s['avg_cost_per_run']:.6f} / run)")

    if ag["by_run"]:
        print("\n  By agent run:")
        print(f"  {'Audit ID':<10}  {'Thesis':<14}  {'Steps':>5}  {'Tokens':>8}  {'Cost':>10}  {'Timestamp':<19}  Goal")
        print("  " + "-" * 110)
        for row in ag["by_run"]:
            goal_preview = (row["goal"][:35] + "…") if len(row["goal"]) > 35 else row["goal"]
            print(
                f"  {row['audit_id'][:8]:<10}  {row['thesis_name']:<14}  "
                f"{row['steps']:>5}  {row['total_tokens']:>8,}  "
                f"${row['cost_usd']:>9.6f}  {row['run_timestamp'][:19]:<19}  {goal_preview}"
            )

    if ag["by_tool"]:
        print("\n  By tool:")
        print(f"  {'Tool':<35}  {'Calls':>5}  {'Tokens':>8}  {'Cost':>10}  Avg latency")
        print("  " + "-" * 72)
        for row in ag["by_tool"]:
            print(
                f"  {row['tool_called']:<35}  {row['calls']:>5}  "
                f"{row['total_tokens']:>8,}  ${row['cost_usd']:>9.6f}  "
                f"{row['avg_latency_ms']:.0f} ms"
            )

    print("=" * 60)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Allow running this module directly.
    # Inserts backend/ into sys.path so that `app.*` imports resolve correctly.

    import argparse

    parser = argparse.ArgumentParser(description="Run orchestrator examples")
    parser.add_argument(
        "--example",
        choices=["views", "bl", "news", "agent", "admin", "all"],
        default="admin",
        help="Which example to run (default: agent)",
    )
    # parser.add_argument(
    #     "--thesis",
    #     default="current",
    #     help="Recipe name for the agent example (default: current)",
    # )
    # parser.add_argument(
    #     "--goal",
    #     default=(
    #         "Stress-test all views by varying confidence and find an allocation "
    #         "for a moderate-risk investor with max 25% per position."
    #     ),
    #     help="Goal text for the agent example",
    # )
    args = parser.parse_args()

    if args.example in ("views", "all"):
        run_view_parsing_example()

    if args.example in ("bl", "all"):
        run_bl_example()

    if args.example in ("news", "all"):
        run_news_example()

    if args.example in ("agent", "all"):
        run_agent_example(thesis_name=args.thesis, goal=args.goal)

    if args.example in ("admin", "all"):
        run_admin_console_example()
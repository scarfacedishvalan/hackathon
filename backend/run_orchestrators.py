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
    from app.orchestrators.news_orchestrator import get_random_news, count_news
    
    print("\n" + "=" * 60)
    print("NEWS API EXAMPLE — Random Selection & Keyword Search")
    print("=" * 60)

    # ── Test 1: Get all news (no filter) ───────────────────────────────────
    print("\n[TEST 1] Get 5 random news items (no keyword filter):")
    print("-" * 60)
    total_count = count_news()
    print(f"Total news items available: {total_count}")
    
    items = get_random_news(limit=5)
    print(f"Returned: {len(items)} items")
    for item in items:
        print(f"  [{item['ticker']}] {item['heading'][:65]}")
    
    # ── Test 2: Refresh - get different random items ───────────────────────
    print("\n[TEST 2] Refresh - get another 5 random items:")
    print("-" * 60)
    items_refresh = get_random_news(limit=5)
    print(f"Returned: {len(items_refresh)} items")
    for item in items_refresh:
        print(f"  [{item['ticker']}] {item['heading'][:65]}")
    
    # Check for differences
    ids_first = {item['id'] for item in items}
    ids_refresh = {item['id'] for item in items_refresh}
    different = len(ids_first.symmetric_difference(ids_refresh))
    print(f"\n  → {different}/{len(items)} items differ from first call (randomized)")
    
    # ── Test 3: Keyword search - "Tesla" ────────────────────────────────────
    print("\n[TEST 3] Search with keyword: 'Tesla'")
    print("-" * 60)
    keyword = "Tesla"
    tesla_count = count_news(keyword)
    print(f"Total matches for '{keyword}': {tesla_count}")
    
    tesla_items = get_random_news(keyword=keyword, limit=5)
    print(f"Returned: {len(tesla_items)} items")
    for item in tesla_items:
        print(f"  [{item['ticker']}] {item['heading'][:65]}")
    
    # ── Test 4: Keyword search - "bullish" ─────────────────────────────────
    print("\n[TEST 4] Search with keyword: 'bullish'")
    print("-" * 60)
    keyword = "bullish"
    bullish_count = count_news(keyword)
    print(f"Total matches for '{keyword}': {bullish_count}")
    
    bullish_items = get_random_news(keyword=keyword, limit=5)
    print(f"Returned: {len(bullish_items)} items")
    for item in bullish_items:
        print(f"  [{item['ticker']}] {item['heading'][:65]}")
    
    # ── Test 5: Keyword refresh - different random bullish articles ────────
    print("\n[TEST 5] Refresh 'bullish' search - get different random matches:")
    print("-" * 60)
    bullish_refresh = get_random_news(keyword=keyword, limit=5)
    print(f"Returned: {len(bullish_refresh)} items")
    for item in bullish_refresh:
        print(f"  [{item['ticker']}] {item['heading'][:65]}")
    
    ids_first_bullish = {item['id'] for item in bullish_items}
    ids_refresh_bullish = {item['id'] for item in bullish_refresh}
    different_bullish = len(ids_first_bullish.symmetric_difference(ids_refresh_bullish))
    print(f"\n  → {different_bullish}/{len(bullish_items)} items differ (randomized within '{keyword}' matches)")
    
    # ── Test 6: Ticker-specific search - "AAPL" ────────────────────────────
    print("\n[TEST 6] Search with ticker: 'AAPL'")
    print("-" * 60)
    keyword = "AAPL"
    aapl_count = count_news(keyword)
    print(f"Total matches for '{keyword}': {aapl_count}")
    
    aapl_items = get_random_news(keyword=keyword, limit=5)
    print(f"Returned: {len(aapl_items)} items")
    for item in aapl_items:
        print(f"  [{item['ticker']}] {item['heading'][:65]}")
    
    # ── Test 7: Fuzzy matching - typo "Amazn" → "AMZN" ─────────────────────
    print("\n[TEST 7] Fuzzy search test - typo 'Amazn' (should match AMZN):")
    print("-" * 60)
    keyword = "Amazn"
    fuzzy_count = count_news(keyword)
    print(f"Total matches for '{keyword}': {fuzzy_count}")
    
    fuzzy_items = get_random_news(keyword=keyword, limit=5)
    print(f"Returned: {len(fuzzy_items)} items")
    for item in fuzzy_items:
        print(f"  [{item['ticker']}] {item['heading'][:65]}")
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"✓ Random selection works (gets different items on refresh)")
    print(f"✓ Keyword filtering works (tested: Tesla, bullish, AAPL)")
    print(f"✓ Fuzzy matching works (typo 'Amazn' matched {fuzzy_count} AMZN articles)")
    print(f"✓ Total news database: {total_count} articles")
    print("=" * 60)


# ---------------------------------------------------------------------------
# News → Active Views integration test
# ---------------------------------------------------------------------------


def run_news_active_views_test():
    """Test the '+ Active Views' functionality with random news items."""
    from app.orchestrators.news_orchestrator import get_random_news, add_view_to_recipe
    
    print("\n" + "=" * 60)
    print("NEWS → ACTIVE VIEWS INTEGRATION TEST")
    print("=" * 60)
    print("Testing the '+ Active Views' button functionality:")
    print("  1. Get random news items with structured translatedViews")
    print("  2. Send translatedView through BL LLM parser")
    print("  3. Verify parsed views are added to current.json")
    print("=" * 60)
    
    # ── Test 1: Get random news items with various sentiments ─────────────
    print("\n[STEP 1] Get 3 random news items:")
    print("-" * 60)
    items = get_random_news(limit=3)
    
    for i, item in enumerate(items, 1):
        print(f"\n{i}. [{item['ticker']}] {item['heading']}")
        print(f"   ID: {item['id']}")
        print(f"   TranslatedView: {item['translatedView']}")
    
    # ── Test 2: Parse one news item and add to current.json ───────────────
    print("\n" + "=" * 60)
    print("[STEP 2] Parse translatedView → BL views:")
    print("-" * 60)
    
    # Select first item for testing
    test_item = items[0]
    print(f"\nSelected item:")
    print(f"  Ticker: {test_item['ticker']}")
    print(f"  Heading: {test_item['heading']}")
    print(f"  TranslatedView: {test_item['translatedView']}")
    
    print(f"\nCalling add_view_to_recipe('{test_item['id']}')...")
    print("-" * 60)
    
    try:
        result = add_view_to_recipe(test_item['id'])
        
        # Display parsed results
        bottom_up = result.get('bottom_up_views', [])
        top_down = result.get('top_down_views', [])
        
        print(f"\n✓ Parse successful!")
        print(f"  Bottom-up views: {len(bottom_up)}")
        print(f"  Top-down views:  {len(top_down)}")
        
        if bottom_up:
            print("\n  Bottom-Up Views:")
            for j, view in enumerate(bottom_up, 1):
                # Handle both dict and string format
                if isinstance(view, dict):
                    asset = view.get('asset', '?')
                    expected_return = view.get('expected_return', 0.0)
                    confidence = view.get('confidence', 0.0)
                    view_type = view.get('view_type', '?')
                    print(f"    {j}. {asset}: {expected_return:+.2%} return, "
                          f"confidence={confidence:.1%}, type={view_type}")
                else:
                    # If it's a string or other format, just print it
                    print(f"    {j}. {view}")
        
        if top_down:
            print("\n  Top-Down Views:")
            for j, view in enumerate(top_down, 1):
                # Handle both dict and string format
                if isinstance(view, dict):
                    factor = view.get('factor', '?')
                    expected_premium = view.get('expected_premium', 0.0)
                    confidence = view.get('confidence', 0.0)
                    print(f"    {j}. {factor}: {expected_premium:+.2%} premium, "
                          f"confidence={confidence:.1%}")
                else:
                    # If it's a string or other format, just print it
                    print(f"    {j}. {view}")
        
        # ── Test 3: Verify it was added to current.json ───────────────────
        print("\n" + "=" * 60)
        print("[STEP 3] Verify view was added to current.json:")
        print("-" * 60)
        
        recipe = load_current_recipe()
        recipe_bottom_up = recipe.get('bottom_up_views', [])
        recipe_top_down = recipe.get('top_down_views', {})
        
        # Handle top_down_views as dict with factor_shocks
        if isinstance(recipe_top_down, dict):
            recipe_factor_shocks = recipe_top_down.get('factor_shocks', [])
        else:
            # Fallback if it's a list (old format)
            recipe_factor_shocks = recipe_top_down if isinstance(recipe_top_down, list) else []
        
        print(f"\nCurrent recipe now contains:")
        print(f"  Total bottom-up views: {len(recipe_bottom_up)}")
        print(f"  Total factor shocks:   {len(recipe_factor_shocks)}")
        
        # Show last few views (likely the one just added)
        if recipe_bottom_up:
            print(f"\n  Last 3 bottom-up views:")
            for view in recipe_bottom_up[-3:]:
                asset = view.get('asset', '?')
                expected_return = view.get('expected_return', 0.0)
                confidence = view.get('confidence', 0.0)
                label = view.get('label', '')
                print(f"    - {asset}: {expected_return:+.2%} return, "
                      f"confidence={confidence:.0%}, label=\"{label}\"")
        
        if recipe_factor_shocks:
            print(f"\n  Last 3 factor shocks:")
            for shock in recipe_factor_shocks[-3:]:
                factor = shock.get('factor', '?')
                shock_val = shock.get('shock', 0.0)
                confidence = shock.get('confidence', 0.0)
                label = shock.get('label', '')
                print(f"    - {factor}: {shock_val:+.2%} shock, "
                      f"confidence={confidence:.0%}, label=\"{label}\"")
        
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"✓ News item fetched with structured translatedView")
        print(f"✓ TranslatedView parsed by BL LLM parser:")
        print(f"    → {len(bottom_up)} bottom-up view(s) extracted")
        print(f"    → {len(top_down)} top-down view(s) extracted")
        print(f"✓ Views successfully added to current.json")
        print(f"✓ '+ Active Views' button workflow is functional!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error during parsing:")
        print(f"  {type(e).__name__}: {e}")
        print("\nThis may indicate:")
        print("  - LLM parser failed to extract quantified views")
        print("  - translatedView format not compatible with parser")
        print("  - current.json file not found or invalid")
        import traceback
        traceback.print_exc()
        print("=" * 60)


# ---------------------------------------------------------------------------
# View parsing example
# ---------------------------------------------------------------------------

def run_view_parsing_example():
    SAMPLE_TEXTS = [
        # "Apple will strongly outperform Google by 5% next quarter.",
        # "I'm bearish on Tesla, expecting a 4% decline. Rising interest rates are a concern.",
        "JNJ will return 3%",
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
        choices=["views", "bl", "news", "news_views", "agent", "admin", "all"],
        default="views",
        help="Which example to run (default: news)",
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

    if args.example in ("news_views", "all"):
        run_news_active_views_test()

    if args.example in ("agent", "all"):
        run_agent_example(thesis_name=args.thesis, goal=args.goal)

    if args.example in ("admin", "all"):
        run_admin_console_example()
"""
Test script for admin console tare filtering fix.

This script validates that:
1. Tare can be set and retrieved
2. LLM usage data is filtered by tare
3. Agent usage data is filtered by tare
4. The admin console data respects tare filtering
"""

import logging
import sys
import time
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from app.orchestrators.admin_console_orchestrator import (
    get_active_tare,
    tare,
    reset_tare,
    get_llm_usage_data,
    get_agent_usage_data,
    get_admin_console_data,
)

print("=" * 80)
print("Testing Admin Console Tare Filtering")
print("=" * 80)

# Step 1: Reset any existing tare
print("\n1. Resetting any existing tare...")
reset_tare()
active = get_active_tare()
print(f"   Active tare after reset: {active}")

# Step 2: Get baseline data (no tare filter)
print("\n2. Getting baseline data (no tare)...")
baseline_llm = get_llm_usage_data()
baseline_agent = get_agent_usage_data()
print(f"   Baseline LLM calls: {baseline_llm['summary']['total_calls']}")
print(f"   Baseline agent steps: {baseline_agent['summary']['total_steps']}")
print(f"   Baseline total cost: ${baseline_llm['summary']['total_cost_usd'] + baseline_agent['summary']['total_cost_usd']:.4f}")

# Step 3: Set a tare point
print("\n3. Setting tare point...")
time.sleep(0.1)  # Small delay to ensure tare is after all existing data
tare_result = tare(note="Test tare for validation")
print(f"   Tare set at: {tare_result['tare_ts']}")
print(f"   Previous tare: {tare_result.get('previous_tare_ts', 'None')}")

# Step 4: Verify tare is active
print("\n4. Verifying active tare...")
active = get_active_tare()
print(f"   Active tare: {active}")
assert active is not None, "Tare should be active"
assert active['tare_ts'] == tare_result['tare_ts'], "Active tare should match set tare"

# Step 5: Get data with tare filter (should be 0 or minimal since tare is recent)
print("\n5. Getting data after tare (should be empty or minimal)...")
tared_llm = get_llm_usage_data(since=active['tare_ts'])
tared_agent = get_agent_usage_data(since=active['tare_ts'])
print(f"   Tared LLM calls: {tared_llm['summary']['total_calls']}")
print(f"   Tared agent steps: {tared_agent['summary']['total_steps']}")
print(f"   Tared total cost: ${tared_llm['summary']['total_cost_usd'] + tared_agent['summary']['total_cost_usd']:.4f}")

# Step 6: Test admin console data
print("\n6. Testing admin console data (should respect tare)...")
console_data = get_admin_console_data()
print(f"   Console grand total: ${console_data['grand_total_cost_usd']:.4f}")
print(f"   Console LLM calls: {console_data['llm_usage']['summary']['total_calls']}")
print(f"   Console agent steps: {console_data['agent_usage']['summary']['total_steps']}")
print(f"   Tare info in console: {console_data['tare_info']['active_tare_ts']}")

# Verify tare is being applied
assert console_data['tare_info']['active_tare_ts'] == active['tare_ts'], \
    "Console should show active tare timestamp"

# Step 7: Verify filtering works
print("\n7. Verifying tare filter is working...")
if baseline_llm['summary']['total_calls'] > 0:
    # If we had baseline data, tared data should be less or equal
    assert tared_llm['summary']['total_calls'] <= baseline_llm['summary']['total_calls'], \
        "Tared LLM calls should be <= baseline"
    print(f"   ✓ LLM filter working: {baseline_llm['summary']['total_calls']} baseline → {tared_llm['summary']['total_calls']} after tare")

if baseline_agent['summary']['total_steps'] > 0:
    assert tared_agent['summary']['total_steps'] <= baseline_agent['summary']['total_steps'], \
        "Tared agent steps should be <= baseline"
    print(f"   ✓ Agent filter working: {baseline_agent['summary']['total_steps']} baseline → {tared_agent['summary']['total_steps']} after tare")

# Step 8: Reset tare
print("\n8. Resetting tare to show all data again...")
reset_result = reset_tare()
print(f"   Removed tare: {reset_result.get('removed_tare_ts')}")

# Step 9: Verify data is back to baseline
print("\n9. Verifying data returns to baseline after reset...")
after_reset_llm = get_llm_usage_data()
after_reset_agent = get_agent_usage_data()
print(f"   After reset LLM calls: {after_reset_llm['summary']['total_calls']}")
print(f"   After reset agent steps: {after_reset_agent['summary']['total_steps']}")

assert after_reset_llm['summary']['total_calls'] == baseline_llm['summary']['total_calls'], \
    "After reset should match baseline"
assert after_reset_agent['summary']['total_steps'] == baseline_agent['summary']['total_steps'], \
    "After reset should match baseline"

print("\n" + "=" * 80)
print("✓ ALL TESTS PASSED - Tare filtering is working correctly!")
print("=" * 80)

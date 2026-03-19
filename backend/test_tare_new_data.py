"""
Test that NEW data created AFTER a tare shows up correctly.
"""

import logging
import sys
import time
from pathlib import Path

backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

from datetime import datetime
from app.orchestrators.admin_console_orchestrator import (
    get_active_tare,
    tare,
    reset_tare,
    get_admin_console_data,
)
from app.services.llm_client.utils import chat_and_record, OpenAIClientWrapper
import os

print("=" * 80)
print("Testing that NEW data after tare IS visible")
print("=" * 80)

# Reset tare
print("\n1. Resetting tare...")
reset_tare()

# Get baseline
print("\n2. Getting baseline...")
baseline = get_admin_console_data()
baseline_calls = baseline['llm_usage']['summary']['total_calls']
print(f"   Baseline calls: {baseline_calls}")

# Set tare
print("\n3. Setting tare NOW...")
tare_result = tare(note="Test - data after tare should be visible")
tare_ts = tare_result['tare_ts']
print(f"   Tare timestamp: {tare_ts}")
time.sleep(0.5)  # Small delay

# Check data immediately after tare (should be 0)
print("\n4. Checking data immediately after tare (should be 0)...")
after_tare = get_admin_console_data()
after_tare_calls = after_tare['llm_usage']['summary']['total_calls']
print(f"   Calls after tare: {after_tare_calls}")
assert after_tare_calls <= 1, f"Expected 0-1 calls but got {after_tare_calls}"

# Create NEW data AFTER the tare
print("\n5. Creating NEW LLM call AFTER tare...")
if not os.getenv("OPENAI_API_KEY"):
    print("   WARNING: No OPENAI_API_KEY set, using mock data")
    # Manually insert a record
    from app.services.llm_client.tracker import LLMUsageTracker, LLMCallRecord
    import uuid
    tracker = LLMUsageTracker(db_path=Path(__file__).parent.parent / "data" / "llm_usage.db")
    record = LLMCallRecord(
        call_id=str(uuid.uuid4()),
        timestamp=datetime.now(),  # This is AFTER the tare
        service="test_after_tare",
        operation="verify_visibility",
        model="gpt-4o-mini",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        input_length=100,
        output_length=50,
        temperature=0.7,
        max_tokens=100,
        success=True,
        latency_ms=500,
        cost_usd=0.001,
    )
    tracker.record_call(record)
    print(f"   Mock call created at: {record.timestamp.isoformat()}")
    print(f"   Tare was at:          {tare_ts}")
    print(f"   New data is AFTER?    {record.timestamp.isoformat() > tare_ts}")
else:
    try:
        client = OpenAIClientWrapper()
        response = chat_and_record(
            system_prompt="You are a test assistant.",
            user_prompt="Say 'test' and nothing else.",
            service="test_after_tare",
            operation="verify_visibility",
            llm_client=client,
        )
        print(f"   ✓ Test LLM call made successfully")
    except Exception as e:
        print(f"   Failed to make test call: {e}")

# Check data again (should now show the new call)
print("\n6. Checking data after creating new call...")
final = get_admin_console_data()
final_calls = final['llm_usage']['summary']['total_calls']
final_cost = final['llm_usage']['summary']['total_cost_usd']
print(f"   Calls now: {final_calls}")
print(f"   Cost: ${final_cost:.6f}")
print(f"   Tare info: {final['tare_info']['active_tare_ts']}")

# Verify the new data is visible
if final_calls > after_tare_calls:
    print(f"\n✓ SUCCESS! New data IS visible after tare")
    print(f"  Went from {after_tare_calls} → {final_calls} calls")
else:
    print(f"\n✗ PROBLEM! New data NOT showing up")
    print(f"  Still showing {final_calls} calls (expected > {after_tare_calls})")
    
    # Debug: check raw database
    print("\n  Debugging: Checking raw database...")
    from app.orchestrators.admin_console_orchestrator import LLM_USAGE_DB
    import sqlite3
    conn = sqlite3.connect(LLM_USAGE_DB)
    conn.row_factory = sqlite3.Row
    recent = conn.execute(
        "SELECT timestamp, service, operation FROM llm_calls ORDER BY timestamp DESC LIMIT 3"
    ).fetchall()
    for row in recent:
        ts = row['timestamp']
        print(f"    {ts} | {row['service']} | {row['operation']} | >= tare? {ts >= tare_ts}")
    conn.close()

# Cleanup
print("\n7. Cleaning up (resetting tare)...")
reset_tare()

print("\n" + "=" * 80)

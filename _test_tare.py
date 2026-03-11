import sys
sys.path.insert(0, r"c:\Python\hackathon\backend")

from app.orchestrators.admin_console_orchestrator import (
    tare, reset_tare, get_admin_console_data
)

d = get_admin_console_data()
full_cost = d["grand_total_cost_usd"]
print(f"No tare     -> grand_total: ${full_cost:.6f}   active_tare: {d['tare_info']['active_tare_ts']}")

r = tare("test fix v2")
print(f"Tare ts     -> {r['tare_ts']}")

d2 = get_admin_console_data()
tapered = d2["grand_total_cost_usd"]
print(f"After tare  -> grand_total: ${tapered:.6f}   active_tare: {d2['tare_info']['active_tare_ts']}")
print(f"Cost zeroed : {tapered == 0.0}")
print(f"LLM calls after tare  : {d2['llm_usage']['summary']['total_calls']}")
print(f"Agent runs after tare : {d2['agent_usage']['summary']['total_runs']}")

reset_tare()
print("Test tare removed.")

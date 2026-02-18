"""
Database Helper Functions for LLM Usage Tracking

Provides convenient functions to query and analyze LLM usage data
from the SQLite tracking database.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from tabulate import tabulate

from app.services.llm_client.tracker import LLMUsageTracker
from app.services.llm_client.utils import DEFAULT_DB_PATH


def print_summary(
    db_path: Optional[Path] = None,
    days: int = 30,
    service: Optional[str] = None
) -> None:
    """
    Print overall usage summary.
    
    Args:
        db_path: Path to database (uses default if None)
        days: Number of days to look back (0 for all time)
        service: Filter by service name (None for all services)
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    
    tracker = LLMUsageTracker(str(db_path))
    
    start_date = None if days == 0 else datetime.now() - timedelta(days=days)
    summary = tracker.get_usage_summary(start_date=start_date, service=service)
    
    if not summary or summary.get('total_calls', 0) == 0:
        print("📊 No usage data found")
        return
    
    print("\n" + "="*70)
    print(f"📊 USAGE SUMMARY ({days} days)" if days > 0 else "📊 USAGE SUMMARY (All Time)")
    if service:
        print(f"   Service: {service}")
    print("="*70)
    
    print(f"\n{'Metric':<25} {'Value':>15}")
    print("-" * 42)
    print(f"{'Total Calls':<25} {summary.get('total_calls', 0):>15,}")
    print(f"{'Successful Calls':<25} {summary.get('successful_calls', 0):>15,}")
    print(f"{'Failed Calls':<25} {summary.get('failed_calls', 0):>15,}")
    print(f"{'Total Tokens':<25} {summary.get('total_tokens', 0):>15,}")
    print(f"{'Prompt Tokens':<25} {summary.get('total_prompt_tokens', 0):>15,}")
    print(f"{'Completion Tokens':<25} {summary.get('total_completion_tokens', 0):>15,}")
    print(f"{'Total Cost (USD)':<25} ${summary.get('total_cost', 0):>14,.4f}")
    print(f"{'Avg Latency (ms)':<25} {summary.get('avg_latency_ms', 0):>14.0f}ms")


def print_by_service(
    db_path: Optional[Path] = None,
    days: int = 30,
    top_n: int = 10
) -> None:
    """
    Print usage breakdown by service.
    
    Args:
        db_path: Path to database (uses default if None)
        days: Number of days to look back (0 for all time)
        top_n: Number of top services to show
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    
    tracker = LLMUsageTracker(str(db_path))
    
    start_date = None if days == 0 else datetime.now() - timedelta(days=days)
    by_service = tracker.get_usage_by_service(start_date=start_date)
    
    if not by_service:
        print("📊 No service data found")
        return
    
    print("\n" + "="*70)
    print(f"📊 USAGE BY SERVICE (Top {top_n})")
    print("="*70)
    
    # Limit to top N
    by_service = by_service[:top_n]
    
    headers = ["Service", "Calls", "Tokens", "Cost (USD)", "Avg Latency (ms)"]
    rows = []
    
    for svc in by_service:
        rows.append([
            svc['service'],
            f"{svc['calls']:,}",
            f"{svc['tokens']:,}",
            f"${svc['cost']:.4f}",
            f"{svc.get('avg_latency_ms', 0):.0f}"
        ])
    
    print("\n" + tabulate(rows, headers=headers, tablefmt="simple"))


def print_recent_calls(
    db_path: Optional[Path] = None,
    limit: int = 10,
    show_details: bool = False
) -> None:
    """
    Print recent LLM calls.
    
    Args:
        db_path: Path to database (uses default if None)
        limit: Number of recent calls to show
        show_details: Show detailed information for each call
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    
    tracker = LLMUsageTracker(str(db_path))
    recent = tracker.get_recent_calls(limit=limit)
    
    if not recent:
        print("📊 No recent calls found")
        return
    
    print("\n" + "="*70)
    print(f"📜 RECENT CALLS (Last {limit})")
    print("="*70)
    
    if show_details:
        for i, call in enumerate(recent, 1):
            status = "✅" if call['success'] else "❌"
            print(f"\n{i}. {status} {call['timestamp']}")
            print(f"   Service: {call['service']}")
            print(f"   Operation: {call['operation']}")
            print(f"   Model: {call['model']}")
            print(f"   Tokens: {call['total_tokens']:,} (input: {call['prompt_tokens']:,}, output: {call['completion_tokens']:,})")
            print(f"   Cost: ${call['cost_usd']:.4f}")
            print(f"   Latency: {call['latency_ms']}ms")
            if call.get('error_message'):
                print(f"   Error: {call['error_message']}")
    else:
        headers = ["Time", "Status", "Service", "Operation", "Tokens", "Cost", "Latency"]
        rows = []
        
        for call in recent:
            status = "✅" if call['success'] else "❌"
            timestamp = call['timestamp'].split('T')[1].split('.')[0] if 'T' in call['timestamp'] else call['timestamp']
            
            rows.append([
                timestamp,
                status,
                call['service'][:20],
                call['operation'][:20],
                f"{call['total_tokens']:,}",
                f"${call['cost_usd']:.4f}",
                f"{call['latency_ms']}ms"
            ])
        
        print("\n" + tabulate(rows, headers=headers, tablefmt="simple"))


def print_failed_calls(
    db_path: Optional[Path] = None,
    days: int = 7,
    limit: int = 20
) -> None:
    """
    Print failed LLM calls for debugging.
    
    Args:
        db_path: Path to database (uses default if None)
        days: Number of days to look back
        limit: Maximum number of failed calls to show
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    
    tracker = LLMUsageTracker(str(db_path))
    
    start_date = datetime.now() - timedelta(days=days)
    failed = tracker.get_failed_calls(start_date=start_date, limit=limit)
    
    if not failed:
        print(f"\n✅ No failed calls in the last {days} days")
        return
    
    print("\n" + "="*70)
    print(f"❌ FAILED CALLS (Last {days} days)")
    print("="*70)
    
    for i, call in enumerate(failed, 1):
        print(f"\n{i}. {call['timestamp']}")
        print(f"   Service: {call['service']}")
        print(f"   Operation: {call['operation']}")
        print(f"   Model: {call['model']}")
        print(f"   Error: {call['error_message']}")


def print_cost_breakdown(
    db_path: Optional[Path] = None,
    days: int = 30
) -> None:
    """
    Print cost breakdown by service and model.
    
    Args:
        db_path: Path to database (uses default if None)
        days: Number of days to look back
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    
    tracker = LLMUsageTracker(str(db_path))
    
    start_date = datetime.now() - timedelta(days=days)
    
    # Get total cost
    total_cost = tracker.get_total_cost(start_date=start_date)
    
    # Get by service
    by_service = tracker.get_usage_by_service(start_date=start_date)
    
    print("\n" + "="*70)
    print(f"💰 COST BREAKDOWN ({days} days)")
    print("="*70)
    
    print(f"\nTotal Cost: ${total_cost:.4f}")
    
    if by_service:
        print("\nBy Service:")
        for svc in by_service:
            percentage = (svc['cost'] / total_cost * 100) if total_cost > 0 else 0
            print(f"  {svc['service']:<30} ${svc['cost']:>8.4f} ({percentage:>5.1f}%)")


def export_to_csv(
    db_path: Optional[Path] = None,
    output_path: str = "llm_usage_export.csv",
    days: int = 30
) -> None:
    """
    Export usage data to CSV file.
    
    Args:
        db_path: Path to database (uses default if None)
        output_path: Path to output CSV file
        days: Number of days to look back (0 for all time)
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    
    tracker = LLMUsageTracker(str(db_path))
    
    start_date = None if days == 0 else datetime.now() - timedelta(days=days)
    calls = tracker.get_recent_calls(limit=100000)  # Get all calls
    
    # Filter by date if needed
    if start_date:
        calls = [c for c in calls if datetime.fromisoformat(c['timestamp']) >= start_date]
    
    if not calls:
        print(f"❌ No data to export")
        return
    
    import csv
    
    with open(output_path, 'w', newline='') as f:
        if calls:
            writer = csv.DictWriter(f, fieldnames=calls[0].keys())
            writer.writeheader()
            writer.writerows(calls)
    
    print(f"✅ Exported {len(calls)} records to {output_path}")


def show_all_stats(db_path: Optional[Path] = None, days: int = 30) -> None:
    """
    Show all statistics in one comprehensive view.
    
    Args:
        db_path: Path to database (uses default if None)
        days: Number of days to look back
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    
    print("\n" + "="*70)
    print("🤖 LLM USAGE ANALYTICS")
    print(f"📁 Database: {db_path}")
    print("="*70)
    
    print_summary(db_path=db_path, days=days)
    print_by_service(db_path=db_path, days=days, top_n=10)
    print_cost_breakdown(db_path=db_path, days=days)
    print_recent_calls(db_path=db_path, limit=10)
    print_failed_calls(db_path=db_path, days=days, limit=10)
    
    print("\n" + "="*70)

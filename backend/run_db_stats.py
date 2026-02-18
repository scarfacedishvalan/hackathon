from app.services.llm_client.db_helpers import (
    show_all_stats,
    print_summary,
    print_by_service,
    print_recent_calls,
    print_failed_calls,
    print_cost_breakdown,
    export_to_csv,
)


if __name__ == "__main__":
    print_recent_calls()  # Show stats for last 30 days
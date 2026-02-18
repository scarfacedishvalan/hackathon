"""
LLM Client with Tracking - Test Runner

Demonstrates the LLM client usage tracking functionality.

This runner script:
- Uses OpenAI client for demonstration
- Makes sample LLM calls with automatic tracking
- Saves usage data to SQLite database
- Shows various tracking queries and statistics

Usage:
    python backend/run_llm_client_test.py
    python backend/run_llm_client_test.py --stats-only
    python backend/run_llm_client_test.py --export output.csv
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add backend directory to path for imports
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.llm_client import chat_and_record, DEFAULT_DB_PATH
from app.services.llm_client.db_helpers import (
    show_all_stats,
    print_summary,
    print_by_service,
    print_recent_calls,
    print_failed_calls,
    print_cost_breakdown,
    export_to_csv,
)


def test_basic_call():
    """Test basic LLM call with tracking using default client."""
    print("\n" + "="*70)
    print("TEST 1: Basic LLM Call with Default Client")
    print("="*70)
    
    system_prompt = "You are a helpful assistant that provides concise answers."
    user_prompt = "What is the capital of France? Answer in one word."
    
    print(f"\n📤 System: {system_prompt}")
    print(f"📤 User: {user_prompt}")
    
    try:
        response = chat_and_record(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            service="test_runner",
            operation="simple_question"
        )
        
        print(f"\n📥 Response: {response}")
        print(f"✅ Call recorded successfully to {DEFAULT_DB_PATH}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")


def test_json_response():
    """Test LLM call with JSON response."""
    print("\n" + "="*70)
    print("TEST 2: JSON Response with Tracking")
    print("="*70)
    
    system_prompt = """You are a financial analyst. Return your response as valid JSON.
Example format: {"analysis": "text", "sentiment": "positive/negative/neutral", "confidence": 0.8}"""
    
    user_prompt = """Analyze this news: "Apple announces record-breaking Q4 earnings, 
beating analyst expectations by 15%." Return JSON with analysis, sentiment, and confidence."""
    
    print(f"\n📤 System: {system_prompt[:80]}...")
    print(f"📤 User: {user_prompt[:80]}...")
    
    try:
        response = chat_and_record(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            service="test_runner",
            operation="json_analysis"
        )
        
        print(f"\n📥 Response: {response}")
        
        # Try to parse JSON
        parsed = json.loads(response)
        print(f"✅ Valid JSON response parsed successfully")
        print(f"   Sentiment: {parsed.get('sentiment', 'N/A')}")
        
    except json.JSONDecodeError as e:
        print(f"\n⚠️  Response is not valid JSON: {e}")
    except Exception as e:
        print(f"\n❌ Error: {e}")


def test_multiple_calls():
    """Test multiple calls to demonstrate tracking."""
    print("\n" + "="*70)
    print("TEST 3: Multiple Calls for Statistics")
    print("="*70)
    
    test_cases = [
        {
            "system": "You are a math tutor. Be concise.",
            "user": "What is 15 * 23?",
            "operation": "math_problem"
        },
        {
            "system": "You are a code explainer. Be brief.",
            "user": "Explain what a Python decorator is in one sentence.",
            "operation": "code_explanation"
        },
        {
            "system": "You are a translator.",
            "user": "Translate 'Hello, how are you?' to Spanish.",
            "operation": "translation"
        }
    ]
    
    print(f"\n🔄 Making {len(test_cases)} test calls...")
    
    for i, test in enumerate(test_cases, 1):
        try:
            response = chat_and_record(
                system_prompt=test["system"],
                user_prompt=test["user"],
                service="test_runner",
                operation=test["operation"]
            )
            print(f"   {i}. {test['operation']}: ✅")
        except Exception as e:
            print(f"   {i}. {test['operation']}: ❌ {e}")


def test_default_client():
    """Test using default OpenAI client (no client parameter)."""
    print("\n" + "="*70)
    print("TEST 4: Default OpenAI Client (No Client Parameter)")
    print("="*70)
    
    system_prompt = "You are a helpful assistant."
    user_prompt = "List 3 benefits of using SQLite for local data storage. Be brief."
    
    print(f"\n📤 System: {system_prompt}")
    print(f"📤 User: {user_prompt[:50]}...")
    print("ℹ️  Using default OpenAI client (gpt-4o-mini)")
    
    try:
        # No llm_client parameter - uses default OpenAI client
        response = chat_and_record(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            service="test_runner",
            operation="default_client_test"
        )
        
        print(f"\n📥 Response: {response[:150]}...")
        print(f"✅ Default client worked! Call recorded to {DEFAULT_DB_PATH}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")


def test_failed_call():
    """Test that failed calls are also tracked."""
    print("\n" + "="*70)
    print("TEST 5: Failed Call Tracking")
    print("="*70)
    
    class BrokenClient:
        """A client that always fails."""
        model = "broken-model"
        last_prompt_tokens = 0
        last_completion_tokens = 0
        
        def chat(self, **kwargs):
            raise ValueError("Simulated API failure for testing")
    
    client = BrokenClient()
    
    print("\n🔄 Attempting call with broken client...")
    
    try:
        response = chat_and_record(
            system_prompt="Test system prompt",
            user_prompt="Test user prompt",
            service="test_runner",
            operation="intentional_failure",
            llm_client=client
        )
    except ValueError as e:
        print(f"❌ Call failed as expected: {e}")
        print(f"✅ Failure should be recorded in database")


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(
        description="Test LLM client with usage tracking"
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only show statistics, don't make new calls"
    )
    parser.add_argument(
        "--export",
        type=str,
        help="Export usage data to CSV file"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to look back for statistics (default: 30)"
    )
    
    args = parser.parse_args()
    
    print("\n🤖 LLM Client Usage Tracking - Test Runner")
    print(f"📁 Database: {DEFAULT_DB_PATH}")
    
    if args.export:
        # Export to CSV
        export_to_csv(output_path=args.export, days=args.days)
        return
    
    if args.stats_only:
        # Show comprehensive statistics
        show_all_stats(days=args.days)
    else:
        # Validate API key
        if not os.getenv("OPENAI_API_KEY"):
            print("\n❌ Error: OpenAI API key required")
            print("   Set OPENAI_API_KEY environment variable")
            sys.exit(1)
        
        # Run all tests
        print("\n" + "="*70)
        print("RUNNING TESTS")
        print("="*70)
        
        test_basic_call()
        test_json_response()
        test_multiple_calls()
        test_default_client()
        test_failed_call()
        
        # Show statistics after tests
        print("\n" + "="*70)
        print("TEST RESULTS & STATISTICS")
        print("="*70)
        
        show_all_stats(days=args.days)
    
    print("\n" + "="*70)
    print("✅ Complete!")
    print(f"💡 Run with --stats-only to view statistics without making new calls")
    print(f"💡 Run with --export output.csv to export data to CSV")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()

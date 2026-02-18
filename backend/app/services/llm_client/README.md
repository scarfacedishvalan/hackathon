# LLM Client with Usage Tracking

Centralized LLM client utilities with automatic usage tracking to SQLite database.

## Features

- **Automatic tracking**: Every LLM call is automatically logged to SQLite
- **Token usage monitoring**: Tracks prompt tokens, completion tokens, and total usage
- **Cost calculation**: Automatically calculates costs based on current pricing
- **Performance metrics**: Records latency for each API call
- **Error tracking**: Failed calls are also logged with error messages
- **Service attribution**: Track which service/operation made each call
- **Analytics**: Built-in queries for usage summaries and statistics
- **Default client**: Uses OpenAI GPT-4o-mini by default when no client provided

## Installation

```bash
pip install openai tabulate
```

## Components

### `utils.py`
- `chat_and_record()`: Main function for making tracked LLM calls
- `OpenAIClientWrapper`: Default OpenAI client implementation
- `DEFAULT_DB_PATH`: Path to tracking database (backend/data/llm_usage.db)

### `tracker.py`
- `LLMCallRecord`: Dataclass for call metadata
- `LLMUsageTracker`: SQLite interface for storing and querying calls

### `db_helpers.py`
- `show_all_stats()`: Comprehensive statistics view
- `print_summary()`: Overall usage summary
- `print_by_service()`: Service breakdown
- `print_recent_calls()`: Recent call history
- `print_failed_calls()`: Failed calls for debugging
- `print_cost_breakdown()`: Cost analysis
- `export_to_csv()`: Export data to CSV

## Usage

### Basic Usage with Default Client

```python
from app.services.llm_client import chat_and_record

# Uses default OpenAI client (gpt-4o-mini) and default database path
response = chat_and_record(
    system_prompt="You are a helpful assistant",
    user_prompt="What is 2+2?",
    service="my_service",
    operation="simple_math"
)
```

### Using Custom Client

```python
from app.services.llm_client import chat_and_record

# Your custom LLM client
client = MyCustomClient(api_key="...")

response = chat_and_record(
    system_prompt="You are a helpful assistant",
    user_prompt="What is 2+2?",
    service="my_service",
    operation="simple_math",
    llm_client=client  # ← Custom client
)
```

### Database Location

By default, the database is stored at `backend/data/llm_usage.db`. You can override this:

```python
response = chat_and_record(
    system_prompt="...",
    user_prompt="...",
    service="my_service",
    operation="my_operation",
    db_path="custom/path/usage.db"
)
```

### Query Usage Statistics

```python
from app.services.llm_client.db_helpers import (
    show_all_stats,
    print_summary,
    print_by_service,
    export_to_csv
)

# Show comprehensive statistics
show_all_stats(days=30)

# Show specific views
print_summary(days=7)
print_by_service(days=30, top_n=10)
print_recent_calls(limit=20)
print_failed_calls(days=7)
print_cost_breakdown(days=30)

# Export to CSV
export_to_csv(output_path="usage_export.csv", days=30)
```

### Command Line Usage

```bash
# Run tests and show statistics
python backend/run_llm_client_test.py

# Show statistics only (no API calls)
python backend/run_llm_client_test.py --stats-only

# Show statistics for last 7 days
python backend/run_llm_client_test.py --stats-only --days 7

# Export to CSV
python backend/run_llm_client_test.py --export my_usage_data.csv --days 30
```

### LLM Client Requirements

Your LLM client must have:
- A `.chat(system_prompt, user_prompt, schema=None)` method
- Optionally: `.last_prompt_tokens` and `.last_completion_tokens` attributes

If token counts aren't available, they will be estimated (4 chars per token).

## Database Schema

```sql
CREATE TABLE llm_calls (
    call_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    service TEXT NOT NULL,
    operation TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    input_length INTEGER NOT NULL,
    output_length INTEGER NOT NULL,
    temperature REAL NOT NULL,
    max_tokens INTEGER NOT NULL,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    latency_ms INTEGER NOT NULL,
    cost_usd REAL NOT NULL
);
```

## Testing

Run the test script to verify functionality:

```bash
# Set your OpenAI API key
export OPENAI_API_KEY="sk-..."

# Run tests
python run_llm_client_test.py

# View statistics only (no API calls)
python run_llm_client_test.py --stats-only

# Use custom database path
python run_llm_client_test.py --db-path my_custom.db
```

## Cost Tracking

The tracker includes built-in pricing for common models (as of February 2026):

- **GPT-4o**: $2.50 per 1M input tokens, $10.00 per 1M output tokens
- **GPT-4o-mini**: $0.15 per 1M input tokens, $0.60 per 1M output tokens
- **Claude Sonnet 4.5**: $3.00 per 1M input tokens, $15.00 per 1M output tokens
- **Claude Sonnet 3.5**: $3.00 per 1M input tokens, $15.00 per 1M output tokens

Update pricing in `utils.py` as models/pricing changes.

## Integration with Existing Services

To integrate with existing services (e.g., bl_llm_parser):

```python
from app.services.llm_client.utils import chat_and_record

# Instead of:
response = self.llm_client.chat(
    system_prompt=system_prompt,
    user_prompt=user_prompt,
    schema=schema
)

# Use:
response = chat_and_record(
    llm_client=self.llm_client,
    system_prompt=system_prompt,
    user_prompt=user_prompt,
    service="bl_llm_parser",
    operation="parse_views",
    schema=schema,
    db_path="llm_usage.db"
)
```

## Benefits

✅ **Visibility**: Know exactly how much you're spending on LLM calls  
✅ **Attribution**: Track which services use the most tokens  
✅ **Debugging**: See failed calls with error messages  
✅ **Performance**: Monitor API latency over time  
✅ **Budget control**: Total cost tracking across all services  
✅ **No refactoring**: Minimal changes to existing code  

## Future Enhancements

- Dashboard UI for visualizing usage
- Rate limiting and budget alerts
- Export to CSV/JSON for external analysis
- Integration with cost monitoring tools

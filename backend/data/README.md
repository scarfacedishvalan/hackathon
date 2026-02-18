# LLM Usage Tracking Data

This directory stores the SQLite database that tracks all LLM API calls made by the application.

## Database File

- **llm_usage.db** - SQLite database containing all LLM usage records

## Database Schema

The database contains a single table `llm_calls` with the following structure:

- `call_id`: Unique identifier for each call
- `timestamp`: When the call was made
- `service`: Which service made the call (e.g., "bl_llm_parser", "recipe_interpreter")
- `operation`: What operation was performed (e.g., "parse_views", "parse_strategy")
- `model`: Which LLM model was used (e.g., "gpt-4o-mini")
- `prompt_tokens`: Number of tokens in the input
- `completion_tokens`: Number of tokens in the output
- `total_tokens`: Total tokens used
- `input_length`: Character count of input
- `output_length`: Character count of output
- `temperature`: Sampling temperature used
- `max_tokens`: Maximum tokens requested
- `success`: Whether the call succeeded
- `error_message`: Error message if failed
- `latency_ms`: API call duration in milliseconds
- `cost_usd`: Estimated cost in USD

## Viewing Statistics

Use the helper functions in `app/services/llm_client/db_helpers.py`:

```python
from app.services.llm_client.db_helpers import show_all_stats

# Show comprehensive statistics
show_all_stats(days=30)
```

Or run the test runner:

```bash
# View statistics only
python backend/run_llm_client_test.py --stats-only

# Export to CSV
python backend/run_llm_client_test.py --export usage_data.csv
```

## Git Ignore

Database files in this directory are ignored by git to prevent committing potentially sensitive usage data.

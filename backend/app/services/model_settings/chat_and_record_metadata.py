"""
Central metadata configuration for all chat_and_record LLM calls.

This file defines service names, operations, model choices, and parameters
for all LLM calls across the application. Centralizing this configuration
makes it easier to:
- Track which services use which models
- Update model versions consistently
- Manage temperature and other hyperparameters
- Monitor LLM usage analytics by service/operation
"""

# Nested dictionary: service -> operation -> parameters
CHAT_AND_RECORD_METADATA = {
    "black_litterman_parser": {
        "parse_views": {
            "service": "black_litterman_parser",
            "operation": "parse_views",
            "model": "gpt-4o",
            "temperature": 0.7,  # Default temperature
        }
    },
    "recipe_interpreter_bt": {
        "parse_strategy": {
            "service": "recipe_interpreter_bt",
            "operation": "parse_strategy",
            "model": "gpt-4o",
            "temperature": 0,  # Deterministic for backtesting strategies
        }
    },
    "news_api": {
        "parse_article_views": {
            "service": "news_api",
            "operation": "parse_article_views",
            "model": "gpt-4o",
            "temperature": 0,  # Deterministic for structured extraction
        }
    },
}


def get_metadata(service: str, operation: str) -> dict:
    """
    Get metadata for a specific service and operation.
    
    Args:
        service: Service name (e.g., "black_litterman_parser")
        operation: Operation name (e.g., "parse_views")
        
    Returns:
        Dictionary with service, operation, model, and temperature
        
    Raises:
        KeyError: If service or operation not found
    """
    if service not in CHAT_AND_RECORD_METADATA:
        raise KeyError(f"Service '{service}' not found in CHAT_AND_RECORD_METADATA")
    
    if operation not in CHAT_AND_RECORD_METADATA[service]:
        raise KeyError(
            f"Operation '{operation}' not found for service '{service}' "
            f"in CHAT_AND_RECORD_METADATA"
        )
    
    return CHAT_AND_RECORD_METADATA[service][operation]

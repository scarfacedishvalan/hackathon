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
# Pricing per 1M tokens as of February 2026
# Update these values as pricing changes
PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.150, "output": 0.600},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "claude-sonnet-4.5": {"input": 3.00, "output": 15.00},
    "claude-sonnet-3.5": {"input": 3.00, "output": 15.00},
    "claude-opus-3": {"input": 15.00, "output": 75.00},
    "claude-haiku-3": {"input": 0.25, "output": 1.25},
}
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
            "model": "gpt-4.1-mini",
            "temperature": 0,  # Deterministic for structured extraction
        }
    },
    "bl_stress_parser": {
        "parse_stress_request": {
            "service": "bl_stress_parser",
            "operation": "parse_stress_request",
            "model": "gpt-4o",
            "temperature": 0,  # Deterministic for stress test specification
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

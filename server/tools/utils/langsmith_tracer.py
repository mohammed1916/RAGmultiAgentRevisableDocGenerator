"""LangSmith integration for tracing and observability.

Enables tracing of LangGraph orchestrator and agent executions.
"""

import os
from typing import Optional
from server.config.settings import config
from server.base.logger import setup_logger

logger = setup_logger(__name__)


def enable_langsmith_tracing(project_name: Optional[str] = None) -> bool:
    """Enable LangSmith tracing for the application.

    Args:
        project_name: Optional project name override

    Returns:
        True if tracing was enabled, False otherwise
    """
    if not config.langsmith.enabled:
        logger.info("LangSmith tracing disabled (set LANGSMITH_ENABLED=true to enable)")
        return False

    if not config.langsmith.api_key:
        logger.warning("LangSmith API key not set (LANGSMITH_API_KEY)")
        return False

    # Set environment variables for LangSmith
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = config.langsmith.api_key
    os.environ["LANGCHAIN_ENDPOINT"] = config.langsmith.endpoint
    os.environ["LANGCHAIN_PROJECT"] = project_name or config.langsmith.project

    logger.info(f"[LANGSMITH] Enabled tracing")
    logger.info(f"  Project: {os.environ['LANGCHAIN_PROJECT']}")
    logger.info(f"  Endpoint: {os.environ['LANGCHAIN_ENDPOINT']}")

    return True


def disable_langsmith_tracing() -> None:
    """Disable LangSmith tracing."""
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    logger.info("[LANGSMITH] Tracing disabled")


def get_langsmith_status() -> dict:
    """Get current LangSmith status.

    Returns:
        Dictionary with tracing status and configuration
    """
    return {
        "enabled": config.langsmith.enabled,
        "has_api_key": bool(config.langsmith.api_key),
        "project": config.langsmith.project,
        "endpoint": config.langsmith.endpoint,
        "tracing_active": os.environ.get("LANGCHAIN_TRACING_V2", "false") == "true",
    }

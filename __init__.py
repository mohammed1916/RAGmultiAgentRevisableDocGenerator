"""Autonomous Multi-Agent AI Document Generation System.

A production-quality system for generating professional documents
using local AI models with multi-agent orchestration.
"""

__version__ = "1.0.0"
__author__ = "AI Engineering Team"

try:
    from client import DocumentGenerationClient, create_client
except ImportError:
    pass

try:
    from server.orchestrator import Orchestrator
    from server.models import DocumentRequest, DocumentResponse
except ImportError:
    pass

__all__ = [
    "DocumentGenerationClient",
    "create_client",
    "Orchestrator",
    "DocumentRequest",
    "DocumentResponse",
]

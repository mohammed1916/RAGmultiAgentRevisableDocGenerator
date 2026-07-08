"""Autonomous Multi-Agent AI Document Generation System.

A production-quality system for generating professional documents
using local AI models with multi-agent orchestration.
"""

__version__ = "1.0.0"
__author__ = "AI Engineering Team"

from client import DocumentGenerationClient, create_client
from orchestrator import Orchestrator
from models import DocumentRequest, DocumentResponse

__all__ = [
    "DocumentGenerationClient",
    "create_client",
    "Orchestrator",
    "DocumentRequest",
    "DocumentResponse",
]

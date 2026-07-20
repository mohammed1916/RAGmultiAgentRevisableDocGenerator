"""Document generation orchestrators - multiple implementation strategies.

Three orchestrator implementations for different use cases:

1. Base (Orchestrator)
   Traditional multi-agent approach using individual agents.
   Synchronous execution, legacy implementation.
   Use when: Simple linear workflow needed.

2. LangGraph (LangGraphOrchestrator)
   Modern LangGraph StateGraph with complex workflow coordination.
   Async-capable, conditional routing, message history.
   Use when: Complex DAG workflows with conditional branches needed.

3. Chat (ChatOrchestrator)
   LLM-driven conversational state machine.
   No hardcoded logic, pure conversational flow.
   Use when: Interactive dialogue-based generation needed.
"""

from .base import Orchestrator
from .langgraph import LangGraphOrchestrator
from .chat import ChatOrchestrator

__all__ = [
    "Orchestrator",
    "LangGraphOrchestrator",
    "ChatOrchestrator",
]

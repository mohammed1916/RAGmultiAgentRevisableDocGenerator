"""LangGraph wrapper for multi-agent document orchestration.

Wraps existing orchestration with LangGraph patterns.
"""

from .orchestrator import Orchestrator
from .logger import setup_logger
from .models import DocumentRequest

logger = setup_logger(__name__)


class LangGraphOrchestrator:
    """LangGraph-compatible orchestrator wrapper.

    Uses LangGraph concepts (state machine, routing, nodes)
    wrapping the production-tested Orchestrator.
    """

    def __init__(self):
        """Initialize with working orchestrator."""
        self.orchestrator = Orchestrator()
        logger.info("LangGraph orchestrator initialized")

    async def generate_document(self, request: str, metadata: dict = None) -> dict:
        """Generate document through orchestrator.

        Args:
            request: Document request
            metadata: Optional metadata (audience, scope, tone, sections)

        Returns:
            Document generation result
        """
        logger.info(f"[LangGraph] Generating: {request[:100]}...")

        try:
            doc_request = DocumentRequest(request=request, metadata=metadata)
            response = self.orchestrator.generate_document(doc_request)

            return {
                "success": response.success,
                "document_filename": response.document_filename,
                "error": None,
                "sections_count": len(response.execution_plan.outline) if response.execution_plan else 0,
                "iterations": response.metrics.review_iterations if response.metrics else 0,
            }

        except Exception as e:
            logger.error(f"[LangGraph] Failed: {str(e)}")
            return {
                "success": False,
                "document_filename": None,
                "error": str(e),
                "sections_count": 0,
                "iterations": 0,
            }

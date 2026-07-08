"""Orchestrator - coordinates the multi-agent document generation pipeline."""

import time
import os
from datetime import datetime
from typing import Tuple

from agents.planner import PlannerAgent
from agents.writer import WriterAgent
from agents.reviewer import ReviewerAgent
from tools.ollama_client import OllamaClient
from tools.docx_generator import DOCXGenerator
from tools.metrics import MetricsCollector
from models import (
    DocumentRequest,
    DocumentResponse,
    ExecutionPlan,
    DocumentStructure,
    DocumentSection,
)
from exceptions import DocumentGenerationException
from logger import setup_logger
from config import config

logger = setup_logger(__name__)


class Orchestrator:
    """Orchestrates the multi-agent document generation pipeline."""

    def __init__(self):
        """Initialize the orchestrator."""
        self.ollama_client = OllamaClient()
        self.planner = PlannerAgent(self.ollama_client)
        self.writer = WriterAgent(self.ollama_client)
        self.reviewer = ReviewerAgent(self.ollama_client)
        self.docx_generator = DOCXGenerator()
        self.metrics = MetricsCollector()

    def generate_document(self, doc_request: DocumentRequest) -> DocumentResponse:
        """Generate a complete document from a request.

        Args:
            doc_request: DocumentRequest instance

        Returns:
            DocumentResponse instance
        """
        logger.info(f"Starting document generation: {doc_request.request[:100]}...")
        self.metrics.start_pipeline()

        try:
            # Step 1: Planning
            logger.info("=" * 50)
            logger.info("PHASE 1: Planning")
            logger.info("=" * 50)
            plan_start = time.time()
            plan = self.planner.plan(doc_request.request)
            plan_latency = (time.time() - plan_start) * 1000
            self.metrics.record_planner_execution(plan_latency, len(plan.tasks))

            # Step 2: Writing
            logger.info("=" * 50)
            logger.info("PHASE 2: Writing Document")
            logger.info("=" * 50)
            write_start = time.time()
            sections = self.writer.write_all_sections(doc_request.request, plan)
            write_latency = (time.time() - write_start) * 1000
            self.metrics.record_writer_execution(write_latency)

            # Step 3: Review
            logger.info("=" * 50)
            logger.info("PHASE 3: Review & Quality Check")
            logger.info("=" * 50)
            review_start = time.time()
            review_iterations = 0

            for iteration in range(1, config.max_review_iterations + 1):
                logger.info(f"Review iteration {iteration}")
                feedback = self.reviewer.review_document(plan.document_type, sections)

                if not feedback.has_issues:
                    logger.info("Review passed - no issues found")
                    break
                else:
                    logger.warning(f"Issues found: {feedback.corrections[:200]}...")
                    review_iterations = iteration

                if iteration < config.max_review_iterations:
                    # Attempt to fix issues (in real implementation, would call writer again)
                    logger.info("Attempting to fix issues...")

            review_latency = (time.time() - review_start) * 1000
            self.metrics.record_reviewer_execution(review_latency, review_iterations)

            # Step 4: Quality Scoring
            logger.info("Scoring document quality...")
            quality_scores = self.reviewer.score_document(plan.document_type, sections)

            # Step 5: DOCX Generation
            logger.info("=" * 50)
            logger.info("PHASE 4: DOCX Generation")
            logger.info("=" * 50)
            docx_start = time.time()

            structure = DocumentStructure(
                title=plan.document_type,
                sections=sections,
            )

            self.docx_generator.from_structure(structure)

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"document_{timestamp}.docx"
            filepath = os.path.join(config.document_output_dir, filename)

            document_path = self.docx_generator.save(filepath)
            docx_latency = (time.time() - docx_start) * 1000
            self.metrics.record_docx_generation(docx_latency)

            # Collect LLM metrics (simplified - in real implementation, would track per call)
            logger.info("Collecting metrics...")
            pipeline_metrics = self.metrics.get_pipeline_metrics()

            # Build response
            response = DocumentResponse(
                success=True,
                document_filename=filename,
                execution_plan=plan,
                assumptions=plan.assumptions,
                metrics=pipeline_metrics,
                quality_scores=quality_scores,
                message="Document generated successfully",
            )

            logger.info("=" * 50)
            logger.info("DOCUMENT GENERATION COMPLETE")
            logger.info("=" * 50)
            logger.info(f"Total execution time: {pipeline_metrics.total_execution_time_ms:.2f}ms")
            logger.info(f"Document saved: {document_path}")

            return response

        except DocumentGenerationException as e:
            logger.error(f"Document generation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise DocumentGenerationException(f"Unexpected error: {str(e)}")

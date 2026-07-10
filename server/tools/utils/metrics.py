"""Metrics collection and tracking."""

import time
from typing import List, Optional

from ...models import LLMMetrics, PipelineMetrics


class MetricsCollector:
    """Collect metrics from LLM calls and pipeline execution."""

    def __init__(self):
        """Initialize the metrics collector."""
        self.llm_calls: List[LLMMetrics] = []
        self.planner_latency_ms: Optional[float] = None
        self.writer_latency_ms: Optional[float] = None
        self.reviewer_latency_ms: Optional[float] = None
        self.docx_generation_latency_ms: Optional[float] = None
        self.start_time: Optional[float] = None
        self.num_generated_tasks: int = 0
        self.review_iterations: int = 0

    def start_pipeline(self) -> None:
        """Mark the start of the pipeline."""
        self.start_time = time.time()

    def record_llm_call(
        self,
        model: str,
        latency_ms: float,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
    ) -> None:
        """Record an LLM call.

        Args:
            model: Model name
            latency_ms: Call latency in milliseconds
            prompt_tokens: Number of prompt tokens (optional)
            completion_tokens: Number of completion tokens (optional)
            total_tokens: Total number of tokens (optional)
        """
        metric = LLMMetrics(
            model=model,
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )
        self.llm_calls.append(metric)

    def record_planner_execution(self, latency_ms: float, num_tasks: int) -> None:
        """Record planner execution.

        Args:
            latency_ms: Execution latency in milliseconds
            num_tasks: Number of tasks generated
        """
        self.planner_latency_ms = latency_ms
        self.num_generated_tasks = num_tasks

    def record_writer_execution(self, latency_ms: float) -> None:
        """Record writer execution.

        Args:
            latency_ms: Execution latency in milliseconds
        """
        self.writer_latency_ms = latency_ms

    def record_reviewer_execution(self, latency_ms: float, iterations: int) -> None:
        """Record reviewer execution.

        Args:
            latency_ms: Execution latency in milliseconds
            iterations: Number of review iterations
        """
        self.reviewer_latency_ms = latency_ms
        self.review_iterations = iterations

    def record_docx_generation(self, latency_ms: float) -> None:
        """Record DOCX generation.

        Args:
            latency_ms: Generation latency in milliseconds
        """
        self.docx_generation_latency_ms = latency_ms

    def get_pipeline_metrics(self) -> PipelineMetrics:
        """Get complete pipeline metrics.

        Returns:
            PipelineMetrics instance
        """
        total_time_ms = (time.time() - self.start_time) * 1000

        return PipelineMetrics(
            planner_latency_ms=self.planner_latency_ms or 0,
            writer_latency_ms=self.writer_latency_ms or 0,
            reviewer_latency_ms=self.reviewer_latency_ms or 0,
            docx_generation_latency_ms=self.docx_generation_latency_ms or 0,
            total_execution_time_ms=total_time_ms,
            num_generated_tasks=self.num_generated_tasks,
            review_iterations=self.review_iterations,
            llm_calls=self.llm_calls,
        )

    def get_total_llm_latency(self) -> float:
        """Get total LLM latency.

        Returns:
            Sum of all LLM call latencies
        """
        return sum(call.latency_ms for call in self.llm_calls)

    def get_total_prompt_tokens(self) -> int:
        """Get total prompt tokens across all calls.

        Returns:
            Sum of prompt tokens (only counts if available)
        """
        return sum(
            call.prompt_tokens or 0 for call in self.llm_calls
            if call.prompt_tokens is not None
        )

    def get_total_completion_tokens(self) -> int:
        """Get total completion tokens across all calls.

        Returns:
            Sum of completion tokens (only counts if available)
        """
        return sum(
            call.completion_tokens or 0 for call in self.llm_calls
            if call.completion_tokens is not None
        )

    def get_summary(self) -> dict:
        """Get a summary of metrics.

        Returns:
            Dictionary with key metrics
        """
        return {
            "total_llm_calls": len(self.llm_calls),
            "total_llm_latency_ms": self.get_total_llm_latency(),
            "total_prompt_tokens": self.get_total_prompt_tokens(),
            "total_completion_tokens": self.get_total_completion_tokens(),
            "planner_latency_ms": self.planner_latency_ms,
            "writer_latency_ms": self.writer_latency_ms,
            "reviewer_latency_ms": self.reviewer_latency_ms,
            "docx_generation_latency_ms": self.docx_generation_latency_ms,
            "num_generated_tasks": self.num_generated_tasks,
            "review_iterations": self.review_iterations,
        }

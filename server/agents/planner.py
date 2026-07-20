"""Planner Agent - generates execution plans."""

import json
import time
from typing import Dict, List

from ..tools import OllamaClient
from ..base.models import ExecutionPlan, Task
from ..base.exceptions import PlannerException
from ..base.logger import setup_logger

logger = setup_logger(__name__)


class PlannerAgent:
    """Agent responsible for planning document generation."""

    def __init__(self, ollama_client: OllamaClient):
        """Initialize the Planner Agent.

        Args:
            ollama_client: OllamaClient instance
        """
        self.client = ollama_client

    def plan(self, request: str) -> ExecutionPlan:
        """Generate an execution plan for the request.

        Args:
            request: Natural language request

        Returns:
            ExecutionPlan instance

        Raises:
            PlannerException: If planning fails
        """
        logger.info(f"Planning document generation for request: {request[:100]}...")

        prompt = self._build_planning_prompt(request)

        try:
            response = self.client.structured_generate(
                prompt,
                schema={
                    "type": "object",
                    "properties": {
                        "document_type": {"type": "string"},
                        "assumptions": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                        },
                        "tasks": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "integer"},
                                    "description": {"type": "string"},
                                    "dependencies": {
                                        "type": "array",
                                        "items": {"type": "integer"},
                                    },
                                },
                            },
                        },
                        "outline": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["document_type", "assumptions", "tasks", "outline"],
                },
            )

            parsed = response.get("parsed_response", {})

            # Convert tasks to Task objects
            tasks = [
                Task(
                    id=t["id"],
                    description=t["description"],
                    dependencies=t.get("dependencies", []),
                )
                for t in parsed.get("tasks", [])
            ]

            plan = ExecutionPlan(
                document_type=parsed.get("document_type", "Professional Document"),
                assumptions=parsed.get("assumptions", {}),
                tasks=tasks,
                outline=parsed.get("outline", []),
            )

            logger.info(
                f"Planning complete. Generated {len(plan.tasks)} tasks. "
                f"Document type: {plan.document_type}"
            )
            return plan
        except Exception as e:
            raise PlannerException(f"Failed to generate plan: {str(e)}")

    def _build_planning_prompt(self, request: str) -> str:
        """Build the planning prompt.

        Args:
            request: Original request

        Returns:
            Formatted prompt
        """
        return f"""You are a todo list planning agent. Analyze this request and create a prioritized todo list.

Request: {request}

Generate a todo plan that includes:
1. Document type: "Todo List"
2. Assumptions: Any reasonable assumptions about deadlines/context
3. Tasks: Individual todo items with priorities
4. Outline: Section names for the final document

For the tasks, provide:
- Unique task IDs (starting from 1)
- Description (the actual todo item)
- Dependencies (task IDs this depends on, if any)

Each task should be:
- Specific and actionable
- Have an implied priority (High/Medium/Low based on urgency)
- Realistic deadline

Example task: "Complete project analysis"

Return the plan as JSON with these exact fields."""

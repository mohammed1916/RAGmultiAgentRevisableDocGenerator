"""Simple todo list generator agent."""

import json
from typing import List, Dict

from ..tools import OllamaClient
from ..base.models import DocumentSection
from ..base.logger import setup_logger

logger = setup_logger(__name__)


class TodoGenerator:
    """Generate prioritized todo lists from requests."""

    SYSTEM_PROMPT = """You are a todo list generator. Your task is to create a prioritized todo list.

Given a request, generate a structured todo list with:
- Task name (what needs to be done)
- Priority (High, Medium, Low)
- Deadline (if applicable)
- Estimated hours (rough estimate)

Return ONLY valid JSON in this exact format:
{
  "todos": [
    {"task": "...", "priority": "High", "deadline": "...", "hours": 2},
    {"task": "...", "priority": "Medium", "deadline": "...", "hours": 4}
  ]
}

Make the list practical and actionable. Keep it concise."""

    def __init__(self):
        """Initialize the todo generator."""
        self.llm = OllamaClient()
        logger.info("Todo generator initialized")

    def generate_todos(self, request: str) -> List[Dict]:
        """Generate a todo list from a request.

        Args:
            request: What needs to be organized into todos

        Returns:
            List of todo items with priority and deadline
        """
        logger.info(f"Generating todos for: {request[:100]}...")

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"Create a todo list for: {request}"},
        ]

        try:
            result = self.llm.chat(messages)
            response_text = result.get("message", {}).get("content", "").strip()

            # Parse JSON response
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start != -1 and end > start:
                json_str = response_text[start:end]
                data = json.loads(json_str)
                todos = data.get("todos", [])

                if todos:
                    logger.info(f"Generated {len(todos)} todo items")
                    return todos

            logger.warning("No valid todos generated")
            return []

        except Exception as e:
            logger.error(f"Todo generation failed: {e}")
            return []

    def create_todo_document_section(self, todos: List[Dict]) -> DocumentSection:
        """Create a document section from todos as a markdown table.

        Args:
            todos: List of todo items

        Returns:
            DocumentSection with markdown table
        """
        if not todos:
            return DocumentSection(
                title="Todo List",
                content="No tasks generated",
                heading_level=1
            )

        # Build markdown table
        markdown = "| Task | Priority | Deadline | Hours |\n"
        markdown += "|------|----------|----------|-------|\n"

        for todo in todos:
            task = todo.get("task", "").replace("|", "\\|")
            priority = todo.get("priority", "")
            deadline = todo.get("deadline", "")
            hours = todo.get("hours", "")

            markdown += f"| {task} | {priority} | {deadline} | {hours} |\n"

        return DocumentSection(
            title="Priority Todo List",
            content=markdown,
            heading_level=1
        )

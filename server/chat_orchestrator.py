"""Chat-based document generation orchestrator.

Handles conversational flow with clarifying questions before generation.
"""

from typing import List, Optional, Dict
from datetime import datetime

from .models import (
    ChatMessage,
    ClarifyingQuestion,
    ChatContext,
    ChatResponse,
)
from .logger import setup_logger

logger = setup_logger(__name__)


class ChatOrchestrator:
    """Manages chat-based document generation workflow."""

    # Default clarifying questions for document generation
    DEFAULT_QUESTIONS = [
        ClarifyingQuestion(
            question="Who is the target audience for this document?",
            key="audience",
            options=["Executive", "Technical", "General", "Mixed"],
            required=True,
        ),
        ClarifyingQuestion(
            question="What's the desired length/scope?",
            key="scope",
            options=["Brief (1-3 pages)", "Detailed (5-10 pages)", "Comprehensive (10+ pages)"],
            required=True,
        ),
        ClarifyingQuestion(
            question="What tone would you prefer?",
            key="tone",
            options=["Formal", "Professional but conversational", "Casual"],
            required=True,
        ),
        ClarifyingQuestion(
            question="Any specific sections or areas to include?",
            key="sections",
            required=False,
        ),
    ]

    def __init__(self):
        """Initialize chat orchestrator."""
        self.sessions: Dict[str, ChatContext] = {}
        logger.info("Chat orchestrator initialized")

    def start_conversation(self, request: str) -> ChatResponse:
        """Start a new conversation with initial request.

        Args:
            request: User's initial request for document

        Returns:
            ChatResponse with initial questions
        """
        logger.info(f"Starting conversation with request: {request[:100]}...")

        # Create context
        context = ChatContext(initial_request=request)

        # Add user message
        context.conversation.append(
            ChatMessage(role="user", content=request)
        )

        # Generate clarifying questions
        questions = self.DEFAULT_QUESTIONS
        response_text = (
            f"I'll help you create this document. Let me ask a few clarifying questions first:\n\n"
            f"Initial request: {request}"
        )

        context.conversation.append(
            ChatMessage(role="assistant", content=response_text)
        )

        return ChatResponse(
            message=response_text,
            questions=questions,
            context=context,
            is_ready_to_generate=False,
            next_action="ask_more",
        )

    def add_answer(self, context: ChatContext, question_key: str, answer: str) -> ChatResponse:
        """Process user's answer to a clarifying question.

        Args:
            context: Current chat context
            question_key: Key of the question being answered
            answer: User's answer

        Returns:
            ChatResponse with next action
        """
        logger.info(f"Processing answer for {question_key}: {answer[:50]}...")

        # Store answer
        context.answers[question_key] = answer

        # Add to conversation
        context.conversation.append(
            ChatMessage(role="user", content=f"[Answer to {question_key}]: {answer}")
        )

        # Check if we have enough information
        required_questions = [q for q in self.DEFAULT_QUESTIONS if q.required]
        answered = sum(1 for q in required_questions if q.key in context.answers)
        is_ready = answered >= len(required_questions)

        context.is_ready_to_generate = is_ready

        # Calculate confidence
        confidence = min(1.0, len(context.answers) / len(self.DEFAULT_QUESTIONS))
        context.confidence_level = confidence

        if is_ready:
            response_text = (
                f"Great! I have enough information.\n\n"
                f"Document will be:\n"
                f"- Audience: {context.answers.get('audience', 'Not specified')}\n"
                f"- Scope: {context.answers.get('scope', 'Not specified')}\n"
                f"- Tone: {context.answers.get('tone', 'Not specified')}\n"
                f"- Sections: {context.answers.get('sections', 'Standard structure')}\n\n"
                f"Ready to generate your document!"
            )
            context.conversation.append(
                ChatMessage(role="assistant", content=response_text)
            )

            return ChatResponse(
                message=response_text,
                context=context,
                is_ready_to_generate=True,
                next_action="ready_to_generate",
            )
        else:
            # Ask remaining questions
            remaining = [
                q for q in self.DEFAULT_QUESTIONS
                if q.required and q.key not in context.answers
            ]

            response_text = f"Thanks! {len(context.answers)}/{len(self.DEFAULT_QUESTIONS)} details captured."
            context.conversation.append(
                ChatMessage(role="assistant", content=response_text)
            )

            return ChatResponse(
                message=response_text,
                questions=remaining[:2],  # Show next 2 questions
                context=context,
                is_ready_to_generate=False,
                next_action="ask_more",
            )

    def get_generation_prompt(self, context: ChatContext) -> str:
        """Build comprehensive generation prompt from chat context.

        Args:
            context: Chat context with all answers

        Returns:
            Detailed prompt for document generation
        """
        prompt = f"""Generate a document based on this conversation:

Initial Request: {context.initial_request}

Document Specifications:
- Target Audience: {context.answers.get('audience', 'General audience')}
- Scope: {context.answers.get('scope', 'Balanced depth and breadth')}
- Tone: {context.answers.get('tone', 'Professional')}
- Specific Sections: {context.answers.get('sections', 'Use standard structure')}

Conversation History:
"""

        for msg in context.conversation:
            prompt += f"\n{msg.role.upper()}: {msg.content}"

        prompt += "\n\nBased on all this context, generate a comprehensive, well-structured document."

        return prompt

    def export_conversation(self, context: ChatContext) -> str:
        """Export conversation as readable text.

        Args:
            context: Chat context

        Returns:
            Formatted conversation text
        """
        text = f"Document Generation Conversation\n"
        text += f"Initial Request: {context.initial_request}\n"
        text += f"Confidence Level: {context.confidence_level:.1%}\n"
        text += "=" * 50 + "\n\n"

        for msg in context.conversation:
            text += f"{msg.role.upper()}:\n{msg.content}\n\n"

        return text

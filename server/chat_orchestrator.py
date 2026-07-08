"""Chat-based document generation orchestrator.

Handles conversational flow with clarifying questions before generation.
Uses RAG to fetch curriculum and ask context-aware questions.
"""

from typing import List, Optional, Dict
from datetime import datetime

from .models import (
    ChatMessage,
    ClarifyingQuestion,
    ChatContext,
    ChatResponse,
)
from .tools.milvus_rag import MilvusRAG
from .logger import setup_logger

logger = setup_logger(__name__)


class ChatOrchestrator:
    """Manages chat-based document generation workflow."""

    # Initial questions to determine subject/class
    INITIAL_QUESTIONS = [
        ClarifyingQuestion(
            question="What are you studying? (Class/Level/Subject)",
            key="subject",
            options=["Class 10 Science", "Class 12 Physics", "Class 12 Chemistry",
                    "Class 12 Math", "JEE Main", "JEE Advanced", "College Level"],
            required=True,
        ),
        ClarifyingQuestion(
            question="What's your exam/completion deadline?",
            key="deadline",
            options=["1 week", "1 month", "3 months", "6 months"],
            required=True,
        ),
    ]

    # Fallback generic questions if no RAG context
    GENERIC_QUESTIONS = [
        ClarifyingQuestion(
            question="What tone would you prefer?",
            key="tone",
            options=["Formal", "Professional but conversational", "Casual"],
            required=True,
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

        # Use curriculum-aware initial questions
        questions = self.INITIAL_QUESTIONS
        response_text = (
            f"I'm your study scheduling agent! Let me understand what you're studying:\n\n"
            f"Your request: {request}"
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
            ChatMessage(role="user", content=f"{answer}")
        )

        # If user just answered subject, fetch curriculum topics
        if question_key == "subject":
            try:
                rag = MilvusRAG()
                results = rag.search_documents(answer, top_k=10)
                topics = [r.get("title", f"Topic {i+1}") for i, r in enumerate(results)]

                if topics:
                    # Create dynamic question with actual topics from curriculum
                    topics_question = ClarifyingQuestion(
                        question=f"Which topics from {answer} do you want to cover? (Select all that apply)",
                        key="topics",
                        options=topics[:8],  # Show up to 8 topics
                        required=True,
                    )

                    response_text = f"Great! I found {len(topics)} topics in the {answer} curriculum.\nLet me show you what's available..."
                    context.conversation.append(
                        ChatMessage(role="assistant", content=response_text)
                    )

                    return ChatResponse(
                        message=response_text,
                        questions=[topics_question],
                        context=context,
                        is_ready_to_generate=False,
                        next_action="ask_more",
                    )
            except Exception as e:
                logger.warning(f"RAG fetch failed: {e}")

        # Standard flow for other answers
        required_answers = ["subject", "deadline", "topics"]
        answered = sum(1 for k in required_answers if k in context.answers)
        is_ready = answered >= len(required_answers)

        context.is_ready_to_generate = is_ready
        context.confidence_level = min(1.0, answered / len(required_answers))

        if is_ready:
            response_text = (
                f"Perfect! I have everything I need:\n\n"
                f"📚 Subject: {context.answers.get('subject', 'N/A')}\n"
                f"⏰ Deadline: {context.answers.get('deadline', 'N/A')}\n"
                f"📖 Topics: {context.answers.get('topics', 'N/A')}\n\n"
                f"Ready to create your study schedule!"
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
            remaining_keys = [k for k in required_answers if k not in context.answers]
            response_text = f"Got it! {answered}/{len(required_answers)} pieces of information collected."
            context.conversation.append(
                ChatMessage(role="assistant", content=response_text)
            )

            return ChatResponse(
                message=response_text,
                questions=None,  # Let frontend know to continue asking
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

"""Chat-based document generation orchestrator.

Handles conversational flow with clarifying questions before generation.
Uses LLM to generate dynamic questions and RAG to fetch curriculum topics.
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
from .tools.ollama_client import OllamaClient
from .logger import setup_logger

logger = setup_logger(__name__)


class ChatOrchestrator:
    """Manages chat-based document generation workflow."""

    def __init__(self):
        """Initialize orchestrator."""
        self.llm_client = OllamaClient()
        self.rag = MilvusRAG()
        logger.info("Chat orchestrator initialized")

    def __init__(self):
        """Initialize chat orchestrator."""
        self.sessions: Dict[str, ChatContext] = {}
        logger.info("Chat orchestrator initialized")

    def start_conversation(self, request: str) -> ChatResponse:
        """Start a new conversation with initial request.

        Uses LLM to analyze request and suggest relevant subjects.

        Args:
            request: User's initial request for document

        Returns:
            ChatResponse with LLM-generated subject options
        """
        logger.info(f"Starting conversation with request: {request[:100]}...")

        # Create context
        context = ChatContext(initial_request=request)

        # Add user message
        context.conversation.append(
            ChatMessage(role="user", content=request)
        )

        # Use LLM to analyze and suggest subjects
        response_text = f"I'm your study scheduling agent!\n\nYour request: {request}\n\nLet me analyze what you're studying..."
        context.conversation.append(
            ChatMessage(role="assistant", content=response_text)
        )

        # Call LLM to generate relevant subjects
        try:
            subjects = self._generate_subjects_from_llm(request)
            logger.info(f"LLM generated subjects: {subjects}")
        except Exception as e:
            logger.warning(f"LLM subject generation failed: {e}")
            subjects = ["Class 10", "Class 12", "JEE Main", "JEE Advanced"]  # Fallback

        # Create question WITHOUT options - let user TYPE their subject
        subject_question = ClarifyingQuestion(
            question="What are you studying? (e.g., 'Class 12 Physics', 'JEE Mains', 'Calculus')",
            key="subject",
            options=None,  # No buttons - show text input instead
            required=True,
        )

        return ChatResponse(
            message=response_text,
            questions=[subject_question],
            context=context,
            is_ready_to_generate=False,
            next_action="ask_more",
        )

    def _generate_subjects_from_llm(self, request: str) -> List[str]:
        """Generate relevant subjects using LLM based on user request.

        Args:
            request: User's study request

        Returns:
            List of relevant subject options
        """
        prompt = f"""Based on this study request: "{request}"

Generate 4-6 relevant subject/class options from these categories:
- CBSE Classes (Class 10, Class 12)
- Competitive Exams (JEE Main, JEE Advanced)
- College Level
- Specific subjects (Physics, Chemistry, Math, etc.)

Return ONLY the options as a comma-separated list. Example:
Class 12 Physics, JEE Main, Advanced Mathematics

Options for this request:"""

        try:
            response = self.llm_client.call_llm(prompt, max_tokens=100)
            # Parse response into list
            options = [opt.strip() for opt in response.split(",")]
            options = [opt for opt in options if opt]  # Remove empty strings
            return options[:6]  # Return max 6 options
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

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
                results = self.rag.search_documents(answer, top_k=15)
                topics = [r.get("title", f"Topic {i+1}") for i, r in enumerate(results)]

                if topics and len(topics) > 0:
                    # Create question with actual topics from curriculum
                    topics_question = ClarifyingQuestion(
                        question=f"Which topics from {answer} do you want to cover? (You can type multiple, comma-separated)",
                        key="topics",
                        options=topics[:10],  # Show up to 10 topics as suggestions
                        required=True,
                    )

                    response_text = f"Perfect! I found {len(topics)} topics in the {answer} curriculum.\n\nSelect the topics you want to cover:"
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
                else:
                    # No topics found, ask user to specify
                    logger.warning(f"No topics found for: {answer}")
                    response_text = f"I couldn't find specific topics for '{answer}' in the curriculum.\n\nPlease tell me which topics you want to cover (you can type them):"
                    context.conversation.append(
                        ChatMessage(role="assistant", content=response_text)
                    )

                    topics_question = ClarifyingQuestion(
                        question="Which topics do you want to cover?",
                        key="topics",
                        options=None,  # Let user type
                        required=True,
                    )

                    return ChatResponse(
                        message=response_text,
                        questions=[topics_question],
                        context=context,
                        is_ready_to_generate=False,
                        next_action="ask_more",
                    )
            except Exception as e:
                logger.error(f"RAG fetch failed: {e}")
                # Fallback: ask user to specify topics
                response_text = f"I had trouble finding topics for '{answer}'. Please tell me which topics you want to cover:"
                context.conversation.append(
                    ChatMessage(role="assistant", content=response_text)
                )

                topics_question = ClarifyingQuestion(
                    question="Which topics do you want to cover?",
                    key="topics",
                    options=None,
                    required=True,
                )

                return ChatResponse(
                    message=response_text,
                    questions=[topics_question],
                    context=context,
                    is_ready_to_generate=False,
                    next_action="ask_more",
                )

        # Standard flow for other answers
        # Order: subject → topics → deadline → generate
        required_answers = ["subject", "topics", "deadline"]
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

            # Generate next question dynamically based on what's missing
            next_questions = []

            if "topics" not in context.answers:
                # Topics should be asked after subject (handled above)
                # This is fallback in case topics wasn't fetched
                next_questions.append(
                    ClarifyingQuestion(
                        question="Which topics do you want to cover? (type or select from suggestions)",
                        key="topics",
                        options=None,
                        required=True,
                    )
                )
            elif "deadline" not in context.answers:
                # Ask deadline after we have subject and topics
                next_questions.append(
                    ClarifyingQuestion(
                        question="What's your deadline? (e.g., '3 weeks', 'December 2024', '50 days')",
                        key="deadline",
                        options=None,  # Let user type their own deadline
                        required=True,
                    )
                )

            return ChatResponse(
                message=response_text,
                questions=next_questions if next_questions else None,
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

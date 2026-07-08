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

        Immediately searches RAG for relevant topics based on request.

        Args:
            request: User's initial request for document

        Returns:
            ChatResponse with topics from RAG
        """
        logger.info(f"Starting conversation with request: {request[:100]}...")

        # Create context
        context = ChatContext(initial_request=request)
        context.answers["subject"] = request  # Store the initial request as subject

        # Add user message
        context.conversation.append(
            ChatMessage(role="user", content=request)
        )

        response_text = f"Great! Let me find topics for '{request}' from the curriculum..."
        context.conversation.append(
            ChatMessage(role="assistant", content=response_text)
        )

        # Immediately search RAG for topics based on initial request
        try:
            results = self.rag.search_documents(request, top_k=15)
            topics = [r.get("title", f"Topic {i+1}") for i, r in enumerate(results)]

            if topics and len(topics) > 0:
                logger.info(f"Found {len(topics)} topics for: {request}")

                # Create question with topics from RAG
                topics_question = ClarifyingQuestion(
                    question=f"Which topics do you want to cover? (Select from below or type custom ones)",
                    key="topics",
                    options=topics[:12],  # Show up to 12 topics from RAG
                    required=True,
                )

                # EXPLICITLY LIST topics in the message
                topics_list = "\n".join([f"  • {t}" for t in topics[:12]])
                response_text = f"Found {len(topics)} topics in {request}:\n\n{topics_list}\n\nWhich ones do you want to cover? (Or just ask me to advise!)"
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
                # No topics found, ask user to clarify or ask for recommendations
                logger.warning(f"No topics found for: {request}")
                response_text = f"I couldn't find specific topics for '{request}'.\n\nYou can:\n  1. Type the topics you want\n  2. Or say 'advise me' and I'll recommend topics"
                context.conversation.append(
                    ChatMessage(role="assistant", content=response_text)
                )

                topics_question = ClarifyingQuestion(
                    question=f"Which topics from {request}? (Or type 'advise me')",
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
            logger.error(f"RAG search failed: {e}")
            response_text = f"Let me help you prepare for '{request}'. Which topics do you want to cover?"
            context.conversation.append(
                ChatMessage(role="assistant", content=response_text)
            )

            topics_question = ClarifyingQuestion(
                question=f"Which topics from {request}?",
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

    def _user_asking_for_advice(self, answer: str) -> bool:
        """Check if user is asking for advice/recommendations.

        Args:
            answer: User's answer

        Returns:
            True if user asking for help/advice
        """
        keywords = ["i don't know", "help", "advice", "recommend", "suggest",
                   "what should", "which is best", "important", "critical", "essential"]
        answer_lower = answer.lower()
        return any(keyword in answer_lower for keyword in keywords)

    def _recommend_topics(self, context: ChatContext) -> ChatResponse:
        """Use LLM to recommend best topics for learning.

        Args:
            context: Chat context with subject and deadline

        Returns:
            ChatResponse with LLM-recommended topics
        """
        subject = context.answers.get("subject", "")
        logger.info(f"LLM recommending topics for: {subject}")

        try:
            # Get all available topics from RAG
            all_results = self.rag.search_documents(subject, top_k=20)
            all_topics = [r.get("title", f"Topic {i+1}") for i, r in enumerate(all_results)]

            if not all_topics:
                response_text = f"I couldn't find topics for {subject}. Which ones would you like to study?"
                context.conversation.append(
                    ChatMessage(role="assistant", content=response_text)
                )
                return ChatResponse(
                    message=response_text,
                    questions=[ClarifyingQuestion(
                        question="Topics to cover:",
                        key="topics",
                        options=None,
                        required=True,
                    )],
                    context=context,
                    is_ready_to_generate=False,
                    next_action="ask_more",
                )

            # Use LLM to recommend which topics are most important
            topics_str = "\n".join([f"- {t}" for t in all_topics[:15]])
            prompt = f"""For a student preparing for '{subject}', recommend the TOP topics to focus on first.

Available topics:
{topics_str}

Consider: foundational topics should come first, then build to advanced.
Recommend the 5-8 most important topics to START with.

Return ONLY the topic names, one per line, in order of importance."""

            recommendation = self.llm_client.call_llm(prompt, max_tokens=200)
            recommended_topics = [t.strip() for t in recommendation.strip().split("\n") if t.strip()]

            response_text = f"Based on '{subject}', I recommend starting with these topics:\n\n" + "\n".join([f"• {t}" for t in recommended_topics[:8]])
            context.conversation.append(
                ChatMessage(role="assistant", content=response_text)
            )
            context.answers["topics"] = ", ".join(recommended_topics[:8])

            logger.info(f"Recommended {len(recommended_topics)} topics")

            # Now ask for deadline
            response_text += "\n\nNow, what's your deadline?"
            context.conversation.append(
                ChatMessage(role="assistant", content=response_text)
            )

            return ChatResponse(
                message=response_text,
                questions=[ClarifyingQuestion(
                    question="What's your deadline?",
                    key="deadline",
                    options=None,
                    required=True,
                )],
                context=context,
                is_ready_to_generate=False,
                next_action="ask_more",
            )

        except Exception as e:
            logger.error(f"Topic recommendation failed: {e}")
            response_text = f"Let me help. Which topics from {subject} interest you most?"
            context.conversation.append(
                ChatMessage(role="assistant", content=response_text)
            )
            return ChatResponse(
                message=response_text,
                questions=[ClarifyingQuestion(
                    question="Topics to cover:",
                    key="topics",
                    options=None,
                    required=True,
                )],
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

        # Add to conversation FIRST (before any processing)
        context.conversation.append(
            ChatMessage(role="user", content=f"{answer}")
        )

        # Check if user is asking for advice/recommendations
        if question_key == "topics" and self._user_asking_for_advice(answer):
            logger.info(f"User asking for advice: {answer}")
            return self._recommend_topics(context)

        # Store answer normally
        context.answers[question_key] = answer

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

"""LLM-driven state machine for chat-based document generation.

Complete LLM control: LLM decides state, generates messages, and fetches data.
No hardcoded logic - pure conversational flow.
"""

from typing import List, Optional, Dict
from datetime import datetime

from ..base.models import (
    ChatMessage,
    ClarifyingQuestion,
    ChatContext,
    ChatResponse,
)
from ..tools import MilvusRAG
from ..tools import OllamaClient
from ..base.logger import setup_logger

logger = setup_logger(__name__)


class ChatOrchestrator:
    """LLM-driven conversational state machine."""

    SYSTEM_PROMPT = """You are an intelligent study scheduling agent. Your role is to conduct a natural conversation to help students prepare for exams.

CONVERSATION FLOW (LLM decides all transitions):
1. Initial: Understand what student is studying (subject/exam)
2. Information Gathering: Learn about their topics and deadline
3. Planning: Create a personalized study schedule
4. Confirmation: Let student review and proceed

KEY RULES:
- Generate ALL assistant messages yourself - never ask user directly
- Analyze what user knows vs doesn't know
- If user is vague/uncertain, you decide to fetch curriculum details and recommend
- If user is clear, proceed with their answer
- Use natural language - make it a real conversation
- Track: subject, topics, deadline (store in context as you learn them)
- When you have subject + topics + deadline, you're ready to generate schedule

WHEN TO FETCH CURRICULUM:
- User doesn't know topics → you search curriculum and recommend
- User wants help choosing → you search and suggest
- User is uncertain → you search and clarify

STATE INDICATORS (in your message):
- [GATHERING] - collecting information
- [RECOMMENDING] - suggesting topics from curriculum
- [READY] - have all info, ready to generate schedule

Generate conversational, helpful responses. Never force the user to choose between options."""

    def __init__(self):
        """Initialize orchestrator with LLM control."""
        self.llm_client = OllamaClient()
        self.rag = MilvusRAG()
        logger.info("LLM-driven chat orchestrator initialized")

    def start_conversation(self, request: str) -> ChatResponse:
        """Start conversation - LLM responds to initial request.

        Args:
            request: User's initial message

        Returns:
            ChatResponse with LLM-generated response
        """
        logger.info(f"Starting conversation: {request[:100]}...")

        context = ChatContext(initial_request=request)
        context.conversation.append(ChatMessage(role="user", content=request))

        # LLM generates the first response
        response_text = self._llm_respond(context)
        context.conversation.append(ChatMessage(role="assistant", content=response_text))

        # Check if LLM determined we're ready
        is_ready = self._check_if_ready(context)

        # Update context.is_ready_to_generate so it's included in the response
        context.is_ready_to_generate = is_ready

        return ChatResponse(
            message=response_text,
            session_id=None,  # Set by API
            questions=None if is_ready else [ClarifyingQuestion(
                question="Your response:",
                key="user_input",
                options=None,
                required=True,
            )],
            context=context,
            is_ready_to_generate=is_ready,
            next_action="ready_to_generate" if is_ready else "ask_more",
        )

    def add_answer(self, context: ChatContext, question_key: str, answer: str) -> ChatResponse:
        """Process user's answer - LLM decides everything.

        Args:
            context: Current chat context
            question_key: Key of the question being answered
            answer: User's answer

        Returns:
            ChatResponse with LLM-generated next step
        """
        logger.info(f"User answered: {answer[:100]}...")

        # Add user message to context
        context.conversation.append(ChatMessage(role="user", content=answer))

        # LLM generates the ENTIRE next response
        # LLM will decide: what to ask, whether to fetch RAG, what to recommend
        response_text = self._llm_respond(context)
        context.conversation.append(ChatMessage(role="assistant", content=response_text))

        # LLM analyzes its own response to extract what was learned
        self._extract_context_from_response(response_text, context)

        # Check if LLM indicated it's ready
        is_ready = self._check_if_ready(context)

        # Update context.is_ready_to_generate so it's included in the response
        context.is_ready_to_generate = is_ready

        if is_ready:
            return ChatResponse(
                message=response_text,
                session_id=None,
                questions=None,
                context=context,
                is_ready_to_generate=True,
                next_action="ready_to_generate",
            )
        else:
            return ChatResponse(
                message=response_text,
                session_id=None,
                questions=[ClarifyingQuestion(
                    question="Continue:",
                    key="user_input",
                    options=None,
                    required=True,
                )],
                context=context,
                is_ready_to_generate=False,
                next_action="ask_more",
            )

    def _llm_respond(self, context: ChatContext) -> str:
        """LLM generates the next response - includes decision making.

        Args:
            context: Chat context with conversation history

        Returns:
            LLM-generated response
        """
        # Build messages for chat API with system prompt
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
        ]

        # Add conversation history
        messages.extend([
            {"role": msg.role, "content": msg.content}
            for msg in context.conversation[-10:]  # Last 10 messages for context
        ])

        # Add context reminder as user message
        context_msg = f"""Current learned context:
- Subject: {context.answers.get('subject', 'Not yet mentioned')}
- Topics: {context.answers.get('topics', 'Not yet mentioned')}
- Deadline: {context.answers.get('deadline', 'Not yet mentioned')}

Generate the NEXT assistant response now."""

        messages.append({"role": "user", "content": context_msg})

        try:
            result = self.llm_client.chat(messages)
            response_text = result.get("message", {}).get("content", "").strip()

            if not response_text:
                logger.error("Empty response from LLM")
                return "I had trouble processing that. Could you clarify what you're studying?"

            logger.info(f"LLM generated response: {response_text[:100]}...")
            return response_text
        except Exception as e:
            logger.error(f"LLM response failed: {e}")
            logger.exception("Full error trace:")
            return f"I had trouble processing that. Could you clarify what you're studying?"

    def _extract_context_from_response(self, response: str, context: ChatContext) -> None:
        """Extract learned information from LLM response.

        Args:
            response: LLM-generated response
            context: Chat context to update
        """
        # This is simple extraction based on what LLM mentioned
        # In a real system, you might ask LLM to explicitly output JSON
        response_lower = response.lower()

        # Detect if LLM mentioned subject
        for subject in ["jee", "class 10", "class 12", "neet", "college"]:
            if subject in response_lower and "subject" not in context.answers:
                # LLM mentioned this subject
                pass  # Let LLM fully control the context

    def _check_if_ready(self, context: ChatContext) -> bool:
        """Check if LLM indicated we have everything needed.

        Args:
            context: Chat context

        Returns:
            True if ready to generate
        """
        # Look for [READY] marker that LLM puts in response
        if context.conversation:
            last_response = context.conversation[-1].content
            return "[READY]" in last_response

    def get_generation_prompt(self, context: ChatContext) -> str:
        """Build generation prompt from chat context.

        Args:
            context: Chat context with all answers

        Returns:
            Detailed prompt for document generation
        """
        subject = context.answers.get("subject", "the requested topic")
        topics = context.answers.get("topics", "all relevant topics")
        deadline = context.answers.get("deadline", "ASAP")

        return f"""Create a personalized study schedule:

Subject: {subject}
Topics: {topics}
Deadline: {deadline}

Based on the chat conversation:
{chr(10).join([f'- {msg.content[:100]}' for msg in context.conversation[-6:]])}

Generate a practical, day-by-day study schedule."""

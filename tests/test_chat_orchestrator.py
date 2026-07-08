"""Tests for chat-based document generation."""

import pytest

from server.chat_orchestrator import ChatOrchestrator
from server.models import ChatContext, ChatMessage


class TestChatOrchestrator:
    """Test chat orchestrator functionality."""

    def test_start_conversation(self):
        """Test starting a new conversation."""
        orchestrator = ChatOrchestrator()

        response = orchestrator.start_conversation(
            "Create a technical specification for a REST API"
        )

        assert response.message
        assert response.questions
        assert len(response.questions) > 0
        assert not response.is_ready_to_generate
        assert response.next_action == "ask_more"
        assert response.context.initial_request

    def test_add_required_answers(self):
        """Test adding answers to required questions."""
        orchestrator = ChatOrchestrator()

        # Start conversation
        response1 = orchestrator.start_conversation("Create a business proposal")
        context = response1.context

        # Answer first question
        response2 = orchestrator.add_answer(context, "audience", "Executive team")
        assert not response2.is_ready_to_generate

        # Answer second question
        response3 = orchestrator.add_answer(response2.context, "scope", "Detailed (5-10 pages)")
        assert not response3.is_ready_to_generate

        # Answer third required question
        response4 = orchestrator.add_answer(
            response3.context, "tone", "Professional but conversational"
        )
        assert response4.is_ready_to_generate
        assert response4.next_action == "ready_to_generate"

    def test_optional_questions(self):
        """Test handling optional questions."""
        orchestrator = ChatOrchestrator()

        response = orchestrator.start_conversation("Write a technical doc")
        context = response.context

        # Answer all required questions
        response = orchestrator.add_answer(context, "audience", "Technical team")
        response = orchestrator.add_answer(response.context, "scope", "Brief (1-3 pages)")
        response = orchestrator.add_answer(response.context, "tone", "Formal")

        # Should be ready after all required questions
        assert response.is_ready_to_generate

    def test_context_accumulation(self):
        """Test that context accumulates properly."""
        orchestrator = ChatOrchestrator()

        response = orchestrator.start_conversation("Create documentation")
        context = response.context

        assert len(context.answers) == 0
        assert len(context.conversation) > 0

        # Answer question
        response = orchestrator.add_answer(context, "audience", "Developers")
        context = response.context

        assert "audience" in context.answers
        assert context.answers["audience"] == "Developers"
        assert len(context.conversation) > 1

    def test_confidence_level(self):
        """Test confidence level increases with answers."""
        orchestrator = ChatOrchestrator()

        response = orchestrator.start_conversation("Create a spec")
        context = response.context
        initial_confidence = context.confidence_level

        response = orchestrator.add_answer(context, "audience", "Technical")
        new_confidence = response.context.confidence_level

        assert new_confidence > initial_confidence

    def test_generation_prompt(self):
        """Test generation prompt building from context."""
        orchestrator = ChatOrchestrator()

        response = orchestrator.start_conversation("Create a proposal")
        context = response.context

        # Build context with answers
        context.answers = {
            "audience": "Executive",
            "scope": "Detailed",
            "tone": "Professional",
            "sections": "Executive summary, details, appendix",
        }
        context.is_ready_to_generate = True

        prompt = orchestrator.get_generation_prompt(context)

        assert "Executive" in prompt
        assert "Detailed" in prompt
        assert "Professional" in prompt
        assert "Executive summary" in prompt

    def test_export_conversation(self):
        """Test conversation export as text."""
        orchestrator = ChatOrchestrator()

        response = orchestrator.start_conversation("Create documentation")
        context = response.context

        response = orchestrator.add_answer(context, "audience", "Developers")
        response = orchestrator.add_answer(response.context, "scope", "Comprehensive")
        context = response.context

        export = orchestrator.export_conversation(context)

        assert "Conversation" in export
        assert "Developers" in export
        assert "Comprehensive" in export


class TestChatModels:
    """Test chat-related Pydantic models."""

    def test_chat_message_creation(self):
        """Test creating chat messages."""
        from server.models import ChatMessage

        msg = ChatMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.timestamp

    def test_clarifying_question_creation(self):
        """Test creating clarifying questions."""
        from server.models import ClarifyingQuestion

        q = ClarifyingQuestion(
            question="What is the audience?",
            key="audience",
            options=["Technical", "General"],
            required=True,
        )
        assert q.question
        assert q.key == "audience"
        assert len(q.options) == 2

    def test_chat_context_creation(self):
        """Test creating chat context."""
        from server.models import ChatContext

        context = ChatContext(initial_request="Create a spec")
        assert context.initial_request
        assert len(context.conversation) == 0
        assert len(context.answers) == 0
        assert not context.is_ready_to_generate

    def test_chat_response_creation(self):
        """Test creating chat response."""
        from server.models import ChatResponse, ChatContext

        context = ChatContext(initial_request="Test")
        response = ChatResponse(
            message="Starting...",
            context=context,
            is_ready_to_generate=False,
            next_action="ask_more",
        )
        assert response.message
        assert response.next_action == "ask_more"

"""End-to-end tests with two test inputs: standard and complex."""

from unittest.mock import Mock, patch
import pytest

from server.orchestrator import Orchestrator
from server.models import DocumentRequest


class TestStandardBusinessRequest:
    """Test Input 1: Standard, well-defined business request."""

    @patch("server.tools.ollama_client.requests.get")
    @patch("server.tools.ollama_client.requests.post")
    def test_standard_project_plan_request(self, mock_post, mock_get):
        """
        TEST INPUT 1: Standard Request

        Request: "Create a project plan for a web application that needs user
        authentication, payment processing, and real-time notifications.
        We have 3 months and a team of 5."

        Expected behavior:
        - Document type clearly identified: "Project Plan"
        - All requirements explicitly covered
        - No ambiguity requiring assumptions
        - High quality score (4.8-5.0/5)
        """
        # Mock Ollama connection
        mock_get.return_value.json.return_value = {"models": []}
        mock_get.return_value.status_code = 200

        # Mock Planner response - clear TODO list
        planner_response = {
            "document_type": "Project Plan",
            "assumptions": {
                "team_size": "5 developers",
                "timeline": "3 months",
                "features": "Authentication, Payment Processing, Real-time Notifications"
            },
            "tasks": [
                {"id": 1, "description": "Define project scope", "dependencies": []},
                {"id": 2, "description": "Design technical architecture", "dependencies": [1]},
                {"id": 3, "description": "Create resource plan", "dependencies": [1]},
                {"id": 4, "description": "Develop implementation timeline", "dependencies": [2, 3]},
                {"id": 5, "description": "Identify risks and mitigation", "dependencies": [4]},
                {"id": 6, "description": "Define success metrics", "dependencies": [5]}
            ],
            "outline": [
                "Executive Summary",
                "Project Scope",
                "Technical Architecture",
                "Resource Plan",
                "Development Timeline",
                "Risk Management",
                "Success Metrics"
            ]
        }

        # Mock Writer responses
        writer_responses = [
            {"title": "Executive Summary", "content": "Web application with auth, payments, real-time...", "heading_level": 1},
            {"title": "Project Scope", "content": "Scope covers user authentication via OAuth...", "heading_level": 1},
            {"title": "Technical Architecture", "content": "Frontend: React, Backend: FastAPI, DB: PostgreSQL...", "heading_level": 1},
            {"title": "Resource Plan", "content": "Team of 5 distributed as 2 frontend, 2 backend, 1 devops...", "heading_level": 1},
            {"title": "Development Timeline", "content": "Sprint 1-2: Setup. Sprint 3-6: Feature development. Sprint 7-8: Testing...", "heading_level": 1},
            {"title": "Risk Management", "content": "Key risks include integration complexity, payment processing...", "heading_level": 1},
            {"title": "Success Metrics", "content": "On-time delivery, zero critical bugs, 99.5% uptime SLA...", "heading_level": 1}
        ]

        # Mock Reviewer response - high quality
        review_response = {
            "has_issues": False,
            "grammar_issues": [],
            "consistency_issues": [],
            "structure_issues": [],
            "tone_issues": [],
            "corrections": "Document is well-structured and comprehensive"
        }

        score_response = {
            "relevance": 5,
            "completeness": 5,
            "coherence": 5,
            "structure": 5,
            "overall": 5
        }

        # Configure mock responses
        call_count = [0]
        def mock_post_side_effect(*args, **kwargs):
            call_count[0] += 1

            if call_count[0] == 1:  # Planner
                return Mock(json=lambda: {"response": str(planner_response)}, status_code=200)
            elif 2 <= call_count[0] <= 8:  # Writer (7 sections)
                section_idx = call_count[0] - 2
                response = writer_responses[section_idx] if section_idx < len(writer_responses) else writer_responses[-1]
                return Mock(json=lambda r=response: {"response": str(r)}, status_code=200)
            elif call_count[0] == 9:  # Reviewer
                return Mock(json=lambda: {"response": str(review_response)}, status_code=200)
            else:  # Scorer
                return Mock(json=lambda: {"response": str(score_response)}, status_code=200)

        mock_post.side_effect = mock_post_side_effect

        # Execute
        orchestrator = Orchestrator()
        request = DocumentRequest(
            request="Create a project plan for a web application that needs user authentication, "
                   "payment processing, and real-time notifications. We have 3 months and a team of 5."
        )

        with patch("config.config.document_output_dir", "/tmp/test_docs"):
            response = orchestrator.generate_document(request)

        # Assertions
        assert response.success is True
        assert response.execution_plan.document_type == "Project Plan"
        assert len(response.execution_plan.tasks) == 6  # 6 tasks generated
        assert len(response.execution_plan.outline) == 7  # 7 sections
        assert response.quality_scores.overall == 5  # High quality for clear request
        assert response.metrics.review_iterations <= 1


class TestComplexAmbiguousRequest:
    """Test Input 2: Complex, ambiguous business request requiring autonomous reasoning."""

    @patch("tools.ollama_client.requests.get")
    @patch("tools.ollama_client.requests.post")
    def test_complex_improvement_proposal(self, mock_post, mock_get):
        """
        TEST INPUT 2: Complex/Ambiguous Request

        Request: "We need a document but not sure what kind. Something about
        improving our development process. Maybe a process document? Or a proposal?
        We have high turnover and slow deployments. The document should help
        stakeholders understand the changes. We also need it to convince management
        to fund the initiative. What should we do?"

        Complexity factors:
        - Unclear document type (process vs proposal)
        - Multiple conflicting goals (educate vs convince)
        - Multiple stakeholders (team vs management)
        - Missing technical details
        - Requires agent to make assumptions

        Expected behavior:
        - Agent infers hybrid document type
        - Makes reasonable assumptions explicitly
        - Addresses all unstated concerns
        - Good quality despite ambiguity (4.0-4.5/5)
        """
        # Mock Ollama connection
        mock_get.return_value.json.return_value = {"models": []}
        mock_get.return_value.status_code = 200

        # Mock Planner response - agent makes autonomous decisions
        planner_response = {
            "document_type": "Proposal + Process Improvement SOP",
            "assumptions": {
                "current_problem": "Slow deployments and high team turnover",
                "solution": "CI/CD pipeline automation",
                "timeline": "6 weeks implementation",
                "estimated_cost": "$75,000",
                "payoff_period": "4.5 months",
                "primary_audience": "C-level executives (for funding approval)",
                "secondary_audience": "Development team (for implementation)",
                "expected_benefit": "8x faster deployments, improved team satisfaction"
            },
            "tasks": [
                {"id": 1, "description": "Analyze current deployment process", "dependencies": []},
                {"id": 2, "description": "Research CI/CD best practices", "dependencies": []},
                {"id": 3, "description": "Create improvement roadmap", "dependencies": [1, 2]},
                {"id": 4, "description": "Calculate ROI and cost-benefit", "dependencies": [3]},
                {"id": 5, "description": "Estimate implementation costs", "dependencies": [3]},
                {"id": 6, "description": "Write detailed process SOP", "dependencies": [3]},
                {"id": 7, "description": "Create executive summary", "dependencies": [4, 5]},
                {"id": 8, "description": "Review for persuasiveness", "dependencies": [7]}
            ],
            "outline": [
                "Executive Summary",
                "Current State Analysis",
                "Improvement Strategy",
                "Implementation Roadmap",
                "Cost-Benefit Analysis",
                "Risk Management",
                "Detailed Process SOP"
            ]
        }

        # Mock Writer responses for complex document
        writer_responses = [
            {
                "title": "Executive Summary",
                "content": "Slow deployments and team stress contribute to turnover. CI/CD implementation offers 8x faster releases...",
                "heading_level": 1
            },
            {
                "title": "Current State Analysis",
                "content": "Today deployments take 2 hours, are error-prone, and cause team frustration...",
                "heading_level": 1
            },
            {
                "title": "Improvement Strategy",
                "content": "Implement GitHub Actions, automated tests, blue-green deployments...",
                "heading_level": 1
            },
            {
                "title": "Implementation Roadmap",
                "content": "Week 1-2: CI/CD setup. Week 3-4: Testing automation. Week 5-6: Blue-green deployment...",
                "heading_level": 1
            },
            {
                "title": "Cost-Benefit Analysis",
                "content": "$75K investment yields $200K annual savings. Payoff in 4.5 months. 5-year ROI: $925K...",
                "heading_level": 1
            },
            {
                "title": "Risk Management",
                "content": "Main risks: learning curve, early failures. Mitigations: training, canary releases...",
                "heading_level": 1
            },
            {
                "title": "Detailed Process SOP",
                "content": "Step 1: Commit code. Step 2: Automated tests. Step 3: Approval. Step 4: Deploy...",
                "heading_level": 1
            }
        ]

        # Mock Reviewer response - catches incomplete ROI, suggests revision
        review_response = {
            "has_issues": True,
            "grammar_issues": [],
            "consistency_issues": [],
            "structure_issues": ["ROI calculation could show monthly breakdown"],
            "tone_issues": [],
            "corrections": "Revise Cost-Benefit section with month-by-month savings breakdown"
        }

        score_response = {
            "relevance": 4,
            "completeness": 4,
            "coherence": 5,
            "structure": 5,
            "overall": 4
        }

        # Configure mock responses
        call_count = [0]
        def mock_post_side_effect(*args, **kwargs):
            call_count[0] += 1

            if call_count[0] == 1:  # Planner
                return Mock(json=lambda: {"response": str(planner_response)}, status_code=200)
            elif 2 <= call_count[0] <= 8:  # Writer (7 sections)
                section_idx = call_count[0] - 2
                response = writer_responses[section_idx] if section_idx < len(writer_responses) else writer_responses[-1]
                return Mock(json=lambda r=response: {"response": str(r)}, status_code=200)
            elif call_count[0] == 9:  # Reviewer
                return Mock(json=lambda: {"response": str(review_response)}, status_code=200)
            else:  # Scorer
                return Mock(json=lambda: {"response": str(score_response)}, status_code=200)

        mock_post.side_effect = mock_post_side_effect

        # Execute
        orchestrator = Orchestrator()
        request = DocumentRequest(
            request="We need a document but not sure what kind. Something about improving our "
                   "development process. Maybe a process document? Or a proposal? We have high turnover "
                   "and slow deployments. The document should help stakeholders understand the changes. "
                   "We also need it to convince management to fund the initiative. What should we do?"
        )

        with patch("config.config.document_output_dir", "/tmp/test_docs"):
            response = orchestrator.generate_document(request)

        # Assertions - verify autonomous decision-making
        assert response.success is True

        # Agent inferred hybrid document type
        assert "Proposal" in response.execution_plan.document_type
        assert "SOP" in response.execution_plan.document_type or "Process" in response.execution_plan.document_type

        # Agent made multiple reasonable assumptions
        assert len(response.assumptions) >= 5
        assert "CI/CD" in str(response.assumptions) or "automation" in str(response.assumptions).lower()
        assert "ROI" in str(response.assumptions) or "cost" in str(response.assumptions).lower()

        # More complex → more tasks
        assert len(response.execution_plan.tasks) >= 6

        # Addresses ambiguity → good score despite complexity
        assert 3.5 <= response.quality_scores.overall <= 4.5

        # Reviewer found issues and iterated
        assert response.metrics.review_iterations >= 1


class TestAutonomousDecisionMaking:
    """Test that the agent makes reasonable autonomous decisions."""

    @patch("tools.ollama_client.requests.get")
    @patch("tools.ollama_client.requests.post")
    def test_agent_infers_document_type(self, mock_post, mock_get):
        """Verify agent can infer document type from context."""
        mock_get.return_value.json.return_value = {"models": []}
        mock_get.return_value.status_code = 200

        # Request doesn't explicitly say "SOP" but context implies it
        planner_response = {
            "document_type": "Standard Operating Procedure (SOP)",
            "assumptions": {"context": "process documentation"},
            "tasks": [{"id": 1, "description": "Document process", "dependencies": []}],
            "outline": ["Overview", "Steps"]
        }

        writer_response = {
            "title": "Overview",
            "content": "This SOP documents the process...",
            "heading_level": 1
        }

        review_response = {
            "has_issues": False,
            "grammar_issues": [],
            "consistency_issues": [],
            "structure_issues": [],
            "tone_issues": [],
            "corrections": "Good"
        }

        score_response = {
            "relevance": 4,
            "completeness": 4,
            "coherence": 4,
            "structure": 4,
            "overall": 4
        }

        call_count = [0]
        def mock_post_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return Mock(json=lambda: {"response": str(planner_response)}, status_code=200)
            elif call_count[0] == 2:
                return Mock(json=lambda: {"response": str(writer_response)}, status_code=200)
            elif call_count[0] == 3:
                return Mock(json=lambda: {"response": str(review_response)}, status_code=200)
            else:
                return Mock(json=lambda: {"response": str(score_response)}, status_code=200)

        mock_post.side_effect = mock_post_side_effect

        orchestrator = Orchestrator()
        request = DocumentRequest(
            request="Document how we should handle customer onboarding"
        )

        with patch("config.config.document_output_dir", "/tmp/test_docs"):
            response = orchestrator.generate_document(request)

        # Agent should infer document type
        assert "SOP" in response.execution_plan.document_type or "Procedure" in response.execution_plan.document_type
        assert response.success is True


class TestReflectionAndSelfCheck:
    """Test the Reviewer Agent's reflection/self-check improvement."""

    @patch("tools.ollama_client.requests.get")
    @patch("tools.ollama_client.requests.post")
    def test_reviewer_catches_quality_issues(self, mock_post, mock_get):
        """Verify Reviewer Agent catches and flags issues."""
        mock_get.return_value.json.return_value = {"models": []}
        mock_get.return_value.status_code = 200

        planner_response = {
            "document_type": "Report",
            "assumptions": {},
            "tasks": [{"id": 1, "description": "Task", "dependencies": []}],
            "outline": ["Section 1"]
        }

        writer_response = {
            "title": "Section 1",
            "content": "Content with mispeling and inconsistent terminology",
            "heading_level": 1
        }

        # Reviewer catches issues
        review_response = {
            "has_issues": True,
            "grammar_issues": ["Spelling error: 'mispeling' should be 'misspelling'"],
            "consistency_issues": ["Inconsistent terminology usage"],
            "structure_issues": [],
            "tone_issues": [],
            "corrections": "Fix spelling. Use consistent terminology throughout."
        }

        score_response = {
            "relevance": 3,
            "completeness": 3,
            "coherence": 3,
            "structure": 3,
            "overall": 3
        }

        call_count = [0]
        def mock_post_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return Mock(json=lambda: {"response": str(planner_response)}, status_code=200)
            elif call_count[0] == 2:
                return Mock(json=lambda: {"response": str(writer_response)}, status_code=200)
            elif call_count[0] == 3:
                return Mock(json=lambda: {"response": str(review_response)}, status_code=200)
            else:
                return Mock(json=lambda: {"response": str(score_response)}, status_code=200)

        mock_post.side_effect = mock_post_side_effect

        orchestrator = Orchestrator()
        request = DocumentRequest(request="Test document")

        with patch("config.config.document_output_dir", "/tmp/test_docs"):
            response = orchestrator.generate_document(request)

        # Verify Reviewer found issues
        assert response.metrics.review_iterations >= 1
        # Lower quality score indicates issues were found
        assert response.quality_scores.overall <= 3


class TestExecutionMetrics:
    """Test that metrics are properly collected."""

    @patch("tools.ollama_client.requests.get")
    @patch("tools.ollama_client.requests.post")
    def test_metrics_collection(self, mock_post, mock_get):
        """Verify all metrics are collected during execution."""
        mock_get.return_value.json.return_value = {"models": []}
        mock_get.return_value.status_code = 200

        planner_response = {
            "document_type": "Plan",
            "assumptions": {},
            "tasks": [{"id": 1, "description": "Task", "dependencies": []}],
            "outline": ["Section"]
        }

        writer_response = {
            "title": "Section",
            "content": "Content",
            "heading_level": 1
        }

        review_response = {
            "has_issues": False,
            "grammar_issues": [],
            "consistency_issues": [],
            "structure_issues": [],
            "tone_issues": [],
            "corrections": ""
        }

        score_response = {
            "relevance": 4,
            "completeness": 4,
            "coherence": 4,
            "structure": 4,
            "overall": 4
        }

        call_count = [0]
        def mock_post_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return Mock(json=lambda: {"response": str(planner_response)}, status_code=200)
            elif call_count[0] == 2:
                return Mock(json=lambda: {"response": str(writer_response)}, status_code=200)
            elif call_count[0] == 3:
                return Mock(json=lambda: {"response": str(review_response)}, status_code=200)
            else:
                return Mock(json=lambda: {"response": str(score_response)}, status_code=200)

        mock_post.side_effect = mock_post_side_effect

        orchestrator = Orchestrator()
        request = DocumentRequest(request="Test")

        with patch("config.config.document_output_dir", "/tmp/test_docs"):
            response = orchestrator.generate_document(request)

        # Verify metrics collected
        assert response.metrics.planner_latency_ms > 0
        assert response.metrics.writer_latency_ms > 0
        assert response.metrics.reviewer_latency_ms > 0
        assert response.metrics.docx_generation_latency_ms > 0
        assert response.metrics.total_execution_time_ms > 0
        assert response.metrics.num_generated_tasks >= 1
        assert response.metrics.review_iterations >= 0

        # Quality scores collected
        assert 1 <= response.quality_scores.relevance <= 5
        assert 1 <= response.quality_scores.completeness <= 5
        assert 1 <= response.quality_scores.coherence <= 5
        assert 1 <= response.quality_scores.structure <= 5
        assert 1 <= response.quality_scores.overall <= 5

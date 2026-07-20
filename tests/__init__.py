"""Test suite for RAG document generation application.

Test Organization:
- unit/     → Unit tests (fast, isolated component testing)
- e2e/      → End-to-end tests (full workflows and orchestration)
- smoke/    → Smoke tests (API endpoints and critical paths)

Run all tests:
    pytest

Run specific test type:
    pytest tests/unit/
    pytest tests/e2e/
    pytest tests/smoke/

Run with coverage:
    pytest --cov=server tests/

Run with verbose output:
    pytest -v tests/

Run specific test file:
    pytest tests/unit/test_docx_generator.py
"""

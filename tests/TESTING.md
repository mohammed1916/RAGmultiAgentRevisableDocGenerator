# Testing Strategy

## Overview

Tests are organized into three categories based on scope and execution speed:

1. **Unit Tests** - Fast, isolated component testing
2. **End-to-End (E2E) Tests** - Full workflow testing
3. **Smoke Tests** - Critical path API testing

## Test Organization

```
tests/
├── unit/                      (5 tests - ~5s)
│   ├── test_docx_generator.py
│   ├── test_markdown_formatter.py
│   ├── test_milvus_rag.py
│   ├── test_ollama_client.py
│   └── test_ollama_cloud_config.py
│
├── e2e/                       (1 test - ~30s)
│   └── test_langgraph_orchestrator.py
│
├── smoke/                     (1 test - ~5s)
│   └── test_api.py
│
├── conftest.py               (Shared fixtures)
└── TESTING.md               (This file)
```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run by Category
```bash
# Unit tests only (fast)
pytest tests/unit/

# End-to-end tests (slower)
pytest tests/e2e/

# Smoke tests (API checks)
pytest tests/smoke/
```

### Run Specific Test
```bash
pytest tests/unit/test_docx_generator.py
pytest tests/unit/test_docx_generator.py::TestDocxGenerator::test_generate_valid_document
```

### With Coverage
```bash
pytest --cov=server tests/
pytest --cov=server --cov-report=html tests/
```

### With Verbose Output
```bash
pytest -v tests/
pytest -vv tests/        # Extra verbose
```

### Run Async Tests Only
```bash
pytest -m async tests/
```

## Test Categories

### Unit Tests (tests/unit/)

**Purpose:** Test individual components in isolation.

**Characteristics:**
- No external dependencies
- Fast execution (< 1s each)
- Mock external services
- Test single function/class behavior

**Files:**
- `test_docx_generator.py` - Document generation
- `test_markdown_formatter.py` - Markdown formatting
- `test_milvus_rag.py` - RAG system operations
- `test_ollama_client.py` - LLM client operations
- `test_ollama_cloud_config.py` - Configuration

**Run:**
```bash
pytest tests/unit/
```

### End-to-End Tests (tests/e2e/)

**Purpose:** Test complete workflows with all components.

**Characteristics:**
- Full integration of components
- Tests the LangGraph orchestrator
- Includes state management and routing
- Slower but more realistic
- Async tests

**Files:**
- `test_langgraph_orchestrator.py` - Document generation pipeline

**Run:**
```bash
pytest tests/e2e/
```

### Smoke Tests (tests/smoke/)

**Purpose:** Quick validation of critical API paths.

**Characteristics:**
- Test API endpoints
- Basic functionality checks
- Fast execution
- Catch obvious breakage

**Files:**
- `test_api.py` - FastAPI routes

**Run:**
```bash
pytest tests/smoke/
```

## Shared Fixtures (conftest.py)

Common test fixtures available to all tests:

- `sample_document_request` - Sample API request
- `sample_execution_plan` - Sample plan for testing
- `mock_milvus_rag` - Mock RAG instance
- `sample_chunks` - Test curriculum chunks
- `mock_ollama_client` - Mock LLM client

### Using Fixtures

```python
def test_something(sample_document_request):
    # sample_document_request is automatically injected
    assert sample_document_request["request"]
```

## Pytest Configuration

Configuration in `pytest.ini`:

- **Test paths:** `tests/`
- **Async mode:** `auto`
- **Output:** Verbose with short traceback
- **Markers:** `unit`, `e2e`, `smoke`, `slow`, `async`

### Custom Markers

Mark tests to run specific subsets:

```python
@pytest.mark.slow
def test_slow_operation():
    pass

@pytest.mark.async
def test_async_function():
    pass
```

Run marked tests:
```bash
pytest -m slow       # Only slow tests
pytest -m async      # Only async tests
pytest -m "not slow" # All except slow
```

## Deleted Tests

The following outdated tests were removed:

| Test | Reason |
|------|--------|
| `test_agents.py` | Superseded by LangGraph E2E tests |
| `test_integration.py` | Replaced with LangGraph E2E tests |
| `test_milvus_chunks_view.py` | Utility tests, not critical |
| `test_mock_chunks.py` | Mock data tests, not needed with real data |

## Test Coverage

Current coverage focus:

- **Unit:** Individual component functionality
- **E2E:** Complete document generation workflow
- **Smoke:** API reliability and basic functionality

To measure coverage:
```bash
pytest --cov=server --cov-report=term-missing tests/
```

## CI/CD Integration

Recommended CI configuration:

```yaml
# Run unit tests first (fast)
- pytest tests/unit/

# Run smoke tests (critical)
- pytest tests/smoke/

# Run E2E tests (slower)
- pytest tests/e2e/

# Report coverage
- pytest --cov=server tests/
```

## Best Practices

1. **Unit Tests:** Test functions/classes in isolation
2. **Fixtures:** Use conftest.py for shared setup
3. **Mocking:** Mock external APIs and services
4. **Async:** Use `@pytest.mark.asyncio` for async tests
5. **Markers:** Use markers for selective test runs

## Troubleshooting

### Tests fail with import errors
```bash
# Add parent directory to path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Async tests timeout
```bash
# Check asyncio_mode in pytest.ini (should be "auto")
# Increase timeout if needed
pytest --timeout=60 tests/e2e/
```

### Fixtures not found
```bash
# Ensure conftest.py is in tests/ directory
# Restart pytest after conftest.py changes
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Async Testing with Pytest](https://pytest-asyncio.readthedocs.io/)
- [Test Coverage](https://coverage.readthedocs.io/)

# Test Fixtures

This directory contains test fixtures and mock data for development and testing.

## mock_data.py

**Purpose:** Provides realistic mock data for testing without requiring Ollama or real curriculum data.

**Usage:**
```python
from server.tools.fixtures import MockData

# Load mock JEE study plan
plan = MockData.get_jee_study_plan()

# Load mock curriculum chunks for testing
jee_chunks = MockData.get_mock_chunks_jee()
cbse_chunks = MockData.get_mock_chunks_cbse()
python_chunks = MockData.get_mock_chunks_python()
```

**Available Methods:**
- `get_jee_study_plan()` - JEE Mathematics study plan
- `get_cbse_study_plan()` - CBSE Class 12 study plan
- `get_mock_chunks_jee()` - Mock JEE curriculum chunks
- `get_mock_chunks_cbse()` - Mock CBSE curriculum chunks
- `get_mock_chunks_python()` - Mock Python programming chunks
- And more...

**Used By:**
- `scripts/view_chunks.py` - `--load-mock` command for testing chunk viewer
- Testing utilities
- Development without Ollama/Milvus

## When to Use

Use mock data when:
- Testing the chunk viewer without loading real curriculum
- Developing features that depend on curriculum data
- Running tests in CI/CD without Milvus
- Demonstrations and prototyping

## When NOT to Use

Do NOT use mock data for:
- Production systems
- Actual curriculum loading
- Real RAG quality metrics (use actual curriculum data)
- Performance benchmarking (mock data is simplified)

## Adding More Fixtures

To add new mock data:

1. Add a new method to the `MockData` class
2. Follow the naming convention: `get_<type>_<description>()`
3. Return the appropriate object type (ExecutionPlan, chunks, etc.)
4. Document the method in this README

Example:
```python
@staticmethod
def get_mock_organic_chemistry():
    """Mock organic chemistry curriculum."""
    return ExecutionPlan(...)
```

---

**Location Changed:** Moved from `server/base/` to `server/tools/fixtures/` on 2026-07-13
**Reason:** Test fixtures belong with tools, not core base utilities

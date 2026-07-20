# Retrieval Planning System - Integration Guide

## Overview

The new **Retrieval Planning System** has been integrated into the document generation pipeline, replacing direct RAG calls with intelligent planning-based retrieval.

### What Changed

| Component | Before | After |
|-----------|--------|-------|
| **WriterAgent RAG** | Direct `MilvusRAG.search()` | `RetrievalOrchestrator.retrieve()` |
| **Retrieval Logic** | Fixed collection selection | Dynamic planning + execution |
| **Context Awareness** | No session history | Session-aware planning |
| **Error Handling** | Generic exceptions | Domain-specific (PlanningException, RetrievalException) |

## Architecture

```
WriterAgent._fetch_rag_context()
    ↓
RetrievalOrchestrator.retrieve()
    ├─ RetrievalPlanner (phase 1)
    │  ├─ Analyzes query
    │  ├─ Plans collections to search
    │  ├─ Determines filters & top_k
    │  └─ Returns RetrievalPlan
    ├─ Retriever (phase 2)
    │  ├─ Executes plan
    │  ├─ Searches Milvus
    │  ├─ Applies filters
    │  └─ Returns RetrievalResult
    ↓
Document Context (formatted for LLM)
```

## Key Features

### 1. **Intelligent Collection Selection**
Before: `rag.search(query, class_level="12")`  
After: Planner dynamically selects collections based on query analysis

```python
# Automatic handling of:
# "Class 12 Physics" → selects cbse_class_12
# "JEE preparation" → selects jee
# "Compare CBSE and JEE" → selects both
```

### 2. **Session-Aware Planning**
Orchestrator can use conversation history for context:

```python
session_history = [
    {"role": "user", "content": "I'm preparing for Class 12 boards"},
    {"role": "assistant", "content": "Let me help with materials"},
]
result = orchestrator.retrieve(
    "What about Physics?",
    session_history=session_history
)
```

### 3. **Metadata Filtering**
Planner can now request metadata filters:

```python
RetrievalPlan(
    collections=["cbse_class_12"],
    filters=[MetadataFilter(field="subject", value="Physics", operator="eq")],
    top_k=8,
)
```

### 4. **Extensibility for Phase 3**
Designed so evaluation/re-planning can be added without changing current code:

```python
# Future: Add result callback for evaluation
def evaluate_results(result: RetrievalResult):
    if len(result.documents) == 0:
        # trigger re-planning
        pass

retriever = Retriever(on_result_callback=evaluate_results)
```

## Integration Points

### WriterAgent

**File**: `server/agents/writer.py`

```python
# OLD
from server.tools import MilvusRAG
self.rag = MilvusRAG()
results = self.rag.search(search_query, class_level=class_level)

# NEW
from server.rag_planning import RetrievalOrchestrator
self.orchestrator = RetrievalOrchestrator()
result = self.orchestrator.retrieve(retrieval_query)
```

**Changes**:
- Replaced `MilvusRAG` with `RetrievalOrchestrator`
- Direct search call → `orchestrator.retrieve()`
- Result formatting updated to use `RetrievalResult.documents`

### LangGraphOrchestrator

**File**: `server/core/orchestrators/langgraph.py`

Can optionally integrate for session-aware retrieval:

```python
# Future: Pass conversation context to planner
session_history = [
    {"role": "user", "content": msg.content}
    for msg in state.get("messages", [])
]
result = orchestrator.retrieve(query, session_history=session_history)
```

## Configuration

### Adding New Collections

**File**: `server/rag_planning/config/collections.yaml`

```yaml
- name: new_collection
  display_name: New Collection
  description: What this collection contains
  document_count: 1000
  metadata_fields:
    subject: string
    difficulty: string
```

**That's it!** No code changes needed.

## Testing

### Test Files

- `tests/e2e/test_rag_planning_e2e.py` - Complete RAG planning E2E tests
- `tests/e2e/test_document_generation_e2e.py` - Document generation tests (unchanged)

### Running Tests

```bash
# Run RAG planning tests
pytest tests/e2e/test_rag_planning_e2e.py -v

# Run specific test class
pytest tests/e2e/test_rag_planning_e2e.py::TestRetrievalOrchestrator -v

# Run with coverage
pytest tests/e2e/test_rag_planning_e2e.py --cov=server.rag_planning
```

## Error Handling

### Domain-Specific Exceptions

```python
from server.base.exceptions import PlanningException, RetrievalException

try:
    result = orchestrator.retrieve(query)
except PlanningException as e:
    # Planning failed - invalid collections, ambiguous query, etc.
    logger.error(f"Planning error: {e}")
except RetrievalException as e:
    # Retrieval execution failed - Milvus error, no results, etc.
    logger.error(f"Retrieval error: {e}")
```

## Dependency Injection

All components support dependency injection for testing:

```python
from unittest.mock import Mock
from server.rag_planning import RetrievalOrchestrator

# Inject mock components
mock_llm = Mock()
mock_rag = Mock()

orchestrator = RetrievalOrchestrator(
    llm_client=mock_llm,
    rag_system=mock_rag,
)

# Test with mocks
result = orchestrator.retrieve(query)
mock_llm.generate.assert_called_once()
```

## Performance Considerations

### Timing Breakdown

- **Planning**: ~1-2 seconds (LLM analysis)
- **Retrieval**: ~10-100ms (Milvus search)
- **Total**: ~1-3 seconds per query

### Optimization Opportunities

1. **Decision Caching**: Cache planning decisions for identical queries
2. **Batch Planning**: Plan multiple queries at once
3. **Parallel Retrieval**: Search multiple collections in parallel
4. **Result Streaming**: Stream results as they arrive

## SOLID Principles Applied

- **S**ingle Responsibility: Planner plans, Retriever retrieves
- **O**pen/Closed: Open for Phase 3 via callbacks, closed for modification
- **L**iskov Substitution: Components swappable with mocks
- **I**nterface Segregation: Minimal, focused interfaces
- **D**ependency Inversion: Depend on abstractions (CollectionRegistry, OllamaClient)

## Future Enhancements

### Phase 3: Evaluation & Re-planning
- Add `ResultEvaluator` to validate retrieved documents
- Implement automatic re-planning if results are poor
- Track which plans succeed/fail

### Monitoring & Telemetry
- Log planning decisions for analysis
- Track retrieval success rates by collection
- Monitor latency per stage

### Query Expansion
- Multi-step retrieval for complex queries
- Related collection suggestions
- Automatic fallback strategies

### User Feedback Loop
- Learn from user satisfaction with retrieved documents
- Improve planner confidence calibration
- Personalized collection preferences

## Migration Checklist

- [x] Create RAG Planning System (Phase 1)
- [x] Implement RetrievalPlanner
- [x] Implement Retriever
- [x] Create RetrievalOrchestrator
- [x] Update WriterAgent to use new system
- [x] Add E2E tests
- [x] Fix integration bugs
- [ ] Optional: Update LangGraphOrchestrator for session awareness
- [ ] Optional: Add Phase 3 (ResultEvaluator)
- [ ] Optional: Add decision caching
- [ ] Optional: Add monitoring/telemetry

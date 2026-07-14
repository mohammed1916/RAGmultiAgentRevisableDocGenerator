# Retrieval Planning System (Phase 1)

A production-grade retrieval planning system for RAG applications. Analyzes user queries and generates structured retrieval plans **before** any vector search occurs.

## Architecture

```
User Query
    ↓
RetrievalPlanner (LLM analyzes)
    ├─ Selects collections
    ├─ Determines filters
    ├─ Estimates top_k
    └─ Flags ambiguities
    ↓
RetrievalPlan (structured output)
    ↓
Retriever (executes plan)
    ├─ Searches collections
    ├─ Applies filters
    └─ Returns results
    ↓
RetrievalResult
    ↓
LLM (generate answer)
```

## Key Design Principles

### 1. **Separation of Concerns**
- **Planner**: Decides WHAT to search (storage-agnostic)
- **Retriever**: Decides HOW to search (storage-specific)
- **Future Evaluator**: Validates IF results are good

### 2. **Configuration-Driven**
- Collections defined in `config/collections.yaml`
- No hardcoded collection knowledge in code
- Planner prompt regenerates from available collections
- Adding new collection requires ONLY config update

### 3. **Extensible Interfaces**
- `RetrievalResult` has `evaluation_metadata` field for Phase 3
- Retriever accepts `on_result_callback` for future evaluation hooks
- Designed so Phase 3 can be added without modifying Phase 1/2

### 4. **Production Quality**
- SOLID principles throughout
- Dependency injection for testability
- Proper error handling and logging
- Type hints with Pydantic validation
- Immutable RetrievalPlan (frozen)

## What Planner DECIDES

```python
RetrievalPlan(
    collections=["cbse_class_12", "jee"],      # Which to search
    filters=[                                    # What metadata to filter
        MetadataFilter(field="subject", value="Physics", operator="eq")
    ],
    top_k=8,                                    # How many results
    needs_clarification=False,                  # Is query ambiguous?
    clarification_questions=None,
    reasoning="...",
    confidence=0.9
)
```

## What Planner does NOT DECIDE

- **Reranking**: Depends on actual retrieval results (Phase 3)
- **Hybrid search**: Retriever may use keyword + semantic mix
- **Fallback strategies**: If search returns nothing, retry with different plan
- **ANN parameters**: Index-specific, retriever's responsibility
- **Result evaluation**: Phase 3 handles this

## Components

### RetrievalPlanner
- Analyzes query + conversation context
- Calls LLM with dynamic prompt
- Returns validated RetrievalPlan

```python
from server.rag_planning import RetrievalPlanner, RetrievalPlanInput

planner = RetrievalPlanner()
request = RetrievalPlanInput(query="Class 12 Physics syllabus")
plan = planner.plan(request)
print(plan.collections)  # ["cbse_class_12"]
```

### Retriever
- Executes plan against Milvus
- Applies filters
- Returns documents with metadata

```python
from server.rag_planning import Retriever

retriever = Retriever()
result = retriever.execute(plan)
print(len(result.documents))  # Number of retrieved docs
```

### RetrievalOrchestrator
- Coordinates planner + retriever
- Single interface for complete pipeline
- Recommended for integration with agents

```python
from server.rag_planning import RetrievalOrchestrator

orchestrator = RetrievalOrchestrator()
result = orchestrator.retrieve(
    query="JEE and CBSE comparison",
    session_history=[...]  # Optional
)

for doc in result.documents:
    print(f"{doc.collection}: {doc.content[:100]}...")
```

### CollectionRegistry
- Loads collections from YAML
- Validates collection names and metadata
- Provides query interface
- Singleton for app-wide access

```python
from server.rag_planning.config import CollectionRegistry

registry = CollectionRegistry()
collections = registry.get_all_collections()
registry.validate_collections(["cbse_class_12", "invalid"])  # ["cbse_class_12"]
```

## Configuration

### collections.yaml

```yaml
collections:
  - name: cbse_class_12
    display_name: CBSE Class 12
    description: |
      CBSE Class XII (12th grade) syllabi...
    document_count: 924
    metadata_fields:
      subject: string
      chapter: string
      difficulty: string
```

**To add a new collection:**
1. Add entry to `collections.yaml`
2. Update your Milvus with the collection
3. Restart app (or call `CollectionRegistry.reload()`)
4. **That's it** - planner automatically uses it!

## Pydantic Models

All requests/responses are Pydantic models with validation:

- `RetrievalPlanInput`: Query + context
- `RetrievalPlan`: Plan (immutable)
- `RetrievalResult`: Results + metadata
- `Document`: Individual retrieved doc
- `MetadataFilter`: Single filter (with Milvus conversion)
- `CollectionMetadata`: Collection definition

## Error Handling

System raises domain-specific exceptions:

```python
from server.base.exceptions import PlanningException, RetrievalException

try:
    result = orchestrator.retrieve("ambiguous query")
except PlanningException as e:
    print(f"Planning failed: {e}")
    # Handle clarification needed, invalid collections, etc.
except RetrievalException as e:
    print(f"Retrieval failed: {e}")
    # Handle Milvus errors, no results, etc.
```

## Extensibility for Phase 3

### Adding Evaluation/Re-planning

**Option 1: Result Callback**
```python
def evaluate_results(result: RetrievalResult):
    # Validate results
    if len(result.documents) == 0:
        # Trigger re-planning
        pass
    # Add evaluation metadata
    result.evaluation_metadata = {"quality": "good", ...}

retriever = Retriever(on_result_callback=evaluate_results)
```

**Option 2: Wrapper Pattern**
```python
class EvaluatingOrchestrator(RetrievalOrchestrator):
    def retrieve(self, query: str, session_history=None):
        result = super().retrieve(query, session_history)
        
        # Phase 3: Evaluate
        evaluation = self.evaluator.evaluate(result)
        
        # Phase 3b: Re-plan if needed
        if evaluation.should_replan:
            result = self._replan_and_retrieve(...)
        
        return result
```

**Option 3: Pipeline Stage**
```python
class PipelineStage:
    def execute(self, input: Any) -> Any:
        pass

# Each component (planner, retriever, evaluator) is a stage
# Compose: planner_stage → retriever_stage → evaluator_stage
```

All patterns work without modifying current Phase 1 code.

## Testing

Components are unit-testable with dependency injection:

```python
from unittest.mock import Mock
from server.rag_planning import RetrievalPlanner

mock_registry = Mock()
mock_registry.get_all_collections.return_value = [...]
mock_llm = Mock()

planner = RetrievalPlanner(llm_client=mock_llm, registry=mock_registry)
plan = planner.plan(request)

# Verify interactions
mock_llm.generate.assert_called_once()
```

## SOLID Principles Applied

- **S**ingle Responsibility: Planner plans, Retriever retrieves
- **O**pen/Closed: Open for Phase 3 via callbacks, closed for modification
- **L**iskov Substitution: Components can be swapped with mocks
- **I**nterface Segregation: Minimal, focused interfaces
- **D**ependency Inversion: Depend on abstractions (CollectionRegistry, OllamaClient)

## Performance Considerations

- LLM planning: ~1-2 seconds per query
- Milvus retrieval: ~10-100ms depending on collection size
- Filters reduce result size post-retrieval
- No re-ranking (deferred to Phase 3)

## Future Enhancements

- [ ] **Phase 3**: ResultEvaluator + re-planning
- [ ] Decision caching: Same query → same plan within TTL
- [ ] User feedback loop: Learn from which plans work best
- [ ] Metadata schema validation before retrieval
- [ ] Query expansion / multi-step retrieval
- [ ] Collection similarity search (find related collections)
- [ ] Telemetry: Track planning decisions, hit rates

# Query Routing System

A production-grade, modular collection routing system for RAG applications. Routes user queries to appropriate Milvus collections based on intelligent LLM analysis.

## Architecture Overview

```
User Query
    ↓
QueryRouter (LLM analysis + dynamic prompt)
    ↓
CollectionSelector (confidence filtering + rules)
    ↓
MilvusRAG.search_collections() (semantic search)
    ↓
Results
```

## Key Features

✅ **Configuration-Driven**: Collections defined in `collections.yaml`, not hardcoded
✅ **Dynamic Prompts**: Router prompt regenerated from available collections
✅ **Modular Design**: Each component independent and testable
✅ **Confidence Scoring**: LLM returns confidence for each collection
✅ **Flexible Filtering**: Configurable selection rules (min_confidence, source_type, max_collections)
✅ **Fallback Support**: Automatically try alternate collections if primary returns nothing
✅ **Extensible**: Add new collections without changing code

## Components

### 1. **CollectionRegistry** (`config/collection_registry.py`)
- Loads collection metadata from `collections.yaml`
- Provides query interface (by name, source_type, tags, keywords)
- Singleton pattern for app-wide access

### 2. **CollectionMetadata** (`models.py`)
- Pydantic model for collection definition
- Fields: name, display_name, description, source_type, keywords, tags, active, document_count

### 3. **PromptBuilder** (`prompt_builder.py`)
- Constructs dynamic routing prompts from available collections
- Dynamically includes only active collections
- Regenerated on each use to adapt to registry changes

### 4. **QueryRouter** (`router.py`)
- Main routing engine using LLM (OllamaClient)
- Calls LLM with dynamic prompt
- Parses JSON response
- Returns RouterResponse with confidence scores

### 5. **CollectionSelector** (`selector.py`)
- Applies filtering rules to router's decision
- Filters by confidence threshold
- Filters by source type
- Limits to max collections
- Handles fallback logic

### 6. **Updated MilvusRAG** (`tools/rag/milvus_rag.py`)
- New `search_collections(query, collection_names)` method
- Takes explicit list of collections (from router)
- Searches all collections and merges results
- Old `search()` method still supported (backward compatible)

## Configuration

### `collections.yaml` Structure

```yaml
collections:
  - name: cbse_class_10
    display_name: CBSE Class 10
    description: CBSE Class X syllabi...
    source_type: cbse
    keywords: [Class 10, secondary, board exam, ...]
    tags: [board, science, mathematics, ...]
    active: true
    document_count: 126
```

**Adding a New Collection:**
1. Add entry to `collections.yaml`
2. Create Milvus collection and load data
3. Restart app (or call `CollectionRegistry.reload()`)
4. Router automatically includes it

No code changes needed.

## Usage Examples

### Basic Routing

```python
from server.routing import QueryRouter, RouterRequest, SelectorConfig

# Create router (uses default Ollama client and registry)
router = QueryRouter()

# Simple request
request = RouterRequest(query="Class 12 Physics syllabus")
response = router.route(request)

print(response.decision.selected_collections)
# Output: ['cbse_class_12']
```

### With Filtering Rules

```python
from server.routing import QueryRouter, RouterRequest, SelectorConfig

router = QueryRouter()

# Only CBSE collections, min confidence 0.8
config = SelectorConfig(
    min_confidence=0.8,
    source_types=["cbse"],
    max_collections=2,
)

request = RouterRequest(query="Prepare for board exam", selector_config=config)
response = router.route(request)
```

### Integration with RAG Retrieval

```python
from server.routing import QueryRouter, RouterRequest
from server.tools import MilvusRAG

router = QueryRouter()
rag = MilvusRAG()

# Step 1: Route query to collections
request = RouterRequest(query="Optics in Class 12 Physics")
response = router.route(request)

# Step 2: Search using routed collections
results = rag.search_collections(
    query=request.query,
    collection_names=response.decision.selected_collections,
    top_k=5
)

# Step 3: Generate using results
# ... (generate document with retrieved context)
```

### Full Pipeline with Fallback

```python
from server.routing import QueryRouter, RouterRequest, CollectionSelector
from server.tools import MilvusRAG

router = QueryRouter()
selector = CollectionSelector()
rag = MilvusRAG()

request = RouterRequest(query="JEE and CBSE comparison")
response = router.route(request)

# Search with primary collections
results = rag.search_collections(
    query=request.query,
    collection_names=response.decision.selected_collections,
)

# Use fallback if no results
if not results and response.decision.fallback_collections:
    logger.info("Using fallback collections")
    results = rag.search_collections(
        query=request.query,
        collection_names=response.decision.fallback_collections,
    )
```

## Pydantic Models

### RouterRequest
```python
class RouterRequest(BaseModel):
    query: str
    selector_config: Optional[SelectorConfig] = SelectorConfig()
```

### RouterResponse
```python
class RouterResponse(BaseModel):
    decision: RouterDecision  # Routing decision with scores
    collections_info: List[CollectionMetadata]  # Metadata of selected collections
```

### RouterDecision
```python
class RouterDecision(BaseModel):
    query: str
    selected_collections: List[str]  # ["cbse_class_12", "jee"]
    reasoning: str
    collection_scores: Dict[str, float]  # {"cbse_class_12": 0.95, "jee": 0.3}
    fallback_collections: Optional[List[str]]
```

## Testing

```python
# Test with default config
def test_routing_physics():
    router = QueryRouter()
    request = RouterRequest(query="Class 12 Physics")
    response = router.route(request)
    assert "cbse_class_12" in response.decision.selected_collections

# Test with filtering
def test_routing_with_filter():
    config = SelectorConfig(min_confidence=0.9)
    request = RouterRequest(query="JEE Main", selector_config=config)
    response = router.route(request)
    # Only high-confidence collections selected
    for name in response.decision.selected_collections:
        score = response.decision.collection_scores[name]
        assert score >= 0.9
```

## SOLID Principles Applied

1. **Single Responsibility**: Each class handles one concern
   - Registry: collection metadata
   - PromptBuilder: prompt construction
   - Router: LLM routing decision
   - Selector: filtering rules
   - RAG: search execution

2. **Open/Closed**: Open for extension (add collections in YAML), closed for modification

3. **Liskov Substitution**: SearchCollections() can replace search() in most contexts

4. **Interface Segregation**: Small, focused interfaces (no bloat)

5. **Dependency Inversion**: Classes depend on abstractions (CollectionRegistry, OllamaClient)

## Future Enhancements

- [ ] Decision caching (same query → same routing within TTL)
- [ ] Router confidence calibration (learn from feedback)
- [ ] Multi-language support in collection descriptions
- [ ] Collection similarity search (find related collections)
- [ ] Analytics/telemetry on routing decisions
- [ ] A/B testing framework for router improvements
- [ ] Custom routing rules DSL

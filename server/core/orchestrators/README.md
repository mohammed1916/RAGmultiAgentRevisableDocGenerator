# Document Generation Orchestrators

Three different orchestrator implementations for different workflow needs.

## Overview

| Orchestrator | Type | Use Case | Status |
|---|---|---|---|
| **Orchestrator** | Traditional | Simple linear workflows | Legacy |
| **LangGraphOrchestrator** | Modern (LangGraph) | Complex DAGs with conditional routing | Recommended |
| **ChatOrchestrator** | Conversational | Interactive dialogue-based generation | Specialized |

---

## 1. Orchestrator (Base)

**File:** `base.py`

**Type:** Traditional multi-agent approach

**Architecture:**
- Uses individual agent classes: PlannerAgent, WriterAgent, ReviewerAgent
- Linear execution flow
- Synchronous
- State managed manually

**Workflow:**
```
Request → Plan → Write → Review → Document
```

**When to Use:**
- Simple, linear document generation
- No conditional branching needed
- Fallback when LangGraph unavailable
- Backward compatibility required

**Pros:**
- Simple to understand
- Minimal dependencies
- Direct agent control

**Cons:**
- No conditional routing
- Fixed workflow
- Manual state management
- Cannot iterate/refine based on feedback

**Example:**
```python
from server.core import Orchestrator

orchestrator = Orchestrator()
response = orchestrator.generate_document(request)
```

---

## 2. LangGraphOrchestrator (Modern)

**File:** `langgraph.py`

**Type:** LangGraph StateGraph with conditional routing

**Architecture:**
- StateGraph with typed state (DocumentGenerationState)
- 5 nodes: plan → write → review → refine (conditional) → generate
- Async-capable
- Message history tracking
- Conditional branching: review → {refine, generate}
- Self-loop: refine → review (iterate until acceptable)

**Workflow:**
```
Plan Node
    ↓
Write Node
    ↓
Review Node
    ↙         ↖
Refine Node   Generate Node
    ↓            ↓
Review Node    (Document)
(loop)         
    ↓
Generate Node
    ↓
(Document)
```

**When to Use:**
- Complex multi-step workflows
- Conditional routing needed
- Quality iterations required
- Message history important
- Async execution beneficial
- **RECOMMENDED for production use**

**Pros:**
- Powerful graph-based workflows
- Conditional branching & loops
- Built-in message history
- Async support
- State validation
- Clear workflow visualization

**Cons:**
- More complex to debug
- LangGraph dependency required
- Steeper learning curve

**Example:**
```python
from server.core import LangGraphOrchestrator

orchestrator = LangGraphOrchestrator()
result = await orchestrator.generate_document(
    request="Create a study plan for JEE",
    metadata={"level": "Advanced"}
)
```

---

## 3. ChatOrchestrator (Conversational)

**File:** `chat.py`

**Type:** LLM-driven state machine

**Architecture:**
- Pure conversational flow
- LLM decides all state transitions
- No hardcoded workflow logic
- Question-answer dialogue format
- RAG integration for curriculum context

**Workflow:**
```
User Request
    ↓
Chat Session (Stateful)
    ↓
LLM generates clarifying questions
    ↓
User answers questions
    ↓
LLM generates final document
```

**When to Use:**
- Interactive dialogue needed
- User clarification important
- Question-answer style preferred
- Curriculum context (RAG) beneficial
- **Specialized use case, not default**

**Pros:**
- Natural conversational interaction
- Flexible, LLM-driven logic
- Can clarify ambiguous requests
- RAG integration for domain knowledge

**Cons:**
- Multiple turns required (slower)
- Higher latency
- More API calls
- Less predictable than structured workflows

**Example:**
```python
from server.core import ChatOrchestrator

chat = ChatOrchestrator()

# Start conversation
response = chat.start_conversation("Create a JEE Math study plan")
print(response.questions)  # Ask clarifying questions

# User answers
response = chat.add_answer(context, "question_key", "answer")

# Generate final document
prompt = chat.get_generation_prompt(context)
```

---

## Comparison Matrix

| Feature | Orchestrator | LangGraph | Chat |
|---|---|---|---|
| Complexity | Low | High | Medium |
| Speed | Fast | Medium | Slow |
| Iterations | No | Yes (conditional) | Yes (dialogue) |
| State Management | Manual | Automatic | Automatic |
| Message History | No | Yes | Yes |
| Async Support | No | Yes | Partial |
| Configurable Workflow | No | Graph-based | LLM-driven |
| Error Recovery | Limited | Possible | Possible |
| Production Ready | No (legacy) | ✅ Yes | Specialized |

---

## Migration Guide

**From Orchestrator → LangGraphOrchestrator:**

```python
# Old
from server.core import Orchestrator
orchestrator = Orchestrator()
response = orchestrator.generate_document(request)

# New
from server.core import LangGraphOrchestrator
orchestrator = LangGraphOrchestrator()
result = await orchestrator.generate_document(request=request_text)
```

Key differences:
- Async/await required
- Returns different schema (check result format)
- No intermediate agent messages exposed
- Built-in refinement iterations

---

## Recommendations

### For Production Use
Use **LangGraphOrchestrator** - it's the modern, recommended implementation with:
- Complex workflow support
- Conditional routing
- Built-in quality iterations
- Message history tracking

### For Simple Cases
Use **Orchestrator** - only if:
- Workflow is strictly linear
- No LangGraph dependency available
- Backward compatibility required

### For Interactive Use
Use **ChatOrchestrator** - only if:
- Interactive dialogue is primary requirement
- Multiple clarification rounds acceptable
- Curriculum context (RAG) important

---

## See Also

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Document Generation Flow](../../../docs/EXECUTION_FLOW.md)
- [API Routes](../../api/routes.py) - See orchestrator usage in endpoints

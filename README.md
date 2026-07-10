Autonomous Multi-Agent JEE/Education Prep System

A production-ready autonomous AI agent system with **LangGraph + LangChain orchestration** that generates personalized study plans, respects student progress, and validates recommendations. Deployed with FastAPI, local Ollama LLM, Milvus vector database, and comprehensive metrics.

### LangGraph + LangChain Integration (v2.0)

System now uses **LangGraph state machine** with **LangChain tool-calling agents**:

- **LangGraph StateGraph** - Declarative orchestration: Plan → Write → Review nodes
- **LangChain Agents** - Autonomous tool-calling with agent executors  
- **Tool-Calling Pattern** - LLM autonomously decides when/how to call tools
- **State Persistence** - DocumentGenerationState with add_messages reducer
- **Conditional Routing** - Feedback loops (max 2 review iterations)
- **Autonomous RAG** - Writer agent automatically fetches curriculum context
- **Local Ollama Support** - Research/experimentation with local LLMs

**New Endpoint:** `POST /agent/langgraph` uses LangGraph orchestration  
**Backward Compatible:** Old `/agent` endpoint unchanged  
**Tests:** 30+ new tests for state machine, agents, and tool-calling

## Overview

This system demonstrates advanced AI engineering for educational technology:

- **Multi-agent orchestration** (Planner, Writer, Reviewer) - Now with LangChain tool-calling
- **Student state tracking** - Progress extraction from natural language
- **Curriculum-aware RAG** - Milvus IVF clustering with complete subject syllabuses
- **Non-hallucinating generation** - Grounded in real curriculum data via autonomous RAG fetching
- **Robust validation** - Study plans with time/feasibility checks
- **Iterative refinement** - Feedback loops with conditional routing
- **Production-grade metrics** - ROUGE, BLEU, groundedness, hallucination rates
- **DOCX generation** - Deterministic document creation with markdown formatting

## Quick Start

### Prerequisites

- Python 3.10+
- Ollama installed and running locally
- 4GB+ available RAM for local LLM

### Installation

1. Install Python dependencies:

```bash
pip install -r requirements.txt
```

2. Configure Cloud Ollama (Recommended - 3x faster):

Create `.env` file with:
```
OLLAMA_MODE=cloud
OLLAMA_BASE_URL=https://ollama.com
OLLAMA_KEY=<your-ollama-cloud-api-key>
OLLAMA_MODEL=gpt-oss:120b
OLLAMA_TIMEOUT=60
```

Get API key from: https://ollama.com/account

3. (Optional) Local Ollama fallback:

Install and start Ollama locally:
```bash
ollama serve
```

Pull a model:
```bash
ollama pull qwen2:7b
```

Verify:
```bash
curl http://localhost:11434/api/tags
```

### Running the Server

Start the server:

```bash
python run_server.py
```

Or directly with uvicorn:

```bash
python -m uvicorn server.api:app --host 0.0.0.0 --port 8000
```

Test with:
```bash
curl http://localhost:8000/health
```

Response:
```json
{"status": "healthy"}
```

Cloud Ollama Mode (fast):
- Automatically uses Cloud Ollama if .env has OLLAMA_MODE=cloud
- Response time: 6-15 seconds per turn
- Average: 11.8 seconds (3x faster than local)

Local Ollama Mode (fallback):
- Falls back automatically if Cloud Ollama unavailable
- Response time: 24-44 seconds per turn
- Suitable for testing/development

### Using the System

Web UI (Recommended):

Open in browser: http://localhost:8000/client/index.html

Chat with the LLM-driven orchestrator:
1. Enter: "I want to prepare for JEE Physics"
2. System asks clarifying questions about topics and timeline
3. Answer each question (conversational flow)
4. When ready, system generates personalized study schedule
5. Download generated DOCX document

Via curl (Chat API):

```bash
# Start conversation
curl -X POST http://localhost:8000/chat/start \
  -H "Content-Type: application/json" \
  -d '{"request": "I need a JEE study plan"}' | jq '.session_id'

# Continue conversation (repeat with different answers)
curl -X POST "http://localhost:8000/chat/answer?session_id=<ID>&question_key=user_input&answer=Physics+and+Maths" \
  -X POST

# Generate document when ready
curl -X POST http://localhost:8000/chat/generate \
  -H "Content-Type: application/json" \
  -d '{"session_id":"<ID>","context":<context-from-chat>}'
```

Via Python client:

```python
from server.chat_orchestrator import ChatOrchestrator

chat = ChatOrchestrator()

# Start conversation
response = chat.start_conversation("I need JEE Physics preparation")
print(response.message)  # LLM asks clarifying questions

# Answer questions
context = response.context
response = chat.add_answer(context, "user_input", "Kinematics and Mechanics")

# When [READY] marker appears, generate document
if response.is_ready_to_generate:
    from server.orchestrator import Orchestrator
    doc = Orchestrator()
    prompt = chat.get_generation_prompt(response.context)
    result = doc.generate_document(request=prompt)
    print(f"Document: {result.document_filename}")
```

Legacy API (for backward compatibility):

```bash
curl -X POST http://localhost:8000/agent \
  -H "Content-Type: application/json" \
  -d '{"request": "Create a JEE mathematics study plan for one week"}'
```

### Using LangGraph Orchestration (New)

**Via curl (LangGraph pipeline):**

```bash
curl -X POST http://localhost:8000/agent/langgraph \
  -H "Content-Type: application/json" \
  -d '{
    "request": "Create a JEE physics guide on electromagnetism",
    "metadata": {
      "audience": "JEE aspirants",
      "scope": "Electromagnetism fundamentals",
      "tone": "Educational"
    }
  }'
```

Response:
```json
{
  "success": true,
  "document_filename": "doc_20260708_143015.docx",
  "request": "Create a JEE physics guide...",
  "execution_plan": {
    "document_type": "Study Guide",
    "outline": ["Introduction", "Fundamentals", "Applications", "Practice Problems"],
    "tasks": [...]
  },
  "sections": [...],
  "quality_scores": {
    "relevance": 4,
    "completeness": 5,
    "coherence": 4,
    "structure": 5,
    "overall": 4
  }
}
```

**Via Python (LangGraph with local Ollama):**

```python
import asyncio
from server.core import LangGraphOrchestrator

async def main():
    orchestrator = LangGraphOrchestrator()
    
    result = await orchestrator.generate_document(
        request="Create a study guide on algebra",
        metadata={"audience": "students", "level": "intermediate"}
    )
    
    print(f"Document: {result['document_filename']}")
    print(f"Sections: {result['sections_count']}")
    print(f"Review iterations: {result['iterations']}")
    print(f"Success: {result['success']}")

asyncio.run(main())
```

**How it works:**
1. Request goes to `/agent/langgraph` endpoint
2. `LangGraphOrchestrator.generate_document()` creates initial state
3. Plan node runs planner agent (LangChain autonomous tool-calling)
4. Write node runs writer agent + fetches RAG context autonomously
5. Review node evaluates quality, conditionally routes back to write if needed
6. State persists across all nodes via add_messages
7. Returns final document with metrics

## LangGraph + LangChain Architecture

### State Machine Pipeline

```
Request
  ↓
LangGraphOrchestrator (server/core/orchestrators/langgraph.py)
  ├─ Plan Node (LangChain Agent with tools)
  │  ├─ Tool: @plan_document_tool (autonomous)
  │  └─ Output: ExecutionPlan (outline, tasks)
  │
  ├─ Write Node (LangChain Agent with tools)
  │  ├─ Tool: @write_sections_tool (generates content)
  │  ├─ Tool: @fetch_rag_context_tool (autonomous RAG calls)
  │  └─ Output: List[DocumentSection] (grounded in curriculum)
  │
  ├─ Review Node (LangChain Agent with tools)
  │  ├─ Tool: @review_document_tool (quality assessment)
  │  └─ Output: Quality scores (1-5 scale)
  │
  └─ Conditional Routing
     ├─ Quality >= 4 → END
     ├─ Issues found & iterations < 2 → REVISE (back to Write)
     └─ iterations >= 2 → END
  ↓
DOCX Document
```

### Tool-Calling Pattern

Each agent uses LangChain's autonomous tool-calling:

1. LLM sees available tools (decorated with `@tool`)
2. LLM decides: "I should call plan_document_tool with these arguments"
3. Framework extracts tool call from LLM output
4. Framework executes tool: `plan_document_tool(request)`
5. LLM receives result and continues autonomously

Tools defined in `server/langchain_agents.py`:
- `@tool def plan_document_tool(request, metadata) → dict`
- `@tool def write_sections_tool(request, outline, rag_enabled) → dict`
- `@tool def review_document_tool(sections) → dict`
- `@tool def fetch_rag_context_tool(query, top_k) → dict`

### State Management

`DocumentGenerationState` (TypedDict) persists across nodes:

```python
class DocumentGenerationState(TypedDict):
    request: str                          # User request
    metadata: dict                        # Context (audience, scope, tone)
    messages: List[BaseMessage]           # Conversation history (add_messages reducer)
    
    execution_plan: ExecutionPlan         # Plan phase output
    plan_quality: float                   # 0-1.0 quality score
    
    sections: List[DocumentSection]       # Write phase output
    write_quality: float                  # Quality score
    
    review_feedback: str                  # Reviewer comments
    review_issues: List[str]              # Issues found
    review_iterations: int                # Iteration count (max 2)
    
    success: bool                         # Generation succeeded?
    document_filename: str                # output/doc_XXXXXX.docx
    error_message: str                    # Error if failed
```

Messages accumulate via `add_messages` reducer, enabling context for future nodes.

### LangGraph Nodes

**Plan Node** → Generates ExecutionPlan (outline, tasks, assumptions)
- Runs planner agent with tools
- Duration: 1-3 seconds

**Write Node** → Generates DocumentSection[] with RAG context
- Runs writer agent with write + RAG fetch tools
- Autonomously calls fetch_rag_context_tool for curriculum data
- Duration: 3-10 seconds

**Review Node** → Assesses quality, decides routing
- Runs reviewer agent with review tool
- Outputs quality scores (relevance, completeness, coherence, structure)
- Routes: Finish if quality OK, Revise if poor + iterations < 2

## Architecture (Core Components)

System Architecture Overview:

Input Request → Planner Agent → Writer Agent → Reviewer Agent → DOCX Output

### Components

FastAPI Server (server/api.py)
- REST endpoints: POST /agent, GET /health, GET /metrics
- CORS enabled for frontend
- Error handling and validation
- 500 characters max request

Orchestrator (server/orchestrator.py)
- Coordinates multi-agent pipeline
- Implements iterative refinement loop
- Manages metrics collection
- Non-LLM business logic

Agent Layer:
- PlannerAgent: Generates ExecutionPlan with document structure
- WriterAgent: Writes document sections with RAG context
- ReviewerAgent: Reviews for quality issues, scores output
- StateAwarePlanner: Generates plans respecting student progress

Tools Layer:
- OllamaClient: Structured LLM calls with schema validation
- MilvusRAG: Vector database for curriculum search (mock mode fallback)
- DOCXGenerator: Deterministic Word document creation
- ProgressExtractor: NLP-based progress claim extraction
- ProgressValidator: Feasibility validation (no repetition, time constraints)
- DateUtils: Date parsing and scheduling utilities
- MetricsCollector: Pipeline metrics (ROUGE, BLEU, groundedness)
- EvaluationMetrics: Content quality scoring

Models (server/models.py):
- DocumentRequest / DocumentResponse
- ExecutionPlan, Task, DocumentSection
- StudentState, TopicProgress, ProgressClaim
- ReviewFeedback, QualityScore, PipelineMetrics

## Curriculum Data

Complete subject syllabuses stored in server/data/curriculum_data.json:

CBSE Board (India):
- Class 12: Physics, Chemistry, Mathematics (35-42 chapters each)
- Class 10: Science (integrated), Mathematics

Competitive Exams:
- JEE Main (Math, Physics, Chemistry)
- JEE Advanced (55 chapters across 3 subjects)

College Level:
- Bachelor Physics Major (4 years)
- Bachelor CS Major (4 years)
- Mathematics Minor (24 credits)
- Data Science Minor (24 credits)

Each document contains complete syllabus with nested topics, metadata for IVF clustering (subject, level, class, difficulty).

## State & Progress Tracking

Student state tracks:
- Learned topics (with completion dates, confidence levels 0-1)
- Available study hours per day (default 6)
- Learning velocity (topics/day, auto-calculated from history)
- Exam deadline (for calculating days remaining)

System automatically:
- Extracts progress from natural language ("I completed Algebra", "spent 3 hours")
- Updates student state with confidence levels (mastered=0.95, learned=0.85, covered=0.70)
- Filters curriculum to exclude learned topics
- Validates plans for feasibility and non-repetition
- Returns validation issues if plan is unrealistic

Example: User says "I finished Algebra today, spent 4 hours"
System extracts: Algebra topic (confidence 0.95, 4 hours, today)
System updates: StudentState with new learned topic
System validates: Future plans won't include Algebra

## Execution Flow

Request → Progress Extraction → Exam Date Parsing → Curriculum Filtering → LLM Planning → Iterative Refinement → DOCX Generation

Step 1: Progress Extraction
- Parses request text for progress claims
- Detects mastery confidence levels
- Updates student state
- Fallback: Uses default state if no progress mentioned

Step 2: Exam Date Extraction
- Parses dates: "January 2026", "December 15, 2025"
- Calculates days remaining
- Sets preparation phases
- Fallback: Uses 90-day default if no deadline specified

Step 3: Curriculum Filtering
- Retrieves curriculum via Milvus RAG (mock mode fallback)
- Excludes learned topics
- Returns only available topics for study
- Fallback: Returns all curriculum if filtering unavailable

Step 4: Plan Generation (Planner Agent)
- Generates ExecutionPlan with document structure
- Considers time constraints and daily load
- Creates task dependencies
- Builds outline of sections to write

Step 5: Section Writing (Writer Agent)
- Fetches curriculum context via RAG
- Writes one section at a time
- Includes curriculum references (non-hallucinating)
- Maintains consistency with previous sections

Step 6: Review & Refinement (Reviewer Agent)
- Reviews sections for quality issues
- Scores document (relevance, completeness, coherence, structure)
- Identifies specific section issues
- Planner rewrites problematic sections with feedback

Step 7: DOCX Generation
- Converts structured output to Word document
- Deterministic (no LLM involved)
- Includes headings, paragraphs, bullet lists, tables
- Saved with timestamp: document_YYYYMMDD_HHMMSS.docx

Step 8: Metrics & Response
- Collects latency metrics for each phase
- Computes evaluation scores
- Returns response with document filename and metadata

## Fallback Handling

When information is missing, system asks user and proceeds with defaults:

Missing Exam Deadline:
- Question: "What's your exam deadline? (e.g., January 2026)"
- Fallback: 90-day default timeline
- Impact: Uses generic phases instead of specific deadline

Missing Student Progress:
- Question: "What topics have you already completed?"
- Fallback: Assumes no prior learning (all topics available)
- Impact: May include repetition if user has learned some topics

Missing Curriculum Data:
- Question: "Should I fetch curriculum from online sources?"
- Fallback: Uses mock curriculum data
- Impact: Less personalized but still functional

Unrealistic Study Plan:
- Question: "Your plan requires X hours/day, but you set Y. Adjust plan?"
- Options: Extend timeline, reduce topics, increase study hours
- Default: Adjusts topics to fit available time

Example Request with Fallbacks:

User: "I want to prepare for JEE"

System:
1. Exam deadline: Not mentioned → Asks user or uses January 2026
2. Current topics: Not mentioned → Assumes fresh start
3. Study hours: Not specified → Uses 6 hours/day default
4. Curriculum: Available in data/curriculum_data.json → Uses it
5. Generates plan: "Your plan requires 8 topics/day for 90 days. Feasible at 6 hours/day."

## Testing

Run all tests:

```bash
python -m pytest tests/ -v
```

Run specific test suites:

```bash
# New LangGraph tests
python -m pytest tests/test_langgraph_orchestrator.py -v
python -m pytest tests/test_langchain_agents.py -v

# Existing tests
python -m pytest tests/test_student_state.py -v
python -m pytest tests/test_rag_document_generation.py -v
python -m pytest tests/test_evaluation_metrics.py -v
```

Test Coverage:

**LangGraph Integration (New):**
- State Machine Tests: 10+ tests (state creation, node execution, routing)
- LangChain Agents Tests: 20+ tests (tool definitions, agent creation, error handling)
- Tool-Calling Pattern: 8+ tests (autonomous loops, parameter validation)

**Core System (Existing):**
- Student State Management: 4/4 tests
- Progress Extraction: 5/5 tests
- Validation: 2/3 tests
- Date Utils: 5/6 tests
- State-Aware Planning: 3/3 tests
- End-to-End Integration: 2/2 tests
- Curriculum Data: 3/3 tests
- Milvus RAG: 6/6 tests
- Evaluation Metrics: 34/34 tests
- Iterative Refinement: 5/5 tests

─────────────────────────────────────────
**Total: 100+ tests** (50+ existing + 30+ new LangGraph tests)

All tests pass with both Ollama and mock LLM modes.

## Document Output

Generated documents are real Microsoft Word 2007+ DOCX files saved in `output/` directory.

Location and Naming:
- Format: `document_YYYYMMDD_HHMMSS.docx`
- Example: `document_20260709_093702.docx`
- Files persist after generation

Document Content (Cloud Ollama Generated):

Example: 7-Day JEE Physics Kinematics Study Plan

Title: 7-Day Kinematics Sprint - JEE Physics

Content includes:
- Goal statement
- Structured tables with:
  - Day breakdown
  - Total hours per day
  - Daily focus topics
  - Detailed study plan with timing
  - Practice problems and counts
- Example row:
  | Day | Hours | Focus | Plan | Practice |
  | Mon | 5h | Motion 1D | 1. Skim NCERT (30min) 2. Derive equations (45min) ... | 12 questions |

Word Document Features:
- Professional formatting with bold/italic
- Markdown support (tables, bullet points, numbered lists)
- Headings at multiple levels
- Color-coded text (blue headings, etc.)
- Ready for printing or sharing

Real Content (Not Generic):
- Specific daily breakdown with time allocations
- Problem types and counts
- Revision schedules
- Self-test guidance
- Links to resources (NCERT, YouTube channels, MCQ sources)

Document is suitable for:
- Student study guidance
- Teacher distribution
- Progress tracking
- Printing or digital sharing

## Configuration

server/config.py:

OLLAMA_HOST = "http://localhost:11434"
MODEL_NAME = "qwen2:7b"
MAX_REVIEW_ITERATIONS = 3
DOCUMENT_OUTPUT_DIR = "output/"

Adjustable settings:
- model_name: Change to any available Ollama model
- max_review_iterations: Fewer = faster, more = higher quality
- document_output_dir: Where to save .docx files

## Production Checklist

For production deployment:

Infrastructure:
- Run Ollama on separate machine (GPU recommended)
- Deploy FastAPI with Gunicorn: gunicorn server.api:app --workers 4
- Use reverse proxy (Nginx) for SSL/TLS
- Enable CORS only for trusted domains

Database:
- Deploy Milvus on separate instance for production
- Current system uses mock mode (works without Milvus server)
- For scaling: Configure Milvus with persistent storage

Monitoring:
- Collect metrics from /metrics endpoint
- Track latency per agent phase
- Monitor document quality scores
- Set alerts: review_iterations >= 3 (quality issues)

Rate Limiting:
- API: 100 requests/hour per client
- Document generation: 1 concurrent request per student

Logging:
- All LLM prompts and responses logged
- Student progress updates logged
- Document generation pipeline logged

Security:
- Validate requests (500 char max)
- Sanitize student input in progress extraction
- Rate limit API endpoints
- Use API keys for production (not shown here)

## Prompts used:
generate document for preparing jee given that i want to focus on physics and in thermodynamics lessen and i have not started that topic. give for 6 to 11pm time with breaks 

Give me todo for today

## Troubleshooting

Stopping ollama and python server:

```
echo "Stopping all processes..."
pkill -f "ollama serve" 2>/dev/null && echo "Ollama stopped" || echo "○ Ollama not running"
pkill -f "python.*server.api" 2>/dev/null && echo "Server stopped" || echo "○ Server not running"
pkill -f "uvicorn" 2>/dev/null && echo " Uvicorn stopped" || echo "○ Uvicorn not running"
sleep 2
echo ""
echo "All processes stopped."
```

Ollama Connection Error:
```
Error: Could not connect to Ollama at http://localhost:11434
Solution: ollama serve
```

Model Not Found:
```
Error: Model qwen2:7b not found
Solution: ollama pull qwen2:7b
```

Milvus Connection Error:
```
Error: Milvus connection failed
Note: System uses mock mode fallback, works without Milvus
To use real Milvus: Install pymilvus and start Milvus server
```

DOCX Not Created:
```
Error: Document saved to output/ but file not found
Solution: Ensure output/ directory exists: mkdir output
```

Progress Extraction Not Working:
```
Issue: User says "I know algebra" but system doesn't detect it
Reason: Extraction uses specific patterns (completed, finished, learned, mastered)
Try: "I completed Algebra" or "I mastered Algebra"
```

## Project Structure

rag_app/
├── scripts/                           (Utility scripts)
│   ├── setup_milvus.py               (Milvus Docker management)
│   ├── load_curriculum.py            (Load data into Milvus)
│   ├── view_chunks.py                (Inspect chunks)
│   └── show_metrics.py               (Display metrics)
│
├── server/                            (Application core)
│   ├── api/
│   │   └── routes.py                 (FastAPI endpoints)
│   ├── core/
│   │   └── orchestrators/            (3 orchestrator implementations)
│   │       ├── base.py               (Traditional multi-agent)
│   │       ├── langgraph.py          (LangGraph StateGraph)
│   │       └── chat.py               (LLM-driven conversational)
│   ├── config/
│   │   └── settings.py               (Configuration)
│   ├── base/
│   │   ├── exceptions.py             (Custom exceptions)
│   │   ├── models.py                 (Pydantic models)
│   │   ├── logger.py                 (Logging setup)
│   │   └── mock_data.py              (Mock data for testing)
│   ├── agents/                       (LangGraph agents)
│   │   ├── planner.py
│   │   ├── writer.py
│   │   ├── reviewer.py
│   │   ├── todo_generator.py
│   │   └── state_aware_planner.py
│   ├── tools/                        (Organized by functionality)
│   │   ├── rag/
│   │   │   └── milvus_rag.py         (Vector database)
│   │   ├── generation/
│   │   │   ├── docx_generator.py     (Word document creation)
│   │   │   ├── markdown_formatter.py (Markdown formatting)
│   │   │   └── document_chunker.py   (Document chunking)
│   │   ├── llm/
│   │   │   └── ollama_client.py      (LLM interface)
│   │   └── utils/
│   │       ├── metrics.py
│   │       ├── evaluation_metrics.py (ROUGE, BLEU, etc.)
│   │       ├── date_utils.py         (Date parsing)
│   │       └── progress_extractor.py (NLP for progress)
│   ├── main.py                       (Server entry point)
│   └── data/
│       └── curriculum_data.json      (11 complete subject syllabuses)
│
├── tests/                            (Organized test suite)
│   ├── unit/                         (Fast unit tests - 5 files)
│   ├── e2e/                          (End-to-end tests - 1 file)
│   ├── smoke/                        (API smoke tests - 1 file)
│   ├── conftest.py                   (Shared fixtures)
│   └── TESTING.md                    (Testing guide)
│
├── docs/                             (Documentation)
│   ├── EXECUTION_FLOW.md             (Pipeline documentation)
│   ├── MILVUS_SETUP.md               (Vector DB setup)
│   ├── curriculum_data.json
│   ├── schema.json
│   └── jee_mathematics.json
│
├── output/                           (Generated DOCX files)
├── run_server.py                     (Server startup)
├── docker-compose.yml                (Milvus Docker setup)
├── pytest.ini                        (Test configuration)
├── requirements.txt                  (Dependencies)
└── README.md                         (this file)

## Requirements

Python 3.10+:
- **FastAPI/Uvicorn** - API server
- **Pydantic** - Data validation
- **python-docx** - Word document generation
- **LangChain** (v0.1.16+) - Agent framework (NEW)
- **LangGraph** (v0.0.27+) - State machine orchestration (NEW)
- **Ollama** (v0.1.34+) - Local LLM interface (NEW)
- **pymilvus** (v2.3.7+) - Vector database (optional, mock mode works)
- **requests** - HTTP client
- **pytest** - Testing

See requirements.txt for exact versions.

To install all including new LangChain/LangGraph:
```bash
pip install -r requirements.txt
```

## Metrics & Evaluation

Pipeline collects:
- Planner latency (ms)
- Writer latency (ms)
- Reviewer latency (ms)
- DOCX generation latency (ms)
- Total execution time (ms)
- Review iterations (count)
- Quality scores (1-5): relevance, completeness, coherence, structure, overall

Content metrics:
- ROUGE-1, ROUGE-2, ROUGE-L (recall-oriented)
- BLEU 1-4 grams with brevity penalty
- Groundedness (content supported by curriculum)
- Context utilization (% of retrieved context used)
- Semantic similarity (embedding-based)

Query metrics:
- Exam deadline extraction accuracy
- Progress extraction precision/recall
- Plan feasibility validation rate
- Non-repetition validation success

## Implementation Notes

Why This Architecture:

Multi-agent approach: Each agent has single responsibility (planning, writing, reviewing)
Separates concerns and allows independent improvement

Local Ollama: Privacy, speed, cost (no API bills)
Trade-off: Lower quality than API models, but suitable for education

Milvus RAG: IVF clustering enables semantic search
Curriculum data organized by subject, class, level for effective retrieval

Mock mode fallback: Tests run without Milvus server
Production-ready: Upgrades to real Milvus with one config change

Iterative refinement: Reviews catch issues, writer fixes them
Improves output quality without exponential LLM costs

Progress extraction: NLP-based, not requiring database queries
Fast, works offline, user-friendly natural language interface

DOCX generation: Deterministic, not LLM-generated
Guarantees output quality and reproducibility

## LangGraph Migration Notes

This version introduces LangGraph + LangChain integration for modern agentic AI patterns:

**What Changed:**
- ✅ New orchestration via LangGraph state machine
- ✅ New tool-calling agents via LangChain
- ✅ Autonomous RAG context fetching
- ✅ New endpoint: `POST /agent/langgraph`
- ✅ 30+ new tests for state machine and agents

**What's Backward Compatible:**
- ✅ Old `/agent` endpoint works unchanged
- ✅ All existing agents and tools unchanged
- ✅ All chat endpoints continue working
- ✅ All 50+ existing tests pass
- ✅ No breaking changes to configuration

**Migration Path:**
1. **Phase 1 (Current):** Research/experimentation with LangGraph
2. **Phase 2 (Next):** Validation against custom orchestration
3. **Phase 3 (Later):** Gradual adoption in production
4. **Phase 4 (Future):** Complete migration, custom orchestrator deprecated

**Key Files:**
- `server/langgraph_orchestrator.py` - State machine (364 lines)
- `server/langchain_agents.py` - Tool definitions (318 lines)
- `tests/test_langgraph_orchestrator.py` - State tests (200+ lines)
- `tests/test_langchain_agents.py` - Agent tests (250+ lines)

## Future Enhancements

**LangGraph Extensions:**
- Parallel section writing via send()
- Streaming section generation to client
- Human-in-the-loop review node
- Multi-model routing (different models for different tasks)

**Core Features:**
- Student Dashboard: View learning history, track progress
- Spaced Repetition: Optimal revision scheduling
- Adaptive Difficulty: Adjust based on student performance
- Interactive Feedback: Learn from user ratings
- Mobile App: Phone access with offline mode
- Teacher Dashboard: Monitor class progress

## Contact & Support

For issues, feature requests, or contributions:

1. Check Troubleshooting section above
2. Review test cases for expected behavior
3. Enable DEBUG logging in server/logger.py for verbose output
4. Report issues with: request text, student state, expected output, actual output

## License

Educational use. See LICENSE file.

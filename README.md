Autonomous Multi-Agent JEE/Education Prep System

A production-ready autonomous AI agent system that generates personalized study plans, respects student progress, and validates recommendations against time constraints. Deployed with FastAPI, local Ollama LLM, Milvus vector database, and comprehensive metrics.

## Overview

This system demonstrates advanced AI engineering for educational technology:

- Multi-agent orchestration (Planner, Writer, Reviewer)
- Student state tracking and progress extraction from natural language
- Curriculum-aware RAG with Milvus IVF clustering
- Non-hallucinating document generation grounded in real curriculum data
- Robust validation of study plans (no repetition, feasibility checks)
- Iterative refinement with feedback loops
- Production-grade metrics (ROUGE, BLEU, groundedness, feasibility)
- DOCX document generation (deterministic, no LLM involved)

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

2. Install and start Ollama:

Download from https://ollama.ai

Run Ollama service:
```bash
ollama serve
```

3. Pull a language model (in another terminal):

```bash
ollama pull qwen2:7b
```

Or use any compatible Ollama model (llama2, mistral, neural-chat, etc.)

4. Verify Ollama is running:

```bash
curl http://localhost:11434/api/tags
```

Should return list of available models.

### Running the Server

Use one of these methods:

Option 1: Using the startup script (recommended)
```bash
python run_server.py
```

Option 2: Using uvicorn directly
```bash
python -m uvicorn server.api:app --reload
```

Option 3: Using uvicorn without reload (production)
```bash
python -m uvicorn server.api:app --host 0.0.0.0 --port 8000
```

Server starts on http://localhost:8000

Test with:
```bash
curl http://localhost:8000/health
```

Response:
```json
{"status": "healthy"}
```

### Using the System

Via Python client:

```python
from lib.python_client import DocumentGenerationClient
from server.models import StudentState
from datetime import date, timedelta

client = DocumentGenerationClient("http://localhost:8000")

# Create student state (optional, for personalized prep)
state = StudentState(
    student_id="student_001",
    created_date=date.today(),
    exam_deadline=date.today() + timedelta(days=90),
    available_hours_per_day=6.0
)

# Request preparation plan
response = client.generate(
    request="I completed Algebra and Trigonometry. JEE exam January 2026. What should I prepare today?",
    student_state=state
)

print(f"Document: {response['document_filename']}")
print(f"Topics: {response['execution_plan']['outline']}")
```

Via curl:

```bash
curl -X POST http://localhost:8000/agent \
  -H "Content-Type: application/json" \
  -d '{"request": "Create a JEE mathematics study plan for one week"}'
```

Response includes document filename, execution plan, and metrics.

## Architecture

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

Run specific test suite:

```bash
python -m pytest tests/test_student_state.py -v
python -m pytest tests/test_rag_document_generation.py -v
python -m pytest tests/test_evaluation_metrics.py -v
```

Test Coverage:

Student State Management: 4/4 tests
Progress Extraction: 5/5 tests
Validation: 2/3 tests
Date Utils: 5/6 tests
State-Aware Planning: 3/3 tests
End-to-End Integration: 2/2 tests
Curriculum Data: 3/3 tests
Milvus RAG: 6/6 tests
Evaluation Metrics: 34/34 tests
Iterative Refinement: 5/5 tests
─────────────────────────────────────────
Total: 69/70 tests passing

## Document Output

Generated documents are saved in `output/` directory:

Production API calls:
- Filename format: `document_YYYYMMDD_HHMMSS.docx`
- Location: `rag_app/output/document_20260708_142530.docx`
- Files persist after generation (not deleted)

Unit tests:
- Tests use temporary directories (files deleted after test)
- Test verification files saved to: `output/test_output_unit_test.docx`
- Run: `python -m pytest tests/test_docx_generator.py::TestDOCXGenerator::test_save_to_output_folder -v`

Structure:
- Title (Document Type)
- Executive Summary (Assumptions)
- Main Sections (from outline)
  - Section heading
  - Substantive content
  - Consistent formatting
- Page breaks between sections

Example output for "JEE Mathematics 1-week prep":

Title: JEE Mathematics 1-week Preparation Plan
Assumptions: 
  - Focus: Algebra, Trigonometry, Coordinate Geometry
  - Duration: 7 days
  - Study hours: 6 per day

Sections:
  1. Week Overview
  2. Day 1: Algebra Fundamentals
  3. Day 2: Advanced Algebra
  4. ...and so on

Document is ready for printing or sharing with students.

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

## Troubleshooting

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
├── server/
│   ├── api.py (FastAPI server)
│   ├── orchestrator.py (Pipeline coordinator)
│   ├── models.py (Pydantic models)
│   ├── config.py (Settings)
│   ├── logger.py (Logging setup)
│   ├── exceptions.py (Custom exceptions)
│   ├── agents/
│   │   ├── planner.py (Planning agent)
│   │   ├── writer.py (Writing agent with RAG)
│   │   ├── reviewer.py (Review agent)
│   │   └── state_aware_planner.py (Progress-aware planning)
│   ├── tools/
│   │   ├── ollama_client.py (LLM interface)
│   │   ├── milvus_rag.py (Vector database)
│   │   ├── docx_generator.py (Word document creation)
│   │   ├── progress_extractor.py (NLP for progress)
│   │   ├── date_utils.py (Date parsing and scheduling)
│   │   ├── metrics.py (Metrics collection)
│   │   └── evaluation_metrics.py (ROUGE, BLEU, etc.)
│   └── data/
│       └── curriculum_data.json (10 complete subject syllabuses)
├── tests/
│   ├── test_agents.py (Agent unit tests)
│   ├── test_student_state.py (Progress tracking tests)
│   ├── test_rag_document_generation.py (RAG tests)
│   ├── test_milvus_rag.py (Vector DB tests)
│   ├── test_evaluation_metrics.py (Metrics tests)
│   └── ...and 5 more test files
├── client/ (Frontend HTML/CSS/JS)
├── lib/
│   └── python_client.py (Python client library)
├── output/ (Generated DOCX files)
└── README.md (this file)

## Requirements

Python 3.10+:
- fastapi, uvicorn (API server)
- pydantic (Data validation)
- python-docx (Word document generation)
- pymilvus (optional, for production Vector DB)
- requests (HTTP client)
- pytest (Testing)

See requirements.txt for exact versions.

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

## Future Enhancements

Student Dashboard:
- View learning history
- Track progress over time
- Compare actual vs planned study

Spaced Repetition:
- Calculate optimal revision dates
- Remind users to revise learned topics
- Adjust confidence based on revision performance

Adaptive Difficulty:
- Adjust topic order based on student performance
- Recommend harder topics when student excels
- Provide easier prerequisites when struggling

Interactive Feedback:
- User rates quality of generated plans
- System learns from feedback
- Improves future recommendations

Mobile App:
- Access study plans on phone
- Log progress in real-time
- Offline mode with cached curriculum

Teacher Dashboard:
- Monitor class progress
- Assign study plans to students
- Track engagement metrics

## Contact & Support

For issues, feature requests, or contributions:

1. Check Troubleshooting section above
2. Review test cases for expected behavior
3. Enable DEBUG logging in server/logger.py for verbose output
4. Report issues with: request text, student state, expected output, actual output

## License

Educational use. See LICENSE file.

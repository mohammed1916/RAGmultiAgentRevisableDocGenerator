# Documentation Index

## Directory Structure

```
docs/
├── INDEX.md (you are here)
├── guides/          → Main documentation (11 guides)
├── schemas/         → Schema definitions (schema.json)
├── samples/         → Sample data (jee_mathematics.json)
└── diagrams/        → Architecture diagrams (2 mermaid files)
```

## Quick Start

**New to this project?**
→ Read [guides/GETTING_STARTED.md](guides/GETTING_STARTED.md)

**Want to monitor executions with LangSmith?**
→ Read [guides/langsmith_quickstart.md](guides/langsmith_quickstart.md) (5 min setup)

**Want to run production tests?**
→ Read [guides/PRODUCTION_TESTING_GUIDE.md](guides/PRODUCTION_TESTING_GUIDE.md)

**Need to view chunks in Milvus?**
→ Read [guides/CHUNK_VIEWER_GUIDE.md](guides/CHUNK_VIEWER_GUIDE.md)

---

## Guides (12 documents)

### Setup & Configuration
- **[guides/GETTING_STARTED.md](guides/GETTING_STARTED.md)** - Quick start, installation, first run
- **[guides/MILVUS_SETUP.md](guides/MILVUS_SETUP.md)** - Milvus database setup and configuration

### Observability & Monitoring
- **[guides/langsmith_quickstart.md](guides/langsmith_quickstart.md)** - 5-minute LangSmith setup (NEW!)
  - Get API key, enable tracing, view traces
  - See execution pipeline in real-time
  - Compare runs and optimize performance
  
- **[guides/langsmith_setup.md](guides/langsmith_setup.md)** - Complete LangSmith guide (NEW!)
  - Detailed setup instructions
  - Configuration options and examples
  - Tracing architecture overview
  - Best practices and troubleshooting

### Architecture & Understanding
- **[guides/EXECUTION_FLOW.md](guides/EXECUTION_FLOW.md)** - Complete system execution flow and pipeline
- **[guides/API.md](guides/API.md)** - REST API endpoints and usage

### Testing & Quality
- **[guides/PRODUCTION_TESTING_GUIDE.md](guides/PRODUCTION_TESTING_GUIDE.md)** - Production testing strategy
  - BLEU, ROUGE, groundedness, context utilization metrics
  - Quality thresholds and production readiness checklist
  - CI/CD integration examples
  
- **[guides/TESTING_SUMMARY.md](guides/TESTING_SUMMARY.md)** - Quick test results overview
  - Recent test run results
  - Metrics summary
  - Demo vs. production mode

### Data Inspection & Debugging
- **[guides/milvus_analyzer_guide.md](guides/milvus_analyzer_guide.md)** - Production analyzer for collection quality (NEW!)
  - Real data analysis (not mocks)
  - Collection statistics and quality metrics
  - Metadata distribution analysis
  - Embedding quality analysis
  - Retrieval quality testing
  - JSON export for automation
  
- **[guides/CHUNK_VIEWER_GUIDE.md](guides/CHUNK_VIEWER_GUIDE.md)** - Complete guide to viewing/searching chunks
  - All `view_chunks.py` commands and options
  - Search workflows
  - Debugging RAG retrieval issues
  
- **[guides/VIEW_CHUNKS_SUMMARY.md](guides/VIEW_CHUNKS_SUMMARY.md)** - Quick reference
  - Command cheatsheet
  - Example workflows
  - Physics curriculum search examples

---

## Diagrams (2 files)

Located in: `diagrams/`

- **[diagrams/ARCHITECTURE.mermaid](diagrams/ARCHITECTURE.mermaid)** - System architecture diagram
- **[diagrams/sequence.mermaid](diagrams/sequence.mermaid)** - Sequence flow diagram

---

## Schemas (1 file)

Located in: `schemas/`

- **[schemas/schema.json](schemas/schema.json)** - Milvus database schema definition
  - Used by: `server/tools/generation/document_chunker.py`
  - Defines the structure of documents stored in Milvus

---

## Samples (1 file)

Located in: `samples/`

- **[samples/jee_mathematics.json](samples/jee_mathematics.json)** - Sample curriculum data
  - Example JEE Mathematics content
  - Format: Used as reference for document structure
  - Not actively used in code (for reference only)

---

## Navigation by Use Case

### I want to get started quickly
1. Read: [guides/GETTING_STARTED.md](guides/GETTING_STARTED.md)
2. Run: `python run_server.py`
3. Test: `python scripts/show_metrics.py`

### I want to understand the system
1. Read: [guides/EXECUTION_FLOW.md](guides/EXECUTION_FLOW.md)
2. View: [diagrams/ARCHITECTURE.mermaid](diagrams/ARCHITECTURE.mermaid)
3. Check: [guides/API.md](guides/API.md)

### I want to test RAG quality for production
1. Read: [guides/PRODUCTION_TESTING_GUIDE.md](guides/PRODUCTION_TESTING_GUIDE.md)
2. Load data: `python load_curriculum.py`
3. Run tests: `python scripts/test_rag_quality.py`
4. Check results: `cat output/test_results/quality_test_results.json`

### I want to analyze my Milvus collection
1. Read: [guides/milvus_analyzer_guide.md](guides/milvus_analyzer_guide.md)
2. Run: `python scripts/analyze_milvus.py`
3. Test retrieval: `python scripts/analyze_milvus.py --query "topic1" --query "topic2"`
4. Export: `python scripts/analyze_milvus.py --output report.json`

### I want to view chunks in Milvus
1. Read: [guides/CHUNK_VIEWER_GUIDE.md](guides/CHUNK_VIEWER_GUIDE.md)
2. Check status: `python scripts/view_chunks.py --stats`
3. Search: `python scripts/view_chunks.py --search "topic"`

### I want to use the API
1. Read: [guides/API.md](guides/API.md)
2. Start server: `python run_server.py`
3. Make requests: `curl http://localhost:8000/api/...`

### I want to set up Milvus
1. Read: [guides/MILVUS_SETUP.md](guides/MILVUS_SETUP.md)
2. Run: `python setup_milvus.py --start`
3. Verify: `python scripts/view_chunks.py --stats`

### I want to monitor executions with LangSmith
1. Quick start (5 min): [guides/langsmith_quickstart.md](guides/langsmith_quickstart.md)
2. Get API key from https://smith.langchain.com/
3. Set `LANGSMITH_ENABLED=true` and `LANGSMITH_API_KEY=ls_...`
4. Run: `python scripts/verify_langsmith.py`
5. Execute: `python scripts/show_metrics.py`
6. View traces at: https://smith.langchain.com/

---

## Key Commands Reference

### Testing & Metrics
```bash
python scripts/show_metrics.py              # Single test with metrics
python scripts/test_rag_quality.py          # Comprehensive quality test (3 prompts)
```

### Observability & Monitoring
```bash
python scripts/verify_langsmith.py          # Check LangSmith configuration (requires API key)
# View traces at: https://smith.langchain.com/
```

### Analyze & Inspect Collection
```bash
python scripts/analyze_milvus.py                   # Full analysis report
python scripts/analyze_milvus.py --no-embeddings   # Skip embeddings (faster)
python scripts/analyze_milvus.py --query "topic1" --query "topic2"  # Test retrieval
python scripts/analyze_milvus.py --output report.json  # Export to JSON
```

### View & Search Chunks
```bash
python scripts/view_chunks.py --stats       # Check Milvus status
python scripts/view_chunks.py --search "topic"     # Search chunks
python scripts/view_chunks.py --all -v      # List all chunks with content
python scripts/view_chunks.py --id chunk_001       # View specific chunk
```

### Data Loading
```bash
python load_curriculum.py                   # Load curriculum into Milvus
python scripts/view_chunks.py --load-mock   # Load sample data
```

### Server
```bash
python run_server.py                        # Start API server
milvus start                               # Start Milvus database
```

---

## File Organization Summary

| Category | Files | Location |
|----------|-------|----------|
| Documentation Guides | 12 .md files | `guides/` |
| Schema Definitions | 1 .json file | `schemas/` |
| Sample Data | 1 .json file | `samples/` |
| Diagrams | 2 .mermaid files | `diagrams/` |
| Generated Documents | *.docx files | `../output/documents/` |
| Test Results | *.json files | `../output/test_results/` |

---

## What's Each File For?

### Guides/
- **GETTING_STARTED.md** - Beginner friendly intro
- **MILVUS_SETUP.md** - Database setup
- **EXECUTION_FLOW.md** - Deep technical dive
- **API.md** - API reference
- **PRODUCTION_TESTING_GUIDE.md** - Quality metrics & testing
- **TESTING_SUMMARY.md** - Quick test results
- **CHUNK_VIEWER_GUIDE.md** - Complete chunk viewer tutorial
- **VIEW_CHUNKS_SUMMARY.md** - Chunk viewer cheatsheet
- **milvus_analyzer_guide.md** - Production collection analyzer (NEW!)
- **langsmith_quickstart.md** - LangSmith setup in 5 minutes (NEW!)
- **langsmith_setup.md** - Complete LangSmith guide (NEW!)
- **INDEX.md** - This file

### Schemas/
- **schema.json** - Milvus schema used when loading documents
  - Referenced by: `document_chunker.py`
  - Purpose: Defines Milvus collection schema

### Samples/
- **jee_mathematics.json** - Sample curriculum document
  - Purpose: Reference for document format
  - Status: Sample/reference only (not actively used)

### Diagrams/
- **ARCHITECTURE.mermaid** - System architecture
- **sequence.mermaid** - Workflow sequences

---

## Last Updated
- Milvus analyzer added: 2026-07-13
- 12 guide documents (+ production-grade analyzer guide)
- 1 schema definition
- 1 sample document
- 2 architecture diagrams
- Total: 16 documentation files + production analyzer tool

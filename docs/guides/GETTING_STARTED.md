# Getting Started

Quick start guide to get the RAG system running.

## 5-Minute Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Server
```bash
python run_server.py
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 3. Test It Works
```bash
curl http://localhost:8000/health
```

Response:
```json
{"status": "healthy"}
```

Done! The system is running in **mock mode** (no Milvus needed).

---

## First Request

### Via Web UI
Open http://localhost:8000/client/index.html in your browser

### Via curl
```bash
curl -X POST http://localhost:8000/agent/langgraph \
  -H "Content-Type: application/json" \
  -d '{
    "request": "Create a 3-day JEE Physics study plan on Kinematics"
  }'
```

Response will include a generated Word document in `output/`.

### Via Python
```python
import asyncio
from server.core import LangGraphOrchestrator

async def main():
    orchestrator = LangGraphOrchestrator()
    result = await orchestrator.generate_document(
        request="Create a JEE Mathematics study plan on Algebra"
    )
    print(f"Document: {result['document_filename']}")

asyncio.run(main())
```

---

## Three Operating Modes

### 1. Mock Mode (Default)
- **Best for**: Development, testing, learning
- **Setup**: None required
- **Performance**: Instant
- **Database**: In-memory only
- **Data**: Lost on restart

Start server:
```bash
python run_server.py
```

### 2. Milvus Mode (Production)
- **Best for**: Production, large datasets
- **Setup**: Docker + milvus
- **Performance**: Optimized for scale
- **Database**: Persistent vector database
- **Data**: Preserved across restarts

Start Milvus:
```bash
docker-compose up -d
```

Load curriculum:
```bash
python scripts/load_curriculum.py
```

### 3. Cloud Ollama Mode (Faster)
- **Best for**: Testing with real LLM quality
- **Setup**: Get API key from https://ollama.com
- **Performance**: 3x faster than local

Create `.env`:
```
OLLAMA_MODE=cloud
OLLAMA_BASE_URL=https://ollama.com
OLLAMA_KEY=<your-api-key>
OLLAMA_MODEL=gpt-oss:120b
```

---

## Next Steps

### Explore the System
- **View API endpoints**: `curl http://localhost:8000/docs` → Swagger UI
- **Check metrics**: `python scripts/show_metrics.py`
- **Run tests**: `pytest tests/` (90 tests)
- **View documents**: Check `output/` directory for generated `.docx` files

### Load Real Curriculum Data
```bash
python scripts/load_curriculum.py
```

Verify:
```bash
python scripts/view_chunks.py --stats
```

### Understand the Architecture
Read:
- [EXECUTION_FLOW.md](EXECUTION_FLOW.md) — How the pipeline works
- [MILVUS_SETUP.md](MILVUS_SETUP.md) — Vector database setup
- [server/core/orchestrators/README.md](../server/core/orchestrators/README.md) — Orchestrator options
- [tests/TESTING.md](../tests/TESTING.md) — How to run tests

---

## Common Tasks

### Generate a Study Plan
```bash
curl -X POST http://localhost:8000/agent/langgraph \
  -H "Content-Type: application/json" \
  -d '{
    "request": "Create a 1-week JEE Math study plan for Algebra",
    "metadata": {"level": "competitive", "scope": "Algebra fundamentals"}
  }'
```

### View Generated Documents
```bash
ls -lh output/
```

### Check System Status
```bash
python scripts/setup_milvus.py --status
```

### Run Tests
```bash
# All tests (90 total)
pytest

# Fast unit tests only
pytest tests/unit/

# LangGraph E2E tests
pytest tests/e2e/

# API smoke tests
pytest tests/smoke/
```

### Enable Debug Logging
```bash
export LOG_LEVEL=DEBUG
python run_server.py
```

---

## Troubleshooting

### Server won't start
```
Error: Port 8000 already in use
Solution: Kill process on port 8000 or use different port:
  python run_server.py --port 8001
```

### LLM connection error
```
Error: Could not connect to Ollama
Note: System works in mock mode without Ollama
To use Ollama locally:
  1. Install Ollama from https://ollama.com
  2. Run: ollama serve
  3. In another terminal: ollama pull qwen2:7b
```

### Milvus connection error
```
Error: Cannot reach Milvus at localhost:19530
Note: System automatically uses mock mode
To use Milvus: docker-compose up -d
```

### Tests failing
```
Make sure pytest is installed:
  pip install pytest pytest-asyncio

Run with verbose output:
  pytest -v tests/
```

---

## Project Structure

Key directories:
- `scripts/` — Utility scripts (setup, load data, view chunks)
- `server/` — Application code (API, orchestrators, tools, agents)
- `tests/` — Test suite (unit, e2e, smoke)
- `docs/` — Documentation (this guide, architecture, setup)
- `output/` — Generated documents (Word files)

---

## What Happens When You Request a Document?

1. Request arrives at `/agent/langgraph` endpoint
2. **Plan Node**: LLM creates document structure (outline, sections)
3. **Write Node**: LLM writes each section, fetches curriculum context via RAG
4. **Review Node**: LLM evaluates quality, may loop back for refinement
5. **Generate Node**: Converts structured content to Word document
6. Document saved to `output/doc_YYYYMMDD_HHMMSS.docx`

Total time: 5-15 seconds (mock mode) or 15-30 seconds (Cloud Ollama)

---

## Configuration

All settings in `.env` file (optional):

```
# Ollama mode: local or cloud
OLLAMA_MODE=cloud
OLLAMA_BASE_URL=https://ollama.com
OLLAMA_KEY=your-api-key-here
OLLAMA_MODEL=gpt-oss:120b
OLLAMA_TIMEOUT=60

# Logging
LOG_LEVEL=INFO

# Server
HOST=0.0.0.0
PORT=8000
```

---

## Need Help?

1. Check [EXECUTION_FLOW.md](EXECUTION_FLOW.md) for system overview
2. See [MILVUS_SETUP.md](MILVUS_SETUP.md) for database questions
3. Read [tests/TESTING.md](../tests/TESTING.md) for testing info
4. Review test cases in `tests/` for code examples
5. Check troubleshooting section above

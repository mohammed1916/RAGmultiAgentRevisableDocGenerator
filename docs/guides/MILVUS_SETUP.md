# Milvus Vector Database Setup Guide

## Overview

The RAG system supports two storage modes for document indexing and retrieval.

### Mock Mode (Default)

Mock mode requires no additional setup and is enabled automatically if a Milvus server is unavailable.

**Use Cases**

* Development and testing
* Learning the RAG pipeline
* Rapid prototyping

**Characteristics**

* Stores document chunks in memory
* No external dependencies
* Fast startup
* Data is not persisted across restarts

---

### Milvus Mode (Production)

Milvus mode stores embeddings in a persistent vector database.

**Use Cases**

* Production deployments
* Large document collections
* Semantic retrieval

**Characteristics**

* Persistent storage
* Vector similarity search
* Scales to millions of document chunks
* Requires a running Milvus instance

---

# Current Status

If the server starts with the following message:

```text
python run_server.py

Milvus connection failed: Cannot reach Milvus at localhost:19530. Using mock mode.
```

the application is functioning correctly.

This indicates:

* The application started successfully.
* No Milvus instance is currently available.
* The system has automatically switched to Mock Mode.

---

# Option 1: Development with Mock Mode

No additional setup is required.

```bash
python .\run_server.py
```

Load sample data:

```bash
```

View all chunks:

```bash
python scripts/view_chunks.py
```

Search chunks:

```bash
python scripts/view_chunks.py --search "Functions"
```

This mode is recommended for development and testing.

---

# Option 2: Production Setup with Milvus

## Prerequisites

* Docker Desktop
* Approximately 2 GB of available disk space

## Start Milvus

### Windows (PowerShell)

Automatic setup:

```powershell
python scripts/setup_milvus.py --docker --load
```

Manual setup:

```powershell
docker-compose up -d
python scripts/view_chunks.py --stats
python scripts/setup_milvus.py --load
```

### Linux/macOS

```bash
docker-compose up -d
python scripts/setup_milvus.py --load
```

---

## Verify the Installation

```bash
python scripts/view_chunks.py --stats
```

Expected output:

```text
Mode: MILVUS
Total Chunks: 10
Indexed: Yes
```

---

## Load Documents

```bash
python scripts/setup_milvus.py --load
```

Alternatively, documents can be inserted programmatically through the RAG API.

---

# Feature Comparison

| Feature               | Mock Mode                   | Milvus Mode              |
| --------------------- | --------------------------- | ------------------------ |
| Setup                 | None                        | Docker required          |
| Persistence           | No                          | Yes                      |
| Retrieval             | Basic string matching       | Vector similarity search |
| Capacity              | Suitable for small datasets | Millions of vectors      |
| Production Ready      | No                          | Yes                      |
| External Dependencies | None                        | Docker + Milvus          |

---

# Common Commands

## Inspect Stored Chunks

View all chunks:

```bash
python scripts/view_chunks.py
```

View by document type:

```bash
python scripts/view_chunks.py --type jee_math_curriculum
```

View a specific chunk:

```bash
python scripts/view_chunks.py --id jee_001
```

Search:

```bash
python scripts/view_chunks.py --search "Functions"
```

Display complete information:

```bash
python scripts/view_chunks.py --all -v
```

View statistics:

```bash
python scripts/view_chunks.py --stats
```

---

## Manage the Milvus Container

Start:

```bash
docker-compose up -d
```

Stop:

```bash
docker-compose down
```

View logs:

```bash
docker-compose logs -f milvus
```

Remove all stored data:

```bash
docker-compose down -v
```

---

## Programmatically Load Documents

Use the CLI script instead:

```bash
python load_curriculum.py
```

Or programmatically with real embeddings:

```python
from server.tools import MilvusRAG

rag = MilvusRAG()  # Uses sentence-transformers for real embeddings

# Add document with semantic embedding
rag.add_document(
    doc_id="doc_1",
    content="Calculus is the study of continuous change...",
    doc_type="mathematics",
    metadata={"topic": "Calculus"}
)

# Search semantically
results = rag.search("derivatives and limits", top_k=5)
```

Note: Embeddings are real semantic vectors from sentence-transformers, not fake hashes.

---

# Troubleshooting

## Unable to Connect to Milvus

Error:

```text
Cannot reach Milvus at localhost:19530
```

Possible solutions:

Start Milvus:

```bash
docker-compose up -d
```

Verify that Docker is running:

```bash
docker ps
```

If Milvus is unavailable, the application will continue to operate in Mock Mode.

---

## Connection Timeout

Milvus may still be initializing.

Verify the connection:

```bash
python scripts/view_chunks.py --stats
```

---

## Docker Not Installed

Install Docker Desktop before enabling Milvus mode.

---

## Data Is Not Persisted

If document data disappears after restarting the application, the system is operating in Mock Mode.

Switch to Milvus mode:

```bash
docker-compose up -d
python scripts/view_chunks.py --stats
```

---

# Architecture

## Mock Mode

```text
API Request
      │
      ▼
LangGraph Orchestrator
      │
      ▼
Writer Agent
      │
      ▼
MilvusRAG (Mock)
      │
      ▼
In-Memory Storage
      │
      ▼
Retrieved Chunks
```

---

## Milvus Mode

```text
API Request
      │
      ▼
LangGraph Orchestrator
      │
      ▼
Writer Agent
      │
      ▼
MilvusRAG
      │
      ▼
Milvus Vector Database
      │
      ▼
Retrieved Chunks
```

---

# Recommended Workflow

## Development

```bash
python .\run_server.py
```

---

## Production

```bash
python scripts/setup_milvus.py --docker --load
python scripts/view_chunks.py --stats
```

---

## Testing

```bash
python -m pytest tests/
```

---

# Performance

| Metric             | Mock Mode         | Milvus Mode         |
| ------------------ | ----------------- | ------------------- |
| Startup            | Instant           | Requires Milvus     |
| Search Method      | String matching   | Vector similarity   |
| Typical Query Time | ~1 ms             | ~10–50 ms          |
| Scalability        | Up to ~10K chunks | Millions of vectors |

---

# Additional Resources

* `scripts/setup_milvus.py` — Automated Milvus installation and initialization
* `scripts/view_chunks.py` — Command-line utility for inspecting stored chunks
* `server/tools/rag/milvus_rag.py` — Milvus-backed RAG implementation
* [Milvus documentation](https://milvus.io/)
* [RAG System Guide](docs/README.md)
* [Testing Guide](tests/TESTING.md)

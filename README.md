# Atlas Study — AI Learning Operating System

https://youtu.be/_D9tN47QsNM?si=o7OQx8952X_6nu_Y

A profile-scoped study platform built on a FastAPI backend, a PostgreSQL
application store, a Milvus vector database, and Ollama-served LLMs. It combines
retrieval-augmented generation, a multi-agent document generator, and study
tooling (planner, flashcards, knowledge graph) behind a React client.

Each user can maintain several isolated **profiles** (for example "Class 12
Boards", "JEE"). All data — documents, ingested material, tasks, flashcards,
subjects, the knowledge graph, and activity — is scoped to a profile, and
retrieval is filtered by `profile_id` so profiles never leak into one another.

Contributions from Codex 5.6 documented in ```CODEX_CONTRIBUTION.md```.

## Architecture

```
React client  ->  FastAPI  ->  PostgreSQL   (profiles, workspaces, documents, tasks,
                             |                flashcards, subjects, events, cached graph)
                             ->  Milvus       (learning_profile_chunks, profile_id indexed)
                             ->  Ollama       (agents: planner, writer, reviewer, tutor,
                                               todo, chat, concept extractor, prerequisite
                                               mapper, knowledge graph)
```

The full diagram lives in `docs/diagrams/ARCHITECTURE.mermaid`.

- **PostgreSQL** holds structured application state through a repository layer
  (`server/learning_os/repository.py`); the service layer never talks to the
  database directly, so the backend can be swapped without touching the API.
- **Milvus** stores embedded chunks for identity-based retrieval. Ingested data
  and workspace notes are chunked, embedded (sentence-transformers,
  384-dimensional), and stored with `profile_id` as an indexed scalar field.
- **Ollama** serves the LLM. The active model is selectable at runtime (cloud or
  local) from the client; the choice applies to every agent without a restart.

## Features

- **Profiles**: create, edit, archive, and delete; deleting cascades all scoped
  data.
- **Workspace**: markdown notes with live preview; notes are embedded on save.
- **Knowledge base**: upload a PDF or paste text; content is chunked, embedded,
  and stored for retrieval. A panel lists ingested sources with per-source
  removal.
- **Retrieval**: profile-scoped vector search followed by cross-encoder
  reranking.
- **Tutor (chatbot)**: grounded question answering, or document generation. In
  document mode the multi-agent pipeline produces a downloadable `.docx`.
- **Document generator**: LangGraph state machine (plan, write, review, refine,
  generate) exposed at `POST /agent/langgraph` and from the Tutor tab.
- **Planner**: generate a hierarchical task tree from a goal, chapters, and a
  free-text instruction (with presets); full per-task add, edit, and delete.
- **Flashcards**: generate cards from profile material; review with an
  FSRS-style scheduler; per-card add, edit, and delete.
- **Knowledge graph / roadmap**: derived by a three-agent pipeline (concept
  extraction, prerequisite mapping, validation) over ingested material;
  editable and persisted in the client.
- **Analytics**: study time, streak, week-over-week trend, and a seven-day
  activity chart, all derived from logged review and task events.
- **Model selector**: switch between cloud and local models at runtime.

## Requirements

- Python 3.10+
- Node.js 18+ (for the client)
- Docker (for PostgreSQL and Milvus)
- Ollama, local or cloud, for the LLM

## Setup

1. Install Python dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Copy the environment template and adjust as needed:

   ```
   cp .env.example .env
   ```

   PostgreSQL is required. Set `DATABASE_URL` (or the individual `POSTGRES_*`
   variables). Configure the LLM with `OLLAMA_MODE` (`local` or `cloud`),
   `OLLAMA_MODEL`, and, for cloud, `OLLAMA_KEY`.

3. Start the infrastructure (PostgreSQL and Milvus):

   ```
   docker compose up -d
   ```

4. Run the API:

   ```
   python run_server.py
   ```

   The server reads `APP_HOST`, `APP_PORT`, `APP_RELOAD`, and `WEB_CONCURRENCY`
   from the environment. PostgreSQL must be reachable at startup; the LLM and
   Milvus are optional and their features degrade if unavailable.

5. Run the client:

   ```
   cd client
   npm install
   npm run dev
   ```

## API overview

Learning OS endpoints are namespaced under `/learning`. All are scoped by a
`user_id` query parameter and operate within a profile.

| Area                | Endpoints                                                                                          |
| ------------------- | -------------------------------------------------------------------------------------------------- |
| Profiles            | `POST/GET/PATCH/DELETE /learning/profiles[...]`, `POST .../archive`                                |
| Workspaces          | `POST /learning/workspaces`, `GET .../{id}`                                                        |
| Documents           | `POST/GET/PATCH/DELETE /learning/documents[...]`, `GET .../{profile}/documents`                    |
| Knowledge base      | `POST .../ingest` (PDF), `POST .../ingest/text`, `GET .../retrieve`, `GET/DELETE .../sources[...]` |
| Planner             | `POST .../generate/plan`, `POST/PATCH/DELETE .../tasks[...]`                                       |
| Flashcards          | `POST .../generate/flashcards`, `POST/PATCH/DELETE .../flashcards[...]`, `POST .../review`         |
| Subjects            | `POST .../generate/subjects`, `POST/PATCH/DELETE .../subjects[...]`                                |
| Knowledge graph     | `POST .../graph/refresh`, `PUT .../graph`                                                          |
| Tutor               | `POST .../tutor`                                                                                   |
| Dashboard           | `GET .../dashboard`, `GET .../search`                                                              |
| Document generation | `POST /agent`, `POST /agent/langgraph`, `POST /todo`, `POST /chat/*`                               |
| Files               | `GET /files`, `GET /download/{filename}`                                                           |
| Models              | `GET /models`, `GET/PUT /settings/model`                                                           |
| Health              | `GET /health`                                                                                      |

## Project layout

```
server/
  api/            FastAPI application and routes
  agents/         LLM agents (planner, writer, reviewer, knowledge graph, study content)
  core/           orchestrators (custom and LangGraph)
  learning_os/    profile service, PostgreSQL repository, ingestion
  tools/          RAG (Milvus), reranker, LLM client, generation, utilities
  config/         settings
  base/           models, exceptions, logging
client/           React + Vite front end
docs/             diagrams, schemas, samples
extension/docs/   design specification for the platform
evaluation/       retrieval and generation evaluation scripts
tests/            unit, smoke, and end-to-end tests
```

## Testing

```
pytest                 # full suite (end-to-end tests require the LLM and Milvus)
pytest tests/unit      # fast unit tests
pytest tests/smoke     # API smoke tests (require PostgreSQL)
```

## Configuration reference

See `.env.example` for the complete list. Key variables:

**Core:**
- `DATABASE_URL` / `POSTGRES_*` — PostgreSQL connection (required).
- `OLLAMA_MODE`, `OLLAMA_MODEL`, `OLLAMA_BASE_URL`, `OLLAMA_KEY` — LLM backend.
- `MILVUS_HOST`, `MILVUS_PORT` — vector database.
- `APP_HOST`, `APP_PORT`, `APP_RELOAD`, `WEB_CONCURRENCY` — server runtime.

**Limits & Safety** (all optional, environment-configurable):
- `MAX_PDF_UPLOAD_MB` — Max PDF file size (default: 500 MB). Increase for large textbooks.
- `MAX_CHUNK_SIZE` — Chunk size in characters (default: 5000). Larger = fewer vectors, more context per chunk.
- `MAX_CHUNK_OVERLAP` — Character overlap between chunks (default: 2000). Must be < chunk_size.
- `CHAT_SESSION_TTL_MINUTES` — Chat session lifetime before eviction (default: 120). Prevents memory leak.
- `MAX_RECALL_K` — Max vectors fetched per collection (default: 100).
- `MAX_TOP_K` — Max results returned from search (default: 50).

**Other:**
- `CORS_ORIGINS` — comma-separated allowlist of browser origins.
- `LANGSMITH_*` — optional tracing.

All limits are validated at startup and fail fast if invalid (e.g., overlap ≥ chunk_size). Safe for local development (high defaults) and open-source deployment.

## Notes

- This is an MVP. Profiles are the isolation unit; there is no separate login or
  account system. `user_id` scopes ownership.
- Failures surface as errors rather than fabricated results: if Milvus or the
  LLM is unavailable, the affected request fails and the client shows a
  notification instead of returning fake data.

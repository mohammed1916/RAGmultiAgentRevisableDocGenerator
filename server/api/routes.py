"""FastAPI server for document generation and the Learning OS."""

import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import anyio
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ..base.models import (
    DocumentRequest,
    DocumentResponse,
    ChatResponse,
    GenerateFromChatRequest,
    DocumentStructure,
)
from ..core import Orchestrator, ChatOrchestrator, LangGraphOrchestrator
from ..agents.todo_generator import TodoGenerator
from ..tools import DOCXGenerator, OllamaClient
from ..base.exceptions import DocumentGenerationException
from ..base.logger import setup_logger
from ..config import config
from ..learning_os import (
    DocumentCreate,
    LearningDocument,
    LearningOSService,
    LearningProfile,
    LearningProfileCreate,
    ProfilePreferencesUpdate,
    ProfileUpdate,
    FlashcardReview,
    StudyQuestion,
    TaskStatusUpdate,
    Workspace,
    WorkspaceCreate,
)
from ..learning_os.repository import LearningRepository
from ..learning_os.ingestion import IngestionService

logger = setup_logger(__name__)


def _cors_origins() -> list[str]:
    """Return the configured CORS allowlist.

    ``CORS_ORIGINS`` is a comma-separated list. Wide-open ``*`` is only honoured
    in an explicit dev opt-in and is incompatible with credentialed requests.
    """
    raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:8000")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize shared resources once, and dispose them on shutdown.

    The database is a hard dependency: startup fails if Postgres is unreachable.
    The LLM/RAG orchestrators are best-effort so the API can still serve the
    Learning-OS data endpoints when the model backend is temporarily down.
    """
    logger.info("Starting up API server...")

    # --- Database (required) ---
    try:
        repository = LearningRepository()
        if not repository.ping():
            raise RuntimeError("Database ping failed")
    except Exception as error:
        logger.error("Database initialization failed: %s", error)
        raise

    # --- Shared LLM client (best-effort) ---
    llm_client = None
    try:
        llm_client = OllamaClient()
    except Exception as error:
        logger.warning("LLM client unavailable at startup: %s", error)

    app.state.repository = repository
    app.state.learning_service = LearningOSService(repository=repository, llm_client=llm_client)
    app.state.chat_sessions = {}
    app.state.ingestion_service = None

    # --- Document-generation orchestrators (best-effort) ---
    app.state.orchestrator = None
    app.state.langgraph_orchestrator = None
    app.state.chat_orchestrator = None
    app.state.todo_generator = None
    try:
        app.state.orchestrator = Orchestrator()
        app.state.langgraph_orchestrator = LangGraphOrchestrator(orchestrator=app.state.orchestrator)
        app.state.chat_orchestrator = ChatOrchestrator()
        app.state.todo_generator = TodoGenerator()
        logger.info("Document-generation orchestrators initialized")
    except Exception as error:
        logger.warning("Document-generation orchestrators unavailable at startup: %s", error)

    # --- Ingestion service (reuses the orchestrator's Milvus RAG when present) ---
    try:
        rag_system = getattr(app.state.orchestrator, "rag_system", None)
        app.state.ingestion_service = IngestionService(rag_system=rag_system)
        # Let the learning service embed notes + feed the graph from the corpus.
        app.state.learning_service.set_ingestion(app.state.ingestion_service)
        logger.info("Ingestion service initialized (vector store available: %s)",
                    app.state.ingestion_service.rag_available)
    except Exception as error:
        logger.warning("Ingestion service unavailable at startup: %s", error)

    # --- Register every OllamaClient so the model selector can re-point them all ---
    clients = []
    for holder, attr in (
        (llm_client, None),
        (getattr(app.state.orchestrator, "ollama_client", None), None),
        (getattr(app.state.chat_orchestrator, "llm_client", None), None),
        (getattr(app.state.todo_generator, "llm", None), None),
    ):
        if holder is not None and holder not in clients:
            clients.append(holder)
    app.state.llm_clients = clients
    app.state.model_config = {
        "mode": config.ollama.mode,
        "model": config.ollama.model,
        "base_url": config.ollama.base_url,
        "cloud_base_url": os.getenv("OLLAMA_CLOUD_BASE_URL", "https://ollama.com"),
        "local_base_url": os.getenv("OLLAMA_LOCAL_BASE_URL", "http://localhost:11434"),
        "api_key": config.ollama.api_key,
    }

    try:
        yield
    finally:
        logger.info("Shutting down API server...")
        for closable in (
            getattr(app.state, "orchestrator", None),
            getattr(app.state, "repository", None),
        ):
            close = getattr(closable, "close", None)
            if callable(close):
                try:
                    close()
                except Exception as error:  # pragma: no cover
                    logger.warning("Error during shutdown close: %s", error)


app = FastAPI(
    title="Document Generation API",
    description="Autonomous multi-agent document generation + Learning OS",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS: credentials only enabled when a concrete origin allowlist is configured.
_origins = _cors_origins()
_allow_credentials = "*" not in _origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (client UI) if present.
try:
    client_path = Path(__file__).parent.parent.parent / "client"
    if client_path.exists():
        app.mount("/client", StaticFiles(directory=str(client_path)), name="static")
        logger.info("Mounted static files from %s", client_path)
    else:
        logger.warning("Client directory not found at %s", client_path)
except Exception as error:
    logger.warning("Could not mount static files: %s", error)


# --------------------------------------------------------------------- helpers

def _service(request: Request) -> LearningOSService:
    return request.app.state.learning_service


def _require(component, name: str):
    if component is None:
        raise HTTPException(status_code=503, detail=f"{name} is not available")
    return component


def _fail(error: Exception, public_message: str) -> HTTPException:
    """Log the full error server-side; return a generic message to the client."""
    logger.error("%s: %s", public_message, error)
    return HTTPException(status_code=500, detail=public_message)


# ---------------------------------------------------------------------- health

@app.get("/health")
async def health_check(request: Request):
    """Health check with dependency status."""
    repo = getattr(request.app.state, "repository", None)
    db_ok = bool(repo and repo.ping())
    return {
        "status": "healthy" if db_ok else "degraded",
        "service": "document-generation-api",
        "database": "up" if db_ok else "down",
        "generation": "up" if getattr(request.app.state, "orchestrator", None) else "down",
    }


# ------------------------------------------------------------------ model select

def _list_local_models(base_url: str) -> list[str]:
    import requests

    try:
        resp = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=3)
        resp.raise_for_status()
        return [m.get("name") for m in resp.json().get("models", []) if m.get("name")]
    except requests.RequestException:
        return []


@app.get("/models")
async def list_models(request: Request):
    """List selectable models: local (via Ollama /api/tags) + configured cloud."""
    cfg = getattr(request.app.state, "model_config", {})
    local = await anyio.to_thread.run_sync(_list_local_models, cfg.get("local_base_url", "http://localhost:11434"))
    options = [{"mode": "local", "model": name} for name in local]
    # The cloud model configured at startup (e.g. gpt-oss:120b).
    if cfg.get("api_key"):
        options.append({"mode": "cloud", "model": cfg.get("model") if cfg.get("mode") == "cloud" else "gpt-oss:120b"})
    active = request.app.state.llm_clients[0].describe() if getattr(request.app.state, "llm_clients", None) else {}
    return {"options": options, "active": active}


@app.get("/settings/model")
async def get_active_model(request: Request):
    """Return the currently active model target."""
    clients = getattr(request.app.state, "llm_clients", None)
    if not clients:
        raise HTTPException(status_code=503, detail="No LLM client available")
    return clients[0].describe()


@app.put("/settings/model")
async def set_active_model(request: Request, body: dict):
    """Switch the active model/mode for all agents at runtime (no restart).

    Body: {"mode": "local"|"cloud", "model": "<name>"}.
    """
    clients = getattr(request.app.state, "llm_clients", None)
    if not clients:
        raise HTTPException(status_code=503, detail="No LLM client available")
    cfg = request.app.state.model_config
    mode = body.get("mode")
    model = body.get("model")
    if mode not in ("local", "cloud") or not model:
        raise HTTPException(status_code=400, detail="mode must be 'local' or 'cloud' and model is required")

    if mode == "cloud":
        base_url = cfg.get("cloud_base_url", "https://ollama.com")
        api_key = cfg.get("api_key", "")
        if not api_key:
            raise HTTPException(status_code=400, detail="No cloud API key configured (set OLLAMA_KEY)")
    else:
        base_url = cfg.get("local_base_url", "http://localhost:11434")
        api_key = ""

    for client in clients:
        client.set_target(mode=mode, model=model, base_url=base_url, api_key=api_key)
    logger.info("Active model switched to %s/%s across %d clients", mode, model, len(clients))
    return clients[0].describe()


# --------------------------------------------------------------- learning spec

@app.get("/learning/spec")
async def learning_specification():
    """Expose the currently implemented AI-LOS foundation capabilities."""
    return {
        "service": "ai-learning-operating-system",
        "phase": "foundation",
        "capabilities": [
            "profile-isolated learning resources",
            "profile-owned workspaces",
            "workspace documents with retrieval metadata",
            "LLM-derived knowledge graph",
        ],
    }


@app.get("/learning/demo")
async def load_learning_demo(request: Request, user_id: str = "demo-user"):
    """Create starter data once and return all profiles for the learning shell."""
    service = _service(request)
    profiles = await anyio.to_thread.run_sync(service.ensure_demo_data, user_id)
    return [profile.model_dump(mode="json") for profile in profiles]


@app.get("/learning/profiles")
async def list_learning_profiles(request: Request, user_id: str):
    """List the learning profiles that belong to a user."""
    service = _service(request)
    profiles = await anyio.to_thread.run_sync(service.list_profiles, user_id)
    return [profile.model_dump(mode="json") for profile in profiles]


@app.get("/learning/profiles/{profile_id}/dashboard")
async def get_learning_dashboard(request: Request, profile_id: str, user_id: str):
    """Return a profile-scoped workspace, planner, graph, and analytics snapshot."""
    service = _service(request)
    try:
        return await anyio.to_thread.run_sync(service.dashboard, profile_id, user_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/learning/profiles/{profile_id}/graph/refresh")
async def refresh_learning_graph(request: Request, profile_id: str, user_id: str):
    """Rebuild the LLM-derived knowledge graph for a profile."""
    service = _service(request)
    try:
        return await anyio.to_thread.run_sync(service.refresh_graph, profile_id, user_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except Exception as error:
        raise _fail(error, "Knowledge graph could not be generated")


@app.put("/learning/profiles/{profile_id}/graph")
async def save_learning_graph(request: Request, profile_id: str, user_id: str, body: dict):
    """Persist a user-edited roadmap graph ({nodes, edges})."""
    service = _service(request)
    try:
        return await anyio.to_thread.run_sync(service.save_graph, profile_id, user_id, body)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/learning/profiles/{profile_id}/generate/plan")
async def generate_learning_plan(request: Request, profile_id: str, user_id: str, instruction: str = ""):
    """Generate a study plan from the profile's goal, chapters, and instruction."""
    service = _service(request)
    try:
        return await anyio.to_thread.run_sync(service.generate_plan, profile_id, user_id, instruction)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except Exception as error:
        raise _fail(error, "Study plan could not be generated")


@app.post("/learning/profiles/{profile_id}/generate/flashcards")
async def generate_learning_flashcards(request: Request, profile_id: str, user_id: str, instruction: str = ""):
    """Generate flashcards from the profile's notes and ingested material."""
    service = _service(request)
    try:
        return await anyio.to_thread.run_sync(service.generate_flashcards, profile_id, user_id, instruction)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except Exception as error:
        raise _fail(error, "Flashcards could not be generated")


@app.get("/learning/profiles/{profile_id}/sources")
async def list_learning_sources(request: Request, profile_id: str, user_id: str):
    """List ingested knowledge-base sources (grouped by document)."""
    service = _service(request)
    try:
        return await anyio.to_thread.run_sync(service.list_ingested_sources, profile_id, user_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.delete("/learning/profiles/{profile_id}/sources/{doc_id}", status_code=204)
async def delete_learning_source(request: Request, profile_id: str, doc_id: str, user_id: str):
    """Remove one ingested source's chunks from the knowledge base."""
    service = _service(request)
    try:
        await anyio.to_thread.run_sync(service.delete_ingested_source, profile_id, user_id, doc_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/learning/profiles/{profile_id}/generate/subjects")
async def generate_learning_subjects(request: Request, profile_id: str, user_id: str):
    """Derive subjects and coverage from the profile's documents."""
    service = _service(request)
    try:
        return await anyio.to_thread.run_sync(service.generate_subjects, profile_id, user_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/learning/profiles/{profile_id}/search")
async def search_learning_profile(request: Request, profile_id: str, user_id: str, q: str):
    """Search only the active profile's documents and metadata."""
    service = _service(request)
    try:
        return await anyio.to_thread.run_sync(service.search, profile_id, user_id, q)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.patch("/learning/documents/{document_id}/content", response_model=LearningDocument)
async def update_learning_document(
    request: Request, document_id: str, user_id: str, content: str
) -> LearningDocument:
    """Save a document revision in the active profile."""
    service = _service(request)
    try:
        return await anyio.to_thread.run_sync(service.update_document, document_id, user_id, content)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.patch("/learning/profiles/{profile_id}/tasks/{task_id}")
async def update_learning_task(
    request: Request, profile_id: str, task_id: str, user_id: str, body: TaskStatusUpdate
):
    """Move a task through the profile's planner states."""
    service = _service(request)
    try:
        return await anyio.to_thread.run_sync(
            service.update_task_status, profile_id, user_id, task_id, body.status
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/learning/profiles/{profile_id}/flashcards/{card_id}/review")
async def review_learning_flashcard(
    request: Request, profile_id: str, card_id: str, user_id: str, body: FlashcardReview
):
    """Schedule the next review after a recall rating."""
    service = _service(request)
    try:
        return await anyio.to_thread.run_sync(
            service.review_flashcard, profile_id, user_id, card_id, body.rating
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/learning/profiles/{profile_id}/tasks", status_code=201)
async def create_learning_task(request: Request, profile_id: str, user_id: str, body: dict):
    """Add a single task to the planner."""
    service = _service(request)
    try:
        return await anyio.to_thread.run_sync(service.create_task, profile_id, user_id, body)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.patch("/learning/profiles/{profile_id}/tasks/{task_id}/edit")
async def edit_learning_task(request: Request, profile_id: str, task_id: str, user_id: str, body: dict):
    """Edit a task's fields (title, parent, estimate, priority, status)."""
    service = _service(request)
    try:
        return await anyio.to_thread.run_sync(service.update_task, profile_id, user_id, task_id, body)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.delete("/learning/profiles/{profile_id}/tasks/{task_id}", status_code=204)
async def delete_learning_task(request: Request, profile_id: str, task_id: str, user_id: str):
    """Delete a task from the planner."""
    service = _service(request)
    try:
        await anyio.to_thread.run_sync(service.delete_task, profile_id, user_id, task_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/learning/profiles/{profile_id}/flashcards", status_code=201)
async def create_learning_flashcard(request: Request, profile_id: str, user_id: str, body: dict):
    """Add a single flashcard."""
    service = _service(request)
    try:
        return await anyio.to_thread.run_sync(service.create_flashcard, profile_id, user_id, body)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.patch("/learning/profiles/{profile_id}/flashcards/{card_id}")
async def edit_learning_flashcard(request: Request, profile_id: str, card_id: str, user_id: str, body: dict):
    """Edit a flashcard's front/back."""
    service = _service(request)
    try:
        return await anyio.to_thread.run_sync(service.update_flashcard, profile_id, user_id, card_id, body)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.delete("/learning/profiles/{profile_id}/flashcards/{card_id}", status_code=204)
async def delete_learning_flashcard(request: Request, profile_id: str, card_id: str, user_id: str):
    """Delete a flashcard."""
    service = _service(request)
    try:
        await anyio.to_thread.run_sync(service.delete_flashcard, profile_id, user_id, card_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/learning/profiles/{profile_id}/subjects", status_code=201)
async def create_learning_subject(request: Request, profile_id: str, user_id: str, body: dict):
    """Add a subject."""
    service = _service(request)
    try:
        return await anyio.to_thread.run_sync(service.create_subject, profile_id, user_id, body)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.patch("/learning/profiles/{profile_id}/subjects/{name}")
async def edit_learning_subject(request: Request, profile_id: str, name: str, user_id: str, body: dict):
    """Edit a subject's coverage/mastery/color."""
    service = _service(request)
    try:
        return await anyio.to_thread.run_sync(service.update_subject, profile_id, user_id, name, body)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.delete("/learning/profiles/{profile_id}/subjects/{name}", status_code=204)
async def delete_learning_subject(request: Request, profile_id: str, name: str, user_id: str):
    """Delete a subject."""
    service = _service(request)
    try:
        await anyio.to_thread.run_sync(service.delete_subject, profile_id, user_id, name)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/learning/profiles/{profile_id}/tutor")
async def ask_learning_tutor(
    request: Request, profile_id: str, user_id: str, body: StudyQuestion
):
    """Answer a question using notes restricted to the active profile."""
    service = _service(request)
    try:
        return await anyio.to_thread.run_sync(service.tutor, profile_id, user_id, body.question)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/learning/infrastructure")
async def learning_infrastructure_status(request: Request):
    """Expose optional local AI and vector service availability."""
    service = _service(request)
    return await anyio.to_thread.run_sync(service.infrastructure_status)


@app.post("/learning/profiles", response_model=LearningProfile, status_code=201)
async def create_learning_profile(request: Request, body: LearningProfileCreate) -> LearningProfile:
    """Create an isolated learning profile for a user's study goal."""
    service = _service(request)
    return await anyio.to_thread.run_sync(service.create_profile, body)


@app.get("/learning/profiles/{profile_id}", response_model=LearningProfile)
async def get_learning_profile(request: Request, profile_id: str, user_id: str) -> LearningProfile:
    """Read a learning profile owned by the requesting user."""
    service = _service(request)
    try:
        return await anyio.to_thread.run_sync(service.get_profile, profile_id, user_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.patch("/learning/profiles/{profile_id}", response_model=LearningProfile)
async def update_learning_profile(
    request: Request, profile_id: str, user_id: str, body: ProfileUpdate
) -> LearningProfile:
    """Update editable profile fields (name, learner name, exam, target, hours)."""
    service = _service(request)
    try:
        return await anyio.to_thread.run_sync(service.update_profile, profile_id, user_id, body)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/learning/profiles/{profile_id}/archive", response_model=LearningProfile)
async def archive_learning_profile(
    request: Request, profile_id: str, user_id: str, archived: bool = True
) -> LearningProfile:
    """Archive (or restore) a profile without deleting its data."""
    service = _service(request)
    try:
        return await anyio.to_thread.run_sync(
            service.archive_profile, profile_id, user_id, archived
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.delete("/learning/profiles/{profile_id}", status_code=204)
async def delete_learning_profile(request: Request, profile_id: str, user_id: str):
    """Permanently delete a profile and everything scoped to it."""
    service = _service(request)
    try:
        await anyio.to_thread.run_sync(service.delete_profile, profile_id, user_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.patch("/learning/profiles/{profile_id}/preferences", response_model=LearningProfile)
async def update_learning_profile_preferences(
    request: Request, profile_id: str, user_id: str, body: ProfilePreferencesUpdate
) -> LearningProfile:
    """Merge preference changes into a profile owned by the requesting user."""
    service = _service(request)
    try:
        return await anyio.to_thread.run_sync(
            service.update_preferences, profile_id, user_id, body
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/learning/workspaces", response_model=Workspace, status_code=201)
async def create_learning_workspace(request: Request, body: WorkspaceCreate) -> Workspace:
    """Create a workspace after verifying profile ownership."""
    service = _service(request)
    try:
        return await anyio.to_thread.run_sync(service.create_workspace, body)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/learning/workspaces/{workspace_id}", response_model=Workspace)
async def get_learning_workspace(request: Request, workspace_id: str, user_id: str) -> Workspace:
    """Read a workspace owned by the requesting user."""
    service = _service(request)
    try:
        return await anyio.to_thread.run_sync(service.get_workspace, workspace_id, user_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/learning/documents", response_model=LearningDocument, status_code=201)
async def create_learning_document(request: Request, body: DocumentCreate) -> LearningDocument:
    """Store a document within its workspace and profile boundary."""
    service = _service(request)
    try:
        return await anyio.to_thread.run_sync(service.create_document, body)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.get("/learning/documents/{document_id}", response_model=LearningDocument)
async def get_learning_document(request: Request, document_id: str, user_id: str) -> LearningDocument:
    """Read a document owned by the requesting user."""
    service = _service(request)
    try:
        return await anyio.to_thread.run_sync(service.get_document, document_id, user_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.delete("/learning/documents/{document_id}", status_code=204)
async def delete_learning_document(request: Request, document_id: str, user_id: str):
    """Delete a document and its vector chunks."""
    service = _service(request)
    try:
        await anyio.to_thread.run_sync(service.delete_document, document_id, user_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/learning/profiles/{profile_id}/documents", response_model=list[LearningDocument])
async def list_learning_documents(
    request: Request, profile_id: str, user_id: str
) -> list[LearningDocument]:
    """List only the documents belonging to one profile."""
    service = _service(request)
    try:
        return await anyio.to_thread.run_sync(service.list_documents, profile_id, user_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


# ------------------------------------------------------- profile-scoped ingest

def _ingestion(request: Request) -> IngestionService:
    return _require(getattr(request.app.state, "ingestion_service", None), "Ingestion service")


@app.post("/learning/profiles/{profile_id}/ingest/text", status_code=201)
async def ingest_profile_text(
    request: Request,
    profile_id: str,
    user_id: str,
    text: str = Form(...),
    subject: str = Form(None),
    chapter: str = Form(None),
    source: str = Form("text"),
    class_level: str = Form("12"),
):
    """Ingest raw text into a profile's knowledge base (chunk -> embed -> store)."""
    service = _service(request)
    ingestion = _ingestion(request)
    try:
        await anyio.to_thread.run_sync(service.get_profile, profile_id, user_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    try:
        return await anyio.to_thread.run_sync(
            lambda: ingestion.ingest_text(
                user_id=user_id, profile_id=profile_id, text=text,
                subject=subject, chapter=chapter, source=source, class_level=class_level,
            )
        )
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        raise _fail(error, "Ingestion failed")


@app.post("/learning/profiles/{profile_id}/ingest", status_code=201)
async def ingest_profile_pdf(
    request: Request,
    profile_id: str,
    user_id: str,
    file: UploadFile = File(...),
    subject: str = Form(None),
    chapter: str = Form(None),
    class_level: str = Form("12"),
):
    """Upload a PDF into a profile's knowledge base (extract -> chunk -> embed -> store)."""
    service = _service(request)
    ingestion = _ingestion(request)
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only .pdf uploads are supported")
    try:
        await anyio.to_thread.run_sync(service.get_profile, profile_id, user_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    # Persist the upload to a temp file, then ingest and clean up.
    import tempfile

    data = await file.read()
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        return await anyio.to_thread.run_sync(
            lambda: ingestion.ingest_pdf(
                user_id=user_id, profile_id=profile_id, pdf_path=tmp_path,
                subject=subject, chapter=chapter, source=file.filename, class_level=class_level,
            )
        )
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        raise _fail(error, "PDF ingestion failed")
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


@app.get("/learning/profiles/{profile_id}/retrieve")
async def retrieve_profile_chunks(
    request: Request, profile_id: str, user_id: str, q: str, top_k: int = 5
):
    """Profile-scoped vector retrieval with cross-encoder reranking."""
    service = _service(request)
    ingestion = _ingestion(request)
    try:
        await anyio.to_thread.run_sync(service.get_profile, profile_id, user_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    try:
        return await anyio.to_thread.run_sync(
            lambda: ingestion.retrieve(profile_id=profile_id, query=q, top_k=top_k)
        )
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        raise _fail(error, "Retrieval failed")


# ---------------------------------------------------------- document generation

@app.post("/agent", response_model=DocumentResponse)
async def generate_document(request: Request, body: DocumentRequest) -> DocumentResponse:
    """Generate a document from a natural language request (custom orchestration)."""
    if not body.request or not body.request.strip():
        raise HTTPException(status_code=400, detail="Request text cannot be empty")

    orchestrator = _require(getattr(request.app.state, "orchestrator", None), "Document generator")
    logger.info("Received document generation request: %s...", body.request[:100])
    try:
        return await anyio.to_thread.run_sync(orchestrator.generate_document, body)
    except DocumentGenerationException as error:
        raise _fail(error, "Document generation failed")
    except Exception as error:
        raise _fail(error, "Document generation failed")


@app.post("/agent/langgraph", response_model=DocumentResponse)
async def generate_document_langgraph(request: Request, body: DocumentRequest) -> DocumentResponse:
    """Generate a document using the LangGraph state machine + agents."""
    if not body.request or not body.request.strip():
        raise HTTPException(status_code=400, detail="Request text cannot be empty")

    langgraph = _require(
        getattr(request.app.state, "langgraph_orchestrator", None), "LangGraph generator"
    )
    logger.info("[LangGraph] Received request: %s...", body.request[:100])
    try:
        result = await langgraph.generate_document(request=body.request, metadata=body.metadata)
        if not result["success"]:
            raise DocumentGenerationException(result.get("error", "Unknown error"))
        logger.info("[LangGraph] Document generated: %s", result["document_filename"])
        return DocumentResponse(
            success=result["success"],
            document_filename=result["document_filename"],
            request=body.request,
        )
    except DocumentGenerationException as error:
        raise _fail(error, "LangGraph generation failed")
    except Exception as error:
        raise _fail(error, "LangGraph generation failed")


@app.get("/metrics")
async def get_metrics():
    """Get aggregated metrics (detailed metrics are in document responses)."""
    return {"message": "Metrics endpoint - detailed metrics available in document responses"}


@app.get("/files")
async def list_output_files():
    """List all generated documents in the output directory."""
    output_dir = Path(config.document_output_dir)
    if not output_dir.exists():
        return {"files": [], "message": "Output directory not found"}

    files = []
    for filepath in sorted(output_dir.rglob("*.docx"), key=os.path.getmtime, reverse=True):
        stat = filepath.stat()
        files.append({
            "filename": filepath.name,
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "download_url": f"/download/{filepath.name}",
        })
    logger.info("Listed %d files in output directory", len(files))
    return {"files": files, "total": len(files), "output_directory": str(output_dir.absolute())}


@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download a generated document."""
    # Security: prevent directory traversal.
    if "/" in filename or "\\" in filename or filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files can be downloaded")

    # Search the output tree (documents may live in subfolders).
    output_dir = Path(config.document_output_dir)
    matches = list(output_dir.rglob(filename))
    if not matches:
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")

    logger.info("Downloading file: %s", filename)
    return FileResponse(
        matches[0],
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )


# --------------------------------------------------------------------- chat

@app.post("/chat/start")
async def start_chat(request: Request, body: DocumentRequest) -> ChatResponse:
    """Start a new chat conversation for document generation."""
    chat_orchestrator = _require(
        getattr(request.app.state, "chat_orchestrator", None), "Chat orchestrator"
    )
    logger.info("Starting chat: %s...", body.request[:100])
    try:
        response = await anyio.to_thread.run_sync(
            chat_orchestrator.start_conversation, body.request
        )
        session_id = str(uuid.uuid4())
        request.app.state.chat_sessions[session_id] = response.context
        response.session_id = session_id
        return response
    except Exception as error:
        raise _fail(error, "Chat start failed")


@app.post("/chat/answer")
async def answer_question(
    request: Request, session_id: str, question_key: str, answer: str
) -> ChatResponse:
    """Answer a clarifying question in the chat."""
    chat_orchestrator = _require(
        getattr(request.app.state, "chat_orchestrator", None), "Chat orchestrator"
    )
    sessions = request.app.state.chat_sessions
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Chat session not found")
    logger.info("Processing chat answer: %s", question_key)
    try:
        context = sessions[session_id]
        response = await anyio.to_thread.run_sync(
            chat_orchestrator.add_answer, context, question_key, answer
        )
        sessions[session_id] = response.context
        response.session_id = session_id
        return response
    except Exception as error:
        raise _fail(error, "Chat answer failed")


@app.post("/chat/generate")
async def generate_from_chat(request: Request, body: GenerateFromChatRequest) -> DocumentResponse:
    """Generate a document from a completed chat context."""
    orchestrator = _require(getattr(request.app.state, "orchestrator", None), "Document generator")
    chat_orchestrator = _require(
        getattr(request.app.state, "chat_orchestrator", None), "Chat orchestrator"
    )
    logger.info("Generating document from chat: %s", body.session_id)

    if not body.context.is_ready_to_generate and len(body.context.conversation) == 0:
        raise HTTPException(
            status_code=400,
            detail="Chat context not ready for generation. Have a conversation first.",
        )
    try:
        prompt = chat_orchestrator.get_generation_prompt(body.context)
        doc_request = DocumentRequest(
            request=prompt,
            metadata={
                "session_id": body.session_id,
                "chat_history": len(body.context.conversation),
                "source": "chat_orchestrator",
            },
        )
        response = await anyio.to_thread.run_sync(orchestrator.generate_document, doc_request)
        logger.info("Document generated successfully: %s", response.document_filename)
        return response
    except Exception as error:
        raise _fail(error, "Document generation failed")


@app.post("/chat/refine")
async def refine_document(request: Request, body: GenerateFromChatRequest) -> DocumentResponse:
    """Refine an already-generated document based on user feedback."""
    orchestrator = _require(getattr(request.app.state, "orchestrator", None), "Document generator")
    chat_orchestrator = _require(
        getattr(request.app.state, "chat_orchestrator", None), "Chat orchestrator"
    )
    sessions = request.app.state.chat_sessions
    if body.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Chat session not found")
    if not body.refinement_request or not body.refinement_request.strip():
        raise HTTPException(status_code=400, detail="refinement_request is required")

    logger.info("Refining document from chat: %s", body.session_id)
    try:
        context = sessions[body.session_id]
        context.refinement_requests.append(body.refinement_request)

        prompt = chat_orchestrator.get_generation_prompt(context)
        prompt += f"\n\n[REFINEMENT REQUEST]: {body.refinement_request}"
        doc_request = DocumentRequest(
            request=prompt,
            metadata={
                "session_id": body.session_id,
                "chat_history": len(context.conversation),
                "refinement_request": body.refinement_request,
                "source": "chat_refinement",
            },
        )
        response = await anyio.to_thread.run_sync(orchestrator.generate_document, doc_request)
        sessions[body.session_id] = context
        logger.info("Document refined successfully: %s", response.document_filename)
        return DocumentResponse(
            success=True,
            document_filename=response.document_filename,
            request=prompt,
            message=f"Document refined based on: {body.refinement_request}",
        )
    except Exception as error:
        raise _fail(error, "Document refinement failed")


@app.post("/todo")
async def generate_todo_list(request: Request, body: DocumentRequest) -> DocumentResponse:
    """Generate a prioritized todo list."""
    if not body.request or not body.request.strip():
        raise HTTPException(status_code=400, detail="Request cannot be empty")

    todo_generator = _require(
        getattr(request.app.state, "todo_generator", None), "Todo generator"
    )
    logger.info("Generating todo list: %s...", body.request[:100])
    try:
        return await anyio.to_thread.run_sync(_build_todo_document, todo_generator, body.request)
    except DocumentGenerationException as error:
        raise _fail(error, "Todo generation failed")
    except Exception as error:
        raise _fail(error, "Todo generation failed")


def _build_todo_document(todo_generator: TodoGenerator, request_text: str) -> DocumentResponse:
    """Synchronous todo build (run in a threadpool by the handler)."""
    todos = todo_generator.generate_todos(request_text)
    if not todos:
        raise DocumentGenerationException("Failed to generate todos")

    todo_section = todo_generator.create_todo_document_section(todos)
    docx_gen = DOCXGenerator()
    structure = DocumentStructure(title="Todo List", sections=[todo_section])
    docx_gen.from_structure(structure)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"todos_{timestamp}.docx"
    filepath = os.path.join(config.document_output_dir, filename)
    docx_gen.save(filepath)
    logger.info("Todo list generated: %s", filename)
    return DocumentResponse(
        success=True,
        document_filename=filename,
        request=request_text,
        message=f"Generated {len(todos)} todo items",
    )


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Document Generation API",
        "version": "2.0.0",
        "architecture": "LangGraph orchestration + Learning OS (PostgreSQL, Milvus, Ollama)",
        "endpoints": {
            "POST /agent": "Generate document (custom orchestration)",
            "POST /agent/langgraph": "Generate document (LangGraph state machine)",
            "POST /todo": "Generate a priority todo list",
            "POST /chat/start": "Start chatbot conversation",
            "POST /chat/answer": "Answer a clarifying question",
            "POST /chat/generate": "Generate document after chat completion",
            "POST /chat/refine": "Refine generated document",
            "POST /learning/profiles/{id}/graph/refresh": "Rebuild the LLM knowledge graph",
            "GET /health": "Health check",
            "GET /files": "List generated documents",
            "GET /download/{filename}": "Download a document",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=os.getenv("APP_HOST", "0.0.0.0"), port=int(os.getenv("APP_PORT", "8000")))

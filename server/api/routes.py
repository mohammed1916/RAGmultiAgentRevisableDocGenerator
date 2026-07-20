"""FastAPI server for document generation."""

import os
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ..base.models import DocumentRequest, DocumentResponse, ChatContext, ChatResponse, GenerateFromChatRequest, DocumentStructure
from ..core import Orchestrator
from ..core import ChatOrchestrator
from ..core import LangGraphOrchestrator
from ..agents.todo_generator import TodoGenerator
from ..tools import DOCXGenerator
from ..base.exceptions import DocumentGenerationException
from ..base.logger import setup_logger
from ..learning_os import (
    DocumentCreate,
    LearningDocument,
    LearningOSService,
    LearningProfile,
    LearningProfileCreate,
    ProfilePreferencesUpdate,
    FlashcardReview,
    StudyQuestion,
    TaskStatusUpdate,
    Workspace,
    WorkspaceCreate,
)

logger = setup_logger(__name__)

app = FastAPI(
    title="Document Generation API",
    description="Autonomous multi-agent document generation system",
    version="1.0.0",
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global orchestrator instances
orchestrator = None
chat_orchestrator = ChatOrchestrator()
langgraph_orchestrator = None
todo_generator = TodoGenerator()
learning_os_service = LearningOSService()

# Store chat sessions
chat_sessions = {}

# Mount static files (client UI)
try:
    from pathlib import Path
    # Client is at project root: client/ (not in server/)
    client_path = Path(__file__).parent.parent.parent / "client"
    if client_path.exists():
        app.mount("/client", StaticFiles(directory=str(client_path)), name="static")
        logger.info(f"Mounted static files from {client_path}")
    else:
        logger.warning(f"Client directory not found at {client_path}")
except Exception as e:
    logger.warning(f"Could not mount static files: {str(e)}")


@app.on_event("startup")
async def startup_event():
    """Initialize orchestrators on startup."""
    global orchestrator, langgraph_orchestrator
    logger.info("Starting up API server...")
    try:
        orchestrator = Orchestrator()
        logger.info("Custom orchestrator initialized successfully")

        langgraph_orchestrator = LangGraphOrchestrator()
        logger.info("LangGraph orchestrator initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize orchestrator: {str(e)}")
        raise


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "document-generation-api",
    }


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
        ],
    }


@app.get("/learning/demo")
async def load_learning_demo(user_id: str = "demo-user"):
    """Create starter data once and return all profiles for the learning shell."""
    profiles = learning_os_service.ensure_demo_data(user_id)
    return [profile.model_dump(mode="json") for profile in profiles]


@app.get("/learning/profiles")
async def list_learning_profiles(user_id: str):
    """List the learning profiles that belong to a user."""
    return [profile.model_dump(mode="json") for profile in learning_os_service.list_profiles(user_id)]


@app.get("/learning/profiles/{profile_id}/dashboard")
async def get_learning_dashboard(profile_id: str, user_id: str):
    """Return a profile-scoped workspace, planner, graph, and analytics snapshot."""
    try:
        return learning_os_service.dashboard(profile_id, user_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/learning/profiles/{profile_id}/search")
async def search_learning_profile(profile_id: str, user_id: str, q: str):
    """Search only the active profile's documents and metadata."""
    try:
        return learning_os_service.search(profile_id, user_id, q)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.patch("/learning/documents/{document_id}/content", response_model=LearningDocument)
async def update_learning_document(document_id: str, user_id: str, content: str) -> LearningDocument:
    """Save a document revision in the active profile."""
    try:
        return learning_os_service.update_document(document_id, user_id, content)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.patch("/learning/profiles/{profile_id}/tasks/{task_id}")
async def update_learning_task(
    profile_id: str, task_id: str, user_id: str, request: TaskStatusUpdate
):
    """Move a task through the profile's planner states."""
    try:
        return learning_os_service.update_task_status(profile_id, user_id, task_id, request.status)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/learning/profiles/{profile_id}/flashcards/{card_id}/review")
async def review_learning_flashcard(
    profile_id: str, card_id: str, user_id: str, request: FlashcardReview
):
    """Schedule the next review after a recall rating."""
    try:
        return learning_os_service.review_flashcard(profile_id, user_id, card_id, request.rating)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/learning/profiles/{profile_id}/tutor")
async def ask_learning_tutor(profile_id: str, user_id: str, request: StudyQuestion):
    """Answer a question using notes restricted to the active profile."""
    try:
        return learning_os_service.tutor(profile_id, user_id, request.question)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/learning/infrastructure")
async def learning_infrastructure_status():
    """Expose optional local AI and vector service availability."""
    return learning_os_service.infrastructure_status()


@app.post("/learning/profiles", response_model=LearningProfile, status_code=201)
async def create_learning_profile(request: LearningProfileCreate) -> LearningProfile:
    """Create an isolated learning profile for a user's study goal."""
    return learning_os_service.create_profile(request)


@app.get("/learning/profiles/{profile_id}", response_model=LearningProfile)
async def get_learning_profile(profile_id: str, user_id: str) -> LearningProfile:
    """Read a learning profile owned by the requesting user."""
    try:
        return learning_os_service.get_profile(profile_id, user_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.patch("/learning/profiles/{profile_id}/preferences", response_model=LearningProfile)
async def update_learning_profile_preferences(
    profile_id: str,
    user_id: str,
    request: ProfilePreferencesUpdate,
) -> LearningProfile:
    """Merge preference changes into a profile owned by the requesting user."""
    try:
        return learning_os_service.update_preferences(profile_id, user_id, request)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/learning/workspaces", response_model=Workspace, status_code=201)
async def create_learning_workspace(request: WorkspaceCreate) -> Workspace:
    """Create a workspace after verifying profile ownership."""
    try:
        return learning_os_service.create_workspace(request)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/learning/workspaces/{workspace_id}", response_model=Workspace)
async def get_learning_workspace(workspace_id: str, user_id: str) -> Workspace:
    """Read a workspace owned by the requesting user."""
    try:
        return learning_os_service.get_workspace(workspace_id, user_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/learning/documents", response_model=LearningDocument, status_code=201)
async def create_learning_document(request: DocumentCreate) -> LearningDocument:
    """Store a document within its workspace and profile boundary."""
    try:
        return learning_os_service.create_document(request)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.get("/learning/documents/{document_id}", response_model=LearningDocument)
async def get_learning_document(document_id: str, user_id: str) -> LearningDocument:
    """Read a document owned by the requesting user."""
    try:
        return learning_os_service.get_document(document_id, user_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/learning/profiles/{profile_id}/documents", response_model=list[LearningDocument])
async def list_learning_documents(profile_id: str, user_id: str) -> list[LearningDocument]:
    """List only the documents belonging to one profile."""
    try:
        return learning_os_service.list_documents(profile_id, user_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/agent", response_model=DocumentResponse)
async def generate_document(request: DocumentRequest) -> DocumentResponse:
    """Generate a document from a natural language request.

    Args:
        request: DocumentRequest with the document request text

    Returns:
        DocumentResponse with generated document and metrics

    Raises:
        HTTPException: If document generation fails
    """
    if not request.request or not request.request.strip():
        raise HTTPException(status_code=400, detail="Request text cannot be empty")

    logger.info(f"Received document generation request: {request.request[:100]}...")

    try:
        response = orchestrator.generate_document(request)
        return response
    except DocumentGenerationException as e:
        logger.error(f"Document generation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Document generation failed: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}",
        )


@app.post("/agent/langgraph", response_model=DocumentResponse)
async def generate_document_langgraph(request: DocumentRequest) -> DocumentResponse:
    """Generate document using LangGraph orchestration with LangChain agents.

    Uses the new LangGraph state machine with tool-calling agents for
    autonomous multi-agent pipeline (Plan → Write → Review).

    Args:
        request: DocumentRequest with the document request text

    Returns:
        DocumentResponse with generated document and metrics

    Raises:
        HTTPException: If document generation fails
    """
    if not request.request or not request.request.strip():
        raise HTTPException(status_code=400, detail="Request text cannot be empty")

    logger.info(f"[LangGraph] Received document generation request: {request.request[:100]}...")

    try:
        result = await langgraph_orchestrator.generate_document(
            request=request.request,
            metadata=request.metadata,
        )

        if not result["success"]:
            raise DocumentGenerationException(result.get("error", "Unknown error"))

        logger.info(f"[LangGraph] Document generated: {result['document_filename']}")

        # Return response in expected format
        return DocumentResponse(
            success=result["success"],
            document_filename=result["document_filename"],
            request=request.request,
        )
    except DocumentGenerationException as e:
        logger.error(f"[LangGraph] Document generation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"LangGraph generation failed: {str(e)}",
        )
    except Exception as e:
        logger.error(f"[LangGraph] Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"LangGraph error: {str(e)}",
        )


@app.get("/metrics")
async def get_metrics():
    """Get aggregated metrics (placeholder for future enhancement)."""
    return {
        "message": "Metrics endpoint - detailed metrics available in document responses",
    }


@app.get("/files")
async def list_output_files():
    """List all generated documents in output/ folder.

    Returns:
        List of files with metadata (name, size, created date)
    """
    output_dir = Path("output")

    if not output_dir.exists():
        return {"files": [], "message": "Output directory not found"}

    files = []
    for filepath in sorted(output_dir.glob("*.docx"), key=os.path.getmtime, reverse=True):
        stat = filepath.stat()
        files.append({
            "filename": filepath.name,
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "download_url": f"/download/{filepath.name}",
        })

    logger.info(f"Listed {len(files)} files in output directory")
    return {
        "files": files,
        "total": len(files),
        "output_directory": str(output_dir.absolute()),
    }


@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download a generated document.

    Args:
        filename: Name of the file to download

    Returns:
        File response for download
    """
    # Security: prevent directory traversal
    if "/" in filename or "\\" in filename or filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")

    filepath = Path("output") / filename

    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")

    if not filepath.suffix == ".docx":
        raise HTTPException(status_code=400, detail="Only .docx files can be downloaded")

    logger.info(f"Downloading file: {filename}")
    return FileResponse(
        filepath,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )


@app.post("/chat/start")
async def start_chat(request: DocumentRequest) -> ChatResponse:
    """Start a new chat conversation for document generation.

    Args:
        request: Initial document request

    Returns:
        ChatResponse with initial questions and session_id
    """
    logger.info(f"Starting chat: {request.request[:100]}...")

    try:
        response = chat_orchestrator.start_conversation(request.request)

        # Store session with UUID
        import uuid
        session_id = str(uuid.uuid4())
        chat_sessions[session_id] = response.context

        # Add session_id to response
        response.session_id = session_id
        return response
    except Exception as e:
        logger.error(f"Chat start failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/answer")
async def answer_question(
    session_id: str,
    question_key: str,
    answer: str,
) -> ChatResponse:
    """Answer a clarifying question in the chat.

    Args:
        session_id: Chat session ID
        question_key: Key of the question being answered
        answer: User's answer

    Returns:
        ChatResponse with next action
    """
    logger.info(f"Processing chat answer: {question_key}={answer[:50]}")

    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Chat session not found")

    try:
        context = chat_sessions[session_id]
        response = chat_orchestrator.add_answer(context, question_key, answer)
        chat_sessions[session_id] = response.context
        response.session_id = session_id
        return response
    except Exception as e:
        logger.error(f"Chat answer failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/generate")
async def generate_from_chat(req: GenerateFromChatRequest) -> DocumentResponse:
    """Generate document from completed chat context using multi-agent orchestration.

    Uses LangChain/LangGraph agents (Planner, Writer, Reviewer) to create
    a high-quality document from the chat conversation.

    Args:
        req: Request with session ID and context

    Returns:
        Generated document response
    """
    logger.info(f"Generating document from chat: {req.session_id}")
    logger.info(f"Context ready: {req.context.is_ready_to_generate}")
    logger.info(f"Conversation messages: {len(req.context.conversation)}")

    # If context doesn't have is_ready_to_generate set, but has messages, generate anyway
    if not req.context.is_ready_to_generate and len(req.context.conversation) == 0:
        logger.warning(f"Chat context not ready: is_ready={req.context.is_ready_to_generate}, messages={len(req.context.conversation)}")
        raise HTTPException(
            status_code=400,
            detail="Chat context not ready for generation. Have a conversation first."
        )

    try:
        # Build comprehensive prompt from chat context
        prompt = chat_orchestrator.get_generation_prompt(req.context)

        # Create document request with context
        doc_request = DocumentRequest(
            request=prompt,
            metadata={
                "session_id": req.session_id,
                "chat_history": len(req.context.conversation),
                "source": "chat_orchestrator",
            }
        )

        logger.info(f"Calling multi-agent orchestrator for document generation...")

        # Generate document using multi-agent pipeline (Planner -> Writer -> Reviewer)
        response = orchestrator.generate_document(doc_request)

        logger.info(f"Document generated successfully: {response.document_filename}")
        return response

    except Exception as e:
        logger.error(f"Document generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Document generation failed: {str(e)}")


@app.post("/chat/refine")
async def refine_document(req: GenerateFromChatRequest) -> DocumentResponse:
    """Refine an already-generated document based on user feedback.

    Takes a refinement request and re-generates the document with the updated requirements.

    Args:
        req: Request with session ID, context, and refinement request

    Returns:
        Updated DocumentResponse with refined document
    """
    logger.info(f"Refining document from chat: {req.session_id}")

    if req.session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Chat session not found")

    try:
        context = chat_sessions[req.session_id]

        # Add refinement request to conversation context
        if not hasattr(context, 'refinement_requests'):
            context.refinement_requests = []
        context.refinement_requests.append(req.refinement_request)

        # Build refined prompt from chat context + refinement request
        prompt = chat_orchestrator.get_generation_prompt(context)
        prompt += f"\n\n[REFINEMENT REQUEST]: {req.refinement_request}"

        # Create document request with context
        doc_request = DocumentRequest(
            request=prompt,
            metadata={
                "session_id": req.session_id,
                "chat_history": len(context.conversation),
                "refinement_request": req.refinement_request,
                "source": "chat_refinement",
            }
        )

        logger.info(f"Calling orchestrator for document refinement...")

        # Generate refined document using multi-agent pipeline
        response = orchestrator.generate_document(doc_request)

        logger.info(f"Document refined successfully: {response.document_filename}")

        # Update session context
        chat_sessions[req.session_id] = context

        # Return response with refinement message
        return DocumentResponse(
            success=True,
            document_filename=response.document_filename,
            request=prompt,
            message=f"✓ Document refined based on: {req.refinement_request}"
        )

    except Exception as e:
        logger.error(f"Document refinement failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Document refinement failed: {str(e)}")


@app.post("/todo")
async def generate_todo_list(request: DocumentRequest) -> DocumentResponse:
    """Generate a prioritized todo list.

    Args:
        request: Request with task description

    Returns:
        DOCX with todo table
    """
    if not request.request or not request.request.strip():
        raise HTTPException(status_code=400, detail="Request cannot be empty")

    logger.info(f"Generating todo list: {request.request[:100]}...")

    try:
        # Generate todos using LLM
        todos = todo_generator.generate_todos(request.request)

        if not todos:
            raise DocumentGenerationException("Failed to generate todos")

        # Create document section
        todo_section = todo_generator.create_todo_document_section(todos)

        # Build DOCX
        docx_gen = DOCXGenerator()
        structure = DocumentStructure(
            title="Todo List",
            sections=[todo_section]
        )
        docx_gen.from_structure(structure)

        # Save
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"todos_{timestamp}.docx"
        filepath = os.path.join("output", filename)

        document_path = docx_gen.save(filepath)
        logger.info(f"Todo list generated: {filename}")

        return DocumentResponse(
            success=True,
            document_filename=filename,
            request=request.request,
            message=f"Generated {len(todos)} todo items"
        )

    except Exception as e:
        logger.error(f"Todo generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Document Generation API",
        "version": "2.0.0",
        "architecture": "LangGraph orchestration with LangChain agents",
        "endpoints": {
            "POST /agent": "Generate document from natural language request (custom orchestration)",
            "POST /agent/langgraph": "Generate document using LangGraph state machine + LangChain agents",
            "POST /todo": "Generate simple priority todo list (NEW - simple endpoint)",
            "POST /chat/start": "Start chatbot conversation with clarifying questions",
            "POST /chat/answer": "Answer a clarifying question in chat",
            "POST /chat/generate": "Generate document after chat completion",
            "POST /chat/refine": "Refine generated document based on user feedback",
            "GET /health": "Health check",
            "GET /metrics": "Aggregated metrics",
            "GET /files": "List all generated documents",
            "GET /download/{filename}": "Download a document",
        },
        "todo_workflow": {
            "simple": "POST /todo - Quick priority todo list generation"
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

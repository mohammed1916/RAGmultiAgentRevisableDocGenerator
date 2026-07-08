"""FastAPI server for document generation."""

import os
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .models import DocumentRequest, DocumentResponse, ChatContext, ChatResponse, GenerateFromChatRequest
from .orchestrator import Orchestrator
from .chat_orchestrator import ChatOrchestrator
from .langgraph_orchestrator import LangGraphOrchestrator
from .exceptions import DocumentGenerationException
from .logger import setup_logger

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

# Store chat sessions
chat_sessions = {}

# Mount static files (client UI)
try:
    from pathlib import Path
    client_path = Path(__file__).parent.parent / "client"
    if client_path.exists():
        app.mount("/client", StaticFiles(directory=str(client_path)), name="static")
        logger.info(f"Mounted static files from {client_path}")
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
        ChatResponse with initial questions
    """
    logger.info(f"Starting chat: {request.request[:100]}...")

    try:
        response = chat_orchestrator.start_conversation(request.request)

        # Store session
        import uuid
        session_id = str(uuid.uuid4())
        chat_sessions[session_id] = response.context

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
        return response
    except Exception as e:
        logger.error(f"Chat answer failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/generate")
async def generate_from_chat(req: GenerateFromChatRequest) -> DocumentResponse:
    """Generate document from completed chat context.

    Args:
        req: Request with session ID and context

    Returns:
        Generated document response
    """
    logger.info(f"Generating document from chat: {req.session_id}")

    if not req.context.is_ready_to_generate:
        raise HTTPException(
            status_code=400,
            detail="Chat context not ready for generation. Answer all required questions first."
        )

    try:
        # Build comprehensive prompt
        prompt = chat_orchestrator.get_generation_prompt(req.context)

        # Create document request with context
        doc_request = DocumentRequest(
            request=prompt,
            metadata={
                "session_id": req.session_id,
                "audience": req.context.answers.get("audience"),
                "scope": req.context.answers.get("scope"),
                "tone": req.context.answers.get("tone"),
            }
        )

        # Generate document
        response = orchestrator.generate_document(doc_request)
        logger.info(f"Document generated: {response.document_filename}")
        return response
    except Exception as e:
        logger.error(f"Document generation failed: {str(e)}")
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
            "POST /agent/langgraph": "Generate document using LangGraph state machine + LangChain agents (NEW)",
            "POST /chat/start": "Start chatbot conversation with clarifying questions",
            "POST /chat/answer": "Answer a clarifying question in chat",
            "POST /chat/generate": "Generate document after chat completion",
            "GET /health": "Health check",
            "GET /metrics": "Aggregated metrics",
            "GET /files": "List all generated documents",
            "GET /download/{filename}": "Download a document",
        },
        "chat_workflow": {
            "step1": "POST /chat/start - User sends initial request",
            "step2": "POST /chat/answer - User answers clarifying questions (repeat as needed)",
            "step3": "POST /chat/generate - Generate document when ready (uses LangGraph)",
        },
        "langgraph_features": {
            "orchestration": "State machine with Plan → Write → Review nodes",
            "agents": "LangChain tool-calling agents for autonomous loops",
            "llm": "Local Ollama (qwen3:8b by default)",
            "state_management": "LangGraph's add_messages reducer",
            "conditional_routing": "Iterative review with feedback loops",
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

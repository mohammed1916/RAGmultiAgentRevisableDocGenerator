"""FastAPI server for document generation."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import DocumentRequest, DocumentResponse
from .orchestrator import Orchestrator
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

# Global orchestrator instance
orchestrator = None


@app.on_event("startup")
async def startup_event():
    """Initialize orchestrator on startup."""
    global orchestrator
    logger.info("Starting up API server...")
    try:
        orchestrator = Orchestrator()
        logger.info("Orchestrator initialized successfully")
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


@app.get("/metrics")
async def get_metrics():
    """Get aggregated metrics (placeholder for future enhancement)."""
    return {
        "message": "Metrics endpoint - detailed metrics available in document responses",
    }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Document Generation API",
        "version": "1.0.0",
        "endpoints": {
            "POST /agent": "Generate document from natural language request",
            "GET /health": "Health check",
            "GET /metrics": "Aggregated metrics",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

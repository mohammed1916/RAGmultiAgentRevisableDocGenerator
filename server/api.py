"""FastAPI server for document generation."""

import os
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
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
            "GET /files": "List all generated documents",
            "GET /download/{filename}": "Download a document",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

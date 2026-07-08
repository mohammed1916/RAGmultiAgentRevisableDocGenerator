"""Main entry point for the document generation API."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "server.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )

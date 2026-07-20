"""Main entry point for the document generation API."""

import os

import uvicorn

if __name__ == "__main__":
    reload = os.getenv("APP_RELOAD", "false").lower() == "true"
    workers = int(os.getenv("WEB_CONCURRENCY", "1"))
    uvicorn.run(
        "server.api:app",
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", "8000")),
        reload=reload,
        # uvicorn forbids workers>1 together with reload.
        workers=None if reload else workers,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )

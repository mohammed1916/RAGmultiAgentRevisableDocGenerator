#!/usr/bin/env python
"""Start the FastAPI server with environment configuration."""

import os
import sys
import subprocess
from pathlib import Path

from dotenv import load_dotenv

if __name__ == "__main__":
    # Load environment variables from .env file
    env_file = Path(".env")
    if env_file.exists():
        load_dotenv(env_file)
        print(f"[OK] Loaded environment from {env_file}")
    else:
        print("[WARNING] .env file not found, using system environment variables")

    host = os.getenv("APP_HOST", "0.0.0.0")
    port = os.getenv("APP_PORT", "8000")
    reload = os.getenv("APP_RELOAD", "false").lower() == "true"
    workers = os.getenv("WEB_CONCURRENCY", "1")

    cmd = [sys.executable, "-m", "uvicorn", "server.api:app", "--host", host, "--port", port]
    if reload:
        cmd.append("--reload")
    elif workers != "1":
        cmd += ["--workers", workers]

    subprocess.run(cmd, check=False)

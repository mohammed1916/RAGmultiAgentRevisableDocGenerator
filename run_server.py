#!/usr/bin/env python
"""Start the FastAPI server with environment configuration."""

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

    # Run FastAPI server with uvicorn
    subprocess.run(
        [sys.executable, "-m", "uvicorn", "server.api:app", "--reload"],
        check=False
    )

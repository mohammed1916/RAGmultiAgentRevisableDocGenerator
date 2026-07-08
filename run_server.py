#!/usr/bin/env python
"""Start the FastAPI server."""

import sys
import subprocess

if __name__ == "__main__":
    # Run FastAPI server with uvicorn
    subprocess.run(
        [sys.executable, "-m", "uvicorn", "server.api:app", "--reload"],
        check=False
    )

#!/usr/bin/env python
"""Setup Milvus vector database for RAG system.

Provides Docker Compose commands and status checking.

Usage:
    python setup_milvus.py                  # Show status and instructions
    python setup_milvus.py --start           # Start Milvus (docker-compose up)
    python setup_milvus.py --stop            # Stop Milvus (docker-compose down)
    python setup_milvus.py --status          # Check if Milvus is running
    python setup_milvus.py --logs            # View Milvus logs
"""

import subprocess
import sys
import argparse
from pathlib import Path

# Add parent directory to path so we can import server modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.tools import MilvusRAG
from server.logger import setup_logger

logger = setup_logger(__name__)


def check_docker():
    """Check if Docker is installed."""
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def run_docker_compose(command: str):
    """Run a docker-compose command.

    Args:
        command: 'up', 'down', 'logs', 'ps'
    """
    try:
        if command == "up":
            subprocess.run(
                ["docker-compose", "up", "-d"],
                check=True,
                capture_output=False,
            )
        elif command == "down":
            subprocess.run(
                ["docker-compose", "down"],
                check=True,
                capture_output=False,
            )
        elif command == "logs":
            subprocess.run(
                ["docker-compose", "logs", "-f", "milvus"],
                check=False,
            )
        elif command == "ps":
            subprocess.run(
                ["docker-compose", "ps"],
                check=False,
            )
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Docker command failed: {e}")
        return False


def check_milvus_status():
    """Check if Milvus is running and accessible."""
    try:
        rag = MilvusRAG()
        stats = rag.get_stats()
        rag.close()

        if rag.mock_mode:
            return "mock", "Milvus not running (mock mode)"

        return "real", f"Milvus running ({stats.get('total_documents', 0)} chunks)"
    except Exception as e:
        return "error", str(e)


def show_instructions():
    """Show setup instructions."""
    print("\n" + "=" * 80)
    print("🐳 MILVUS SETUP - Vector Database for RAG")
    print("=" * 80)

    mode, status = check_milvus_status()

    print(f"\n📊 Current Status: {status}")

    if mode == "real":
        print("✅ Milvus is running and ready!")
        print("\nNext steps:")
        print("  1. Load curriculum: python load_curriculum.py")
        print("  2. View chunks: python view_chunks.py --stats")
        print("  3. Search: python view_chunks.py --search 'physics'")
        return

    print("""
🚀 QUICK START:

    1. Make sure Docker is installed:
       https://www.docker.com/products/docker-desktop

    2. Start Milvus:
       python setup_milvus.py --start

    3. Load curriculum data:
       python load_curriculum.py

    4. View chunks:
       python view_chunks.py --stats

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 COMMANDS:

    python setup_milvus.py                  # Show this help
    python setup_milvus.py --start          # Start Milvus (docker-compose up -d)
    python setup_milvus.py --stop           # Stop Milvus (docker-compose down)
    python setup_milvus.py --status         # Check if running
    python setup_milvus.py --logs           # View live logs

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 WORKFLOW:

    1. Start Milvus:
       docker-compose up -d

    2. Verify it's running:
       docker-compose ps

    3. Load curriculum:
       python load_curriculum.py

    4. Test the RAG system:
       python run_server.py
       # Then hit: http://localhost:8000/api/generate

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 TROUBLESHOOTING:

    ❌ "Docker not found"
       → Install Docker Desktop

    ❌ "Port already in use"
       → docker-compose down -v
       → docker-compose up -d

    ❌ "Milvus won't start"
       → Check logs: docker-compose logs milvus
       → Try: docker system prune

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """)


def main():
    parser = argparse.ArgumentParser(
        description="Setup Milvus vector database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--start",
        action="store_true",
        help="Start Milvus with docker-compose",
    )
    parser.add_argument(
        "--stop",
        action="store_true",
        help="Stop Milvus",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Check Milvus status",
    )
    parser.add_argument(
        "--logs",
        action="store_true",
        help="View Milvus logs",
    )

    args = parser.parse_args()

    if not check_docker():
        print("❌ Docker is not installed")
        print("   Install from: https://www.docker.com/products/docker-desktop")
        sys.exit(1)

    if args.start:
        print("\n🚀 Starting Milvus...")
        if run_docker_compose("up"):
            print("✅ Milvus started! Check with: docker-compose ps")
        else:
            print("❌ Failed to start Milvus")
            sys.exit(1)

    elif args.stop:
        print("\n🛑 Stopping Milvus...")
        if run_docker_compose("down"):
            print("✅ Milvus stopped")
        else:
            print("❌ Failed to stop Milvus")
            sys.exit(1)

    elif args.status:
        mode, status = check_milvus_status()
        print(f"\n{status}")
        if mode == "real":
            print("✅ Milvus is operational")
        else:
            print("⚠️  Milvus is not running")

    elif args.logs:
        print("\n📋 Milvus Logs (Ctrl+C to exit):")
        run_docker_compose("logs")

    else:
        show_instructions()


if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""Verify LangSmith configuration and connectivity.

Tests if LangSmith is properly set up and connected.
"""

import sys
import io
from pathlib import Path

# Fix Windows console encoding issues with UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path so we can import server modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.config.settings import config
from server.tools.utils.langsmith_tracer import get_langsmith_status, enable_langsmith_tracing
from server.base.logger import setup_logger

logger = setup_logger(__name__)


def verify_langsmith():
    """Verify LangSmith configuration."""
    print("\n" + "=" * 80)
    print("[VERIFY] LangSmith Configuration Check")
    print("=" * 80)

    # Check configuration
    print("\n[1] Configuration Status")
    print("    " + "-" * 76)
    print(f"    Enabled: {'[OK]' if config.langsmith.enabled else '[DISABLED]'}")
    print(f"    API Key: {'[SET]' if config.langsmith.api_key else '[MISSING]'}")
    if config.langsmith.api_key:
        masked_key = config.langsmith.api_key[:5] + "..." + config.langsmith.api_key[-5:]
        print(f"             {masked_key}")
    print(f"    Project: {config.langsmith.project}")
    print(f"    Endpoint: {config.langsmith.endpoint}")

    # Get runtime status
    print("\n[2] Runtime Status")
    print("    " + "-" * 76)
    status = get_langsmith_status()

    if status['enabled']:
        print(f"    Status: [OK] LangSmith is ENABLED")
        print(f"    API Key Present: {'[OK]' if status['has_api_key'] else '[MISSING]'}")
        print(f"    Tracing Active: {'[OK]' if status['tracing_active'] else '[NOT ACTIVE]'}")
        print(f"    Project: {status['project']}")
    else:
        print(f"    Status: [INFO] LangSmith is DISABLED")
        print(f"    To enable, set: LANGSMITH_ENABLED=true")

    # Test connectivity
    if config.langsmith.enabled and config.langsmith.api_key:
        print("\n[3] Connectivity Test")
        print("    " + "-" * 76)
        try:
            import requests
            headers = {
                "x-api-key": config.langsmith.api_key,
            }
            response = requests.get(
                f"{config.langsmith.endpoint}/sessions",
                headers=headers,
                timeout=5
            )
            if response.status_code == 200:
                print("    [OK] Connected to LangSmith API")
                print(f"    Status: HTTP {response.status_code}")
            elif response.status_code == 401:
                print("    [ERROR] Invalid API key")
                print(f"    Status: HTTP {response.status_code}")
            else:
                print(f"    [WARN] Unexpected response")
                print(f"    Status: HTTP {response.status_code}")
        except Exception as e:
            print(f"    [ERROR] Connection failed: {e}")
    else:
        print("\n[3] Connectivity Test")
        print("    " + "-" * 76)
        print("    [SKIP] LangSmith not enabled or API key missing")

    # Recommendations
    print("\n[4] Setup Instructions")
    print("    " + "-" * 76)

    if not config.langsmith.enabled:
        print("    1. Set LANGSMITH_ENABLED=true in .env or environment")

    if config.langsmith.enabled and not config.langsmith.api_key:
        print("    1. Get API key from https://smith.langchain.com/")
        print("    2. Set LANGSMITH_API_KEY=ls_... in .env or environment")

    if config.langsmith.enabled and config.langsmith.api_key:
        print("    Configuration looks good!")
        print("    Next steps:")
        print("    1. Run: python scripts/show_metrics.py")
        print("    2. Visit: https://smith.langchain.com/")
        print("    3. Select project: " + config.langsmith.project)
        print("    4. View traces from your recent runs")

    # Summary
    print("\n[SUMMARY]")
    print("    " + "-" * 76)

    checks = {
        "LangSmith Enabled": config.langsmith.enabled,
        "API Key Set": bool(config.langsmith.api_key),
        "Project Configured": bool(config.langsmith.project),
        "Endpoint Set": bool(config.langsmith.endpoint),
    }

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)

    for check, result in checks.items():
        status_str = "[OK]" if result else "[FAIL]"
        print(f"    {check}: {status_str}")

    print(f"\n    Passed: {passed}/{total}")

    if passed == total and config.langsmith.enabled:
        print("    Status: [OK] Ready to use LangSmith!")
        return 0
    elif not config.langsmith.enabled:
        print("    Status: [INFO] LangSmith disabled (optional feature)")
        return 0
    else:
        print("    Status: [WARN] Some checks failed, see instructions above")
        return 1


def main():
    """Main entry point."""
    try:
        exit_code = verify_langsmith()
        print("\n" + "=" * 80)
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        print(f"\n[ERROR] Verification failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

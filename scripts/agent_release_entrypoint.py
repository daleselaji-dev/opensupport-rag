"""Gate the containerized V1 API on the checked-in release evidence."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    report_path = Path(os.getenv("RELEASE_CHECK_PATH", "/app/reports/release_check_latest.json"))
    if not report_path.exists():
        raise SystemExit(f"Release check report not found: {report_path}")
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    if payload.get("release_ready") is not True:
        failed = [str(item.get("key")) for item in payload.get("checks", []) if not item.get("passed")]
        raise SystemExit(f"Refusing to start V1 Agent; release gates failed: {', '.join(failed)}")
    os.environ["AGENT_ENABLED"] = "true"
    host = os.getenv("AGENT_HOST", "0.0.0.0")
    port = os.getenv("AGENT_PORT", "8000")
    os.execv(sys.executable, [sys.executable, "-m", "uvicorn", "app.main:app", "--host", host, "--port", port])


if __name__ == "__main__":
    main()

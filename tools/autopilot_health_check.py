from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HEALTH_FILE = REPO / "LOCAL_ONLY" / "autopilot" / "health.json"
MAX_HEARTBEAT_AGE_SECONDS = 180


def parse_time(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def main() -> int:
    if not HEALTH_FILE.exists():
        print("ERROR: autopilot health file not found.")
        return 2

    try:
        health = json.loads(HEALTH_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: could not read autopilot health file: {exc}")
        return 2

    heartbeat = parse_time(health.get("heartbeat_at"))
    if heartbeat is None:
        print("ERROR: autopilot heartbeat is missing or invalid.")
        return 2

    age = (datetime.now(timezone.utc) - heartbeat.astimezone(timezone.utc)).total_seconds()
    failures = health.get("consecutive_failures", {})
    if not isinstance(failures, dict):
        failures = {}

    stale = age > MAX_HEARTBEAT_AGE_SECONDS
    unhealthy_jobs = {k: int(v or 0) for k, v in failures.items() if int(v or 0) > 0}

    print("VASTcode21 AUTOPILOT HEALTH")
    print(f"Version: {health.get('version', 'unknown')}")
    print(f"Heartbeat age: {int(max(0, age))}s")
    print(f"Social cadence: {health.get('cadence_seconds', {}).get('social', '?')}s")
    print(f"Business cadence: {health.get('cadence_seconds', {}).get('business', '?')}s")
    print(f"Meta DM cadence: {health.get('cadence_seconds', {}).get('meta_dm', '?')}s")
    print(f"Consecutive failures: {unhealthy_jobs if unhealthy_jobs else 'none'}")
    print("Paid ads: OFF | Live trading: OFF | Sales: OFF | Cold DMs: OFF")

    if stale:
        print("ERROR: daemon heartbeat is stale.")
        return 3
    if unhealthy_jobs:
        print("WARNING: daemon is alive but one or more jobs are retrying after failures.")
        return 4

    print("PASS: daemon heartbeat is current and all jobs are healthy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

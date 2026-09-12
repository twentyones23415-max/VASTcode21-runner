from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
SOCIAL = REPO / "tools" / "social_autopilot_runtime.py"
BUSINESS = REPO / "tools" / "business_autopilot.py"
META_DM = REPO / "tools" / "meta_dm_autopilot.py"

LOCAL = REPO / "LOCAL_ONLY" / "autopilot"
HEALTH_FILE = LOCAL / "health.json"
LOG_FILE = LOCAL / "health.log"

SOCIAL_INTERVAL = 30 * 60
BUSINESS_INTERVAL = 30 * 60
META_DM_INTERVAL = 5 * 60
FAILURE_RETRY = 5 * 60
HEARTBEAT_INTERVAL = 60
IDLE_TICK = 10
VERSION = "3.2.0"


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def log(message: str) -> None:
    LOCAL.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"[{utcnow()}] {message}\n")


def run_job(name: str, script: Path, timeout: int) -> dict[str, Any]:
    started = time.monotonic()
    result: dict[str, Any] = {
        "name": name,
        "started_at": utcnow(),
        "script": str(script.relative_to(REPO)) if script.exists() else str(script),
        "ok": False,
        "return_code": None,
        "error": None,
    }

    if not script.exists():
        result["error"] = "script_missing"
        result["duration_seconds"] = round(time.monotonic() - started, 3)
        return result

    try:
        p = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(REPO),
            check=False,
            timeout=timeout,
        )
        result["return_code"] = int(p.returncode)
        result["ok"] = p.returncode == 0
        if p.returncode != 0:
            result["error"] = f"return_code_{p.returncode}"
    except subprocess.TimeoutExpired:
        result["error"] = "timeout"
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"

    result["finished_at"] = utcnow()
    result["duration_seconds"] = round(time.monotonic() - started, 3)
    return result


def main() -> None:
    LOCAL.mkdir(parents=True, exist_ok=True)
    started_at = utcnow()
    next_social = 0.0
    next_business = 0.0
    next_meta_dm = 0.0
    next_heartbeat = 0.0

    failures = {"social": 0, "business": 0, "meta_dm": 0}
    jobs: dict[str, dict[str, Any]] = {}

    def publish() -> None:
        save_json(
            HEALTH_FILE,
            {
                "version": VERSION,
                "daemon_started_at": started_at,
                "heartbeat_at": utcnow(),
                "healthy": all(int(v) == 0 for v in failures.values()),
                "jobs": jobs,
                "consecutive_failures": failures,
                "retry_policy": "failed jobs retry after 5 minutes; successful jobs return to normal cadence",
                "cadence_seconds": {
                    "social": SOCIAL_INTERVAL,
                    "business": BUSINESS_INTERVAL,
                    "meta_dm": META_DM_INTERVAL,
                },
                "paid_ads": False,
                "live_trading": False,
                "sales_enabled": False,
                "cold_dm": False,
            },
        )

    def execute(name: str, script: Path, timeout: int, normal_interval: int) -> float:
        previous_failures = failures[name]
        result = run_job(name, script, timeout)
        jobs[name] = result

        if result.get("ok"):
            failures[name] = 0
            if previous_failures:
                log(f"RECOVERED {name} after {previous_failures} consecutive failure(s)")
            next_delay = normal_interval
        else:
            failures[name] = previous_failures + 1
            next_delay = FAILURE_RETRY
            log(
                f"FAIL {name} consecutive={failures[name]} "
                f"error={result.get('error')} retry_in_seconds={next_delay}"
            )

        publish()
        return time.monotonic() + next_delay

    publish()

    while True:
        now = time.monotonic()

        if now >= next_social:
            next_social = execute("social", SOCIAL, 5 * 60, SOCIAL_INTERVAL)

        now = time.monotonic()
        if now >= next_business:
            next_business = execute("business", BUSINESS, 5 * 60, BUSINESS_INTERVAL)

        now = time.monotonic()
        if now >= next_meta_dm:
            next_meta_dm = execute("meta_dm", META_DM, 2 * 60, META_DM_INTERVAL)

        now = time.monotonic()
        if now >= next_heartbeat:
            publish()
            next_heartbeat = now + HEARTBEAT_INTERVAL

        time.sleep(IDLE_TICK)


if __name__ == "__main__":
    main()

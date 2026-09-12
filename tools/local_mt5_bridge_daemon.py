from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_log(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n")


def acquire_single_instance(lock_path: Path):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fh = lock_path.open("a+b")
    try:
        import msvcrt
        fh.seek(0)
        if fh.tell() == 0:
            fh.write(b"0")
            fh.flush()
        fh.seek(0)
        msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        return fh
    except Exception:
        fh.close()
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description="VASTcode21 background MT5 bridge daemon")
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--interval-minutes", type=int, default=30)
    ap.add_argument("--max", type=int, default=2)
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    local_only = repo / "LOCAL_ONLY" / "mt5_bridge"
    log = local_only / "daemon.log"
    lock = acquire_single_instance(local_only / "daemon.lock")
    if lock is None:
        append_log(log, f"[{utcnow()}] another bridge daemon is already running; exit")
        return

    append_log(log, f"[{utcnow()}] VASTcode21 MT5 bridge daemon started")
    append_log(log, "live trading OFF; paid services OFF")
    interval = max(10, int(args.interval_minutes)) * 60
    bridge = repo / "tools" / "local_mt5_bridge.py"

    while True:
        try:
            p = subprocess.run(
                [sys.executable, str(bridge), "--repo", str(repo), "--max", str(max(1, args.max))],
                cwd=str(repo),
                text=True,
                capture_output=True,
                timeout=60 * 45,
            )
            append_log(log, f"[{utcnow()}] cycle exit={p.returncode}")
            if p.stdout:
                append_log(log, p.stdout)
            if p.stderr:
                append_log(log, "STDERR:\n" + p.stderr)
        except subprocess.TimeoutExpired:
            append_log(log, f"[{utcnow()}] cycle timed out after 45 minutes")
        except Exception as exc:
            append_log(log, f"[{utcnow()}] ERROR: {exc}")
        time.sleep(interval)


if __name__ == "__main__":
    main()

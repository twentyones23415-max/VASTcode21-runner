from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LOCAL = REPO / "LOCAL_ONLY" / "mt5_bridge"
LOG = LOCAL / "daemon.log"
LOCK = LOCAL / "autopilot.lock"
STATUS = LOCAL / "autopilot_status.json"

INTERVAL_SECONDS = int(os.getenv("VC21_BRIDGE_INTERVAL_SECONDS", "1800"))
LOCK_STALE_SECONDS = 3 * 60 * 60

# Defensive hard-off defaults. The bridge/core may also enforce these independently.
os.environ["VC21_LIVE_TRADING"] = "0"
os.environ["VC21_PAID_SERVICES"] = "0"


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(message: str) -> None:
    LOCAL.mkdir(parents=True, exist_ok=True)
    line = f"[{utcnow()}] {message}"
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def write_status(**extra) -> None:
    LOCAL.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": utcnow(),
        "live_trading": False,
        "paid_services": False,
        **extra,
    }
    STATUS.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def git_exe() -> str:
    configured = os.getenv("VC21_GIT_EXE", "").strip()
    if configured and Path(configured).exists():
        return configured
    default = Path(r"C:\Program Files\Git\cmd\git.exe")
    return str(default if default.exists() else "git")


def run_git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [git_exe(), *args],
        cwd=str(REPO),
        text=True,
        capture_output=True,
        check=False,
    )


def tracked_dirty() -> tuple[bool, str]:
    p = run_git("status", "--porcelain", "--untracked-files=no")
    text = (p.stdout or "").strip()
    return bool(text), text


def inbox_envelopes() -> list[Path]:
    inbox = REPO / "handoff" / "inbox"
    if not inbox.exists():
        return []
    return sorted(inbox.glob("*.enc"))


def acquire_lock() -> bool:
    LOCAL.mkdir(parents=True, exist_ok=True)
    if LOCK.exists():
        try:
            age = time.time() - LOCK.stat().st_mtime
            if age > LOCK_STALE_SECONDS:
                LOCK.unlink(missing_ok=True)
                log(f"removed stale autopilot lock age={int(age)}s")
        except OSError:
            pass
    try:
        fd = os.open(str(LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps({"pid": os.getpid(), "created_at": utcnow()}))
        return True
    except FileExistsError:
        return False


def release_lock() -> None:
    try:
        LOCK.unlink(missing_ok=True)
    except OSError:
        pass


def safe_sync() -> bool:
    dirty, detail = tracked_dirty()
    if dirty:
        log("cycle deferred: tracked working tree changes exist; no automatic reset performed")
        write_status(state="deferred_dirty_tree", detail=detail[:1200])
        return False

    p = run_git("pull", "--rebase", "origin", "main")
    if p.returncode != 0:
        detail = ((p.stdout or "") + "\n" + (p.stderr or "")).strip()
        log(f"cycle deferred: git pull --rebase failed: {detail[-1500:]}")
        # Never force/reset automatically. Leave evidence for recovery.
        write_status(state="deferred_git_sync", detail=detail[-1500:])
        return False

    return True


def cycle(check_only: bool = False) -> int:
    if not acquire_lock():
        log("cycle skipped: another VASTcode21 autopilot instance owns the lock")
        return 0

    try:
        if not safe_sync():
            return 0

        pending_files = inbox_envelopes()
        if pending_files:
            names = [p.name for p in pending_files]
            log(
                "cycle deferred: encrypted MT5 validation envelope(s) already await "
                f"cloud ingest: {', '.join(names)}"
            )
            write_status(
                state="awaiting_cloud_ingest",
                pending_envelopes=len(pending_files),
                envelope_names=names[:20],
            )
            return 0

        if check_only:
            log("autopilot preflight OK")
            write_status(state="preflight_ok", pending_envelopes=0)
            return 0

        bridge = REPO / "tools" / "local_mt5_bridge.py"
        if not bridge.exists():
            log(f"ERROR: missing bridge: {bridge}")
            write_status(state="error", detail=f"missing bridge: {bridge}")
            return 2

        log("starting guarded MT5 bridge cycle")
        p = subprocess.run(
            [sys.executable, str(bridge)],
            cwd=str(REPO),
            text=True,
            capture_output=True,
            check=False,
            timeout=45 * 60,
            env=os.environ.copy(),
        )

        if p.stdout:
            for line in p.stdout.rstrip().splitlines():
                log("BRIDGE: " + line)
        if p.stderr:
            for line in p.stderr.rstrip().splitlines():
                log("BRIDGE-STDERR: " + line)

        if p.returncode != 0:
            log(f"bridge cycle exit={p.returncode}")
            write_status(state="bridge_error", exit_code=p.returncode)
            return p.returncode

        post = inbox_envelopes()
        if post:
            # This is the critical duplicate guard:
            # do not validate again until the cloud has ingested and removed these.
            log(f"bridge cycle complete; {len(post)} envelope(s) now await cloud ingest")
            write_status(
                state="awaiting_cloud_ingest",
                pending_envelopes=len(post),
                envelope_names=[x.name for x in post[:20]],
            )
        else:
            log("bridge cycle complete; no local envelope awaiting ingest")
            write_status(state="idle", pending_envelopes=0)

        return 0

    except subprocess.TimeoutExpired:
        log("bridge cycle timed out; no force reset or MT5 kill was attempted")
        write_status(state="bridge_timeout")
        return 3
    except Exception as exc:
        log(f"autopilot cycle error: {type(exc).__name__}: {exc}")
        write_status(state="error", detail=f"{type(exc).__name__}: {exc}")
        return 4
    finally:
        release_lock()


def main() -> None:
    ap = argparse.ArgumentParser(description="VASTcode21 guarded automatic MT5 bridge daemon")
    ap.add_argument("--once", action="store_true", help="Run one guarded cycle and exit")
    ap.add_argument("--check-only", action="store_true", help="Run only sync/safety preflight")
    args = ap.parse_args()

    LOCAL.mkdir(parents=True, exist_ok=True)
    log("VASTcode21 Autopilot v1.3.0 daemon started")
    log("live trading OFF; paid services OFF; force-push/reset disabled")

    if args.once or args.check_only:
        raise SystemExit(cycle(check_only=args.check_only))

    while True:
        cycle(check_only=False)
        time.sleep(max(300, INTERVAL_SECONDS))


if __name__ == "__main__":
    main()

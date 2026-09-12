from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def find_local_core(repo: Path) -> Path:
    for p in sorted(repo.parent.glob("VASTcode21_local_v*"), reverse=True):
        if (p / ".venv" / "Scripts" / "pythonw.exe").exists() and (p / "vastcode21").exists():
            return p.resolve()
    raise SystemExit("Could not find a VASTcode21_local_v* installation with .venv")


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    local_core = find_local_core(repo)
    pythonw = local_core / ".venv" / "Scripts" / "pythonw.exe"
    python = local_core / ".venv" / "Scripts" / "python.exe"
    daemon = repo / "tools" / "local_mt5_bridge_daemon.py"
    key = repo / "LOCAL_ONLY" / "VC21_CORE_KEY.txt"
    if not key.exists():
        raise SystemExit(f"Missing local-only key: {key}")

    startup = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    startup.mkdir(parents=True, exist_ok=True)
    cmd = startup / "VASTcode21_MT5_Bridge.cmd"
    cmd.write_text(
        "@echo off\r\n"
        f'cd /d "{repo}"\r\n'
        f'start "VASTcode21 MT5 Bridge" /min "{pythonw}" "{daemon}" --repo "{repo}" --interval-minutes 30 --max 2\r\n',
        encoding="utf-8",
    )

    # Start immediately too. pythonw keeps it silent; all details go to LOCAL_ONLY log.
    subprocess.Popen(
        [str(pythonw), str(daemon), "--repo", str(repo), "--interval-minutes", "30", "--max", "2"],
        cwd=str(repo),
        close_fds=True,
    )

    print("VASTcode21 automatic MT5 bridge installed for this Windows user.")
    print(f"Startup entry: {cmd}")
    print(f"Local core: {local_core}")
    print(f"Log: {repo / 'LOCAL_ONLY' / 'mt5_bridge' / 'daemon.log'}")
    print("Runs immediately and every 30 minutes while this PC is on.")
    print("Cloud research continues independently while this PC is off.")
    print("Live trading remains OFF. Paid services remain OFF.")


if __name__ == "__main__":
    main()

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
STARTUP = Path(os.environ.get("APPDATA", str(Path.home() / "AppData/Roaming"))) / "Microsoft/Windows/Start Menu/Programs/Startup"
STARTUP_FILE = STARTUP / "VASTcode21_Social_Autopilot.cmd"


def locate_python() -> tuple[Path, Path]:
    for core in sorted(REPO.parent.glob("VASTcode21_local_v*"), reverse=True):
        py = core / ".venv" / "Scripts" / "python.exe"
        pyw = core / ".venv" / "Scripts" / "pythonw.exe"
        if py.exists() and pyw.exists():
            return py, pyw
    return Path(sys.executable), Path(sys.executable)


def stop_existing_daemon() -> None:
    ps = (
        "$needle='social_autopilot_daemon.py'; "
        "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -like ('*'+$needle+'*') } | "
        "ForEach-Object { if ($_.ProcessId -ne $PID) { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } }"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], text=True, check=False)


def main() -> None:
    print("VASTcode21 SOCIAL AUTOPILOT v2.1")
    print("Organic Instagram automation | Paid ads OFF | Live trading OFF\n")
    py, pyw = locate_python()
    git = Path(r"C:\Program Files\Git\cmd\git.exe")
    git_exe = str(git if git.exists() else "git")
    p = subprocess.run([git_exe, "pull", "--rebase", "origin", "main"], cwd=str(REPO), text=True)
    if p.returncode != 0:
        raise SystemExit("ERROR: git pull --rebase failed. No reset or force-push was attempted.")
    rc = subprocess.run([str(py), str(REPO / "tools" / "social_autopilot.py"), "--configure"], cwd=str(REPO)).returncode
    if rc != 0:
        raise SystemExit(rc)
    STARTUP.mkdir(parents=True, exist_ok=True)
    STARTUP_FILE.write_text(
        "@echo off\n"
        f'start "" "{pyw}" "{REPO / "tools" / "social_autopilot_daemon.py"}\n',
        encoding="utf-8",
    )
    stop_existing_daemon()
    subprocess.Popen(
        [str(pyw), str(REPO / "tools" / "social_autopilot_daemon.py")],
        cwd=str(REPO),
        creationflags=0x00000008 | 0x00000200,
    )
    dry = subprocess.run([str(py), str(REPO / "tools" / "social_autopilot.py"), "--dry-run"], cwd=str(REPO)).returncode
    if dry != 0:
        print("WARNING: setup succeeded but dry-run validation reported an issue. Check LOCAL_ONLY\\social\\social.log")
    print("\nSUCCESS: VASTcode21 Social Autopilot v2.1 is installed.")
    print(f"Startup entry: {STARTUP_FILE}")
    print(f"Local log: {REPO / 'LOCAL_ONLY' / 'social' / 'social.log'}")
    print("Maximum organic posting rate: 1 post/day")
    print("Paid ads: OFF | Live trading: OFF")
    input("\nPress Enter to close...")


if __name__ == "__main__":
    main()

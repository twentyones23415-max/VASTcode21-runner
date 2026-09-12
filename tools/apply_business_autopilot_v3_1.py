from __future__ import annotations

import subprocess
from pathlib import Path

import install_social_autopilot as installer

REPO = Path(__file__).resolve().parents[1]


def main() -> None:
    print("VASTcode21 BUSINESS AUTOPILOT v3.1")
    print("Organic social + official Meta Instagram DM operations")
    print("Cold DMs OFF | Paid ads OFF | Live trading OFF | Sales OFF\n")

    py, pyw = installer.locate_python()

    checks = [
        ("social", REPO / "tools" / "social_autopilot_runtime.py", ["--dry-run"]),
        ("business", REPO / "tools" / "business_autopilot.py", []),
        ("meta-dm", REPO / "tools" / "meta_dm_autopilot.py", ["--check"]),
    ]
    for name, script, args in checks:
        p = subprocess.run([str(py), str(script), *args], cwd=str(REPO), check=False)
        if p.returncode != 0:
            raise SystemExit(
                f"ERROR: {name} check returned {p.returncode}. "
                "No daemon changes were made. Review LOCAL_ONLY logs."
            )

    p = subprocess.run(
        [str(py), str(REPO / "tools" / "meta_dm_autopilot.py")],
        cwd=str(REPO),
        check=False,
    )
    if p.returncode != 0:
        raise SystemExit(
            f"ERROR: meta-dm first cycle returned {p.returncode}. "
            "No daemon changes were made."
        )

    installer.stop_existing_daemon()
    subprocess.Popen(
        [str(pyw), str(REPO / "tools" / "social_autopilot_daemon.py")],
        cwd=str(REPO),
        creationflags=0x00000008 | 0x00000200,
    )

    print("\nSUCCESS: VASTcode21 Business Autopilot v3.1 is active.")
    print("Auto posting: ON")
    print("Safe public comment replies: ON")
    print("Official Meta Instagram DM ingestion: ON")
    print("Safe replies to user-initiated DMs: ON")
    print("Lead capture + escalation: ON")
    print("Cold DMs: OFF")
    print("Paid ads: OFF | Live trading: OFF | Sales: OFF")


if __name__ == "__main__":
    main()

from __future__ import annotations

import subprocess
from pathlib import Path

import install_social_autopilot as installer

REPO = Path(__file__).resolve().parents[1]


def main() -> None:
    print("VASTcode21 BUSINESS AUTOPILOT v3.0")
    print("Organic growth + comment operations + lead triage")
    print("Paid ads OFF | Live trading OFF | Sales OFF\n")

    py, pyw = installer.locate_python()
    installer.stop_existing_daemon()
    subprocess.Popen(
        [str(pyw), str(REPO / "tools" / "social_autopilot_daemon.py")],
        cwd=str(REPO),
        creationflags=0x00000008 | 0x00000200,
    )

    checks = [
        ("social", REPO / "tools" / "social_autopilot_runtime.py", ["--dry-run"]),
        ("business", REPO / "tools" / "business_autopilot.py", []),
    ]
    for name, script, args in checks:
        p = subprocess.run([str(py), str(script), *args], cwd=str(REPO), check=False)
        if p.returncode != 0:
            raise SystemExit(f"ERROR: {name} check returned {p.returncode}. Review LOCAL_ONLY logs.")

    print("\nSUCCESS: VASTcode21 Business Autopilot v3.0 is active.")
    print("Auto posting: ON")
    print("Safe public comment replies: ON")
    print("High-intent lead capture: ON")
    print("Growth analytics: ON")
    print("Private Instagram DMs: PENDING official Meta Messaging API setup")
    print("Paid ads: OFF | Live trading: OFF | Sales: OFF")


if __name__ == "__main__":
    main()

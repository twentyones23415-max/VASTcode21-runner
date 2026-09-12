from __future__ import annotations

import subprocess
import time
from pathlib import Path

import install_social_autopilot as installer

REPO = Path(__file__).resolve().parents[1]


def main() -> None:
    print("VASTcode21 BUSINESS AUTOPILOT v3.2.0")
    print("Organic social + Meta DM + health guard / self-recovery")
    print("Cold DMs OFF | Paid ads OFF | Live trading OFF | Sales OFF\n")

    py, pyw = installer.locate_python()

    checks = [
        ("social", REPO / "tools" / "social_autopilot_runtime.py", ["--dry-run"]),
        ("business", REPO / "tools" / "business_autopilot.py", []),
        ("meta-dm", REPO / "tools" / "meta_dm_autopilot.py", ["--check"]),
        ("meta-dm-selftest", REPO / "tools" / "meta_dm_selftest.py", []),
    ]
    for name, script, args in checks:
        p = subprocess.run([str(py), str(script), *args], cwd=str(REPO), check=False)
        if p.returncode != 0:
            raise SystemExit(
                f"ERROR: {name} check returned {p.returncode}. "
                "Daemon was not restarted. Review LOCAL_ONLY logs."
            )

    installer.stop_existing_daemon()
    subprocess.Popen(
        [str(pyw), str(REPO / "tools" / "social_autopilot_daemon.py")],
        cwd=str(REPO),
        creationflags=0x00000008 | 0x00000200,
    )

    # The daemon writes its first heartbeat immediately on startup.
    time.sleep(2)
    health = subprocess.run(
        [str(py), str(REPO / "tools" / "autopilot_health_check.py")],
        cwd=str(REPO),
        check=False,
    )
    if health.returncode not in (0, 4):
        raise SystemExit(
            f"ERROR: health guard check returned {health.returncode}. "
            "Review LOCAL_ONLY\\autopilot\\health.json and health.log."
        )

    print("\nSUCCESS: VASTcode21 Business Autopilot v3.2.0 is active.")
    print("Auto posting: ON")
    print("Safe public comment replies: ON")
    print("Official Meta Instagram DM ingestion: ON")
    print("Safe replies to user-initiated DMs: ON")
    print("Meta DM inbox scan: every 5 minutes")
    print("Social + business cycle: every 30 minutes")
    print("Health heartbeat: every 60 seconds")
    print("Failed-job automatic retry: every 5 minutes until recovery")
    print("Local health status: LOCAL_ONLY\\autopilot\\health.json")
    print("Cold DMs: OFF")
    print("Paid ads: OFF | Live trading: OFF | Sales: OFF")


if __name__ == "__main__":
    main()

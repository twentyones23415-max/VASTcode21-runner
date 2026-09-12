from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SOCIAL = REPO / "tools" / "social_autopilot_runtime.py"
BUSINESS = REPO / "tools" / "business_autopilot.py"
META_DM = REPO / "tools" / "meta_dm_autopilot.py"

SOCIAL_INTERVAL = 30 * 60
BUSINESS_INTERVAL = 30 * 60
META_DM_INTERVAL = 5 * 60
IDLE_TICK = 10


def run(script: Path, timeout: int) -> None:
    if not script.exists():
        return
    try:
        subprocess.run([sys.executable, str(script)], cwd=str(REPO), check=False, timeout=timeout)
    except Exception:
        pass


def main() -> None:
    next_social = 0.0
    next_business = 0.0
    next_meta_dm = 0.0

    while True:
        now = time.monotonic()

        if now >= next_social:
            run(SOCIAL, 5 * 60)
            next_social = time.monotonic() + SOCIAL_INTERVAL

        now = time.monotonic()
        if now >= next_business:
            run(BUSINESS, 5 * 60)
            next_business = time.monotonic() + BUSINESS_INTERVAL

        now = time.monotonic()
        if now >= next_meta_dm:
            run(META_DM, 2 * 60)
            next_meta_dm = time.monotonic() + META_DM_INTERVAL

        time.sleep(IDLE_TICK)


if __name__ == "__main__":
    main()

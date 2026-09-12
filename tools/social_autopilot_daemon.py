from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SOCIAL = REPO / "tools" / "social_autopilot_runtime.py"
BUSINESS = REPO / "tools" / "business_autopilot.py"
INTERVAL = 30 * 60


def run(script: Path, timeout: int) -> None:
    if not script.exists():
        return
    try:
        subprocess.run([sys.executable, str(script)], cwd=str(REPO), check=False, timeout=timeout)
    except Exception:
        pass


def main() -> None:
    while True:
        run(SOCIAL, 5 * 60)
        run(BUSINESS, 5 * 60)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()

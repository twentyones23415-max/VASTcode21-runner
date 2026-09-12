from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "tools" / "social_autopilot.py"
INTERVAL = 30 * 60


def main() -> None:
    while True:
        try:
            subprocess.run([sys.executable, str(SCRIPT)], cwd=str(REPO), check=False, timeout=5 * 60)
        except Exception:
            pass
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()

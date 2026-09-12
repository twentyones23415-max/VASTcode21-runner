from __future__ import annotations

import os
from pathlib import Path

startup = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
cmd = startup / "VASTcode21_MT5_Bridge.cmd"
if cmd.exists():
    cmd.unlink()
    print(f"Removed startup entry: {cmd}")
else:
    print("Startup entry was not installed.")
print("Any currently running bridge process will stop at Windows sign-out/restart.")

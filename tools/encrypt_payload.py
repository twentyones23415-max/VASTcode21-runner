from __future__ import annotations
import argparse, os
from pathlib import Path
from crypto_utils import encrypt_file

p = argparse.ArgumentParser()
p.add_argument("src")
p.add_argument("dst")
p.add_argument("--key-env", default="VC21_CORE_KEY")
a = p.parse_args()
key = os.environ.get(a.key_env)
if not key:
    raise SystemExit(f"Missing environment variable {a.key_env}")
encrypt_file(Path(a.src), Path(a.dst), key)
print(f"encrypted {a.src} -> {a.dst}")

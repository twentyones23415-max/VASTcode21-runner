from __future__ import annotations
import argparse, tarfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('tar');p.add_argument('dst');a=p.parse_args()
d=Path(a.dst);d.mkdir(parents=True,exist_ok=True)
with tarfile.open(a.tar,'r:gz') as tf:
    tf.extractall(d)
print(d)

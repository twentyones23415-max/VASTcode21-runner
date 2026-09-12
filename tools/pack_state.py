from __future__ import annotations
import argparse, tarfile
from pathlib import Path

p=argparse.ArgumentParser(); p.add_argument('core_dir'); p.add_argument('out_tar')
a=p.parse_args(); core=Path(a.core_dir); out=Path(a.out_tar); out.parent.mkdir(parents=True,exist_ok=True)
items=[
    Path('data/cloud/vastcode21_cloud.db'),
    Path('data/context'),
    Path('cloud_out/mt5_validation_queue.json'),
    Path('cloud_out/leaderboard.json'),
    Path('cloud_out/generated'),
]
with tarfile.open(out,'w:gz') as tf:
    for rel in items:
        path=core/rel
        if path.exists(): tf.add(path,arcname=str(rel).replace('\\','/'))
print(out)

from __future__ import annotations
import argparse,json,sqlite3
from datetime import datetime,timezone
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('db');p.add_argument('out');a=p.parse_args()
db=Path(a.db); out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True)
summary={'updated_at':datetime.now(timezone.utc).isoformat(),'scope':['GOLD','BITCOIN'],'live_trading':False,'paid_services':False,'mode':'persistent_evolution'}
if db.exists():
    con=sqlite3.connect(db); con.row_factory=sqlite3.Row
    def q(sql):
        r=con.execute(sql).fetchone(); return int(r[0] if r else 0)
    summary['experiments']=q('select count(*) from experiments')
    summary['cloud_pass']=q("select count(*) from experiments where status='cloud_pass'")
    summary['rejected']=q("select count(*) from experiments where status='reject'")
    # v0.9 fields are backward-compatible with old DB state.
    try: summary['pending_mt5_validation']=q("select count(*) from validation_queue where status='pending'")
    except sqlite3.OperationalError: summary['pending_mt5_validation']=0
    try: summary['max_generation']=q('select coalesce(max(generation),0) from experiments')
    except sqlite3.OperationalError: summary['max_generation']=0
    try:
        rows=con.execute("select origin,count(*) n from experiments group by origin order by n desc").fetchall()
        summary['origins']={str(r['origin'] or 'legacy'):int(r['n']) for r in rows}
    except sqlite3.OperationalError:
        summary['origins']={'legacy':summary['experiments']}
    con.close()
out.write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary))

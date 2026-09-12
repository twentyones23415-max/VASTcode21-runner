from __future__ import annotations
import argparse,json,sqlite3
from datetime import datetime,timezone
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('db');p.add_argument('out');a=p.parse_args()
db=Path(a.db); out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True)
summary={'updated_at':datetime.now(timezone.utc).isoformat(),'scope':['GOLD','BITCOIN'],'live_trading':False,'paid_services':False}
if db.exists():
    con=sqlite3.connect(db); con.row_factory=sqlite3.Row
    def q(sql):
        r=con.execute(sql).fetchone(); return int(r[0] if r else 0)
    summary['experiments']=q('select count(*) from experiments')
    summary['cloud_pass']=q("select count(*) from experiments where status='cloud_pass'")
    summary['rejected']=q("select count(*) from experiments where status='reject'")
    con.close()
out.write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary))

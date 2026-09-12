from __future__ import annotations
import argparse,json,sqlite3
from datetime import datetime,timezone
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('db');p.add_argument('out');a=p.parse_args()
db=Path(a.db); out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True)
summary={'updated_at':datetime.now(timezone.utc).isoformat(),'scope':['GOLD','BITCOIN'],'live_trading':False,'paid_services':False,'mode':'persistent_evolution_mt5_handoff'}
if db.exists():
    con=sqlite3.connect(db); con.row_factory=sqlite3.Row
    def q(sql):
        r=con.execute(sql).fetchone(); return int(r[0] if r else 0)
    def scalar(sql, default=0.0):
        r=con.execute(sql).fetchone(); return float(r[0]) if r and r[0] is not None else default
    summary['experiments']=q('select count(*) from experiments')
    summary['cloud_pass']=q("select count(*) from experiments where status='cloud_pass'")
    summary['rejected']=q("select count(*) from experiments where status='reject'")
    try:
        summary['pending_mt5_validation']=q("select count(*) from validation_queue where status='pending'")
        summary['mt5_validation_passed']=q("select count(*) from validation_queue where status='passed'")
        summary['mt5_validation_rejected']=q("select count(*) from validation_queue where status='rejected'")
    except sqlite3.OperationalError:
        summary['pending_mt5_validation']=0; summary['mt5_validation_passed']=0; summary['mt5_validation_rejected']=0
    try: summary['max_generation']=q('select coalesce(max(generation),0) from experiments')
    except sqlite3.OperationalError: summary['max_generation']=0
    try:
        rows=con.execute("select origin,count(*) n from experiments group by origin order by n desc").fetchall()
        summary['origins']={str(r['origin'] or 'legacy'):int(r['n']) for r in rows}
    except sqlite3.OperationalError:
        summary['origins']={'legacy':summary['experiments']}
    try:
        summary['best_score']=round(scalar('select max(score) from experiments where score is not null'),4)
        summary['best_cloud_pass_score']=round(scalar("select max(score) from experiments where status='cloud_pass'"),4)
        rows=con.execute("""select e.symbol,count(*) n from validation_queue q join experiments e on e.id=q.experiment_id
                            where q.status='pending' group by e.symbol order by e.symbol""").fetchall()
        summary['pending_mt5_by_asset']={str(r['symbol']):int(r['n']) for r in rows}
    except sqlite3.OperationalError:
        pass
    con.close()
out.write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary))

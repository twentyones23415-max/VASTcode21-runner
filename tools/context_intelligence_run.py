from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import context_intelligence_ingest as ci

VERSION = "1.2.1"
_ORIGINAL_RELATIONSHIP_SCAN = ci.relationship_scan


def robust_fetch_bytes(url: str, timeout: int = 8, attempts: int = 1) -> bytes:
    """One bounded attempt per public endpoint.

    Context sources are informative, never critical. A slow or unavailable source
    is marked degraded for the current cycle instead of holding autonomous research.
    """
    last: Exception | None = None
    for _ in range(max(1, attempts)):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": ci.UA, "Accept": "*/*"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read()
        except Exception as exc:
            last = exc
            break
    raise RuntimeError(f"fetch failed: {last}")


def generic_ingest_rss(db, item):
    root = ci.ET.fromstring(robust_fetch_bytes(str(item["url"]), timeout=8, attempts=1))
    entries = list(root.findall(".//item"))
    if not entries:
        entries = [x for x in root.iter() if x.tag.split("}")[-1].lower() == "entry"]
    count = 0
    for entry in entries:
        title = ci.text_of(entry, ("title",))
        date_text = ci.text_of(entry, ("pubdate", "published", "updated"))
        dt = ci.parse_dt(date_text) or ci.utcnow()
        link = ci.text_of(entry, ("link",))
        if not link:
            for child in entry.iter():
                if child.tag.split("}")[-1].lower() == "link" and child.attrib.get("href"):
                    link = child.attrib["href"]
                    break
        count += ci.add_news(
            db,
            str(item["name"]),
            str(item.get("category", "official_news")),
            dt,
            title,
            link,
            str(item.get("domain", "")),
            str(item.get("language", "en")),
            {"feed": "rss"},
        )
    return count, {"records_seen": len(entries), "feed": "rss"}


def relationship_scan_with_gold_alias(db, target: str):
    if target == "FRED:GOLDAMGBD228NLBM":
        target = "FRED:NASDAQQGLDI"
    return _ORIGINAL_RELATIONSHIP_SCAN(db, target)


ci.fetch_bytes = robust_fetch_bytes
ci.ingest_rss = generic_ingest_rss
ci.relationship_scan = relationship_scan_with_gold_alias


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("core_dir")
    parser.add_argument("sources_json")
    parser.add_argument("status_json")
    args = parser.parse_args()

    core = Path(args.core_dir)
    cfg = json.loads(Path(args.sources_json).read_text(encoding="utf-8"))
    out_dir = core / "data" / "context"
    db = ci.init_db(out_dir / "context.db")
    health: dict[str, dict] = {}
    inserted = 0

    rss_items = list(cfg.get("news", {}).get("rss", []))
    gdelt_items = list(cfg.get("news", {}).get("gdelt", []))
    fred_items = list(cfg.get("fred_graph_series", []))
    total = len(gdelt_items) + len(rss_items) + len(fred_items) + 1
    ordinal = 0

    def run_source(name: str, fn) -> None:
        nonlocal inserted, ordinal
        ordinal += 1
        started = time.time()
        print(f"[{ordinal:02d}/{total:02d}] START {name}", flush=True)
        try:
            n, meta = fn()
            elapsed_ms = int((time.time() - started) * 1000)
            inserted += int(n)
            health[name] = {
                "ok": True,
                "records_written": int(n),
                "elapsed_ms": elapsed_ms,
                **meta,
            }
            print(f"[{ordinal:02d}/{total:02d}] PASS  {name} records={int(n)} elapsed={elapsed_ms}ms", flush=True)
        except Exception as exc:
            elapsed_ms = int((time.time() - started) * 1000)
            error = f"{type(exc).__name__}: {str(exc)[:240]}"
            health[name] = {
                "ok": False,
                "error": error,
                "elapsed_ms": elapsed_ms,
            }
            print(f"[{ordinal:02d}/{total:02d}] FAIL  {name} elapsed={elapsed_ms}ms -> {error}", flush=True)

    for item in gdelt_items:
        run_source(f"gdelt:{item['name']}", lambda item=item: ci.ingest_gdelt(db, item))
    for item in rss_items:
        run_source(f"rss:{item['name']}", lambda item=item: ci.ingest_rss(db, item))
    for item in fred_items:
        run_source(f"fred:{item['id']}", lambda item=item: ci.ingest_fred_graph(db, item))
    run_source("binance", lambda: ci.ingest_binance(db, cfg.get("binance", {})))

    print("[FINAL] Building context features and lag relationships...", flush=True)
    ci.cleanup(db, cfg.get("retention", {}))
    db.commit()
    manifest = ci.build_outputs(db, out_dir, health)
    db.commit()
    db.close()

    attempted = len(health)
    succeeded = sum(1 for value in health.values() if value.get("ok"))
    failed = attempted - succeeded
    status = {
        "updated_at": ci.iso(),
        "version": VERSION,
        "execution_scope": ["XAUUSD", "BTCUSD"],
        "information_scope": "unbounded_relevant",
        "mode": "persistent_zero_cost_context_intelligence",
        "sources_attempted": attempted,
        "sources_succeeded": succeeded,
        "sources_failed": failed,
        "rows_written_this_cycle": inserted,
        "observation_rows_persistent": manifest["observation_rows"],
        "news_rows_persistent": manifest["news_rows"],
        "series_count": manifest["series_count"],
        "private_context_history": True,
        "live_trading": False,
        "paid_data": False,
        "paid_services": False,
        "source_health": {key: {"ok": bool(value.get("ok"))} for key, value in health.items()},
    }
    status_path = Path(args.status_json)
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps(status, indent=2, sort_keys=True), encoding="utf-8")

    print(
        f"VASTcode21 context intelligence: {succeeded}/{attempted} sources healthy; "
        f"observations={manifest['observation_rows']} news={manifest['news_rows']}",
        flush=True,
    )
    return 0 if succeeded > 0 else 2


if __name__ == "__main__":
    print(f"VASTcode21 CONTEXT INTELLIGENCE RUNNER v{VERSION}", flush=True)
    raise SystemExit(main())

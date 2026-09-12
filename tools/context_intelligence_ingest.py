from __future__ import annotations

import argparse
import csv
import email.utils
import hashlib
import io
import json
import math
import sqlite3
import statistics
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

UA = "VASTcode21-ContextIntelligence/1.0 (+research; zero-cost public data)"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None = None) -> str:
    return (dt or utcnow()).astimezone(timezone.utc).isoformat()


def parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            scale = 1000.0 if float(value) > 10_000_000_000 else 1.0
            return datetime.fromtimestamp(float(value) / scale, tz=timezone.utc)
        except Exception:
            return None
    s = str(value).strip()
    if not s:
        return None
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    try:
        dt = email.utils.parsedate_to_datetime(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def fetch_bytes(url: str, timeout: int = 25, attempts: int = 3) -> bytes:
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as exc:
            last = exc
            if attempt + 1 < attempts:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"fetch failed: {last}")


def fetch_json(url: str) -> Any:
    return json.loads(fetch_bytes(url).decode("utf-8", errors="replace"))


def init_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute(
        """CREATE TABLE IF NOT EXISTS observations (
        source TEXT NOT NULL,
        category TEXT NOT NULL,
        series TEXT NOT NULL,
        event_time TEXT NOT NULL,
        value REAL,
        collected_at TEXT NOT NULL,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        PRIMARY KEY(source, series, event_time)
        )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS news (
        item_id TEXT PRIMARY KEY,
        source TEXT NOT NULL,
        category TEXT NOT NULL,
        event_time TEXT NOT NULL,
        title TEXT NOT NULL,
        url TEXT,
        domain TEXT,
        language TEXT,
        collected_at TEXT NOT NULL,
        metadata_json TEXT NOT NULL DEFAULT '{}'
        )"""
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_obs_series_time ON observations(series,event_time)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_news_time ON news(event_time)")
    return db


def add_obs(db: sqlite3.Connection, source: str, category: str, series: str, event_time: datetime, value: Any, metadata: dict[str, Any] | None = None) -> int:
    try:
        num = float(value)
        if not math.isfinite(num):
            return 0
    except Exception:
        return 0
    db.execute(
        "INSERT OR REPLACE INTO observations(source,category,series,event_time,value,collected_at,metadata_json) VALUES(?,?,?,?,?,?,?)",
        (source, category, series, iso(event_time), num, iso(), json.dumps(metadata or {}, sort_keys=True)),
    )
    return 1


def add_news(db: sqlite3.Connection, source: str, category: str, event_time: datetime, title: str, url: str = "", domain: str = "", language: str = "", metadata: dict[str, Any] | None = None) -> int:
    title = " ".join(str(title).split()).strip()
    if not title:
        return 0
    raw = f"{source}|{url}|{title}|{iso(event_time)}".encode("utf-8", errors="replace")
    item_id = hashlib.sha256(raw).hexdigest()
    before = db.total_changes
    db.execute(
        "INSERT OR IGNORE INTO news(item_id,source,category,event_time,title,url,domain,language,collected_at,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (item_id, source, category, iso(event_time), title[:1000], url[:2000], domain[:255], language[:64], iso(), json.dumps(metadata or {}, sort_keys=True)),
    )
    return 1 if db.total_changes > before else 0


def ingest_gdelt(db: sqlite3.Connection, item: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    params = {
        "query": str(item["query"]),
        "mode": "ArtList",
        "maxrecords": str(int(item.get("maxrecords", 100))),
        "format": "json",
        "timespan": str(item.get("timespan", "6h")),
        "sort": "HybridRel",
    }
    url = "https://api.gdeltproject.org/api/v2/doc/doc?" + urllib.parse.urlencode(params)
    data = fetch_json(url)
    count = 0
    for art in (data.get("articles") or []):
        dt = parse_dt(art.get("seendate")) or utcnow()
        count += add_news(
            db,
            f"gdelt:{item['name']}",
            "global_news",
            dt,
            art.get("title") or "",
            art.get("url") or "",
            art.get("domain") or "",
            art.get("language") or "",
            {"sourcecountry": art.get("sourcecountry")},
        )
    return count, {"records_seen": len(data.get("articles") or [])}


def text_of(node: ET.Element, names: tuple[str, ...]) -> str:
    for child in node.iter():
        tag = child.tag.split("}")[-1].lower()
        if tag in names and child.text:
            return child.text.strip()
    return ""


def ingest_rss(db: sqlite3.Connection, item: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    root = ET.fromstring(fetch_bytes(str(item["url"])))
    entries = list(root.findall(".//item"))
    if not entries:
        entries = [x for x in root.iter() if x.tag.split("}")[-1].lower() == "entry"]
    count = 0
    for entry in entries:
        title = text_of(entry, ("title",))
        date_text = text_of(entry, ("pubdate", "published", "updated"))
        dt = parse_dt(date_text) or utcnow()
        link = text_of(entry, ("link",))
        if not link:
            for child in entry.iter():
                if child.tag.split("}")[-1].lower() == "link" and child.attrib.get("href"):
                    link = child.attrib["href"]
                    break
        count += add_news(db, str(item["name"]), str(item.get("category", "official_news")), dt, title, link, "federalreserve.gov", "en")
    return count, {"records_seen": len(entries)}


def ingest_fred_graph(db: sqlite3.Connection, item: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    sid = str(item["id"])
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?" + urllib.parse.urlencode({"id": sid})
    text = fetch_bytes(url).decode("utf-8", errors="replace")
    rows = list(csv.DictReader(io.StringIO(text)))
    count = 0
    for row in rows:
        dt = parse_dt(row.get("DATE") or row.get("observation_date"))
        raw = row.get(sid)
        if dt is None or raw in (None, "", "."):
            continue
        count += add_obs(db, "fred_graph", str(item.get("category", "macro")), f"FRED:{sid}", dt, raw, {"description": item.get("description")})
    return count, {"records_seen": len(rows)}


def ingest_binance(db: sqlite3.Connection, cfg: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    spot = str(cfg.get("spot_symbol", "BTCUSDT"))
    fut = str(cfg.get("futures_symbol", "BTCUSDT"))
    count = 0
    meta: dict[str, Any] = {}

    q = urllib.parse.urlencode({"symbol": spot, "interval": cfg.get("spot_kline_interval", "1h"), "limit": int(cfg.get("spot_kline_limit", 1000))})
    klines = fetch_json("https://api.binance.com/api/v3/klines?" + q)
    for row in klines:
        dt = parse_dt(row[0])
        if dt:
            count += add_obs(db, "binance_spot", "crypto_spot", f"BINANCE:{spot}:spot_close", dt, row[4], {"volume": row[5], "trades": row[8]})
            count += add_obs(db, "binance_spot", "crypto_spot", f"BINANCE:{spot}:spot_volume", dt, row[5], {})
    meta["spot_klines"] = len(klines)

    fq = urllib.parse.urlencode({"symbol": fut, "interval": cfg.get("futures_kline_interval", "1h"), "limit": int(cfg.get("futures_kline_limit", 1000))})
    fklines = fetch_json("https://fapi.binance.com/fapi/v1/klines?" + fq)
    for row in fklines:
        dt = parse_dt(row[0])
        if dt:
            count += add_obs(db, "binance_futures", "crypto_derivatives", f"BINANCE:{fut}:futures_close", dt, row[4], {"volume": row[5], "trades": row[8]})
    meta["futures_klines"] = len(fklines)

    funding_q = urllib.parse.urlencode({"symbol": fut, "limit": int(cfg.get("funding_limit", 100))})
    funding = fetch_json("https://fapi.binance.com/fapi/v1/fundingRate?" + funding_q)
    for row in funding:
        dt = parse_dt(row.get("fundingTime"))
        if dt:
            count += add_obs(db, "binance_futures", "crypto_derivatives", f"BINANCE:{fut}:funding_rate", dt, row.get("fundingRate"), {"markPrice": row.get("markPrice")})
    meta["funding_rows"] = len(funding)

    oi = fetch_json("https://fapi.binance.com/fapi/v1/openInterest?" + urllib.parse.urlencode({"symbol": fut}))
    count += add_obs(db, "binance_futures", "crypto_derivatives", f"BINANCE:{fut}:open_interest", utcnow(), oi.get("openInterest"), {})

    premium = fetch_json("https://fapi.binance.com/fapi/v1/premiumIndex?" + urllib.parse.urlencode({"symbol": fut}))
    pdt = parse_dt(premium.get("time")) or utcnow()
    count += add_obs(db, "binance_futures", "crypto_derivatives", f"BINANCE:{fut}:mark_price", pdt, premium.get("markPrice"), {})
    count += add_obs(db, "binance_futures", "crypto_derivatives", f"BINANCE:{fut}:index_price", pdt, premium.get("indexPrice"), {})
    count += add_obs(db, "binance_futures", "crypto_derivatives", f"BINANCE:{fut}:last_funding_rate", pdt, premium.get("lastFundingRate"), {})
    return count, meta


def cleanup(db: sqlite3.Connection, retention: dict[str, Any]) -> None:
    news_cut = iso(utcnow() - timedelta(days=int(retention.get("news_days", 365))))
    market_cut = iso(utcnow() - timedelta(days=int(retention.get("market_days", 3650))))
    db.execute("DELETE FROM news WHERE event_time < ?", (news_cut,))
    db.execute("DELETE FROM observations WHERE event_time < ?", (market_cut,))


def series_feature(rows: list[tuple[str, float]]) -> dict[str, Any]:
    vals = [float(v) for _, v in rows if v is not None and math.isfinite(float(v))]
    if not vals:
        return {}
    out: dict[str, Any] = {"latest": vals[-1], "points": len(vals), "latest_time": rows[-1][0]}
    if len(vals) >= 2:
        out["delta_1"] = vals[-1] - vals[-2]
        if vals[-2] != 0:
            out["pct_1"] = (vals[-1] / vals[-2] - 1.0) * 100.0
    if len(vals) >= 6:
        out["delta_5"] = vals[-1] - vals[-6]
        if vals[-6] != 0:
            out["pct_5"] = (vals[-1] / vals[-6] - 1.0) * 100.0
    window = vals[-20:]
    if len(window) >= 5:
        sd = statistics.pstdev(window)
        if sd > 0:
            out["zscore_20"] = (vals[-1] - statistics.mean(window)) / sd
    return out


def pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 20:
        return None
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def daily_changes(db: sqlite3.Connection, series: str) -> dict[str, float]:
    rows = db.execute("SELECT event_time,value FROM observations WHERE series=? ORDER BY event_time", (series,)).fetchall()
    day_last: dict[str, float] = {}
    for ts, val in rows:
        day_last[str(ts)[:10]] = float(val)
    days = sorted(day_last)
    out: dict[str, float] = {}
    for i in range(1, len(days)):
        prev, cur = day_last[days[i - 1]], day_last[days[i]]
        if prev == 0:
            out[days[i]] = cur - prev
        else:
            out[days[i]] = cur / prev - 1.0
    return out


def relationship_scan(db: sqlite3.Connection, target: str) -> list[dict[str, Any]]:
    target_changes = daily_changes(db, target)
    if len(target_changes) < 20:
        return []
    series = [r[0] for r in db.execute("SELECT DISTINCT series FROM observations WHERE series<>?", (target,)).fetchall()]
    findings: list[dict[str, Any]] = []
    for predictor in series:
        p = daily_changes(db, predictor)
        if len(p) < 20:
            continue
        p_days = sorted(p)
        p_index = {d: i for i, d in enumerate(p_days)}
        for lag in (0, 1, 2, 3):
            xs: list[float] = []
            ys: list[float] = []
            for day, y in target_changes.items():
                idx = p_index.get(day)
                if idx is None or idx - lag < 0:
                    continue
                xday = p_days[idx - lag]
                xs.append(p[xday])
                ys.append(y)
            corr = pearson(xs, ys)
            if corr is not None:
                findings.append({"predictor": predictor, "target": target, "lag_days": lag, "correlation": round(corr, 5), "samples": len(xs)})
    findings.sort(key=lambda x: abs(float(x["correlation"])), reverse=True)
    return findings[:30]


def build_outputs(db: sqlite3.Connection, out_dir: Path, source_health: dict[str, Any]) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    features: dict[str, Any] = {}
    series = [r[0] for r in db.execute("SELECT DISTINCT series FROM observations ORDER BY series").fetchall()]
    for s in series:
        rows = db.execute("SELECT event_time,value FROM observations WHERE series=? ORDER BY event_time DESC LIMIT 40", (s,)).fetchall()
        rows.reverse()
        features[s] = series_feature(rows)

    now = utcnow()
    news_counts = {}
    for hours in (1, 6, 24, 72):
        cutoff = iso(now - timedelta(hours=hours))
        news_counts[f"last_{hours}h"] = int(db.execute("SELECT COUNT(*) FROM news WHERE event_time>=?", (cutoff,)).fetchone()[0])

    recent_news = [
        {"event_time": r[0], "source": r[1], "category": r[2], "title": r[3], "url": r[4], "domain": r[5]}
        for r in db.execute("SELECT event_time,source,category,title,url,domain FROM news ORDER BY event_time DESC LIMIT 250").fetchall()
    ]
    relationships = {
        "XAUUSD_proxy": relationship_scan(db, "FRED:GOLDAMGBD228NLBM"),
        "BTCUSD_proxy": relationship_scan(db, "BINANCE:BTCUSDT:spot_close"),
        "note": "Exploratory lag correlations only; not trading signals and not evidence of causality.",
    }
    snapshot = {
        "schema_version": 1,
        "generated_at": iso(now),
        "trade_scope": ["XAUUSD", "BTCUSD"],
        "information_scope": "unbounded_relevant",
        "features": features,
        "news_intensity": news_counts,
        "recent_news": recent_news,
        "relationships": relationships,
    }
    (out_dir / "latest.json").write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
    (out_dir / "features.json").write_text(json.dumps({"generated_at": iso(now), "features": features, "relationships": relationships}, indent=2, sort_keys=True), encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "generated_at": iso(now),
        "source_health": source_health,
        "observation_rows": int(db.execute("SELECT COUNT(*) FROM observations").fetchone()[0]),
        "news_rows": int(db.execute("SELECT COUNT(*) FROM news").fetchone()[0]),
        "series_count": len(series),
        "paths": {"database": "data/context/context.db", "latest": "data/context/latest.json", "features": "data/context/features.json"},
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("core_dir")
    p.add_argument("sources_json")
    p.add_argument("status_json")
    args = p.parse_args()
    core = Path(args.core_dir)
    cfg = json.loads(Path(args.sources_json).read_text(encoding="utf-8"))
    out_dir = core / "data" / "context"
    db = init_db(out_dir / "context.db")
    health: dict[str, Any] = {}
    inserted = 0

    def run_source(name: str, fn) -> None:
        nonlocal inserted
        started = time.time()
        try:
            n, meta = fn()
            inserted += int(n)
            health[name] = {"ok": True, "records_written": int(n), "elapsed_ms": int((time.time() - started) * 1000), **meta}
        except Exception as exc:
            health[name] = {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:240]}", "elapsed_ms": int((time.time() - started) * 1000)}

    for item in cfg.get("news", {}).get("gdelt", []):
        run_source(f"gdelt:{item['name']}", lambda item=item: ingest_gdelt(db, item))
    for item in cfg.get("news", {}).get("rss", []):
        run_source(f"rss:{item['name']}", lambda item=item: ingest_rss(db, item))
    for item in cfg.get("fred_graph_series", []):
        run_source(f"fred:{item['id']}", lambda item=item: ingest_fred_graph(db, item))
    run_source("binance", lambda: ingest_binance(db, cfg.get("binance", {})))

    cleanup(db, cfg.get("retention", {}))
    db.commit()
    manifest = build_outputs(db, out_dir, health)
    db.commit()
    db.close()

    attempted = len(health)
    succeeded = sum(1 for v in health.values() if v.get("ok"))
    failed = attempted - succeeded
    status = {
        "updated_at": iso(),
        "version": "1.0.0",
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
        "source_health": {k: {"ok": bool(v.get("ok"))} for k, v in health.items()},
    }
    status_path = Path(args.status_json)
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps(status, indent=2, sort_keys=True), encoding="utf-8")
    print(f"VASTcode21 context intelligence: {succeeded}/{attempted} sources healthy; observations={manifest['observation_rows']} news={manifest['news_rows']}")
    return 0 if succeeded > 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

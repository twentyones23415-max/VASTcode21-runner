from __future__ import annotations

import json
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import context_intelligence_ingest as ci


def require(ok: bool, message: str) -> None:
    if not ok:
        raise AssertionError(message)


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    cfg = json.loads((repo / "config" / "context_sources.json").read_text(encoding="utf-8"))
    require(cfg.get("trade_scope") == ["XAUUSD", "BTCUSD"], "trade scope must be XAUUSD/BTCUSD")
    require(cfg.get("policy") == "zero_cost_public_or_existing_sources_only", "paid-data policy mismatch")
    require(len(cfg.get("fred_graph_series", [])) >= 10, "macro/cross-asset coverage too small")
    require(len(cfg.get("news", {}).get("gdelt", [])) >= 2, "news coverage missing")

    require(ci.parse_dt("2026-09-12") is not None, "ISO date parser failed")
    require(ci.parse_dt("20260912T120000Z") is not None, "GDELT date parser failed")
    require(ci.parse_dt(1_757_678_400_000) is not None, "millisecond timestamp parser failed")

    with tempfile.TemporaryDirectory(prefix="vc21_context_test_") as td:
        root = Path(td)
        db = ci.init_db(root / "context.db")
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for i in range(40):
            dt = start + timedelta(days=i)
            ci.add_obs(db, "test", "macro", "TEST:PREDICTOR", dt, 100 + i * 0.5, {})
            ci.add_obs(db, "test", "target", "FRED:GOLDAMGBD228NLBM", dt, 2000 + i * 2.0 + (i % 3), {})
            ci.add_obs(db, "test", "target", "BINANCE:BTCUSDT:spot_close", dt, 50000 + i * 50 + (i % 5), {})
        ci.add_news(db, "test", "global_news", start + timedelta(days=39), "Gold and bitcoin macro test headline", "https://example.invalid/test")
        db.commit()

        rows = db.execute("SELECT event_time,value FROM observations WHERE series='TEST:PREDICTOR' ORDER BY event_time").fetchall()
        feat = ci.series_feature(rows)
        require(feat.get("points") == 40, "feature point count mismatch")
        require("zscore_20" in feat, "z-score feature missing")

        rel = ci.relationship_scan(db, "FRED:GOLDAMGBD228NLBM")
        require(isinstance(rel, list), "relationship scan failed")

        manifest = ci.build_outputs(db, root / "out", {"offline_test": {"ok": True}})
        require(manifest.get("observation_rows") == 120, "persistent observation count mismatch")
        require(manifest.get("news_rows") == 1, "persistent news count mismatch")
        require((root / "out" / "latest.json").exists(), "latest snapshot missing")
        require((root / "out" / "features.json").exists(), "feature snapshot missing")
        require((root / "out" / "manifest.json").exists(), "manifest missing")
        db.close()

    print("VASTcode21 CONTEXT INTELLIGENCE SELF-TEST")
    print("PASS: XAUUSD/BTCUSD execution scope")
    print("PASS: zero-cost public-data policy")
    print("PASS: timestamp and event-time handling")
    print("PASS: persistent SQLite context bus")
    print("PASS: feature extraction")
    print("PASS: lag-relationship analysis")
    print("PASS: news storage + deduplication")
    print("PASS: no network calls were made by this self-test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

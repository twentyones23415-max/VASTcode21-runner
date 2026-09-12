from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import context_intelligence_ingest as ci

VERSION = "1.1.2"
_LAST_GDELT_CALL = 0.0
_ORIGINAL_RELATIONSHIP_SCAN = ci.relationship_scan


def robust_fetch_bytes(url: str, timeout: int = 20, attempts: int = 3) -> bytes:
    """Bounded retry policy for ordinary public sources.

    GDELT is handled by its own fast-fail wrapper below so it can never hold the
    whole research cycle during rate limits, TLS stalls, or endpoint outages.
    """
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": ci.UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code == 429:
                break
            if attempt + 1 < attempts and exc.code >= 500:
                time.sleep(min(6.0, 2.0 * (attempt + 1)))
                continue
            break
        except Exception as exc:
            last = exc
            if attempt + 1 < attempts:
                time.sleep(min(4.0, 1.5 * (attempt + 1)))
    raise RuntimeError(f"fetch failed: {last}")


def fast_fetch_bytes(url: str, timeout: int = 7) -> bytes:
    """Single-attempt fetch for optional sources that have a fallback."""
    req = urllib.request.Request(url, headers={"User-Agent": ci.UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def google_news_fallback(db, item, reason: str):
    params = {
        "q": str(item.get("query", "gold bitcoin")),
        "hl": "en-US",
        "gl": "US",
        "ceid": "US:en",
    }
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(params)
    root = ci.ET.fromstring(robust_fetch_bytes(url, timeout=12, attempts=2))
    entries = list(root.findall(".//item"))
    count = 0
    for entry in entries[: int(item.get("maxrecords", 100))]:
        title = ci.text_of(entry, ("title",))
        date_text = ci.text_of(entry, ("pubdate", "published", "updated"))
        dt = ci.parse_dt(date_text) or ci.utcnow()
        link = ci.text_of(entry, ("link",))
        count += ci.add_news(
            db,
            f"google_news_fallback:{item.get('name','news')}",
            "global_news",
            dt,
            title,
            link,
            "news.google.com",
            "en",
            {"fallback_for": "gdelt", "fallback_reason": reason[:120]},
        )
    return count, {"records_seen": len(entries), "fallback": "google_news_rss", "gdelt_degraded": True}


def resilient_ingest_gdelt(db, item):
    """Fast-fail GDELT and immediately fall back on any transport/API failure."""
    global _LAST_GDELT_CALL
    elapsed = time.monotonic() - _LAST_GDELT_CALL
    if elapsed < 2.0:
        time.sleep(2.0 - elapsed)

    params = {
        "query": str(item["query"]),
        "mode": "ArtList",
        "maxrecords": str(int(item.get("maxrecords", 100))),
        "format": "json",
        "timespan": str(item.get("timespan", "6h")),
        "sort": "HybridRel",
    }
    url = "https://api.gdeltproject.org/api/v2/doc/doc?" + urllib.parse.urlencode(params)

    try:
        data = json.loads(fast_fetch_bytes(url, timeout=7).decode("utf-8", errors="replace"))
        count = 0
        articles = data.get("articles") or []
        for art in articles:
            dt = ci.parse_dt(art.get("seendate")) or ci.utcnow()
            count += ci.add_news(
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
        _LAST_GDELT_CALL = time.monotonic()
        return count, {"records_seen": len(articles), "fallback": None, "gdelt_degraded": False}
    except Exception as exc:
        _LAST_GDELT_CALL = time.monotonic()
        return google_news_fallback(db, item, f"{type(exc).__name__}: {exc}")


def relationship_scan_with_gold_alias(db, target: str):
    if target == "FRED:GOLDAMGBD228NLBM":
        target = "FRED:NASDAQQGLDI"
    return _ORIGINAL_RELATIONSHIP_SCAN(db, target)


ci.fetch_bytes = robust_fetch_bytes
ci.ingest_gdelt = resilient_ingest_gdelt
ci.relationship_scan = relationship_scan_with_gold_alias


if __name__ == "__main__":
    print(f"VASTcode21 CONTEXT INTELLIGENCE RUNNER v{VERSION}", flush=True)
    raise SystemExit(ci.main())

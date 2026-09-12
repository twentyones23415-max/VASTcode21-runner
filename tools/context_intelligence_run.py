from __future__ import annotations

import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import context_intelligence_ingest as ci

VERSION = "1.1.1"
_LAST_GDELT_CALL = 0.0
_ORIGINAL_RELATIONSHIP_SCAN = ci.relationship_scan
_ORIGINAL_INGEST_GDELT = ci.ingest_gdelt


def robust_fetch_bytes(url: str, timeout: int = 25, attempts: int = 5) -> bytes:
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": ci.UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as exc:
            last = exc
            # GDELT 429 means the public endpoint is rate-limiting us. Do not burn
            # the cycle on repeated calls: hand control back immediately so the
            # resilient GDELT wrapper can use the RSS fallback.
            if exc.code == 429 and "gdeltproject.org" in url.lower():
                break
            if exc.code == 429 and attempt + 1 < attempts:
                retry_after = (exc.headers or {}).get("Retry-After") if exc.headers else None
                try:
                    wait = float(retry_after) if retry_after else min(30.0, 4.0 * (2 ** attempt))
                except Exception:
                    wait = min(30.0, 4.0 * (2 ** attempt))
                time.sleep(max(4.0, wait))
                continue
            if attempt + 1 < attempts and exc.code >= 500:
                time.sleep(min(20.0, 2.0 * (attempt + 1)))
                continue
            break
        except Exception as exc:
            last = exc
            if attempt + 1 < attempts:
                time.sleep(min(15.0, 2.0 * (attempt + 1)))
    raise RuntimeError(f"fetch failed: {last}")


def google_news_fallback(db, item):
    params = {
        "q": str(item.get("query", "gold bitcoin")),
        "hl": "en-US",
        "gl": "US",
        "ceid": "US:en",
    }
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(params)
    root = ci.ET.fromstring(ci.fetch_bytes(url))
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
            {"fallback_for": "gdelt_rate_limit"},
        )
    return count, {"records_seen": len(entries), "fallback": "google_news_rss"}


def resilient_ingest_gdelt(db, item):
    global _LAST_GDELT_CALL
    elapsed = time.monotonic() - _LAST_GDELT_CALL
    if elapsed < 8.0:
        time.sleep(8.0 - elapsed)
    try:
        result = _ORIGINAL_INGEST_GDELT(db, item)
        _LAST_GDELT_CALL = time.monotonic()
        return result
    except Exception as exc:
        _LAST_GDELT_CALL = time.monotonic()
        if "429" not in str(exc):
            raise
        return google_news_fallback(db, item)


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

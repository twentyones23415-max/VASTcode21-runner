from __future__ import annotations

import time
import urllib.error
import urllib.request
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import context_intelligence_ingest as ci

VERSION = "1.2.0"
_ORIGINAL_RELATIONSHIP_SCAN = ci.relationship_scan


def robust_fetch_bytes(url: str, timeout: int = 15, attempts: int = 2) -> bytes:
    """Bounded public-source fetch. No single source may hold the research cycle."""
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
                time.sleep(2.0)
                continue
            break
        except Exception as exc:
            last = exc
            if attempt + 1 < attempts:
                time.sleep(1.5)
    raise RuntimeError(f"fetch failed: {last}")


def generic_ingest_rss(db, item):
    root = ci.ET.fromstring(robust_fetch_bytes(str(item["url"]), timeout=12, attempts=2))
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


if __name__ == "__main__":
    print(f"VASTcode21 CONTEXT INTELLIGENCE RUNNER v{VERSION}", flush=True)
    raise SystemExit(ci.main())

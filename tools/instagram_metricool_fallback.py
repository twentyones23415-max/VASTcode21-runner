#!/usr/bin/env python3
"""Automatic Instagram fallback via Metricool.

This path is intentionally separate from the direct Meta publisher. It is used
when a Metricool account is connected and the required server-side credentials
are configured as GitHub Actions secrets. No credential is ever exposed to the
site/browser.

The script enforces the same organic safety guards as the direct publisher:
max one post per local day, minimum 20-hour spacing, no service-pillar posts
while the account is below 10 followers, and local idempotency by queue id.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = ROOT / "marketing" / "queue.json"
CONFIG_PATH = ROOT / "marketing" / "social_config.json"
STATE_PATH = ROOT / "marketing" / "publish_state.json"
GROWTH_PATH = ROOT / "marketing" / "growth_metrics.json"
METRICOOL_SCHEDULER = "https://app.metricool.com/api/v2/scheduler/posts"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_dt(value: str | None):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def build_caption(item: dict, config: dict) -> str:
    hashtags = " ".join(str(x) for x in (item.get("hashtags") or config.get("hashtags", [])))
    parts = [
        str(item.get("hook") or "").strip(),
        str(item.get("caption") or "").strip(),
        str(item.get("cta") or "").strip(),
        str(item.get("disclaimer") or "").strip(),
        hashtags,
    ]
    return "\n\n".join(x for x in parts if x)


def schedule_metricool(*, token: str, user_id: str, blog_id: str, text: str,
                       media_url: str, publish_local: datetime, timezone_name: str):
    query = urllib.parse.urlencode({"blogId": blog_id, "userId": user_id})
    url = f"{METRICOOL_SCHEDULER}?{query}"
    payload = {
        "publicationDate": {
            "dateTime": publish_local.strftime("%Y-%m-%dT%H:%M:%S"),
            "timezone": timezone_name,
        },
        "text": text,
        "providers": [{"network": "instagram"}],
        "autoPublish": True,
        "draft": False,
        "shortener": False,
        "saveExternalMediaFiles": True,
        "media": [media_url],
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Mc-Auth": token,
            "User-Agent": "VASTcode21-MetricoolFallback/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Metricool API HTTP {exc.code}: {detail}") from exc


def main() -> int:
    token = os.environ.get("METRICOOL_USER_TOKEN", "").strip()
    user_id = os.environ.get("METRICOOL_USER_ID", "").strip()
    blog_id = os.environ.get("METRICOOL_BLOG_ID", "").strip()
    validate_only = os.environ.get("VALIDATE_ONLY", "false").lower() == "true"
    force_publish = os.environ.get("FORCE_PUBLISH", "false").lower() == "true"

    if not (token and user_id and blog_id):
        print("METRICOOL_FALLBACK_UNAVAILABLE: configure METRICOOL_USER_TOKEN, METRICOOL_USER_ID and METRICOOL_BLOG_ID as repository secrets.")
        return 3

    config = load_json(CONFIG_PATH)
    queue = load_json(QUEUE_PATH)
    state = load_json(STATE_PATH) if STATE_PATH.exists() else {"version": "2.0.0", "last_publish_at": None, "published": []}
    growth = load_json(GROWTH_PATH) if GROWTH_PATH.exists() else {}
    followers = int(growth.get("followers_count", 0) or 0)

    if not config.get("enabled", False):
        print("Instagram publishing disabled in social_config.json")
        return 0
    if config.get("paid_ads", True):
        raise RuntimeError("Safety stop: paid_ads must remain false.")
    if config.get("live_trading", True):
        raise RuntimeError("Safety stop: live_trading must remain false.")

    timezone_name = config.get("timezone", "Europe/Bucharest")
    local_tz = ZoneInfo(timezone_name)
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(local_tz)
    publish_hour = int(config.get("publish_hour_local", 19))

    if not force_publish and now_local.hour != publish_hour:
        print(f"Outside publish hour: now {now_local:%Y-%m-%d %H:%M} {timezone_name}, target hour {publish_hour}:00.")
        return 0

    published = state.get("published", [])
    published_ids = {entry.get("queue_id") for entry in published}

    today_count = 0
    for entry in published:
        dt = parse_dt(entry.get("published_at"))
        if dt and dt.astimezone(local_tz).date() == now_local.date():
            today_count += 1
    if today_count >= int(config.get("max_posts_per_day", 1)):
        print("Daily publish limit reached.")
        return 0

    last_publish = parse_dt(state.get("last_publish_at"))
    min_hours = int(config.get("min_hours_between_posts", 20))
    if last_publish and now_utc - last_publish.astimezone(timezone.utc) < timedelta(hours=min_hours):
        print("Minimum spacing between posts has not elapsed.")
        return 0

    candidates = [
        item for item in queue.get("items", [])
        if "Instagram" in item.get("platforms", [])
        and item.get("id") not in published_ids
        and not (followers < 10 and str(item.get("pillar") or "").lower() == "services")
    ]
    candidates.sort(key=lambda item: int(item.get("priority", 0)), reverse=True)
    if not candidates:
        print("No unpublished Instagram queue items available.")
        return 0

    item = candidates[0]
    queue_id = str(item["id"])
    fmt = str(item.get("format") or "image").lower()
    base = config["raw_asset_base"].rstrip("/")
    if fmt == "reel":
        media_url = f"{base}/{queue_id}.mp4"
    elif fmt == "carousel":
        # Conservative fallback: use the first prepared slide rather than risk
        # malformed carousel payloads when the direct Meta app is unavailable.
        media_url = f"{base}/{queue_id}-1.jpg"
        fmt = "image"
    else:
        media_url = f"{base}/{queue_id}.jpg"

    caption = build_caption(item, config)
    publish_local = now_local + timedelta(minutes=10)

    if validate_only:
        print(f"Metricool fallback ready for {queue_id} at {publish_local:%Y-%m-%d %H:%M} {timezone_name}; no scheduling performed.")
        return 0

    result = schedule_metricool(
        token=token,
        user_id=user_id,
        blog_id=blog_id,
        text=caption,
        media_url=media_url,
        publish_local=publish_local,
        timezone_name=timezone_name,
    )

    provider_id = str(result.get("id") or result.get("postId") or result.get("uuid") or "metricool-scheduled")
    published_at = publish_local.astimezone(timezone.utc).isoformat()
    state["version"] = "2.3.0"
    state["last_publish_at"] = published_at
    state.setdefault("published", []).append({
        "queue_id": queue_id,
        "media_id": provider_id,
        "published_at": published_at,
        "account": config.get("account_name"),
        "media_url": media_url,
        "format": fmt,
        "pillar": item.get("pillar"),
        "provider": "metricool",
        "publication_status": "scheduled_autopublish",
        "scheduled_at_local": publish_local.isoformat(),
    })
    save_json(STATE_PATH, state)
    print(f"Metricool scheduled {queue_id} for automatic Instagram publishing at {publish_local:%Y-%m-%d %H:%M} {timezone_name}.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise

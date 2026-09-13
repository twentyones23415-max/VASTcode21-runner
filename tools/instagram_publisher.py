#!/usr/bin/env python3
"""VASTcode21 Instagram publisher using the Instagram API with Instagram Login.

Reads marketing/queue.json and marketing/social_config.json, enforces daily/rate
limits, verifies the token belongs to the configured account, publishes the
highest-priority eligible image post, and records the result in
marketing/publish_state.json.
"""

from __future__ import annotations

import json
import os
import sys
import time
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
API_BASE = "https://graph.instagram.com"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def api(method: str, path: str, token: str, params: dict | None = None):
    params = dict(params or {})
    params["access_token"] = token
    url = f"{API_BASE}{path}"
    body = None
    headers = {"User-Agent": "VASTcode21-InstagramPublisher/1.0"}
    if method == "GET":
        url += "?" + urllib.parse.urlencode(params)
    else:
        body = urllib.parse.urlencode(params).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Instagram API HTTP {e.code}: {detail}") from e


def parse_dt(value: str | None):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def main() -> int:
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "").strip()
    if not token:
        print("ERROR: INSTAGRAM_ACCESS_TOKEN is not configured.", file=sys.stderr)
        return 2

    validate_only = os.environ.get("VALIDATE_ONLY", "false").lower() == "true"
    force_publish = os.environ.get("FORCE_PUBLISH", "false").lower() == "true"

    config = load_json(CONFIG_PATH)
    queue = load_json(QUEUE_PATH)
    state = load_json(STATE_PATH) if STATE_PATH.exists() else {"version": "1.0.0", "last_publish_at": None, "published": []}

    if not config.get("enabled", False):
        print("Instagram publishing disabled in social_config.json")
        return 0
    if config.get("paid_ads", True):
        raise RuntimeError("Safety stop: paid_ads must remain false.")
    if config.get("live_trading", True):
        raise RuntimeError("Safety stop: live_trading must remain false.")

    me = api("GET", "/me", token, {"fields": "id,username"})
    username = me.get("username")
    ig_user_id = me.get("id")
    expected = config.get("account_name")
    if not ig_user_id or not username:
        raise RuntimeError(f"Could not resolve Instagram account from token: {me}")
    if expected and username.lower() != expected.lower():
        raise RuntimeError(f"Safety stop: token belongs to @{username}, expected @{expected}.")

    print(f"Token validated for @{username} ({ig_user_id}).")
    if validate_only:
        print("VALIDATE_ONLY=true: no post will be published.")
        return 0

    tz_name = config.get("timezone", "Europe/Bucharest")
    local_tz = ZoneInfo(tz_name)
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(local_tz)
    publish_hour = int(config.get("publish_hour_local", 19))

    if not force_publish and now_local.hour != publish_hour:
        print(f"Outside publish hour: now {now_local:%Y-%m-%d %H:%M} {tz_name}, target hour {publish_hour}:00.")
        return 0

    published = state.get("published", [])
    published_ids = {x.get("queue_id") for x in published}
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
        if "Instagram" in item.get("platforms", []) and item.get("id") not in published_ids
    ]
    candidates.sort(key=lambda x: int(x.get("priority", 0)), reverse=True)
    if not candidates:
        print("No unpublished Instagram queue items available.")
        return 0

    item = candidates[0]
    queue_id = item["id"]
    image_url = config["raw_asset_base"].rstrip("/") + f"/{queue_id}.jpg"
    hashtags = " ".join(config.get("hashtags", []))
    caption_parts = [item.get("hook", "").strip(), item.get("caption", "").strip(), item.get("disclaimer", "").strip(), hashtags]
    caption = "\n\n".join(x for x in caption_parts if x)

    print(f"Preparing @{username} post: {queue_id}")
    container = api("POST", f"/{ig_user_id}/media", token, {"image_url": image_url, "caption": caption})
    creation_id = container.get("id")
    if not creation_id:
        raise RuntimeError(f"No creation id returned: {container}")

    # Image containers are normally quick, but wait for Meta to report readiness.
    for _ in range(12):
        status = api("GET", f"/{creation_id}", token, {"fields": "status_code,status"})
        code = status.get("status_code")
        if code == "FINISHED":
            break
        if code in {"ERROR", "EXPIRED"}:
            raise RuntimeError(f"Media container failed: {status}")
        time.sleep(5)
    else:
        raise RuntimeError("Media container did not become ready within 60 seconds.")

    result = api("POST", f"/{ig_user_id}/media_publish", token, {"creation_id": creation_id})
    media_id = result.get("id")
    if not media_id:
        raise RuntimeError(f"Publish did not return media id: {result}")

    published_at = datetime.now(timezone.utc).isoformat()
    state["last_publish_at"] = published_at
    state.setdefault("published", []).append({
        "queue_id": queue_id,
        "media_id": media_id,
        "published_at": published_at,
        "account": username,
        "image_url": image_url,
    })
    save_json(STATE_PATH, state)
    print(f"Published {queue_id} successfully as media {media_id}.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise

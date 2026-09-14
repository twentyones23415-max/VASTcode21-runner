#!/usr/bin/env python3
"""VASTcode21 Instagram publisher.

Supports single-image, carousel and Reel publishing through Instagram Login.
Enforces conservative rate limits, validates the target account, performs remote
and local idempotency checks, and records every publication/reconciliation.
"""

from __future__ import annotations

import hashlib
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
GROWTH_PATH = ROOT / "marketing" / "growth_metrics.json"
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
    headers = {"User-Agent": "VASTcode21-InstagramPublisher/2.0"}
    if method == "GET":
        url += "?" + urllib.parse.urlencode(params)
    else:
        body = urllib.parse.urlencode(params).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Instagram API HTTP {e.code}: {detail}") from e


def parse_dt(value: str | None):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def normalize_caption(value: str | None) -> str:
    return "\n".join(line.rstrip() for line in (value or "").strip().splitlines())


def fingerprint(caption: str) -> str:
    return hashlib.sha256(normalize_caption(caption).encode("utf-8")).hexdigest()


def find_remote_duplicate(token: str, caption: str, now_utc: datetime, window_hours: int = 336):
    response = api("GET", "/me/media", token, {"fields": "id,caption,timestamp,media_type,media_product_type", "limit": 50})
    target = normalize_caption(caption)
    cutoff = now_utc - timedelta(hours=window_hours)
    for media in response.get("data", []):
        ts = parse_dt(media.get("timestamp"))
        if ts and ts.astimezone(timezone.utc) < cutoff:
            continue
        if normalize_caption(media.get("caption")) == target:
            return media
    return None


def wait_container(token: str, creation_id: str, attempts: int = 36, sleep_seconds: int = 5) -> None:
    for _ in range(attempts):
        status = api("GET", f"/{creation_id}", token, {"fields": "status_code,status"})
        code = status.get("status_code")
        if code == "FINISHED":
            return
        if code in {"ERROR", "EXPIRED"}:
            raise RuntimeError(f"Media container failed: {status}")
        time.sleep(sleep_seconds)
    raise RuntimeError("Media container did not become ready in time.")


def create_image_container(ig_user_id: str, token: str, image_url: str, caption: str) -> str:
    result = api("POST", f"/{ig_user_id}/media", token, {"image_url": image_url, "caption": caption})
    cid = result.get("id")
    if not cid:
        raise RuntimeError(f"No creation id returned for image: {result}")
    wait_container(token, cid, attempts=18)
    return cid


def create_carousel_container(ig_user_id: str, token: str, base: str, queue_id: str, caption: str) -> str:
    children: list[str] = []
    for slide in range(1, 4):
        url = f"{base}/{queue_id}-{slide}.jpg"
        child = api("POST", f"/{ig_user_id}/media", token, {
            "image_url": url,
            "is_carousel_item": "true",
        })
        child_id = child.get("id")
        if not child_id:
            raise RuntimeError(f"No child container id for carousel slide {slide}: {child}")
        wait_container(token, child_id, attempts=18)
        children.append(child_id)

    parent = api("POST", f"/{ig_user_id}/media", token, {
        "media_type": "CAROUSEL",
        "children": ",".join(children),
        "caption": caption,
    })
    cid = parent.get("id")
    if not cid:
        raise RuntimeError(f"No carousel container id returned: {parent}")
    wait_container(token, cid, attempts=24)
    return cid


def create_reel_container(ig_user_id: str, token: str, video_url: str, caption: str) -> str:
    result = api("POST", f"/{ig_user_id}/media", token, {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true",
    })
    cid = result.get("id")
    if not cid:
        raise RuntimeError(f"No Reel creation id returned: {result}")
    wait_container(token, cid, attempts=60)
    return cid


def record_state(state: dict, *, queue_id: str, media_id: str, published_at: str, username: str, media_url: str, fmt: str, pillar: str | None, caption_fp: str, reconciled: bool = False) -> None:
    state["version"] = "2.0.0"
    state["last_publish_at"] = published_at
    state.setdefault("published", []).append({
        "queue_id": queue_id,
        "media_id": media_id,
        "published_at": published_at,
        "account": username,
        "media_url": media_url,
        "format": fmt,
        "pillar": pillar,
        "caption_fingerprint": caption_fp,
        "reconciled": reconciled,
    })
    save_json(STATE_PATH, state)


def main() -> int:
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "").strip()
    if not token:
        print("ERROR: INSTAGRAM_ACCESS_TOKEN is not configured.", file=sys.stderr)
        return 2

    validate_only = os.environ.get("VALIDATE_ONLY", "false").lower() == "true"
    force_publish = os.environ.get("FORCE_PUBLISH", "false").lower() == "true"

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
        if "Instagram" in item.get("platforms", [])
        and item.get("id") not in published_ids
        and not (followers < 10 and str(item.get("pillar") or "").lower() == "services")
    ]
    candidates.sort(key=lambda x: int(x.get("priority", 0)), reverse=True)
    if not candidates:
        print("No unpublished Instagram queue items available.")
        return 0

    if followers < 10:
        print(f"Discovery-first guard active at {followers} followers: service posts excluded from organic cadence.")

    item = candidates[0]
    queue_id = str(item["id"])
    fmt = str(item.get("format") or "image").lower()
    pillar = item.get("pillar")
    base = config["raw_asset_base"].rstrip("/")
    image_url = f"{base}/{queue_id}.jpg"
    video_url = f"{base}/{queue_id}.mp4"

    item_hashtags = item.get("hashtags") or config.get("hashtags", [])
    hashtags = " ".join(str(x) for x in item_hashtags)
    cta = str(item.get("cta") or "").strip()
    caption_parts = [
        str(item.get("hook") or "").strip(),
        str(item.get("caption") or "").strip(),
        cta,
        str(item.get("disclaimer") or "").strip(),
        hashtags,
    ]
    caption = "\n\n".join(x for x in caption_parts if x)
    caption_fp = fingerprint(caption)

    if any(x.get("caption_fingerprint") == caption_fp for x in published):
        print(f"Local caption fingerprint already published for {queue_id}. Skipping.")
        return 0

    remote_duplicate = find_remote_duplicate(token, caption, now_utc, int(config.get("remote_duplicate_window_hours", 336)))
    if remote_duplicate:
        media_id = str(remote_duplicate.get("id"))
        published_at = remote_duplicate.get("timestamp") or now_utc.isoformat()
        print(f"Remote duplicate detected for {queue_id}; media {media_id}. Skipping publish.")
        record_state(state, queue_id=queue_id, media_id=media_id, published_at=published_at, username=username, media_url=image_url, fmt=fmt, pillar=pillar, caption_fp=caption_fp, reconciled=True)
        return 0

    print(f"Preparing @{username} {fmt} post: {queue_id}")
    creation_id = None
    media_url = image_url

    try:
        if fmt == "carousel":
            creation_id = create_carousel_container(ig_user_id, token, base, queue_id, caption)
            media_url = f"{base}/{queue_id}-1.jpg"
        elif fmt == "reel":
            creation_id = create_reel_container(ig_user_id, token, video_url, caption)
            media_url = video_url
        else:
            creation_id = create_image_container(ig_user_id, token, image_url, caption)
    except Exception as exc:
        if fmt in {"carousel", "reel"} and bool(config.get("format_fallback_to_image", True)):
            print(f"{fmt} creation failed ({exc}); falling back to single image.")
            fmt = "image"
            media_url = image_url
            creation_id = create_image_container(ig_user_id, token, image_url, caption)
        else:
            raise

    remote_duplicate = find_remote_duplicate(token, caption, datetime.now(timezone.utc), window_hours=2)
    if remote_duplicate:
        media_id = str(remote_duplicate.get("id"))
        published_at = remote_duplicate.get("timestamp") or datetime.now(timezone.utc).isoformat()
        print(f"Duplicate appeared before media_publish; media {media_id}. Skipping publish.")
        record_state(state, queue_id=queue_id, media_id=media_id, published_at=published_at, username=username, media_url=media_url, fmt=fmt, pillar=pillar, caption_fp=caption_fp, reconciled=True)
        return 0

    result = api("POST", f"/{ig_user_id}/media_publish", token, {"creation_id": creation_id})
    media_id = result.get("id")
    if not media_id:
        raise RuntimeError(f"Publish did not return media id: {result}")

    published_at = datetime.now(timezone.utc).isoformat()
    record_state(state, queue_id=queue_id, media_id=str(media_id), published_at=published_at, username=username, media_url=media_url, fmt=fmt, pillar=pillar, caption_fp=caption_fp, reconciled=False)
    print(f"Published {queue_id} successfully as {fmt} media {media_id}.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise

#!/usr/bin/env python3
"""Publish approved VASTcode21 service-offer posts through the shared organic cadence.

This path is limited to organic service/revenue offer items. It keeps account
validation, paid-ads/live-trading safety stops, local/remote duplicate protection,
Instagram media-container checks, and the same global daily/spacing limits as the
main Instagram publisher. While the account has fewer than 10 followers, service
posts are deferred so the scarce organic slot is reserved for discovery/value.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import instagram_publisher as pub


def _advance_last_publish_at(state: dict, published_at: str) -> None:
    """Keep last_publish_at aligned with the newest known publication timestamp."""
    candidate = pub.parse_dt(published_at)
    current = pub.parse_dt(state.get("last_publish_at"))
    if candidate and (current is None or candidate.astimezone(timezone.utc) > current.astimezone(timezone.utc)):
        state["last_publish_at"] = candidate.isoformat()


def main() -> int:
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "").strip()
    if not token:
        print("ERROR: INSTAGRAM_ACCESS_TOKEN is not configured.")
        return 2

    config = pub.load_json(pub.CONFIG_PATH)
    queue = pub.load_json(pub.QUEUE_PATH)
    state = pub.load_json(pub.STATE_PATH) if pub.STATE_PATH.exists() else {
        "version": "2.2.0", "last_publish_at": None, "published": []
    }

    if not config.get("enabled", False):
        print("Instagram publishing disabled.")
        return 0
    if config.get("paid_ads", True):
        raise RuntimeError("Safety stop: paid_ads must remain false.")
    if config.get("live_trading", True):
        raise RuntimeError("Safety stop: live_trading must remain false.")

    growth_path = pub.ROOT / "marketing" / "growth_metrics.json"
    growth = pub.load_json(growth_path) if growth_path.exists() else {}
    followers = int(growth.get("followers_count", 0) or 0)
    if followers < 10:
        print(f"Discovery-first guard active: {followers} followers. Service offers stay profile-only until 10 followers.")
        return 0

    me = pub.api("GET", "/me", token, {"fields": "id,username"})
    username = me.get("username")
    ig_user_id = me.get("id")
    expected = config.get("account_name")
    if not ig_user_id or not username:
        raise RuntimeError(f"Could not resolve Instagram account from token: {me}")
    if expected and username.lower() != expected.lower():
        raise RuntimeError(f"Safety stop: token belongs to @{username}, expected @{expected}.")

    tz_name = config.get("timezone", "Europe/Bucharest")
    local_tz = ZoneInfo(tz_name)
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(local_tz)
    published = state.get("published", [])
    published_ids = {x.get("queue_id") for x in published}

    # Global organic cadence: service offers share the same daily and spacing budget
    # as research/education posts. No publishing path may bypass these guards.
    today_count = 0
    for entry in published:
        dt = pub.parse_dt(entry.get("published_at"))
        if dt and dt.astimezone(local_tz).date() == now_local.date():
            today_count += 1

    max_posts = int(config.get("max_posts_per_day", 1))
    if today_count >= max_posts:
        print(f"Daily publish limit reached ({today_count}/{max_posts}).")
        return 0

    last_publish = pub.parse_dt(state.get("last_publish_at"))
    min_hours = int(config.get("min_hours_between_posts", 20))
    if last_publish and now_utc - last_publish.astimezone(timezone.utc) < timedelta(hours=min_hours):
        print("Minimum spacing between posts has not elapsed.")
        return 0

    candidates = [
        item for item in queue.get("items", [])
        if "Instagram" in item.get("platforms", [])
        and item.get("id") not in published_ids
        and (bool(item.get("free_publish")) or str(item.get("pillar") or "") == "services")
    ]
    candidates.sort(key=lambda x: int(x.get("priority", 0)), reverse=True)
    if not candidates:
        print("No unpublished service offers available.")
        return 0

    item = candidates[0]
    queue_id = str(item["id"])
    fmt = str(item.get("format") or "image").lower()
    pillar = item.get("pillar")
    base = config["raw_asset_base"].rstrip("/")
    image_url = f"{base}/{queue_id}.jpg"
    video_url = f"{base}/{queue_id}.mp4"

    hashtags = " ".join(str(x) for x in (item.get("hashtags") or config.get("hashtags", [])))
    caption = "\n\n".join(x for x in [
        str(item.get("hook") or "").strip(),
        str(item.get("caption") or "").strip(),
        str(item.get("cta") or "").strip(),
        str(item.get("disclaimer") or "").strip(),
        hashtags,
    ] if x)
    caption_fp = pub.fingerprint(caption)

    if any(x.get("caption_fingerprint") == caption_fp for x in published):
        print(f"Local duplicate blocked for {queue_id}.")
        return 0

    remote = pub.find_remote_duplicate(token, caption, now_utc, int(config.get("remote_duplicate_window_hours", 336)))
    if remote:
        published_at = remote.get("timestamp") or now_utc.isoformat()
        state["version"] = "2.2.0"
        state.setdefault("published", []).append({
            "queue_id": queue_id,
            "media_id": str(remote.get("id")),
            "published_at": published_at,
            "account": username,
            "media_url": image_url,
            "format": fmt,
            "pillar": pillar,
            "caption_fingerprint": caption_fp,
            "reconciled": True,
            "free_publish": True,
        })
        _advance_last_publish_at(state, published_at)
        pub.save_json(pub.STATE_PATH, state)
        print(f"Remote duplicate reconciled for {queue_id}; no second post created.")
        return 0

    print(f"Preparing @{username} {fmt} service offer: {queue_id}")
    media_url = image_url
    try:
        if fmt == "carousel":
            creation_id = pub.create_carousel_container(ig_user_id, token, base, queue_id, caption)
            media_url = f"{base}/{queue_id}-1.jpg"
        elif fmt == "reel":
            creation_id = pub.create_reel_container(ig_user_id, token, video_url, caption)
            media_url = video_url
        else:
            creation_id = pub.create_image_container(ig_user_id, token, image_url, caption)
    except Exception as exc:
        if fmt in {"carousel", "reel"} and bool(config.get("format_fallback_to_image", True)):
            print(f"{fmt} creation failed ({exc}); falling back to image.")
            fmt = "image"
            media_url = image_url
            creation_id = pub.create_image_container(ig_user_id, token, image_url, caption)
        else:
            raise

    remote = pub.find_remote_duplicate(token, caption, datetime.now(timezone.utc), window_hours=2)
    if remote:
        media_id = str(remote.get("id"))
        published_at = remote.get("timestamp") or datetime.now(timezone.utc).isoformat()
        reconciled = True
    else:
        result = pub.api("POST", f"/{ig_user_id}/media_publish", token, {"creation_id": creation_id})
        media_id = str(result.get("id") or "")
        if not media_id:
            raise RuntimeError(f"Publish did not return media id: {result}")
        published_at = datetime.now(timezone.utc).isoformat()
        reconciled = False

    state["version"] = "2.2.0"
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
        "free_publish": True,
    })
    _advance_last_publish_at(state, published_at)
    pub.save_json(pub.STATE_PATH, state)
    print(f"Published service offer {queue_id} as {fmt} media {media_id}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

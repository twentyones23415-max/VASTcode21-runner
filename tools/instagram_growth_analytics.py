from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METRICS_PATH = ROOT / "marketing" / "growth_metrics.json"
HISTORY_PATH = ROOT / "marketing" / "growth_history.json"
STATE_PATH = ROOT / "marketing" / "publish_state.json"
API_BASE = "https://graph.instagram.com"


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def api(path: str, token: str, params: dict | None = None):
    params = dict(params or {})
    params["access_token"] = token
    url = f"{API_BASE}{path}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "VASTcode21-GrowthAnalytics/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Instagram API HTTP {e.code}: {detail}") from e


def safe_profile(token: str) -> dict:
    try:
        return api("/me", token, {"fields": "id,username,followers_count,media_count"})
    except Exception:
        return api("/me", token, {"fields": "id,username"})


def safe_media(token: str) -> list[dict]:
    fields = "id,caption,media_type,media_product_type,permalink,timestamp,like_count,comments_count"
    try:
        return list(api("/me/media", token, {"fields": fields, "limit": 50}).get("data", []))
    except Exception:
        fallback = "id,caption,media_type,permalink,timestamp"
        try:
            return list(api("/me/media", token, {"fields": fallback, "limit": 50}).get("data", []))
        except Exception:
            return []


def parse_dt(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def main() -> int:
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "").strip()
    if not token:
        print("ERROR: INSTAGRAM_ACCESS_TOKEN is not configured.", file=sys.stderr)
        return 2

    now = datetime.now(timezone.utc)
    profile = safe_profile(token)
    media = safe_media(token)
    state = load_json(STATE_PATH, {"published": []})
    history = load_json(HISTORY_PATH, {"version": "1.0.0", "snapshots": []})

    publish_by_media = {
        str(x.get("media_id")): x
        for x in state.get("published", [])
        if x.get("media_id")
    }

    recent = []
    format_scores: dict[str, list[float]] = {}
    for m in media:
        ts = parse_dt(m.get("timestamp"))
        if ts and now - ts.astimezone(timezone.utc) > timedelta(days=30):
            continue
        likes = int(m.get("like_count", 0) or 0)
        comments = int(m.get("comments_count", 0) or 0)
        score = likes + 3 * comments
        mapped = publish_by_media.get(str(m.get("id")), {})
        fmt = str(mapped.get("format") or m.get("media_product_type") or m.get("media_type") or "unknown").lower()
        format_scores.setdefault(fmt, []).append(float(score))
        recent.append({
            "media_id": m.get("id"),
            "published_at": m.get("timestamp"),
            "format": fmt,
            "likes": likes,
            "comments": comments,
            "engagement_score": score,
            "queue_id": mapped.get("queue_id"),
            "pillar": mapped.get("pillar"),
            "permalink": m.get("permalink"),
        })

    best_format = None
    best_avg = -1.0
    for fmt, vals in format_scores.items():
        if not vals:
            continue
        avg = sum(vals) / len(vals)
        if avg > best_avg:
            best_avg = avg
            best_format = fmt

    snapshots = list(history.get("snapshots", []))
    followers = profile.get("followers_count")
    followers_int = int(followers or 0) if followers is not None else None

    previous_24 = None
    for snap in reversed(snapshots):
        ts = parse_dt(snap.get("captured_at"))
        if ts and now - ts >= timedelta(hours=20):
            previous_24 = snap
            break

    delta_24h = None
    if followers_int is not None and previous_24 and previous_24.get("followers_count") is not None:
        delta_24h = followers_int - int(previous_24.get("followers_count") or 0)

    snapshot = {
        "captured_at": now.isoformat(),
        "username": profile.get("username"),
        "followers_count": followers_int,
        "media_count": profile.get("media_count"),
        "followers_delta_24h": delta_24h,
        "recent_media_count": len(recent),
        "best_format": best_format,
        "best_format_avg_engagement": round(best_avg, 2) if best_avg >= 0 else None,
    }
    snapshots.append(snapshot)
    snapshots = snapshots[-180:]

    metrics = {
        "version": "1.0.0",
        "updated_at": now.isoformat(),
        "account": profile.get("username"),
        "followers_count": followers_int or 0,
        "media_count": int(profile.get("media_count", 0) or 0),
        "followers_delta_24h": delta_24h,
        "best_format": best_format,
        "best_format_avg_engagement": round(best_avg, 2) if best_avg >= 0 else None,
        "recent_media": sorted(recent, key=lambda x: x.get("published_at") or "", reverse=True)[:20],
        "paid_ads": False,
        "live_trading": False,
    }

    save_json(METRICS_PATH, metrics)
    save_json(HISTORY_PATH, {"version": "1.0.0", "snapshots": snapshots})
    print(json.dumps({
        "account": metrics["account"],
        "followers": metrics["followers_count"],
        "delta_24h": metrics["followers_delta_24h"],
        "recent_media": len(metrics["recent_media"]),
        "best_format": metrics["best_format"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

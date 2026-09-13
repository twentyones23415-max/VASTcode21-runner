#!/usr/bin/env python3
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "marketing" / "revenue_config.json"
STATE_PATH = ROOT / "marketing" / "mailchimp_state.json"
KEY = os.getenv("MAILCHIMP_API_KEY", "").strip()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def data_center():
    if "-" not in KEY:
        return ""
    return KEY.rsplit("-", 1)[-1].strip()


def request(method, endpoint, payload=None):
    dc = data_center()
    if not dc:
        raise RuntimeError("Mailchimp API key does not include a data-center suffix.")
    body = None
    headers = {
        "Authorization": "Basic " + base64.b64encode(f"vastcode21:{KEY}".encode()).decode(),
        "Accept": "application/json",
    }
    if payload is not None:
        body = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"https://{dc}.api.mailchimp.com/3.0{endpoint}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        try:
            parsed = json.loads(detail)
            msg = parsed.get("detail") or parsed.get("title") or "Mailchimp API error"
        except Exception:
            msg = "Mailchimp API error"
        raise RuntimeError(f"Mailchimp {exc.code}: {msg}") from None


def ensure_tag(list_id, name):
    segments = request("GET", f"/lists/{list_id}/segments?count=1000").get("segments", [])
    for seg in segments:
        if seg.get("name") == name:
            return seg
    return request("POST", f"/lists/{list_id}/segments", {"name": name, "static_segment": []})


def main():
    config = load_json(CONFIG_PATH, {})
    state = load_json(STATE_PATH, {})
    state["updated_at"] = now_iso()
    state["paid_ads"] = False
    state["live_trading"] = False

    if not KEY:
        state["connected"] = False
        state["mode"] = "waiting_for_mailchimp_api_key"
        save_json(STATE_PATH, state)
        print("Mailchimp setup waiting for MAILCHIMP_API_KEY GitHub Secret.")
        return 0

    ping = request("GET", "/ping")
    lists = request("GET", "/lists?count=100").get("lists", [])
    if not lists:
        raise RuntimeError("Mailchimp account has no audience/list yet.")

    audience = lists[0]
    list_id = audience["id"]
    tags = {}
    for name in ("VAST Early Access", "Research Brief Subscriber"):
        seg = ensure_tag(list_id, name)
        tags[name] = {"id": seg.get("id"), "name": seg.get("name")}

    signup_url = audience.get("subscribe_url_short") or audience.get("subscribe_url_long") or ""
    config.setdefault("connections", {})["mailchimp"] = True
    config["connections"]["subscriber_sync"] = bool(config["connections"].get("subscriber_sync", False))
    if config.get("connections", {}).get("stripe"):
        config["mode"] = "stripe_mailchimp_connected"

    for offer in config.get("offers", []):
        if offer.get("id") == "vast-early-access":
            offer["signup_url"] = signup_url
            offer["email_provider"] = "mailchimp"
        if offer.get("id") == "research-brief":
            offer["email_provider"] = "mailchimp"

    state.update({
        "connected": True,
        "mode": "live_ready",
        "health": ping.get("health_status"),
        "data_center": data_center(),
        "audience_id": list_id,
        "audience_name": audience.get("name"),
        "signup_url": signup_url,
        "tags": tags,
    })
    save_json(CONFIG_PATH, config)
    save_json(STATE_PATH, state)
    print(f"Mailchimp setup complete. audience={list_id} connected=true")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)

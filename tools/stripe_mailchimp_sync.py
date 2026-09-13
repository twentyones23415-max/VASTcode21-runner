#!/usr/bin/env python3
import base64
import hashlib
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
STRIPE_STATE_PATH = ROOT / "marketing" / "stripe_state.json"
MAILCHIMP_STATE_PATH = ROOT / "marketing" / "mailchimp_state.json"
SYNC_STATE_PATH = ROOT / "marketing" / "subscriber_sync_state.json"
STRIPE_API = "https://api.stripe.com/v1"
STRIPE_KEY = os.getenv("STRIPE_RESTRICTED_KEY", "").strip()
MAILCHIMP_KEY = os.getenv("MAILCHIMP_API_KEY", "").strip()
TAG_NAME = "Research Brief Subscriber"
ACTIVE_STATUSES = {"active", "trialing"}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def stripe_request(endpoint, params=None):
    if params:
        endpoint += ("&" if "?" in endpoint else "?") + urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(
        STRIPE_API + endpoint,
        headers={"Authorization": f"Bearer {STRIPE_KEY}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        try:
            parsed = json.loads(detail)
            msg = parsed.get("error", {}).get("message", "Stripe API error")
        except Exception:
            msg = "Stripe API error"
        raise RuntimeError(f"Stripe {exc.code}: {msg}") from None


def mailchimp_dc():
    return MAILCHIMP_KEY.rsplit("-", 1)[-1].strip() if "-" in MAILCHIMP_KEY else ""


def mailchimp_request(method, endpoint, payload=None):
    dc = mailchimp_dc()
    if not dc:
        raise RuntimeError("Mailchimp API key does not include a data-center suffix.")
    body = None
    headers = {
        "Authorization": "Basic " + base64.b64encode(f"vastcode21:{MAILCHIMP_KEY}".encode()).decode(),
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


def all_subscriptions_for_price(price_id):
    matches = []
    starting_after = None
    while True:
        params = {"status": "all", "limit": 100}
        if starting_after:
            params["starting_after"] = starting_after
        page = stripe_request("/subscriptions", params)
        data = page.get("data", [])
        for sub in data:
            item_prices = {
                (item.get("price") or {}).get("id")
                for item in (sub.get("items") or {}).get("data", [])
            }
            if price_id in item_prices:
                matches.append(sub)
        if not page.get("has_more") or not data:
            break
        starting_after = data[-1].get("id")
    return matches


def customer_email(customer_ref, cache):
    if isinstance(customer_ref, dict):
        return str(customer_ref.get("email") or "").strip().lower()
    customer_id = str(customer_ref or "").strip()
    if not customer_id:
        return ""
    if customer_id not in cache:
        cache[customer_id] = stripe_request(f"/customers/{urllib.parse.quote(customer_id)}")
    return str(cache[customer_id].get("email") or "").strip().lower()


def member_hash(email):
    return hashlib.md5(email.lower().encode()).hexdigest()


def sync_member(list_id, email, active):
    h = member_hash(email)
    member = mailchimp_request(
        "PUT",
        f"/lists/{list_id}/members/{h}",
        {"email_address": email, "status_if_new": "subscribed"},
    )
    mailchimp_request(
        "POST",
        f"/lists/{list_id}/members/{h}/tags",
        {"tags": [{"name": TAG_NAME, "status": "active" if active else "inactive"}]},
    )
    return member.get("status", "")


def set_connection(config, value):
    config.setdefault("connections", {})["subscriber_sync"] = bool(value)


def main():
    config = load_json(CONFIG_PATH, {})
    stripe_state = load_json(STRIPE_STATE_PATH, {})
    mailchimp_state = load_json(MAILCHIMP_STATE_PATH, {})
    state = load_json(SYNC_STATE_PATH, {})
    state.update({
        "updated_at": now_iso(),
        "paid_ads": False,
        "live_trading": False,
        "provider": "stripe_to_mailchimp",
        "tag": TAG_NAME,
    })

    if not STRIPE_KEY or not MAILCHIMP_KEY:
        state.update({"connected": False, "mode": "waiting_for_secrets", "last_error": ""})
        set_connection(config, False)
        save_json(CONFIG_PATH, config)
        save_json(SYNC_STATE_PATH, state)
        print("Subscriber sync waiting for Stripe and Mailchimp GitHub Secrets.")
        return 0

    if not (STRIPE_KEY.startswith("rk_live_") or STRIPE_KEY.startswith("sk_live_")):
        state.update({"connected": False, "mode": "blocked_non_live_stripe_key", "last_error": "Non-live Stripe key configured."})
        set_connection(config, False)
        save_json(CONFIG_PATH, config)
        save_json(SYNC_STATE_PATH, state)
        print("Refusing subscriber sync: Stripe key is not live mode.", file=sys.stderr)
        return 2

    price_id = str((((stripe_state.get("offers") or {}).get("research-brief") or {}).get("price_id")) or "").strip()
    list_id = str(mailchimp_state.get("audience_id") or "").strip()
    if not price_id or not list_id:
        state.update({"connected": False, "mode": "waiting_for_provider_state", "last_error": "Missing research price or Mailchimp audience id."})
        set_connection(config, False)
        save_json(CONFIG_PATH, config)
        save_json(SYNC_STATE_PATH, state)
        print("Subscriber sync waiting for Stripe/Mailchimp provider state.")
        return 0

    try:
        subscriptions = all_subscriptions_for_price(price_id)
        customer_cache = {}
        purchasers = {}
        skipped_no_email = 0

        for sub in subscriptions:
            email = customer_email(sub.get("customer"), customer_cache)
            if not email:
                skipped_no_email += 1
                continue
            is_active = str(sub.get("status") or "") in ACTIVE_STATUSES
            purchasers[email] = bool(purchasers.get(email, False) or is_active)

        active_count = 0
        inactive_count = 0
        suppressed_count = 0
        synced_count = 0

        for email, active in purchasers.items():
            member_status = sync_member(list_id, email, active)
            synced_count += 1
            active_count += int(active)
            inactive_count += int(not active)
            if member_status in {"unsubscribed", "cleaned", "pending"}:
                suppressed_count += 1

        set_connection(config, True)
        if config.get("connections", {}).get("stripe") and config.get("connections", {}).get("mailchimp"):
            config["mode"] = "stripe_mailchimp_connected"
        state.update({
            "connected": True,
            "mode": "ready",
            "last_error": "",
            "research_price_id": price_id,
            "subscriptions_seen": len(subscriptions),
            "members_synced": synced_count,
            "active_subscribers": active_count,
            "inactive_subscribers": inactive_count,
            "suppressed_members": suppressed_count,
            "skipped_no_email": skipped_no_email,
        })
        save_json(CONFIG_PATH, config)
        save_json(SYNC_STATE_PATH, state)
        print(
            "Subscriber sync complete: "
            f"subscriptions={len(subscriptions)} synced={synced_count} active={active_count} inactive={inactive_count}"
        )
        return 0
    except Exception as exc:
        set_connection(config, False)
        state.update({"connected": False, "mode": "error", "last_error": str(exc)[:500]})
        save_json(CONFIG_PATH, config)
        save_json(SYNC_STATE_PATH, state)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

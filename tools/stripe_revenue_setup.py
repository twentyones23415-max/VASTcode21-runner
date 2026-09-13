#!/usr/bin/env python3
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
STATE_PATH = ROOT / "marketing" / "stripe_state.json"
API = "https://api.stripe.com/v1"
KEY = os.getenv("STRIPE_RESTRICTED_KEY", "").strip()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def request(method, endpoint, data=None):
    body = None
    headers = {"Authorization": f"Bearer {KEY}"}
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(API + endpoint, data=body, headers=headers, method=method)
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


def get_or_none(endpoint):
    try:
        return request("GET", endpoint)
    except RuntimeError as exc:
        if "Stripe 404" in str(exc):
            return None
        raise


def find_product(offer_id):
    items = request("GET", "/products?active=true&limit=100").get("data", [])
    for item in items:
        if item.get("metadata", {}).get("vastcode21_offer_id") == offer_id:
            return item
    return None


def find_price(lookup_key):
    q = urllib.parse.urlencode({"lookup_keys[]": lookup_key, "active": "true", "limit": 10})
    items = request("GET", "/prices?" + q).get("data", [])
    return items[0] if items else None


def find_link(offer_id):
    items = request("GET", "/payment_links?active=true&limit=100").get("data", [])
    for item in items:
        if item.get("metadata", {}).get("vastcode21_offer_id") == offer_id:
            return item
    return None


def create_product(offer):
    return request("POST", "/products", {
        "name": offer["name"],
        "description": offer["deliverable"],
        "metadata[vastcode21_offer_id]": offer["id"],
        "metadata[offer_type]": offer["type"],
    })


def create_price(offer, product_id):
    amount = int(round(float(offer["price_eur"]) * 100))
    lookup_key = f"vastcode21_{offer['id'].replace('-', '_')}_eur_{amount}_v1"
    data = {
        "currency": "eur",
        "unit_amount": amount,
        "product": product_id,
        "lookup_key": lookup_key,
        "metadata[vastcode21_offer_id]": offer["id"],
    }
    if offer["billing"] == "monthly":
        data["recurring[interval]"] = "month"
    return request("POST", "/prices", data), lookup_key


def create_link(offer, price_id):
    return request("POST", "/payment_links", {
        "line_items[0][price]": price_id,
        "line_items[0][quantity]": 1,
        "billing_address_collection": "auto",
        "metadata[vastcode21_offer_id]": offer["id"],
        "metadata[brand]": "VASTcode21",
    })


def main():
    config = load_json(CONFIG_PATH, {})
    state = load_json(STATE_PATH, {"offers": {}})
    state.setdefault("offers", {})
    state["updated_at"] = now_iso()
    state["live_trading"] = False
    state["paid_ads"] = False

    if not KEY:
        state["mode"] = "waiting_for_live_restricted_key"
        state["connected"] = False
        save_json(STATE_PATH, state)
        print("Stripe live setup waiting for STRIPE_RESTRICTED_KEY GitHub Secret.")
        return 0

    if not (KEY.startswith("rk_live_") or KEY.startswith("sk_live_")):
        state["mode"] = "blocked_non_live_key"
        state["connected"] = False
        save_json(STATE_PATH, state)
        print("Refusing Stripe setup: configured key is not a live-mode server key.", file=sys.stderr)
        return 2

    paid_offers = [o for o in config.get("offers", []) if o.get("enabled") and o.get("price_eur", 0) > 0]
    all_ready = True

    for offer in paid_offers:
        offer_state = state["offers"].setdefault(offer["id"], {})
        product = None
        if offer_state.get("product_id"):
            product = get_or_none(f"/products/{offer_state['product_id']}")
        if not product:
            product = find_product(offer["id"]) or create_product(offer)
        offer_state["product_id"] = product["id"]

        amount = int(round(float(offer["price_eur"]) * 100))
        lookup_key = f"vastcode21_{offer['id'].replace('-', '_')}_eur_{amount}_v1"
        price = None
        if offer_state.get("price_id"):
            price = get_or_none(f"/prices/{offer_state['price_id']}")
        if not price:
            price = find_price(lookup_key)
        if not price:
            price, lookup_key = create_price(offer, product["id"])
        offer_state["price_id"] = price["id"]
        offer_state["lookup_key"] = lookup_key

        link = None
        if offer_state.get("payment_link_id"):
            link = get_or_none(f"/payment_links/{offer_state['payment_link_id']}")
        if not link:
            link = find_link(offer["id"]) or create_link(offer, price["id"])
        offer_state["payment_link_id"] = link["id"]
        offer_state["checkout_url"] = link["url"]
        offer_state["livemode"] = bool(link.get("livemode"))
        all_ready = all_ready and offer_state["livemode"] and bool(link.get("url"))

        for cfg_offer in config.get("offers", []):
            if cfg_offer.get("id") == offer["id"]:
                cfg_offer["checkout_url"] = link["url"]

    config.setdefault("connections", {})["stripe"] = bool(all_ready and paid_offers)
    if config["connections"]["stripe"]:
        config["mode"] = "stripe_live_connected"

    state["mode"] = "live_ready" if config["connections"]["stripe"] else "incomplete"
    state["connected"] = config["connections"]["stripe"]
    save_json(CONFIG_PATH, config)
    save_json(STATE_PATH, state)
    print(f"Stripe live setup complete for {len(paid_offers)} paid offers. connected={state['connected']}")
    return 0 if state["connected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

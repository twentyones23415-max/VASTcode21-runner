#!/usr/bin/env python3
from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "marketing" / "revenue_config.json"
GROWTH = ROOT / "marketing" / "growth_metrics.json"
SUMMARY = ROOT / "status" / "summary.json"
OUT = ROOT / "marketing" / "revenue_status.json"
SITE = ROOT / "site" / "index.html"


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def offer_ready(offer: dict, config: dict) -> tuple[bool, list[str]]:
    reqs = config.get("launch_requirements", {}).get(offer.get("id"), [])
    conns = config.get("connections", {})
    missing = [x for x in reqs if not conns.get(x, False)]
    if offer.get("billing") != "free" and not offer.get("checkout_url"):
        missing.append("checkout_url")
    if offer.get("id") == "mt5-setup-audit" and not offer.get("booking_url"):
        missing.append("booking_url")
    return len(missing) == 0, sorted(set(missing))


def build_site(config: dict, statuses: list[dict]) -> str:
    cards = []
    for s in statuses:
        o = s["offer"]
        ready = s["ready"]
        price = "FREE" if o.get("billing") == "free" else f"€{o.get('price_eur')}" + ("/mo" if o.get("billing") == "monthly" else "")
        if ready:
            if o.get("billing") == "free":
                href = "mailto:vastcode21@gmail.com?subject=VAST%20Early%20Access"
                label = "Join early access"
            else:
                href = o.get("checkout_url", "#")
                label = "Buy now"
            button = f'<a class="btn" href="{html.escape(href)}" rel="noopener">{label}</a>'
        else:
            button = '<span class="btn disabled">Opening soon</span>'
        cards.append(f"""
        <article class="card">
          <div class="tag">{html.escape(o.get('type','').replace('_',' ').upper())}</div>
          <h2>{html.escape(o.get('name',''))}</h2>
          <div class="price">{html.escape(price)}</div>
          <p>{html.escape(o.get('headline',''))}</p>
          <p class="small"><strong>Includes:</strong> {html.escape(o.get('deliverable',''))}</p>
          <p class="small"><strong>Does not include:</strong> {html.escape(o.get('not_included',''))}</p>
          {button}
        </article>
        """)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>VASTcode21 — MT5 Research & Technical Services</title>
<meta name="description" content="VASTcode21 technical MT5 services and research membership. No profit guarantees. VAST remains in validation.">
<style>
body{{font-family:Arial,sans-serif;background:#09111e;color:#eef3f8;margin:0;line-height:1.55}}.wrap{{max-width:1000px;margin:auto;padding:48px 20px}}h1{{font-size:44px;margin:0 0 12px}}.lead{{color:#b8c4d2;font-size:20px;max-width:760px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:18px;margin-top:34px}}.card{{background:#101b2d;border:1px solid #26364d;border-radius:20px;padding:24px}}.tag{{font-size:12px;color:#e1ba56;font-weight:700}}.price{{font-size:32px;font-weight:800;margin:8px 0}}.small{{font-size:14px;color:#b8c4d2}}.btn{{display:inline-block;background:#4acbff;color:#07111d;text-decoration:none;font-weight:800;padding:12px 18px;border-radius:10px;margin-top:10px}}.disabled{{background:#425166;color:#cfd8e3}}.notice{{margin-top:32px;padding:18px;border-left:4px solid #e1ba56;background:#111c2d;color:#c9d4df}}footer{{margin-top:44px;color:#8090a3;font-size:13px}}
</style>
</head><body><main class="wrap">
<h1>VAST<span style="color:#4acbff">code21</span></h1>
<p class="lead">Technical MT5 help and transparent research education for GOLD & BITCOIN system builders. The VAST indicator itself is still under validation and is not being sold yet.</p>
<section class="grid">{''.join(cards)}</section>
<div class="notice"><strong>Risk disclosure:</strong> Trading involves risk. Historical or backtested results do not guarantee future performance. Nothing on this page is financial advice, a signal service, account management, or a promise of profit.</div>
<footer>© VASTcode21 · Paid ads OFF · Live trading OFF · Validation first.</footer>
</main></body></html>"""


def main() -> None:
    config = load(CONFIG)
    growth = load(GROWTH)
    summary = load(SUMMARY)
    statuses = []
    for offer in config.get("offers", []):
        if not offer.get("enabled", False):
            continue
        ready, missing = offer_ready(offer, config)
        statuses.append({"id": offer.get("id"), "ready": ready, "missing": missing, "offer": offer})
    launchable = [x["id"] for x in statuses if x["ready"]]
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "mode": config.get("mode"),
        "followers_count": growth.get("followers_count"),
        "research_experiments": summary.get("experiments"),
        "launchable_offers": launchable,
        "offers": [{"id": x["id"], "ready": x["ready"], "missing": x["missing"]} for x in statuses],
        "vast_indicator_sales_enabled": False,
        "paid_ads": False,
        "live_trading": False,
        "note": "Revenue is a business target, not a guarantee."
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    SITE.parent.mkdir(parents=True, exist_ok=True)
    SITE.write_text(build_site(config, statuses), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()

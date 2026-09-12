from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import social_autopilot_runtime as social
import social_autopilot as core

REPO = Path(__file__).resolve().parents[1]
LOCAL = REPO / "LOCAL_ONLY" / "business"
POLICY_FILE = REPO / "marketing" / "business_policy.json"
STATE_FILE = LOCAL / "state.json"
LEADS_FILE = LOCAL / "leads.json"
ESCALATIONS_FILE = LOCAL / "escalations.json"
GROWTH_FILE = LOCAL / "growth.json"
STATUS_FILE = LOCAL / "business_status.json"
LOG_FILE = LOCAL / "business.log"
VERSION = "3.0.0"


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(message: str) -> None:
    LOCAL.mkdir(parents=True, exist_ok=True)
    line = f"[{utcnow()}] {message}"
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(f"[VASTcode21 Business] {message}", flush=True)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def contains_any(text: str, phrases: list[str]) -> bool:
    value = text.casefold()
    return any(str(p).casefold() in value for p in phrases)


def obvious_spam(text: str) -> bool:
    value = text.casefold()
    markers = (
        "promote it on", "send pic", "dm for promo", "dm me for promo", "investment recovery",
        "recover your funds", "forex signal provider", "guaranteed signals", "whatsapp me",
        "telegram me", "contact my manager", "binary options recovery"
    )
    return any(x in value for x in markers)


def classify(text: str, policy: dict[str, Any]) -> str:
    if not text.strip():
        return "ignore"
    if obvious_spam(text):
        return "spam"
    if contains_any(text, list(policy.get("escalation_keywords", []))):
        return "escalate"
    if contains_any(text, list(policy.get("risk_keywords", []))):
        return "risk"
    if contains_any(text, list(policy.get("interest_keywords", []))):
        return "interest"
    if contains_any(text, list(policy.get("product_keywords", []))):
        return "product"
    if contains_any(text, list(policy.get("positive_keywords", []))):
        return "thanks"
    return "escalate"


def fetch_comments(api_key: str, account_id: str, lookback_days: int) -> list[dict[str, Any]]:
    payload = core.request_json(
        "GET",
        "instagram",
        api_key,
        query={
            "date_preset": f"last_{max(1, lookback_days)}d",
            "fields": "media_id,comment_id,comment_text,comment_timestamp,comment_parent_id,comment_reply_count",
            "select_accounts": account_id,
            "_max_rows": "300",
        },
    )
    rows = payload.get("data", payload if isinstance(payload, list) else [])
    return [x for x in rows if isinstance(x, dict)] if isinstance(rows, list) else []


def reply_comment(api_key: str, connector: str, account_id: str, comment_id: str, message: str) -> Any:
    return core.request_json(
        "POST",
        f"{connector}/actions",
        api_key,
        body={
            "account": account_id,
            "action": "reply_to_comment",
            "params": {"comment_id": comment_id, "message": message},
        },
        timeout=90,
    )


def add_unique(path: Path, item: dict[str, Any], key: str, limit: int = 1000) -> None:
    rows = load_json(path, [])
    if not isinstance(rows, list):
        rows = []
    existing = {str(x.get(key) or "") for x in rows if isinstance(x, dict)}
    if str(item.get(key) or "") not in existing:
        rows.append(item)
    save_json(path, rows[-limit:])


def update_growth() -> dict[str, Any]:
    raw = load_json(core.ANALYTICS_FILE, {})
    profile = raw.get("profile") if isinstance(raw, dict) else []
    media = raw.get("media") if isinstance(raw, dict) else []
    if not isinstance(profile, list):
        profile = []
    if not isinstance(media, list):
        media = []

    followers = None
    media_count = None
    for row in profile:
        if not isinstance(row, dict):
            continue
        if followers is None:
            followers = row.get("followers_count") or row.get("profile_followers_count")
        if media_count is None:
            media_count = row.get("media_count") or row.get("profile_media_count")

    scored: list[dict[str, Any]] = []
    for row in media:
        if not isinstance(row, dict):
            continue
        def num(name: str) -> float:
            try:
                return float(row.get(name) or 0)
            except Exception:
                return 0.0
        score = num("media_engagement") + num("media_like_count") + 2 * num("media_comments_count") + 2 * num("media_saved") + 2 * num("media_shares")
        scored.append({
            "media_id": str(row.get("media_id") or ""),
            "media_type": str(row.get("media_type") or ""),
            "score": score,
            "reach": num("media_reach"),
            "likes": num("media_like_count"),
            "comments": num("media_comments_count"),
            "saved": num("media_saved"),
            "shares": num("media_shares"),
        })
    scored.sort(key=lambda x: x["score"], reverse=True)
    payload = {
        "updated_at": utcnow(),
        "followers": followers,
        "media_count": media_count,
        "top_media": scored[:10],
        "optimization_mode": "organic_zero_cost",
        "rule": "favor verified topics and formats that earn real engagement; never optimize for unsupported profit claims"
    }
    save_json(GROWTH_FILE, payload)
    return payload


def main() -> int:
    LOCAL.mkdir(parents=True, exist_ok=True)
    policy = load_json(POLICY_FILE, {})
    if not policy:
        log("idle: business policy missing")
        return 0
    if bool(policy.get("paid_ads", False)) or bool(policy.get("live_trading", False)) or bool(policy.get("sales_enabled", False)):
        log("SAFETY BLOCK: paid ads/live trading/sales must remain OFF in pre-release mode")
        return 4

    try:
        api_key = core.load_key()
        config = social.load_json(social.CONFIG_FILE, social.default_config())
        validated = social.validate_configuration(api_key, config)
    except Exception as exc:
        log(f"connection deferred: {exc}")
        return 0

    connector = str(validated["connector"])
    account_id = str(validated["account"]["account_id"])
    account_name = str(validated["account"]["account_name"])

    state = load_json(STATE_FILE, {})
    handled = set(str(x) for x in state.get("handled_comment_ids", []))
    today = datetime.now().astimezone().date().isoformat()
    if state.get("reply_day") != today:
        state["reply_day"] = today
        state["replies_today"] = 0

    replies_today = int(state.get("replies_today", 0) or 0)
    max_day = int(policy.get("max_comment_replies_per_day", 20) or 20)
    max_cycle = int(policy.get("max_comment_replies_per_cycle", 5) or 5)
    replies_cycle = 0
    observed = 0
    escalated = 0
    leads_added = 0

    try:
        comments = fetch_comments(api_key, account_id, int(policy.get("comment_lookback_days", 7) or 7))
    except Exception as exc:
        comments = []
        log(f"comment scan deferred: {exc}")

    templates = dict(policy.get("reply_templates", {}))
    template_values = {str(v).strip() for v in templates.values() if str(v).strip()}

    for row in comments:
        cid = str(row.get("comment_id") or "").strip()
        text = str(row.get("comment_text") or "").strip()
        parent = str(row.get("comment_parent_id") or "").strip()
        media_id = str(row.get("media_id") or "").strip()
        if not cid or cid in handled:
            continue
        observed += 1

        # Do not create reply loops on replies, and never answer our own known templates.
        if parent or text in template_values:
            handled.add(cid)
            continue

        category = classify(text, policy)
        record = {
            "comment_id": cid,
            "media_id": media_id,
            "text": text,
            "comment_timestamp": row.get("comment_timestamp"),
            "category": category,
            "observed_at": utcnow(),
        }

        if category == "interest":
            lead = dict(record)
            lead.update({"status": "warm_lead_pre_release", "source": "instagram_comment"})
            before = load_json(LEADS_FILE, [])
            before_len = len(before) if isinstance(before, list) else 0
            add_unique(LEADS_FILE, lead, "comment_id")
            after = load_json(LEADS_FILE, [])
            if isinstance(after, list) and len(after) > before_len:
                leads_added += 1

        if category in {"escalate", "spam"}:
            item = dict(record)
            item["status"] = "needs_review" if category == "escalate" else "ignored_spam"
            add_unique(ESCALATIONS_FILE, item, "comment_id")
            if category == "escalate":
                escalated += 1
            handled.add(cid)
            continue

        if not bool(policy.get("auto_reply_comments", True)):
            add_unique(ESCALATIONS_FILE, {**record, "status": "reply_disabled"}, "comment_id")
            handled.add(cid)
            continue

        if replies_cycle >= max_cycle or replies_today >= max_day:
            break

        message = str(templates.get(category) or "").strip()
        if not message:
            handled.add(cid)
            continue
        try:
            reply_comment(api_key, connector, account_id, cid, message)
            replies_cycle += 1
            replies_today += 1
            log(f"replied to Instagram comment {cid} category={category}")
            handled.add(cid)
        except Exception as exc:
            add_unique(ESCALATIONS_FILE, {**record, "status": "reply_error", "error": str(exc)}, "comment_id")
            log(f"reply deferred for comment {cid}: {exc}")
            handled.add(cid)

    state.update({
        "version": VERSION,
        "updated_at": utcnow(),
        "account_name": account_name,
        "account_id": account_id,
        "handled_comment_ids": list(handled)[-3000:],
        "reply_day": today,
        "replies_today": replies_today,
        "paid_ads": False,
        "live_trading": False,
        "sales_enabled": False,
        "auto_dm": False,
    })
    save_json(STATE_FILE, state)
    growth = update_growth()
    status = {
        "version": VERSION,
        "updated_at": utcnow(),
        "instagram": account_name,
        "comments_observed_this_cycle": observed,
        "comment_replies_this_cycle": replies_cycle,
        "comment_replies_today": replies_today,
        "new_warm_leads_this_cycle": leads_added,
        "new_escalations_this_cycle": escalated,
        "followers": growth.get("followers"),
        "auto_posting": True,
        "auto_comment_replies": bool(policy.get("auto_reply_comments", True)),
        "auto_dm": False,
        "auto_dm_reason": "Windsor Instagram write actions do not expose private-message actions; official Meta Messaging API setup is required before DM automation can be enabled.",
        "paid_ads": False,
        "live_trading": False,
        "sales_enabled": False,
    }
    save_json(STATUS_FILE, status)
    log(f"cycle complete: observed={observed} replied={replies_cycle} leads={leads_added} escalations={escalated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

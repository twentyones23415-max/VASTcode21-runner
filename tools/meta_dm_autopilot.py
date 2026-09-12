from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import business_autopilot as business
import social_autopilot as social

REPO = Path(__file__).resolve().parents[1]
LOCAL = REPO / "LOCAL_ONLY" / "meta_dm"
TOKEN_FILE = LOCAL / "instagram_access_token.bin"
SETUP_STATE_FILE = LOCAL / "state.json"
RUNTIME_STATE_FILE = LOCAL / "runtime_state.json"
STATUS_FILE = LOCAL / "runtime_status.json"
LOG_FILE = LOCAL / "meta_dm.log"
INBOX_FILE = LOCAL / "inbox.jsonl"

POLICY_FILE = REPO / "marketing" / "business_policy.json"
GRAPH_BASE = "https://graph.instagram.com/v26.0"
VERSION = "3.1.0"


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(message: str) -> None:
    LOCAL.mkdir(parents=True, exist_ok=True)
    line = f"[{utcnow()}] {message}"
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(f"[VASTcode21 Meta DM] {message}", flush=True)


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


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def redact(text: str, secret: str) -> str:
    value = str(text)
    return value.replace(secret, "[REDACTED]") if secret else value


def load_token() -> str:
    if not TOKEN_FILE.exists():
        raise RuntimeError("Meta Instagram token is not configured")
    token = social.unprotect_secret(TOKEN_FILE.read_bytes()).strip()
    if len(token) < 20:
        raise RuntimeError("Meta Instagram token storage is invalid")
    return token


def meta_request(
    method: str,
    path: str,
    token: str,
    *,
    query: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: int = 45,
) -> Any:
    url = f"{GRAPH_BASE}/{path.lstrip('/')}"
    if query:
        url += "?" + urllib.parse.urlencode(query)
    data = None
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "VASTcode21-Meta-DM-Autopilot/3.1",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")[:1600]
        raise RuntimeError(redact(f"Meta HTTP {exc.code}: {raw}", token)) from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Meta network error: {exc.reason}") from None


def parse_time(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def account_check(token: str) -> dict[str, str]:
    payload = meta_request("GET", "me", token, query={"fields": "id,username"})
    account_id = str(payload.get("id") or "").strip()
    username = str(payload.get("username") or "").strip()
    if not account_id or not username:
        raise RuntimeError("Meta account check did not return id and username")
    if username.casefold() != "vast.code21":
        raise RuntimeError(f"Meta token belongs to '{username}', not vast.code21")
    return {"account_id": account_id, "username": username}


def list_conversations(token: str, account_id: str) -> list[dict[str, Any]]:
    last_error: Exception | None = None
    for owner in (account_id, "me"):
        try:
            payload = meta_request(
                "GET",
                f"{owner}/conversations",
                token,
                query={"fields": "id,updated_time", "limit": "50"},
            )
            rows = payload.get("data", []) if isinstance(payload, dict) else []
            return [x for x in rows if isinstance(x, dict)] if isinstance(rows, list) else []
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Could not read Instagram conversations: {last_error}")


def list_messages(token: str, conversation_id: str) -> list[dict[str, Any]]:
    try:
        payload = meta_request(
            "GET",
            f"{conversation_id}/messages",
            token,
            query={"fields": "id,created_time,from,to,message", "limit": "25"},
        )
        rows = payload.get("data", []) if isinstance(payload, dict) else []
        if isinstance(rows, list):
            return [x for x in rows if isinstance(x, dict)]
    except Exception:
        pass

    payload = meta_request(
        "GET",
        conversation_id,
        token,
        query={"fields": "messages.limit(25){id,created_time,from,to,message}"},
    )
    messages = payload.get("messages", {}) if isinstance(payload, dict) else {}
    rows = messages.get("data", []) if isinstance(messages, dict) else []
    return [x for x in rows if isinstance(x, dict)] if isinstance(rows, list) else []


def sender_info(message: dict[str, Any]) -> tuple[str, str]:
    raw = message.get("from")
    if not isinstance(raw, dict):
        return "", ""
    sender_id = str(raw.get("id") or "").strip()
    sender_name = str(raw.get("username") or raw.get("name") or "").strip()
    return sender_id, sender_name


def is_ours(message: dict[str, Any], account_id: str, username: str) -> bool:
    sender_id, sender_name = sender_info(message)
    if sender_id and sender_id == account_id:
        return True
    return bool(sender_name and sender_name.casefold() == username.casefold())


def newest_message(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None

    def key(row: dict[str, Any]) -> tuple[int, str]:
        dt = parse_time(row.get("created_time"))
        stamp = int(dt.timestamp()) if dt else 0
        return stamp, str(row.get("id") or "")

    return max(rows, key=key)


def send_text(token: str, account_id: str, recipient_id: str, text: str) -> dict[str, Any]:
    if not recipient_id:
        raise RuntimeError("Missing Instagram-scoped recipient id")
    payload = meta_request(
        "POST",
        f"{account_id}/messages",
        token,
        body={"recipient": {"id": recipient_id}, "message": {"text": text}},
    )
    return payload if isinstance(payload, dict) else {}


def dm_category(text: str, policy: dict[str, Any]) -> str:
    value = text.casefold()
    dm_escalations = [str(x).casefold() for x in policy.get("dm_escalation_keywords", [])]
    if any(x and x in value for x in dm_escalations):
        return "escalate"
    return business.classify(text, policy)


def add_business_record(path: Path, record: dict[str, Any], key: str = "message_id") -> bool:
    before = business.load_json(path, [])
    before_len = len(before) if isinstance(before, list) else 0
    business.add_unique(path, record, key)
    after = business.load_json(path, [])
    return isinstance(after, list) and len(after) > before_len


def write_status(**kwargs: Any) -> None:
    payload = {
        "version": VERSION,
        "updated_at": utcnow(),
        "mode": "official_meta_instagram_login",
        "account": "vast.code21",
        "auto_dm": True,
        "cold_dm": False,
        "paid_ads": False,
        "live_trading": False,
        "sales_enabled": False,
        **kwargs,
    }
    save_json(STATUS_FILE, payload)

    # Keep the existing Business Autopilot status truthful without rebuilding it.
    business_status = business.load_json(business.STATUS_FILE, {})
    if isinstance(business_status, dict):
        business_status.update(
            {
                "updated_at": payload["updated_at"],
                "auto_dm": bool(payload.get("auto_dm", False) and payload.get("ready", False)),
                "meta_dm_ready": bool(payload.get("ready", False)),
                "auto_dm_reason": (
                    "Official Meta Instagram Messaging API configured. "
                    "Replies are restricted to user-initiated conversations; cold DMs are disabled."
                    if payload.get("ready", False)
                    else str(payload.get("check_error") or payload.get("reason") or "Meta DM not ready")
                ),
                "paid_ads": False,
                "live_trading": False,
                "sales_enabled": False,
            }
        )
        business.save_json(business.STATUS_FILE, business_status)


def run_check() -> int:
    try:
        token = load_token()
        account = account_check(token)
        conversations = list_conversations(token, account["account_id"])
    except Exception as exc:
        write_status(ready=False, check_error=str(exc))
        print(f"ERROR: {exc}")
        return 2

    write_status(
        ready=True,
        account_id=account["account_id"],
        username=account["username"],
        conversations_visible=len(conversations),
        check_error=None,
    )
    print(f"SUCCESS: Meta DM API ready for '{account['username']}'.")
    print(f"Conversations visible: {len(conversations)}")
    print("Cold DMs: OFF | Paid ads: OFF | Live trading: OFF | Sales: OFF")
    return 0


def run_cycle() -> int:
    LOCAL.mkdir(parents=True, exist_ok=True)
    policy = load_json(POLICY_FILE, {})
    if not isinstance(policy, dict) or not policy:
        log("idle: business policy missing")
        return 0

    if bool(policy.get("paid_ads", False)) or bool(policy.get("live_trading", False)) or bool(policy.get("sales_enabled", False)):
        log("SAFETY BLOCK: paid ads/live trading/sales must remain OFF")
        return 4

    if not bool(policy.get("auto_dm", False)):
        write_status(ready=True, auto_dm=False, reason="policy_disabled")
        log("idle: Meta DM automation disabled by policy")
        return 0

    try:
        token = load_token()
        account = account_check(token)
        conversations = list_conversations(token, account["account_id"])
    except Exception as exc:
        write_status(ready=False, check_error=str(exc))
        log(f"cycle deferred: {exc}")
        return 0

    state = load_json(RUNTIME_STATE_FILE, {})
    if not isinstance(state, dict):
        state = {}
    handled = set(str(x) for x in state.get("handled_message_ids", []) if str(x))

    today = datetime.now().astimezone().date().isoformat()
    if state.get("reply_day") != today:
        state["reply_day"] = today
        state["replies_today"] = 0

    replies_today = int(state.get("replies_today", 0) or 0)
    max_day = int(policy.get("max_dm_replies_per_day", 12) or 12)
    max_cycle = int(policy.get("max_dm_replies_per_cycle", 3) or 3)
    replies_cycle = 0
    observed = 0
    escalated = 0
    leads_added = 0
    skipped_history = 0

    setup = load_json(SETUP_STATE_FILE, {})
    activation_text = str(state.get("activation_at") or setup.get("configured_at") or utcnow())
    activation_at = parse_time(activation_text) or datetime.now(timezone.utc)
    state["activation_at"] = activation_at.isoformat()

    templates = policy.get("dm_reply_templates")
    if not isinstance(templates, dict):
        templates = policy.get("reply_templates", {})
    if not isinstance(templates, dict):
        templates = {}

    for conversation in conversations:
        conversation_id = str(conversation.get("id") or "").strip()
        if not conversation_id:
            continue
        try:
            messages = list_messages(token, conversation_id)
        except Exception as exc:
            log(f"conversation read deferred {conversation_id}: {exc}")
            continue

        latest = newest_message(messages)
        if not latest:
            continue

        message_id = str(latest.get("id") or "").strip()
        if not message_id or message_id in handled:
            continue

        if is_ours(latest, account["account_id"], account["username"]):
            handled.add(message_id)
            continue

        sender_id, sender_name = sender_info(latest)
        created_at = parse_time(latest.get("created_time"))
        text = str(latest.get("message") or "").strip()

        record = {
            "message_id": message_id,
            "conversation_id": conversation_id,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "text": text,
            "created_time": latest.get("created_time"),
            "observed_at": utcnow(),
            "source": "instagram_dm",
        }
        append_jsonl(INBOX_FILE, record)
        observed += 1

        # Never auto-reply to historical inbox content from before secure Meta DM activation.
        if created_at and created_at < activation_at:
            handled.add(message_id)
            skipped_history += 1
            continue

        if not sender_id:
            add_business_record(
                business.ESCALATIONS_FILE,
                {**record, "category": "escalate", "status": "needs_review_missing_sender"},
            )
            handled.add(message_id)
            escalated += 1
            continue

        if not text:
            add_business_record(
                business.ESCALATIONS_FILE,
                {**record, "category": "escalate", "status": "needs_review_non_text_dm"},
            )
            handled.add(message_id)
            escalated += 1
            continue

        category = dm_category(text, policy)
        record["category"] = category

        if category == "interest":
            lead = {**record, "status": "warm_lead_pre_release"}
            if add_business_record(business.LEADS_FILE, lead):
                leads_added += 1

        if category in {"escalate", "spam"}:
            status = "needs_review" if category == "escalate" else "ignored_spam"
            add_business_record(business.ESCALATIONS_FILE, {**record, "status": status})
            if category == "escalate":
                escalated += 1
            handled.add(message_id)
            continue

        if replies_cycle >= max_cycle or replies_today >= max_day:
            add_business_record(
                business.ESCALATIONS_FILE,
                {**record, "status": "deferred_rate_limit"},
            )
            continue

        reply = str(templates.get(category) or "").strip()
        if not reply:
            add_business_record(
                business.ESCALATIONS_FILE,
                {**record, "status": "needs_review_no_template"},
            )
            handled.add(message_id)
            escalated += 1
            continue

        # Recipient always comes from a user-originated inbound message.
        # There is intentionally no API path in this program for cold outreach.
        try:
            result = send_text(token, account["account_id"], sender_id, reply)
            handled.add(message_id)
            replies_cycle += 1
            replies_today += 1
            log(
                f"replied to user-initiated Instagram DM {message_id} "
                f"category={category} sent_id={str(result.get('message_id') or '')[:40]}"
            )
        except Exception as exc:
            add_business_record(
                business.ESCALATIONS_FILE,
                {**record, "status": "reply_error", "error": str(exc)},
            )
            handled.add(message_id)
            log(f"DM reply deferred {message_id}: {exc}")

    state.update(
        {
            "version": VERSION,
            "updated_at": utcnow(),
            "account_id": account["account_id"],
            "username": account["username"],
            "handled_message_ids": list(handled)[-5000:],
            "reply_day": today,
            "replies_today": replies_today,
            "cold_dm": False,
            "paid_ads": False,
            "live_trading": False,
            "sales_enabled": False,
        }
    )
    save_json(RUNTIME_STATE_FILE, state)
    write_status(
        ready=True,
        account_id=account["account_id"],
        username=account["username"],
        conversations_visible=len(conversations),
        inbound_observed_this_cycle=observed,
        replies_this_cycle=replies_cycle,
        replies_today=replies_today,
        new_warm_leads_this_cycle=leads_added,
        new_escalations_this_cycle=escalated,
        historical_messages_skipped_this_cycle=skipped_history,
        check_error=None,
    )
    log(
        f"cycle complete: conversations={len(conversations)} observed={observed} "
        f"replied={replies_cycle} leads={leads_added} escalations={escalated} "
        f"historical_skipped={skipped_history}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Validate Meta DM read access without sending messages")
    args = parser.parse_args()
    return run_check() if args.check else run_cycle()


if __name__ == "__main__":
    raise SystemExit(main())

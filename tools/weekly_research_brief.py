#!/usr/bin/env python3
import base64
import html
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
MAILCHIMP_STATE_PATH = ROOT / "marketing" / "mailchimp_state.json"
SUBSCRIBER_STATE_PATH = ROOT / "marketing" / "subscriber_sync_state.json"
BRIEF_STATE_PATH = ROOT / "marketing" / "research_brief_state.json"
SUMMARY_PATH = ROOT / "status" / "summary.json"
AUTONOMY_PATH = ROOT / "status" / "autonomy.json"
MAILCHIMP_KEY = os.getenv("MAILCHIMP_API_KEY", "").strip()
TAG_NAME = "Research Brief Subscriber"
CONNECTION_NAME = "weekly_research_brief"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def week_key():
    y, w, _ = datetime.now(timezone.utc).isocalendar()
    return f"{y}-W{w:02d}"


def load_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def data_center():
    return MAILCHIMP_KEY.rsplit("-", 1)[-1].strip() if "-" in MAILCHIMP_KEY else ""


def request(method, endpoint, payload=None):
    dc = data_center()
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


def set_delivery_connection(config, value):
    conns = config.setdefault("connections", {})
    conns[CONNECTION_NAME] = bool(value)
    reqs = config.setdefault("launch_requirements", {}).setdefault("research-brief", [])
    if CONNECTION_NAME not in reqs:
        reqs.append(CONNECTION_NAME)


def fmt_score(value):
    try:
        return f"{float(value):.4f}"
    except Exception:
        return "n/a"


def build_html(summary, autonomy, wk):
    candidates = autonomy.get("candidates") or []
    candidate_rows = ""
    for c in candidates[:5]:
        candidate_rows += (
            "<tr>"
            f"<td>{html.escape(str(c.get('experiment_id', '—')))}</td>"
            f"<td>{html.escape(str(c.get('asset', '—')))}</td>"
            f"<td>{html.escape(str(c.get('timeframe', '—')))}</td>"
            f"<td>{html.escape(str(c.get('mt5', '—')))}</td>"
            f"<td>{html.escape(str(c.get('robustness', '—')))}</td>"
            f"<td>{html.escape(str(c.get('forward', '—')))}</td>"
            "</tr>"
        )
    if not candidate_rows:
        candidate_rows = '<tr><td colspan="6">No active validation candidate this week.</td></tr>'

    pending = summary.get("pending_mt5_by_asset") or {}
    pending_text = ", ".join(f"{k}: {v}" for k, v in pending.items()) or "None"

    return f"""<!doctype html>
<html><body style="margin:0;background:#0b1220;color:#eef3f8;font-family:Arial,sans-serif;line-height:1.6">
<div style="max-width:720px;margin:0 auto;padding:30px 20px">
  <div style="font-size:13px;letter-spacing:.12em;color:#69d2ff;font-weight:700">VASTCODE21 RESEARCH BRIEF · {html.escape(wk)}</div>
  <h1 style="font-size:30px;margin:8px 0 12px">Validation progress, without hype.</h1>
  <p style="color:#bdc8d6">This weekly note summarizes verified VASTcode21 research state. It is educational research content, not a trading signal, investment advice, account management, or a promise of profit.</p>

  <div style="background:#121d30;border:1px solid #2a3b55;border-radius:14px;padding:20px;margin:22px 0">
    <h2 style="margin-top:0;font-size:20px">Research snapshot</h2>
    <table style="width:100%;border-collapse:collapse;color:#eef3f8">
      <tr><td>Experiments</td><td style="text-align:right"><strong>{summary.get('experiments', 0)}</strong></td></tr>
      <tr><td>Cloud pass</td><td style="text-align:right"><strong>{summary.get('cloud_pass', 0)}</strong></td></tr>
      <tr><td>MT5 validation passed</td><td style="text-align:right"><strong>{summary.get('mt5_validation_passed', 0)}</strong></td></tr>
      <tr><td>MT5 validation rejected</td><td style="text-align:right"><strong>{summary.get('mt5_validation_rejected', 0)}</strong></td></tr>
      <tr><td>Pending MT5 validation</td><td style="text-align:right"><strong>{summary.get('pending_mt5_validation', 0)}</strong></td></tr>
      <tr><td>Best score</td><td style="text-align:right"><strong>{fmt_score(summary.get('best_score'))}</strong></td></tr>
      <tr><td>Best MT5-pass score</td><td style="text-align:right"><strong>{fmt_score(summary.get('best_mt5_pass_score'))}</strong></td></tr>
      <tr><td>Max generation</td><td style="text-align:right"><strong>{summary.get('max_generation', 0)}</strong></td></tr>
    </table>
    <p style="margin-bottom:0;color:#bdc8d6"><strong>Pending by asset:</strong> {html.escape(pending_text)}</p>
  </div>

  <div style="background:#121d30;border:1px solid #2a3b55;border-radius:14px;padding:20px;margin:22px 0">
    <h2 style="margin-top:0;font-size:20px">Validation pipeline</h2>
    <table style="width:100%;border-collapse:collapse;color:#eef3f8;font-size:14px">
      <tr style="color:#93a4b8"><th align="left">Exp</th><th align="left">Asset</th><th align="left">TF</th><th align="left">MT5</th><th align="left">Robust</th><th align="left">Forward</th></tr>
      {candidate_rows}
    </table>
    <p style="color:#bdc8d6">Robustness passed: <strong>{autonomy.get('robustness_passed', 0)}</strong> · Forward collecting: <strong>{autonomy.get('forward_collecting', 0)}</strong> · Release candidates: <strong>{autonomy.get('release_candidates', 0)}</strong></p>
  </div>

  <div style="background:#172136;border-left:4px solid #e3bb55;padding:16px 18px;margin:22px 0">
    <strong>What this means:</strong> passing one stage is not a release decision. VAST remains in validation until robustness and forward criteria are satisfied. Historical, backtest, or validation results do not guarantee future performance.
  </div>

  <p style="color:#8798ac;font-size:12px">VAST indicator sales remain disabled while validation is incomplete. Paid ads and live trading remain disabled in the VASTcode21 automation stack.</p>
</div>
</body></html>"""


def main():
    config = load_json(CONFIG_PATH, {})
    mailchimp_state = load_json(MAILCHIMP_STATE_PATH, {})
    subscriber_state = load_json(SUBSCRIBER_STATE_PATH, {})
    summary = load_json(SUMMARY_PATH, {})
    autonomy = load_json(AUTONOMY_PATH, {})
    state = load_json(BRIEF_STATE_PATH, {})
    wk = week_key()
    state.update({
        "updated_at": now_iso(),
        "provider": "mailchimp",
        "tag": TAG_NAME,
        "week": wk,
        "paid_ads": False,
        "live_trading": False,
    })

    if not MAILCHIMP_KEY:
        set_delivery_connection(config, False)
        state.update({"delivery_ready": False, "mode": "waiting_for_mailchimp_api_key", "last_error": ""})
        save_json(CONFIG_PATH, config)
        save_json(BRIEF_STATE_PATH, state)
        print("Weekly Research Brief waiting for MAILCHIMP_API_KEY.")
        return 0

    list_id = str(mailchimp_state.get("audience_id") or "").strip()
    tag_info = (mailchimp_state.get("tags") or {}).get(TAG_NAME) or {}
    tag_id = tag_info.get("id")
    if not list_id or not tag_id:
        set_delivery_connection(config, False)
        state.update({"delivery_ready": False, "mode": "waiting_for_mailchimp_state", "last_error": "Missing audience or Research Brief tag."})
        save_json(CONFIG_PATH, config)
        save_json(BRIEF_STATE_PATH, state)
        return 0

    try:
        ping = request("GET", "/ping")
        audience = request("GET", f"/lists/{urllib.parse.quote(list_id)}")
        segment = request("GET", f"/lists/{urllib.parse.quote(list_id)}/segments/{tag_id}")
        defaults = audience.get("campaign_defaults") or {}
        from_name = str(defaults.get("from_name") or "VASTcode21").strip()
        reply_to = str(defaults.get("from_email") or "").strip()
        if not reply_to:
            raise RuntimeError("Mailchimp audience has no default sender email configured.")

        set_delivery_connection(config, True)
        state.update({
            "delivery_ready": True,
            "connected": True,
            "health": ping.get("health_status"),
            "segment_member_count": int(segment.get("member_count") or 0),
            "active_subscribers": int(subscriber_state.get("active_subscribers") or 0),
            "last_error": "",
        })

        if state.get("last_sent_week") == wk:
            state["mode"] = "already_sent_this_week"
            save_json(CONFIG_PATH, config)
            save_json(BRIEF_STATE_PATH, state)
            print(f"Research Brief already sent for {wk}; duplicate blocked.")
            return 0

        if state["active_subscribers"] <= 0 or state["segment_member_count"] <= 0:
            state["mode"] = "ready_no_subscribers"
            save_json(CONFIG_PATH, config)
            save_json(BRIEF_STATE_PATH, state)
            print("Weekly Research Brief delivery is ready; no active subscribers, so no campaign was sent.")
            return 0

        subject = f"VASTcode21 Research Brief — {wk}"
        campaign = request("POST", "/campaigns", {
            "type": "regular",
            "recipients": {
                "list_id": list_id,
                "segment_opts": {"saved_segment_id": int(tag_id)},
            },
            "settings": {
                "subject_line": subject,
                "preview_text": "Verified VASTcode21 MT5 validation progress, robustness and forward status.",
                "title": subject,
                "from_name": from_name,
                "reply_to": reply_to,
                "auto_footer": True,
                "inline_css": True,
            },
        })
        campaign_id = campaign["id"]
        request("PUT", f"/campaigns/{campaign_id}/content", {"html": build_html(summary, autonomy, wk)})
        checklist = request("GET", f"/campaigns/{campaign_id}/send-checklist")
        if not checklist.get("is_ready", False):
            issues = []
            for item in checklist.get("items", []):
                if item.get("type") in {"error", "warning"} and item.get("details"):
                    issues.append(str(item.get("details")))
            try:
                request("DELETE", f"/campaigns/{campaign_id}")
            except Exception:
                pass
            raise RuntimeError("Mailchimp send checklist not ready: " + "; ".join(issues[:5]))

        request("POST", f"/campaigns/{campaign_id}/actions/send")
        state.update({
            "mode": "sent",
            "last_sent_week": wk,
            "last_sent_at": now_iso(),
            "last_campaign_id": campaign_id,
            "last_subject": subject,
        })
        save_json(CONFIG_PATH, config)
        save_json(BRIEF_STATE_PATH, state)
        print(f"Weekly Research Brief sent successfully for {wk}.")
        return 0
    except Exception as exc:
        set_delivery_connection(config, False)
        state.update({"delivery_ready": False, "connected": False, "mode": "error", "last_error": str(exc)[:500]})
        save_json(CONFIG_PATH, config)
        save_json(BRIEF_STATE_PATH, state)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

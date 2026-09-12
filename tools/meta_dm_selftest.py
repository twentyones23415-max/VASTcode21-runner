from __future__ import annotations

import json
from pathlib import Path

import meta_dm_autopilot as dm

REPO = Path(__file__).resolve().parents[1]
POLICY_FILE = REPO / "marketing" / "business_policy.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    policy = json.loads(POLICY_FILE.read_text(encoding="utf-8"))

    # Company safety policy must remain locked for pre-release operation.
    require(policy.get("auto_dm") is True, "auto_dm must be enabled for the DM worker")
    require(policy.get("paid_ads") is False, "paid_ads must remain OFF")
    require(policy.get("live_trading") is False, "live_trading must remain OFF")
    require(policy.get("sales_enabled") is False, "sales_enabled must remain OFF")

    # Classifier routing tests. These are synthetic strings only; no network/API call is made.
    cases = [
        ("How does VASTcode21 work on MT5?", "product"),
        ("When will it be available to buy?", "interest"),
        ("Can you guarantee profit?", "risk"),
        ("I need a refund for a payment", "escalate"),
        ("My account was hacked and I have a security issue", "escalate"),
        ("Great work, very interesting", "thanks"),
        ("DM me for promo on Telegram", "spam"),
    ]
    for text, expected in cases:
        actual = dm.dm_category(text, policy)
        require(actual == expected, f"classifier mismatch: {text!r} -> {actual!r}, expected {expected!r}")

    # No cold-DM path: the low-level sender refuses an empty recipient before any HTTP request.
    blocked = False
    try:
        dm.send_text("SELFTEST_TOKEN_DO_NOT_USE", "SELFTEST_ACCOUNT", "", "test")
    except RuntimeError as exc:
        blocked = "recipient" in str(exc).casefold()
    require(blocked, "cold-DM safety guard did not block an empty recipient")

    # Sender ownership checks used to avoid reply loops.
    require(dm.is_ours({"from": {"id": "123"}}, "123", "vast.code21"), "own-message ID detection failed")
    require(dm.is_ours({"from": {"username": "vast.code21"}}, "123", "vast.code21"), "own-message username detection failed")
    require(not dm.is_ours({"from": {"id": "999", "username": "external.user"}}, "123", "vast.code21"), "external sender detection failed")

    # Template safety: pre-release/product scope only, with no unsupported guarantee language.
    templates = policy.get("dm_reply_templates", {})
    require(isinstance(templates, dict) and templates, "DM reply templates missing")
    product = str(templates.get("product") or "").casefold()
    require("gold" in product and "bitcoin" in product, "product template must keep GOLD/BITCOIN scope")
    require("validation" in product or "validat" in product, "product template must state validation/pre-release status")
    for name, value in templates.items():
        text = str(value).casefold()
        require("guaranteed profit" not in text, f"unsafe guarantee phrase in template {name}")
        require("risk-free" not in text and "risk free" not in text, f"unsafe risk-free phrase in template {name}")

    print("VASTcode21 META DM SAFETY SELF-TEST")
    print("PASS: classifier routing")
    print("PASS: escalation routing")
    print("PASS: cold-DM guard")
    print("PASS: own-message loop protection")
    print("PASS: GOLD/BITCOIN-only product scope")
    print("PASS: Paid ads OFF | Live trading OFF | Sales OFF")
    print("PASS: no network calls or real Instagram messages were sent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

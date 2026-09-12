from __future__ import annotations

import getpass
import json
from pathlib import Path

import social_autopilot as sa


def normalize_key(value: str) -> tuple[str, bool]:
    key = value.strip()
    # Common console paste mistake: the exact API key is pasted twice back-to-back.
    # Collapse only when the two halves are byte-for-byte identical.
    if len(key) >= 24 and len(key) % 2 == 0:
        half = len(key) // 2
        if key[:half] == key[half:]:
            return key[:half], True
    return key, False


def sanitize(message: str, secret: str) -> str:
    text = str(message)
    if secret:
        text = text.replace(secret, "[REDACTED]")
    return text


def main() -> None:
    config = sa.load_json(sa.CONFIG_FILE, sa.default_config())
    print("VASTcode21 Social Autopilot v2.1 secure configuration")
    print("The Windsor API key stays local and is stored with Windows DPAPI encryption.")
    print("It will not be printed or committed to GitHub.\n")

    raw = getpass.getpass("Paste NEW Windsor API key once (hidden input) and press Enter: ")
    key, duplicate = normalize_key(raw)
    if duplicate:
        print("Detected an accidental duplicate paste; using one copy of the key.")
    if len(key) < 12:
        raise SystemExit("ERROR: API key looks invalid.")

    try:
        result = sa.validate_configuration(key, config)
    except Exception as exc:
        # Never echo a credential even if the remote API includes it in an error body.
        raise SystemExit("ERROR: " + sanitize(str(exc), key)) from None

    sa.store_key(key)
    state = sa.load_json(sa.STATE_FILE, {})
    state.update({
        "version": sa.VERSION,
        "configured_at": sa.iso_now(),
        "account_id": result["account"]["account_id"],
        "account_name": result["account"]["account_name"],
        "connector": result["connector"],
        "write_action_ready": True,
        "paid_ads": False,
        "live_trading": False,
    })
    sa.save_json(sa.STATE_FILE, state)
    print(f"SUCCESS: Instagram account '{state['account_name']}' is ready for organic posting.")
    print("Paid ads: OFF | Live trading: OFF")


if __name__ == "__main__":
    main()

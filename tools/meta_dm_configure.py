from __future__ import annotations

import getpass
import json
import urllib.error
import urllib.request
from pathlib import Path

import social_autopilot as social

REPO = Path(__file__).resolve().parents[1]
LOCAL = REPO / "LOCAL_ONLY" / "meta_dm"
TOKEN_FILE = LOCAL / "instagram_access_token.bin"
STATE_FILE = LOCAL / "state.json"


def redact(text: str, secret: str) -> str:
    value = str(text)
    return value.replace(secret, "[REDACTED]") if secret else value


def validate_token(token: str) -> dict[str, str]:
    req = urllib.request.Request(
        "https://graph.instagram.com/me?fields=id,username",
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "VASTcode21-DM-Autopilot/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:1200]
        raise RuntimeError(redact(f"Meta HTTP {exc.code}: {body}", token)) from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Meta network error: {exc.reason}") from None

    account_id = str(payload.get("id") or "").strip()
    username = str(payload.get("username") or "").strip()
    if not account_id or not username:
        raise RuntimeError("Meta token validation did not return Instagram id and username")
    return {"account_id": account_id, "username": username}


def main() -> None:
    print("VASTcode21 META DM SECURE SETUP")
    print("The Instagram access token stays on this Windows account and is encrypted with DPAPI.")
    print("It is never printed or committed to GitHub.\n")

    token = getpass.getpass("Paste the Meta Instagram access token once (hidden input), then press Enter: ").strip()
    if len(token) < 20:
        raise SystemExit("ERROR: token looks invalid.")

    try:
        account = validate_token(token)
    except Exception as exc:
        raise SystemExit("ERROR: " + redact(str(exc), token)) from None

    if account["username"].casefold() != "vast.code21":
        raise SystemExit(f"ERROR: token belongs to Instagram account '{account['username']}', not vast.code21.")

    LOCAL.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_bytes(social.protect_secret(token))
    STATE_FILE.write_text(
        json.dumps(
            {
                "configured_at": social.iso_now(),
                "instagram_account_id": account["account_id"],
                "instagram_username": account["username"],
                "token_storage": "windows_dpapi_local_only",
                "paid_ads": False,
                "live_trading": False,
                "sales": False,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"SUCCESS: Meta Instagram token validated for '{account['username']}'.")
    print("Token storage: Windows DPAPI / LOCAL_ONLY")
    print("Paid ads: OFF | Live trading: OFF | Sales: OFF")


if __name__ == "__main__":
    main()

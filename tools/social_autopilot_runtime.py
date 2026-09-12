from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import social_autopilot as core

# Re-export the stable pieces used by the secure configurator.
CONFIG_FILE = core.CONFIG_FILE
STATE_FILE = core.STATE_FILE
VERSION = "2.1.1"
load_json = core.load_json
save_json = core.save_json
store_key = core.store_key
iso_now = core.iso_now
default_config = core.default_config

_ORIGINAL_REQUEST_JSON = core.request_json


def _redact(text: str, secret: str) -> str:
    value = str(text)
    if secret:
        value = value.replace(secret, "[REDACTED]")
        value = value.replace(urllib.parse.quote(secret, safe=""), "[REDACTED]")
    return value


def safe_request_json(*args: Any, **kwargs: Any) -> Any:
    api_key = ""
    if len(args) >= 3:
        api_key = str(args[2])
    elif "api_key" in kwargs:
        api_key = str(kwargs.get("api_key") or "")
    try:
        return _ORIGINAL_REQUEST_JSON(*args, **kwargs)
    except Exception as exc:
        raise RuntimeError(_redact(str(exc), api_key)) from None


# Harden all subsequent connector requests made by the original engine.
core.request_json = safe_request_json


def _connected_accounts(api_key: str) -> list[dict[str, str]]:
    """Return Windsor's connected-account selectors for Instagram.

    Instagram's read field `account_id` is an alias of the Instagram user id,
    but Windsor's `select_accounts` expects the connected-account id shown in
    Windsor's Data Sources page. Those values can differ. The onboarding
    accounts endpoint exposes the selector ids directly.
    """
    url = (
        "https://onboard.windsor.ai/api/ds/accounts/instagram?"
        + urllib.parse.urlencode({"api_key": api_key})
    )
    req = urllib.request.Request(url, headers={"User-Agent": "VASTcode21-Social-Autopilot/2.1.1"})
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(_redact(f"Windsor accounts HTTP {exc.code}: {raw[:1000]}", api_key)) from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Windsor accounts network error: {exc.reason}") from None

    candidates: list[dict[str, str]] = []

    def walk(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                walk(item)
            return
        if not isinstance(value, dict):
            return

        raw_id = value.get("id") or value.get("account_id") or value.get("accountId")
        raw_name = (
            value.get("name")
            or value.get("account_name")
            or value.get("accountName")
            or value.get("username")
            or value.get("user_name")
        )
        if raw_id is not None:
            account_id = str(raw_id).strip()
            account_name = str(raw_name or "").strip()
            if account_id:
                candidates.append({"account_id": account_id, "account_name": account_name})

        for child in value.values():
            if isinstance(child, (dict, list)):
                walk(child)

    walk(payload)

    dedup: dict[str, dict[str, str]] = {}
    for item in candidates:
        existing = dedup.get(item["account_id"])
        if existing is None or (not existing.get("account_name") and item.get("account_name")):
            dedup[item["account_id"]] = item
    return list(dedup.values())


def discover_instagram_account(api_key: str, preferred_name: str) -> dict[str, str]:
    wanted = preferred_name.casefold().strip()
    try:
        accounts = _connected_accounts(api_key)
    except Exception:
        accounts = []

    if accounts:
        for item in accounts:
            if str(item.get("account_name") or "").casefold().strip() == wanted:
                return item
        if len(accounts) == 1:
            return accounts[0]

    # Fail-safe fallback for Windsor deployments where the onboarding endpoint
    # does not expose account selectors. This preserves prior behaviour.
    return core.discover_instagram_account(api_key, preferred_name)


def validate_configuration(api_key: str, config: dict[str, Any]) -> dict[str, Any]:
    connector, actions = core.list_actions(api_key)
    action_ids = {str(a.get("id") or "") for a in actions}
    if "create_image_post" not in action_ids:
        raise RuntimeError("Instagram create_image_post write action is not available/enabled in Windsor")
    account = discover_instagram_account(api_key, str(config.get("account_name") or "vast.code21"))
    return {"connector": connector, "account": account, "actions": sorted(action_ids)}


# Patch the original engine so dry-run, analytics and publishing all use the
# connected-account selector rather than the Instagram platform user id.
core.validate_configuration = validate_configuration
core.VERSION = VERSION


def main() -> None:
    core.main()


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import ctypes
import getpass
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from ctypes import wintypes
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
LOCAL = REPO / "LOCAL_ONLY" / "social"
SECRET_FILE = LOCAL / "windsor_key.dpapi"
STATE_FILE = LOCAL / "state.json"
LOG_FILE = LOCAL / "social.log"
CONFIG_FILE = REPO / "marketing" / "social_config.json"
QUEUE_FILE = REPO / "marketing" / "queue.json"
ASSET_DIR = REPO / "marketing" / "assets"
BASE_URL = "https://connectors.windsor.ai"
VERSION = "2.1.0"

FORBIDDEN_PHRASES = (
    "guaranteed profit",
    "guaranteed returns",
    "risk-free",
    "risk free",
    "sure profit",
    "100% win",
    "100 percent win",
    "get rich",
    "no risk",
)

DISCLAIMER = "Trading involves risk. Historical or backtested results do not guarantee future performance."


def now_local() -> datetime:
    return datetime.now().astimezone()


def iso_now() -> str:
    return now_local().isoformat()


def log(message: str) -> None:
    LOCAL.mkdir(parents=True, exist_ok=True)
    line = f"[{iso_now()}] {message}"
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(f"[VASTcode21 Social] {message}", flush=True)


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


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _dpapi_available() -> bool:
    return os.name == "nt"


def protect_secret(text: str) -> bytes:
    if not _dpapi_available():
        raise RuntimeError("Windows DPAPI is required for secure local secret storage")
    raw = text.encode("utf-8")
    buf = ctypes.create_string_buffer(raw)
    in_blob = DATA_BLOB(len(raw), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte)))
    out_blob = DATA_BLOB()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    ok = crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        "VASTcode21 Windsor API key",
        None,
        None,
        None,
        0x1,
        ctypes.byref(out_blob),
    )
    if not ok:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        kernel32.LocalFree(out_blob.pbData)


def unprotect_secret(blob: bytes) -> str:
    if not _dpapi_available():
        raise RuntimeError("Windows DPAPI is required for secure local secret storage")
    buf = ctypes.create_string_buffer(blob)
    in_blob = DATA_BLOB(len(blob), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte)))
    out_blob = DATA_BLOB()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    ok = crypt32.CryptUnprotectData(
        ctypes.byref(in_blob), None, None, None, None, 0x1, ctypes.byref(out_blob)
    )
    if not ok:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData).decode("utf-8")
    finally:
        kernel32.LocalFree(out_blob.pbData)


def store_key(key: str) -> None:
    LOCAL.mkdir(parents=True, exist_ok=True)
    SECRET_FILE.write_bytes(protect_secret(key))


def load_key() -> str:
    if not SECRET_FILE.exists():
        raise RuntimeError("Windsor API key is not configured")
    return unprotect_secret(SECRET_FILE.read_bytes()).strip()


def request_json(method: str, path: str, api_key: str, *, query: dict[str, str] | None = None,
                 body: dict[str, Any] | None = None, timeout: int = 45) -> Any:
    params = dict(query or {})
    params["api_key"] = api_key
    url = f"{BASE_URL}/{path.lstrip('/')}?{urllib.parse.urlencode(params)}"
    data = None
    headers = {"User-Agent": "VASTcode21-Social-Autopilot/2.1"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(payload)
        except Exception:
            detail = payload[:1000]
        raise RuntimeError(f"Windsor HTTP {exc.code}: {detail}") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Windsor network error: {exc.reason}") from None


def list_actions(api_key: str) -> tuple[str, list[dict[str, Any]]]:
    last_error = None
    for connector in ("instagram", "all"):
        try:
            payload = request_json("GET", f"{connector}/actions", api_key)
            actions = payload.get("data") if isinstance(payload, dict) else payload
            if isinstance(actions, list):
                return connector, [a for a in actions if isinstance(a, dict)]
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Could not discover Instagram write actions: {last_error}")


def discover_instagram_account(api_key: str, preferred_name: str) -> dict[str, str]:
    payload = request_json(
        "GET",
        "instagram",
        api_key,
        query={
            "date_preset": "last_7d",
            "fields": "account_id,account_name,source,datasource",
            "_max_rows": "100",
        },
    )
    rows = payload.get("data", payload if isinstance(payload, list) else [])
    if not isinstance(rows, list):
        rows = []
    clean = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        account_id = str(row.get("account_id") or "").strip()
        account_name = str(row.get("account_name") or "").strip()
        if account_id:
            clean.append({"account_id": account_id, "account_name": account_name})
    dedup: dict[str, dict[str, str]] = {}
    for item in clean:
        dedup[item["account_id"]] = item
    accounts = list(dedup.values())
    wanted = preferred_name.lower().strip()
    for item in accounts:
        if item["account_name"].lower().strip() == wanted:
            return item
    if len(accounts) == 1:
        return accounts[0]
    if not accounts:
        raise RuntimeError("No connected Instagram account with account_id was returned by Windsor")
    names = ", ".join(i["account_name"] or i["account_id"] for i in accounts)
    raise RuntimeError(f"Multiple Instagram accounts found and none matched '{preferred_name}': {names}")


def validate_configuration(api_key: str, config: dict[str, Any]) -> dict[str, Any]:
    connector, actions = list_actions(api_key)
    action_ids = {str(a.get("id") or "") for a in actions}
    if "create_image_post" not in action_ids:
        raise RuntimeError("Instagram create_image_post write action is not available/enabled in Windsor")
    account = discover_instagram_account(api_key, str(config.get("account_name") or "vast.code21"))
    return {"connector": connector, "account": account, "actions": sorted(action_ids)}


def default_config() -> dict[str, Any]:
    return {
        "version": VERSION,
        "enabled": True,
        "account_name": "vast.code21",
        "publish_hour_local": 19,
        "max_posts_per_day": 1,
        "min_hours_between_posts": 20,
        "image_action": "create_image_post",
        "raw_asset_base": "https://raw.githubusercontent.com/twentyones23415-max/VASTcode21-runner/main/marketing/assets",
        "hashtags": ["#VASTcode21", "#MT5", "#AlgorithmicTrading", "#GoldTrading", "#BitcoinTrading"],
        "paid_ads": False,
        "live_trading": False,
    }


def configure() -> int:
    config = load_json(CONFIG_FILE, default_config())
    print("VASTcode21 Social Autopilot v2.1")
    print("The Windsor API key will be stored only on this Windows account using DPAPI encryption.")
    print("It will not be printed, committed to GitHub, or sent to ChatGPT.\n")
    key = getpass.getpass("Paste Windsor API key (hidden input) and press Enter: ").strip()
    if len(key) < 12:
        print("ERROR: key looks invalid.")
        return 2
    try:
        result = validate_configuration(key, config)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 3
    store_key(key)
    state = load_json(STATE_FILE, {})
    state.update({
        "version": VERSION,
        "configured_at": iso_now(),
        "account_id": result["account"]["account_id"],
        "account_name": result["account"]["account_name"],
        "connector": result["connector"],
        "write_action_ready": True,
        "paid_ads": False,
        "live_trading": False,
    })
    save_json(STATE_FILE, state)
    print(f"SUCCESS: connected Instagram account '{state['account_name']}' is ready for organic posting.")
    print("Paid ads: OFF | Live trading: OFF")
    return 0


def is_safe_text(text: str) -> tuple[bool, str | None]:
    lower = text.casefold()
    for phrase in FORBIDDEN_PHRASES:
        if phrase in lower:
            return False, phrase
    return True, None


def caption_for(item: dict[str, Any], config: dict[str, Any]) -> str:
    hook = str(item.get("hook") or "").strip()
    body = str(item.get("caption") or "").strip()
    disclaimer = str(item.get("disclaimer") or DISCLAIMER).strip()
    cta = "Follow VASTcode21 for verified development updates."
    hashtags = " ".join(str(x) for x in config.get("hashtags", []) if str(x).strip())
    parts = [hook, body, disclaimer, cta, hashtags]
    return "\n\n".join(x for x in parts if x)


def due_now(state: dict[str, Any], config: dict[str, Any], force: bool) -> tuple[bool, str]:
    if force:
        return True, "forced"
    now = now_local()
    publish_hour = int(config.get("publish_hour_local", 19))
    if now.hour < publish_hour:
        return False, f"before publish hour {publish_hour:02d}:00"
    last = state.get("last_posted_at")
    if last:
        try:
            last_dt = datetime.fromisoformat(str(last))
            if last_dt.tzinfo is None:
                last_dt = last_dt.astimezone()
            elapsed = now - last_dt.astimezone()
            min_hours = int(config.get("min_hours_between_posts", 20))
            if elapsed < timedelta(hours=min_hours):
                return False, f"minimum interval not reached ({elapsed.total_seconds()/3600:.1f}h)"
            if last_dt.astimezone().date() == now.date() and int(config.get("max_posts_per_day", 1)) <= 1:
                return False, "daily post limit reached"
        except Exception:
            pass
    return True, "due"


def select_item(queue: dict[str, Any], state: dict[str, Any]) -> dict[str, Any] | None:
    posted = set(str(x) for x in state.get("posted_ids", []))
    items = queue.get("items") or []
    candidates = []
    for item in items:
        if not isinstance(item, dict):
            continue
        pid = str(item.get("id") or "")
        if not pid or pid in posted:
            continue
        if str(item.get("status") or "") != "ready_for_design":
            continue
        asset = ASSET_DIR / f"{pid}.jpg"
        if not asset.exists():
            continue
        candidates.append(item)
    if not candidates:
        return None
    candidates.sort(key=lambda x: (-int(x.get("priority", 0) or 0), str(x.get("id") or "")))
    return candidates[0]


def post_image(api_key: str, connector: str, account_id: str, item: dict[str, Any], config: dict[str, Any]) -> Any:
    pid = str(item["id"])
    image_url = f"{str(config.get('raw_asset_base')).rstrip('/')}/{urllib.parse.quote(pid)}.jpg"
    caption = caption_for(item, config)
    ok, phrase = is_safe_text(caption)
    if not ok:
        raise RuntimeError(f"compliance blocked phrase: {phrase}")
    body = {
        "account": account_id,
        "action": str(config.get("image_action") or "create_image_post"),
        "params": {"image_url": image_url, "caption": caption},
    }
    return request_json("POST", f"{connector}/actions", api_key, body=body, timeout=90)


def run_once(force: bool = False, dry_run: bool = False) -> int:
    config = load_json(CONFIG_FILE, default_config())
    if not bool(config.get("enabled", True)):
        log("disabled by marketing/social_config.json")
        return 0
    if bool(config.get("paid_ads", False)) or bool(config.get("live_trading", False)):
        log("SAFETY BLOCK: paid_ads/live_trading must remain false")
        return 4
    try:
        api_key = load_key()
    except Exception as exc:
        log(f"not configured: {exc}")
        return 0
    state = load_json(STATE_FILE, {"posted_ids": []})
    state.setdefault("posted_ids", [])
    due, reason = due_now(state, config, force)
    if not due:
        log(f"idle: {reason}")
        return 0
    queue = load_json(QUEUE_FILE, {})
    item = select_item(queue, state)
    if not item:
        log("idle: no unposted compliant asset is ready")
        return 0
    try:
        validated = validate_configuration(api_key, config)
    except Exception as exc:
        state["last_error"] = str(exc)
        state["last_error_at"] = iso_now()
        save_json(STATE_FILE, state)
        log(f"configuration check failed: {exc}")
        return 5
    connector = str(validated["connector"])
    account_id = str(validated["account"]["account_id"])
    if dry_run:
        log(f"DRY RUN ready: would post {item['id']} to {validated['account']['account_name']}")
        return 0
    try:
        result = post_image(api_key, connector, account_id, item, config)
    except Exception as exc:
        state["last_error"] = str(exc)
        state["last_error_at"] = iso_now()
        state["consecutive_errors"] = int(state.get("consecutive_errors", 0) or 0) + 1
        save_json(STATE_FILE, state)
        log(f"post failed for {item['id']}: {exc}")
        return 6
    posted_ids = [str(x) for x in state.get("posted_ids", [])]
    posted_ids.append(str(item["id"]))
    state.update({
        "version": VERSION,
        "last_posted_at": iso_now(),
        "last_posted_id": str(item["id"]),
        "posted_ids": posted_ids[-500:],
        "account_id": account_id,
        "account_name": validated["account"]["account_name"],
        "connector": connector,
        "consecutive_errors": 0,
        "last_result": result,
        "paid_ads": False,
        "live_trading": False,
    })
    save_json(STATE_FILE, state)
    log(f"POSTED: {item['id']} to Instagram account {state['account_name']}")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="VASTcode21 automatic organic Instagram publisher")
    ap.add_argument("--configure", action="store_true", help="Securely store Windsor key and validate account")
    ap.add_argument("--force", action="store_true", help="Ignore publish-time gate (still respects compliance)")
    ap.add_argument("--dry-run", action="store_true", help="Validate and select without publishing")
    args = ap.parse_args()
    if args.configure:
        raise SystemExit(configure())
    raise SystemExit(run_once(force=args.force, dry_run=args.dry_run))


if __name__ == "__main__":
    main()

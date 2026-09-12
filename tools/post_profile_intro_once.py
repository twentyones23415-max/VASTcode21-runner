from __future__ import annotations

from datetime import datetime

import social_autopilot_runtime as social
import social_autopilot as core

INTRO_ID = "evergreen-001"


def main() -> int:
    config = social.load_json(social.CONFIG_FILE, social.default_config())
    if bool(config.get("paid_ads", False)) or bool(config.get("live_trading", False)):
        core.log("SAFETY BLOCK: paid_ads/live_trading must remain false")
        return 4

    try:
        api_key = core.load_key()
    except Exception as exc:
        core.log(f"not configured: {exc}")
        return 2

    state = social.load_json(social.STATE_FILE, {"posted_ids": []})
    state.setdefault("posted_ids", [])

    # Never create a second organic post on the same local calendar day.
    last = state.get("last_posted_at")
    if last:
        try:
            last_dt = datetime.fromisoformat(str(last))
            if last_dt.tzinfo is None:
                last_dt = last_dt.astimezone()
            if last_dt.astimezone().date() == datetime.now().astimezone().date():
                core.log(f"PROFILE INTRO: a post already exists today ({state.get('last_posted_id','unknown')}); no duplicate post created")
                return 0
        except Exception:
            pass

    if INTRO_ID in {str(x) for x in state.get("posted_ids", [])}:
        core.log("PROFILE INTRO: evergreen-001 was already posted; nothing to do")
        return 0

    queue = core.load_json(core.QUEUE_FILE, {})
    item = None
    for candidate in queue.get("items") or []:
        if isinstance(candidate, dict) and str(candidate.get("id") or "") == INTRO_ID:
            item = candidate
            break
    if item is None:
        core.log("PROFILE INTRO ERROR: evergreen-001 is missing from marketing/queue.json")
        return 3

    asset = core.ASSET_DIR / f"{INTRO_ID}.jpg"
    if not asset.exists():
        core.log(f"PROFILE INTRO ERROR: missing asset {asset}")
        return 3

    caption = core.caption_for(item, config)
    safe, phrase = core.is_safe_text(caption)
    if not safe:
        core.log(f"PROFILE INTRO SAFETY BLOCK: compliance phrase {phrase}")
        return 4

    try:
        validated = social.validate_configuration(api_key, config)
    except Exception as exc:
        state["last_error"] = str(exc)
        state["last_error_at"] = core.iso_now()
        social.save_json(social.STATE_FILE, state)
        core.log(f"PROFILE INTRO connection check failed: {exc}")
        return 5

    connector = str(validated["connector"])
    account_id = str(validated["account"]["account_id"])
    account_name = str(validated["account"]["account_name"])

    try:
        result = core.post_image(api_key, connector, account_id, item, config)
    except Exception as exc:
        state["last_error"] = str(exc)
        state["last_error_at"] = core.iso_now()
        state["consecutive_errors"] = int(state.get("consecutive_errors", 0) or 0) + 1
        social.save_json(social.STATE_FILE, state)
        core.log(f"PROFILE INTRO post failed: {exc}")
        return 6

    posted_ids = [str(x) for x in state.get("posted_ids", [])]
    posted_ids.append(INTRO_ID)
    state.update({
        "version": social.VERSION,
        "last_posted_at": core.iso_now(),
        "last_posted_id": INTRO_ID,
        "posted_ids": posted_ids[-500:],
        "account_id": account_id,
        "account_name": account_name,
        "connector": connector,
        "consecutive_errors": 0,
        "last_result": result,
        "paid_ads": False,
        "live_trading": False,
    })
    social.save_json(social.STATE_FILE, state)
    core.log(f"PROFILE INTRO POSTED: {INTRO_ID} to Instagram account {account_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

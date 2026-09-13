#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "marketing" / "queue.json"


def main() -> None:
    if not QUEUE.exists():
        raise SystemExit("marketing/queue.json not found")

    payload = json.loads(QUEUE.read_text(encoding="utf-8"))
    followers = int(payload.get("followers_count", 0) or 0)
    if followers >= 10:
        print(json.dumps({"zero_to_ten": False, "changed": 0}))
        return

    changed = 0
    for item in payload.get("items", []):
        if not isinstance(item, dict):
            continue

        pillar = str(item.get("pillar") or "").lower()
        hook = str(item.get("hook") or "")

        # With zero audience signal, discovery/value content should outrank sales.
        if pillar == "services":
            if int(item.get("priority", 0) or 0) > 5:
                item["priority"] = 5
                changed += 1
            item["growth_role"] = "profile_funnel_only"
            continue

        # Turn the near-term FOMC alert into a saveable, search-intent educational Reel.
        # It makes no directional prediction and keeps the official-event context intact.
        if pillar == "market_risk" and "fomc" in hook.lower():
            new_hook = "FOMC Wednesday 21:00: 3 things to check before XAUUSD or BTCUSD moves."
            new_caption = (
                "FOMC decision: Wednesday 16 Sep at 21:00 local time; press conference follows at 21:30. "
                "For XAUUSD and BTCUSD, watch three things instead of guessing direction: "
                "1) spread/liquidity conditions around the release, 2) the first reaction versus the reaction after the statement is digested, "
                "and 3) whether the press conference changes the market's interpretation. "
                "This is event-risk context, not a trade call. Verify the Federal Reserve schedule before acting."
            )
            new_script = [
                "FOMC · WED 21:00",
                "1 · SPREAD / LIQUIDITY",
                "2 · FIRST MOVE ≠ FINAL MOVE",
                "3 · PRESSER 21:30",
                "XAUUSD · BTCUSD\nSAVE THIS CHECKLIST",
            ]
            new_tags = ["#FOMC", "#XAUUSD", "#GoldTrading", "#BTCUSD", "#BitcoinTrading", "#MT5"]
            new_cta = "Save this checklist and follow @vast.code21 for verified XAUUSD/BTCUSD event-risk context."
            if item.get("hook") != new_hook:
                item["hook"] = new_hook
                changed += 1
            if item.get("caption") != new_caption:
                item["caption"] = new_caption
                changed += 1
            if item.get("reel_script") != new_script:
                item["reel_script"] = new_script
                changed += 1
            if item.get("hashtags") != new_tags:
                item["hashtags"] = new_tags
                changed += 1
            if item.get("cta") != new_cta:
                item["cta"] = new_cta
                changed += 1
            item["priority"] = max(int(item.get("priority", 0) or 0), 260)
            item["growth_hypothesis"] = "timely_saveable_search_intent_reel"

    payload["growth_strategy"] = {
        "stage": "zero_to_ten",
        "principle": "discovery_and_saves_before_sales",
        "evidence": "0 followers and 0 measured likes/comments across current media",
    }
    QUEUE.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"zero_to_ten": True, "changed": changed, "strategy": "discovery_and_saves_before_sales"}))


if __name__ == "__main__":
    main()

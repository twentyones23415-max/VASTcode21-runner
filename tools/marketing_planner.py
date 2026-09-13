from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "status" / "summary.json"
AUTONOMY = ROOT / "status" / "autonomy.json"
GROWTH = ROOT / "marketing" / "growth_metrics.json"
CONFIG = ROOT / "marketing" / "social_config.json"
REVENUE_CONFIG = ROOT / "marketing" / "revenue_config.json"
REVENUE_STATUS = ROOT / "marketing" / "revenue_status.json"
OUT = ROOT / "marketing" / "queue.json"
DISCLAIMER = "Trading involves risk. Historical or backtested results do not guarantee future performance."


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def growth_item(pid: str, pillar: str, hook: str, caption: str, creative: str, fmt: str, hashtags: list[str], cta: str, priority: int = 100, disclaimer: str = DISCLAIMER) -> dict:
    return {
        "id": pid,
        "pillar": pillar,
        "hook": hook,
        "caption": caption,
        "creative_brief": creative,
        "format": fmt,
        "platforms": ["Instagram"],
        "priority": priority,
        "status": "ready_for_design",
        "hashtags": hashtags,
        "cta": cta,
        "disclaimer": disclaimer,
    }


def main() -> None:
    summary = load_json(SUMMARY)
    autonomy = load_json(AUTONOMY)
    growth = load_json(GROWTH)
    config = load_json(CONFIG)
    revenue_config = load_json(REVENUE_CONFIG)
    revenue_status = load_json(REVENUE_STATUS)

    experiments = int(summary.get("experiments", 0) or 0)
    rejected = int(summary.get("rejected", 0) or 0)
    mt5_passed = int(summary.get("mt5_validation_passed", 0) or 0)
    mt5_rejected = int(summary.get("mt5_validation_rejected", 0) or 0)
    generation = int(summary.get("max_generation", 0) or 0)
    robustness_passed = int(autonomy.get("robustness_passed", 0) or 0)
    forward_collecting = int(autonomy.get("forward_collecting", 0) or 0)
    forward_passed = int(autonomy.get("forward_passed", 0) or 0)
    release_candidates = int(autonomy.get("release_candidates", 0) or 0)
    followers = int(growth.get("followers_count", 0) or 0)

    tz_name = config.get("timezone", "Europe/Bucharest")
    now_local = datetime.now(timezone.utc).astimezone(ZoneInfo(tz_name))
    day_key = now_local.strftime("%Y%m%d")
    slot = now_local.toordinal() % 7

    ctas = config.get("cta_variants") or [
        "Follow @vast.code21 for transparent MT5 research and validation updates.",
        "Follow @vast.code21 to watch the VAST validation process evolve in public.",
        "Follow @vast.code21 for GOLD, BITCOIN and MT5 research without profit promises.",
    ]
    hashtag_sets = config.get("hashtag_sets") or [
        ["#VASTcode21", "#MT5", "#AlgorithmicTrading", "#GoldTrading", "#BitcoinTrading", "#TradingSystems", "#QuantTrading"],
        ["#VASTcode21", "#MetaTrader5", "#AlgoTrading", "#XAUUSD", "#Bitcoin", "#TradingResearch", "#SystematicTrading"],
        ["#VASTcode21", "#MT5Trading", "#TradingAlgo", "#Gold", "#BTC", "#Backtesting", "#TradingEducation"],
    ]
    cta = ctas[now_local.toordinal() % len(ctas)]
    hashtags = hashtag_sets[now_local.toordinal() % len(hashtag_sets)]

    mode = "launch_discovery" if followers < 10 else ("growth_10_100" if followers < 100 else "community_growth")

    templates = [
        {
            "pillar": "education",
            "format": "reel",
            "hook": "A backtest is not a promise.",
            "caption": "A strategy can look excellent on historical data and still fail when execution detail, new market regimes and forward observation are introduced. VASTcode21 treats every pass as permission for more testing—not as permission for hype.",
            "creative": "9:16 three-card Reel: BACKTEST → REAL-TICK MT5 → FORWARD. Strong first-frame hook, clean quant aesthetic.",
        },
        {
            "pillar": "engineering",
            "format": "carousel",
            "hook": "What happens when a trading idea fails?",
            "caption": "It gets rejected. The VASTcode21 pipeline is designed to eliminate weak candidates before they become products. Failure is data: it can inform the next generation, but it does not become a marketing claim.",
            "creative": "Three-slide carousel: 1) FAIL FAST 2) LEARN FROM REJECTION 3) ONLY SURVIVORS ADVANCE.",
        },
        {
            "pillar": "scope",
            "format": "reel",
            "hook": "Why VASTcode21 is focused on GOLD and BITCOIN.",
            "caption": "Narrow scope creates cleaner research. Instead of claiming to trade everything, VASTcode21 concentrates its current autonomous validation on GOLD and BITCOIN so the testing process can go deeper.",
            "creative": "9:16 split visual: GOLD / BITCOIN, then validation funnel.",
        },
        {
            "pillar": "research_progress",
            "format": "image",
            "hook": f"{experiments} experiments. Generation {generation}. Still testing.",
            "caption": f"The current research state has evaluated {experiments} experiments, with {rejected} rejected in research, {mt5_passed} MT5 PASS and {mt5_rejected} MT5 REJECT result(s). Most ideas are expected to fail. That is the point of a validation-first process.",
            "creative": "4:5 data card with experiment count, generation, MT5 pass/reject, no P&L imagery.",
        },
        {
            "pillar": "education",
            "format": "carousel",
            "hook": "Three gates before a VAST candidate can earn trust.",
            "caption": f"Research is only the first gate. Candidates then face real-tick MT5 validation, robustness checks and shadow-forward observation. Current state: {robustness_passed} robustness PASS and {forward_collecting} collecting forward evidence.",
            "creative": "Three-slide validation ladder: RESEARCH → ROBUSTNESS → FORWARD, with current stage highlighted.",
        },
        {
            "pillar": "engineering",
            "format": "reel",
            "hook": "Most trading ideas should fail in research.",
            "caption": "If nearly every experiment becomes a product, the filter is probably too weak. VASTcode21 is built to reject aggressively and keep only candidates that survive progressively harder tests.",
            "creative": "9:16 funnel animation: many candidates → few survivors.",
        },
        {
            "pillar": "weekly_digest",
            "format": "image",
            "hook": "VASTcode21 weekly research snapshot.",
            "caption": f"Current snapshot: {experiments} experiments, generation {generation}, {mt5_passed} MT5 PASS, {robustness_passed} robustness PASS, {forward_collecting} in forward observation and {release_candidates} release candidate(s). Live trading remains OFF.",
            "creative": "4:5 weekly dashboard card with verified counters only.",
        },
    ]

    selected = dict(templates[slot])

    if release_candidates > 0:
        selected = {
            "pillar": "verified_milestone",
            "format": "carousel",
            "hook": "A VASTcode21 release candidate exists.",
            "caption": f"The validation pipeline currently shows {release_candidates} release candidate(s). This is still a controlled pre-release state. A release candidate is not a guarantee of performance and does not switch live trading on.",
            "creative": "Three-slide controlled milestone carousel: RELEASE CANDIDATE / WHAT IT MEANS / WHAT IT DOES NOT MEAN.",
        }
    elif forward_passed > 0:
        selected = {
            "pillar": "verified_milestone",
            "format": "reel",
            "hook": "A candidate cleared shadow-forward observation.",
            "caption": f"The current autonomous state shows {forward_passed} forward PASS candidate(s). That is a meaningful validation milestone, but it still does not imply guaranteed performance or automatic live trading.",
            "creative": "9:16 milestone Reel: FORWARD PASS → next controlled gate.",
        }

    daily = growth_item(
        f"growth-{day_key}", selected["pillar"], selected["hook"], selected["caption"], selected["creative"],
        selected["format"], hashtags, cta, 120,
    )

    evergreen = [
        growth_item(
            "evergreen-validation-stack", "education", "The four-stage VASTcode21 validation stack.",
            "Research → real-tick MT5 → robustness → shadow-forward. A candidate must keep surviving as the evidence gets harder.",
            "4:5 validation ladder graphic.", "image", hashtag_sets[0], ctas[0], 60,
        ),
        growth_item(
            "evergreen-no-hype", "brand", "No profit screenshots. No guaranteed returns. Just the process.",
            "VASTcode21 publishes verified research milestones and validation stages while keeping proprietary strategy logic private.",
            "Minimal 4:5 manifesto card.", "image", hashtag_sets[1 % len(hashtag_sets)], ctas[1 % len(ctas)], 55,
        ),
        growth_item(
            "evergreen-real-ticks", "education", "Why real ticks matter in MT5.",
            "Simplified data can hide execution detail. Real-tick validation is one of the gates VASTcode21 uses before a candidate can advance.",
            "Three-slide educational carousel.", "carousel", hashtag_sets[2 % len(hashtag_sets)], ctas[2 % len(ctas)], 50,
        ),
    ]

    items = [daily] + evergreen

    launchable = set(revenue_status.get("launchable_offers") or [])
    guardrails = revenue_config.get("sales_guardrails") or {}
    offers = {str(o.get("id")): o for o in revenue_config.get("offers", []) if isinstance(o, dict)}
    required_offers = {"mt5-setup-audit", "research-brief", "vast-early-access"}
    revenue_safe = (
        required_offers.issubset(launchable)
        and not bool(guardrails.get("paid_ads", True))
        and not bool(guardrails.get("live_trading", True))
        and not bool(guardrails.get("vast_indicator_sales_enabled", True))
    )
    if revenue_safe:
        audit = offers.get("mt5-setup-audit", {})
        brief = offers.get("research-brief", {})
        early = offers.get("vast-early-access", {})
        offer_caption = (
            "Three VASTcode21 offers are now operational: "
            "MT5 Setup & Automation Audit — €99 one-time for a 45-minute technical MT5 setup/automation review; "
            "VASTcode21 Research Brief — €15/month for weekly educational validation notes; "
            "VAST Early Access — free for verified development and release updates. "
            "The VAST indicator itself is NOT for sale while validation is incomplete.\n\n"
            f"Audit: {audit.get('checkout_url', '')}\n"
            f"Research Brief: {brief.get('checkout_url', '')}\n"
            f"Early Access: {early.get('signup_url', '')}"
        )
        offers_item = growth_item(
            "offers-ready-v1",
            "services",
            "VASTcode21 services are now available.",
            offer_caption,
            "Clean 4:5 three-offer availability card. Show €99 Audit, €15/mo Research Brief and FREE Early Access. Do not depict profit charts, returns or the VAST indicator as released.",
            "image",
            hashtag_sets[0],
            "Choose the Audit, Research Brief or free Early Access option. Links are in this caption.",
            300,
            "Technical and educational services only. No signals, account management, personalized investment advice or profit guarantees. Trading involves risk.",
        )
        items = [offers_item] + items

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "followers_count": followers,
        "growth_goal_followers": int(config.get("growth_goal_followers", 100)),
        "paid_ads": False,
        "live_trading": False,
        "source_status": {
            "experiments": experiments,
            "generation": generation,
            "mt5_validation_passed": mt5_passed,
            "mt5_validation_rejected": mt5_rejected,
            "robustness_passed": robustness_passed,
            "forward_collecting": forward_collecting,
            "forward_passed": forward_passed,
            "release_candidates": release_candidates,
            "revenue_offers_ready": revenue_safe,
        },
        "items": items,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({
        "generated": len(items),
        "daily_id": daily["id"],
        "daily_format": daily["format"],
        "growth_mode": mode,
        "followers": followers,
        "revenue_offers_ready": revenue_safe,
        "paid_ads": False,
        "live_trading": False,
    }))


if __name__ == "__main__":
    main()

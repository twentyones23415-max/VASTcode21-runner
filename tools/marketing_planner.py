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
EVENT_RISK = ROOT / "site" / "data" / "event_risk.json"
OUT = ROOT / "marketing" / "queue.json"
DISCLAIMER = "Trading involves risk. Historical or backtested results do not guarantee future performance."


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def growth_item(pid: str, pillar: str, hook: str, caption: str, creative: str, fmt: str, hashtags: list[str], cta: str, priority: int = 100, disclaimer: str = DISCLAIMER, reel_script: list[str] | None = None) -> dict:
    item = {
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
    if reel_script:
        item["reel_script"] = reel_script
    return item


def parse_iso(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def event_discovery_item(event_risk: dict, now_local: datetime, hashtags: list[str], cta: str) -> dict | None:
    events = [e for e in event_risk.get("events", []) if isinstance(e, dict)]
    candidates = []
    for event in events:
        if str(event.get("impact", "")).lower() != "high":
            continue
        scheduled = parse_iso(event.get("scheduled_at"))
        if not scheduled:
            continue
        delta = scheduled.astimezone(timezone.utc) - now_local.astimezone(timezone.utc)
        if delta.total_seconds() < 0 or delta.total_seconds() > 7 * 86400:
            continue
        candidates.append((scheduled, event))
    if not candidates:
        return None

    scheduled, event = sorted(candidates, key=lambda x: x[0])[0]
    local_event = scheduled.astimezone(now_local.tzinfo)
    title = str(event.get("title") or "High-impact macro event")
    relevance = ", ".join(event.get("relevance") or ["XAUUSD", "BTCUSD"])
    day_key = now_local.strftime("%Y%m%d")
    hook = f"High-impact event ahead: {title}."
    caption = (
        f"{title} is scheduled for {local_event:%A %d %b, %H:%M} local time. "
        f"VASTcode21 flags it as high-impact context for {relevance}. Around major scheduled releases, volatility and execution conditions can change quickly. "
        "Mark the time, reduce assumptions, and verify the official source before acting."
    )
    return growth_item(
        f"event-risk-{day_key}",
        "market_risk",
        hook,
        caption,
        "9:16 event-risk Reel. First frame: EVENT RISK AHEAD. Second: event name + local time. Third: XAUUSD / BTCUSD + CHECK CONTEXT, NOT HYPE.",
        "reel",
        hashtags,
        "Save the time and follow @vast.code21 for the next verified market-risk alert.",
        240,
        "Event-risk context only, not a trading instruction. Scheduled times can change; verify the linked official source. Trading involves risk.",
        [
            "EVENT RISK AHEAD",
            f"{title}\n{local_event:%d %b · %H:%M}",
            "XAUUSD + BTCUSD\nCHECK CONTEXT FIRST",
        ],
    )


def main() -> None:
    summary = load_json(SUMMARY)
    autonomy = load_json(AUTONOMY)
    growth = load_json(GROWTH)
    config = load_json(CONFIG)
    revenue_config = load_json(REVENUE_CONFIG)
    revenue_status = load_json(REVENUE_STATUS)
    event_risk = load_json(EVENT_RISK)

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
        "Follow @vast.code21 to watch VAST survive—or fail—real validation in public.",
        "Save this and follow @vast.code21 for practical MT5, GOLD and BITCOIN research.",
        "Follow @vast.code21 for the next validation result, market-risk alert and MT5 lesson.",
    ]
    hashtag_sets = config.get("hashtag_sets") or [
        ["#VASTcode21", "#XAUUSD", "#MT5", "#AlgoTrading", "#TradingEducation", "#Backtesting"],
        ["#VASTcode21", "#Bitcoin", "#MetaTrader5", "#QuantTrading", "#SystematicTrading", "#TradingResearch"],
        ["#VASTcode21", "#GoldTrading", "#BTCUSD", "#MT5Trading", "#TradingSystems", "#RiskManagement"],
    ]
    cta = ctas[now_local.toordinal() % len(ctas)]
    hashtags = hashtag_sets[now_local.toordinal() % len(hashtag_sets)]

    rescue_threshold = int(config.get("growth_rescue_followers_below", 10))
    rescue_mode = followers < rescue_threshold
    mode = "zero_to_ten_rescue" if rescue_mode else ("growth_10_100" if followers < 100 else "community_growth")

    rescue_templates = [
        {
            "pillar": "education",
            "format": "reel",
            "hook": "Your backtest is not proof.",
            "caption": "A strong historical curve is only the start. Spread, ticks, execution detail, regime change and forward observation can expose weaknesses that a clean backtest hides. VASTcode21 is documenting that filtering process in public.",
            "creative": "Fast 9:16 Reel with four words appearing sequentially: BACKTEST / TICKS / ROBUSTNESS / FORWARD.",
            "script": ["YOUR BACKTEST\nIS NOT PROOF", "TICKS · SPREAD · REGIME", "FORWARD TEST\nOR IT DIDN'T SURVIVE"],
        },
        {
            "pillar": "build_in_public",
            "format": "reel",
            "hook": "We are building VASTcode21 from zero—in public.",
            "caption": f"Current state: {experiments} experiments, generation {generation}, {mt5_passed} MT5 pass result(s), {mt5_rejected} MT5 reject result(s). We will publish the process, including failures, without turning a backtest into a profit promise.",
            "creative": "9:16 build-in-public Reel: ZERO → TEST → REJECT → IMPROVE. Large numeric counters.",
            "script": ["BUILDING FROM ZERO", f"{experiments} EXPERIMENTS\nGEN {generation}", "FOLLOW THE BUILD\nNOT THE HYPE"],
        },
        {
            "pillar": "education",
            "format": "carousel",
            "hook": "3 reasons an MT5 strategy can fail after a good backtest.",
            "caption": "1) execution assumptions were too clean, 2) the market regime changed, 3) the strategy was overfit to historical noise. Robustness and forward observation exist to expose exactly this.",
            "creative": "Three-slide carousel: EXECUTION / REGIME / OVERFIT. End with a save CTA.",
            "script": None,
        },
        {
            "pillar": "scope",
            "format": "reel",
            "hook": "Why we keep testing GOLD and BITCOIN.",
            "caption": "A narrower research scope lets the validation process go deeper. VASTcode21 currently concentrates on XAUUSD and BTCUSD context instead of pretending one system understands every market equally well.",
            "creative": "9:16 split-screen style GOLD / BITCOIN research Reel.",
            "script": ["WHY GOLD + BITCOIN?", "NARROWER SCOPE\nDEEPER TESTING", "XAUUSD · BTCUSD\nFOLLOW THE RESEARCH"],
        },
        {
            "pillar": "engineering",
            "format": "reel",
            "hook": "A failed trading idea is useful data.",
            "caption": "Weak candidates should die early. VASTcode21 keeps rejection visible because a research process that never rejects anything is not much of a filter.",
            "creative": "9:16 funnel Reel: MANY IDEAS → REJECTION → FEWER SURVIVORS.",
            "script": ["MOST IDEAS\nSHOULD FAIL", "REJECTION = DATA", "ONLY SURVIVORS\nMOVE FORWARD"],
        },
        {
            "pillar": "education",
            "format": "carousel",
            "hook": "Before you trust an MT5 backtest, check these 3 things.",
            "caption": "Data quality. Execution assumptions. Out-of-sample or forward evidence. A beautiful equity curve without these checks can be more persuasive than useful.",
            "creative": "Saveable three-slide checklist carousel.",
            "script": None,
        },
        {
            "pillar": "research_progress",
            "format": "reel",
            "hook": f"{experiments} experiments. Still not calling it finished.",
            "caption": f"VASTcode21 currently shows {experiments} experiments, {robustness_passed} robustness pass result(s) and {forward_collecting} candidate(s) collecting forward evidence. Progress matters, but evidence comes before launch claims.",
            "creative": "9:16 counter-led Reel with current verified research numbers.",
            "script": [f"{experiments} EXPERIMENTS", f"{robustness_passed} ROBUSTNESS PASS", "STILL TESTING\nFOLLOW THE NEXT GATE"],
        },
    ]

    standard_templates = [
        {
            "pillar": "education",
            "format": "reel",
            "hook": "A backtest is not a promise.",
            "caption": "A strategy can look excellent on historical data and still fail when execution detail, new market regimes and forward observation are introduced. VASTcode21 treats every pass as permission for more testing—not as permission for hype.",
            "creative": "9:16 three-card Reel: BACKTEST → REAL-TICK MT5 → FORWARD.",
            "script": ["BACKTEST", "REAL-TICK MT5", "FORWARD"],
        },
        {
            "pillar": "engineering",
            "format": "carousel",
            "hook": "What happens when a trading idea fails?",
            "caption": "It gets rejected. Failure is data: it can inform the next generation, but it does not become a marketing claim.",
            "creative": "Three-slide carousel: FAIL FAST / LEARN / ONLY SURVIVORS ADVANCE.",
            "script": None,
        },
        {
            "pillar": "scope",
            "format": "reel",
            "hook": "Why VASTcode21 is focused on GOLD and BITCOIN.",
            "caption": "Narrow scope creates cleaner research. VASTcode21 concentrates its current autonomous validation on GOLD and BITCOIN so the testing process can go deeper.",
            "creative": "9:16 GOLD / BITCOIN split visual.",
            "script": ["GOLD", "BITCOIN", "DEEPER VALIDATION"],
        },
        {
            "pillar": "research_progress",
            "format": "image",
            "hook": f"{experiments} experiments. Generation {generation}. Still testing.",
            "caption": f"The current research state has evaluated {experiments} experiments, with {rejected} rejected in research, {mt5_passed} MT5 PASS and {mt5_rejected} MT5 REJECT result(s).",
            "creative": "4:5 verified data card.",
            "script": None,
        },
        {
            "pillar": "education",
            "format": "carousel",
            "hook": "Three gates before a VAST candidate can earn trust.",
            "caption": f"Research is only the first gate. Candidates then face real-tick MT5 validation, robustness checks and shadow-forward observation. Current state: {robustness_passed} robustness PASS and {forward_collecting} collecting forward evidence.",
            "creative": "Three-slide validation ladder.",
            "script": None,
        },
        {
            "pillar": "engineering",
            "format": "reel",
            "hook": "Most trading ideas should fail in research.",
            "caption": "If nearly every experiment becomes a product, the filter is probably too weak. VASTcode21 is built to reject aggressively and keep only candidates that survive progressively harder tests.",
            "creative": "9:16 funnel animation.",
            "script": ["MANY IDEAS", "HARD FILTERS", "FEW SURVIVORS"],
        },
        {
            "pillar": "weekly_digest",
            "format": "image",
            "hook": "VASTcode21 weekly research snapshot.",
            "caption": f"Current snapshot: {experiments} experiments, generation {generation}, {mt5_passed} MT5 PASS, {robustness_passed} robustness PASS, {forward_collecting} in forward observation and {release_candidates} release candidate(s).",
            "creative": "4:5 weekly dashboard card.",
            "script": None,
        },
    ]

    templates = rescue_templates if rescue_mode else standard_templates
    selected = dict(templates[slot])

    if release_candidates > 0:
        selected = {
            "pillar": "verified_milestone",
            "format": "carousel",
            "hook": "A VASTcode21 release candidate exists.",
            "caption": f"The validation pipeline currently shows {release_candidates} release candidate(s). This remains a controlled pre-release state and is not a guarantee of performance.",
            "creative": "Three-slide controlled milestone carousel.",
            "script": None,
        }
    elif forward_passed > 0:
        selected = {
            "pillar": "verified_milestone",
            "format": "reel",
            "hook": "A candidate cleared shadow-forward observation.",
            "caption": f"The current autonomous state shows {forward_passed} forward PASS candidate(s). That is a validation milestone, not a guarantee of future performance.",
            "creative": "9:16 milestone Reel.",
            "script": ["FORWARD PASS", "ONE GATE CLEARED", "NOT A GUARANTEE"],
        }

    daily = growth_item(
        f"growth-{day_key}", selected["pillar"], selected["hook"], selected["caption"], selected["creative"],
        selected["format"], hashtags, cta, 220 if rescue_mode else 120, reel_script=selected.get("script"),
    )

    items = [daily]
    event_item = event_discovery_item(event_risk, now_local, hashtag_sets[0], cta)
    if event_item:
        items.insert(0, event_item)

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
    items.extend(evergreen)

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
            "VASTcode21 educational and technical services are available: "
            "MT5 Setup & Automation Audit, VASTcode21 Research Brief and free VAST Early Access. "
            "The VAST indicator itself is not for sale while validation is incomplete.\n\n"
            f"Audit: {audit.get('checkout_url', '')}\n"
            f"Research Brief: {brief.get('checkout_url', '')}\n"
            f"Early Access: {early.get('signup_url', '')}"
        )
        service_priority = 25 if followers < 25 else 75
        items.append(growth_item(
            "offers-ready-v1",
            "services",
            "VASTcode21 services are available.",
            offer_caption,
            "Clean 4:5 service card. No profit charts or performance claims.",
            "image",
            hashtag_sets[0],
            "Use the profile links for the Audit, Research Brief or free Early Access.",
            service_priority,
            "Technical and educational services only. No signals, account management, personalized investment advice or profit guarantees. Trading involves risk.",
        ))

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
            "growth_rescue_mode": rescue_mode,
            "event_risk_active": bool(event_item),
        },
        "items": sorted(items, key=lambda x: int(x.get("priority", 0)), reverse=True),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({
        "generated": len(items),
        "daily_id": daily["id"],
        "daily_format": daily["format"],
        "growth_mode": mode,
        "followers": followers,
        "event_risk_item": event_item["id"] if event_item else None,
        "revenue_offers_ready": revenue_safe,
        "paid_ads": False,
        "live_trading": False,
    }))


if __name__ == "__main__":
    main()

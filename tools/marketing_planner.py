from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "status" / "summary.json"
AUTONOMY = ROOT / "status" / "autonomy.json"
OUT = ROOT / "marketing" / "queue.json"
DISCLAIMER = "Trading involves risk. Historical or backtested results do not guarantee future performance."


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def post(pid: str, pillar: str, hook: str, caption: str, creative: str, priority: int = 50) -> dict:
    return {
        "id": pid,
        "pillar": pillar,
        "hook": hook,
        "caption": caption,
        "creative_brief": creative,
        "platforms": ["Instagram", "TikTok", "YouTube Shorts", "Facebook", "X", "Threads"],
        "priority": priority,
        "status": "ready_for_design",
        "disclaimer": DISCLAIMER,
    }


def main() -> None:
    summary = load_json(SUMMARY)
    autonomy = load_json(AUTONOMY)
    experiments = int(summary.get("experiments", 0) or 0)
    mt5_passed = int(summary.get("mt5_validation_passed", 0) or 0)
    mt5_rejected = int(summary.get("mt5_validation_rejected", 0) or 0)
    generation = int(summary.get("max_generation", 0) or 0)
    robustness_passed = int(autonomy.get("robustness_passed", 0) or 0)
    forward_collecting = int(autonomy.get("forward_collecting", 0) or 0)
    release_candidates = int(autonomy.get("release_candidates", 0) or 0)

    items = [
        post(
            "evergreen-001",
            "engineering",
            "A trading idea is not a product until it survives testing.",
            "VASTcode21 is being built as a validation-first MT5 research system focused only on GOLD and BITCOIN. Candidates move through research, real-tick MT5 testing, robustness checks and forward observation before they can become release candidates.",
            "Dark technical vertical visual: four-stage pipeline Research → MT5 Real Ticks → Robustness → Forward. VASTcode21 logo, clean typography, no profit imagery.",
            80,
        ),
        post(
            "evergreen-002",
            "education",
            "Why real ticks matter in MT5 testing.",
            "A strategy can look impressive on simplified data and fail when execution detail is introduced. VASTcode21 uses real-tick MT5 validation as a gate, not as a marketing screenshot generator.",
            "15-second Reel/Short: animated tick stream entering an MT5 test gate, then PASS/REJECT split. Minimal futuristic style.",
            70,
        ),
        post(
            "evergreen-003",
            "scope",
            "Why only GOLD and BITCOIN?",
            "VASTcode21 deliberately stays narrow: GOLD and BITCOIN. The goal is deeper validation and cleaner product specialization rather than claiming to trade everything.",
            "Split-screen vertical creative: gold texture on one side, abstract Bitcoin network on the other, centered VASTcode21 mark.",
            65,
        ),
        post(
            "evergreen-004",
            "education",
            "Backtest ≠ future guarantee.",
            "A backtest is evidence from historical data, not a promise about tomorrow. VASTcode21 treats every pass as permission for more testing—not permission for hype.",
            "Bold typographic carousel: BACKTEST ≠ GUARANTEE. Second slide: PASS = MORE TESTING. Third slide: VASTcode21 validation stack.",
            75,
        ),
    ]

    if experiments > 0:
        items.append(post(
            "milestone-experiments",
            "research_progress",
            f"{experiments} research experiments and counting.",
            f"The VASTcode21 research engine has evaluated {experiments} experiments so far, reaching generation {generation}. Most candidates are expected to fail—because rejection is part of the validation process.",
            "Data-driven vertical graphic with large experiment count, generation number, and a funnel narrowing toward validation.",
            95,
        ))

    if mt5_passed > 0:
        items.append(post(
            "milestone-mt5-pass",
            "verified_milestone",
            "First real-tick MT5 validation milestone reached.",
            f"VASTcode21 has recorded {mt5_passed} MT5 real-tick PASS and {mt5_rejected} MT5 real-tick REJECT result(s) in the current research state. A PASS does not mean live-ready—it means the candidate is allowed to face stricter testing.",
            "Professional milestone card: MT5 REAL-TICK PASS. Small subtext: Next gate: robustness. Avoid P&L screenshots or money imagery.",
            100,
        ))

    if robustness_passed > 0:
        items.append(post(
            "milestone-robustness-pass",
            "verified_milestone",
            "A candidate survived the robustness gate.",
            f"The autonomous VASTcode21 pipeline now shows {robustness_passed} robustness PASS candidate(s). Next step: shadow-forward observation. No live-trading claim is being made.",
            "Validation ladder graphic highlighting Robustness PASS and Forward next.",
            100,
        ))

    if forward_collecting > 0:
        items.append(post(
            "milestone-forward",
            "verified_milestone",
            "Now collecting forward evidence.",
            f"{forward_collecting} VASTcode21 candidate(s) are in shadow-forward observation. This stage is intentionally slow: time and new market data are part of the test.",
            "Calendar/time visual with forward-observation progress bar, no performance promises.",
            100,
        ))

    if release_candidates > 0:
        items.append(post(
            "milestone-release-candidate",
            "product_milestone",
            "A VASTcode21 release candidate exists.",
            f"The validation pipeline currently shows {release_candidates} release candidate(s). This is still a controlled pre-release state and requires explicit human approval before any commercial or live-trading launch.",
            "Premium product reveal silhouette with RELEASE CANDIDATE badge and controlled-access feel.",
            100,
        ))

    items.extend([
        post(
            "evergreen-005",
            "engineering",
            "What happens when a strategy fails?",
            "It gets rejected. VASTcode21 is designed to keep failures in the research process instead of turning them into marketing claims. Failed candidates can inform future generations, but they do not become products.",
            "Red reject stamp over a generic strategy card, followed by mutation/exploration arrows toward new candidates.",
            60,
        ),
        post(
            "evergreen-006",
            "education",
            "Profit Factor is only one number.",
            "A serious validation process looks at more than one metric. Trade count, drawdown, recovery, Sharpe, regime behavior and forward evidence all matter before a candidate can advance.",
            "Metric dashboard visual with PF, DD, Recovery, Sharpe, Trades—no actual unapproved performance values.",
            65,
        ),
        post(
            "evergreen-007",
            "brand",
            "VASTcode21 is building in public—without exposing the core IP.",
            "The research logic and strategy parameters remain private. Public updates focus on process, validation stages and verified milestones.",
            "Encrypted core icon in center, public status ring around it; sleek cybersecurity + quant aesthetic.",
            60,
        ),
    ])

    items = sorted(items, key=lambda x: (-x["priority"], x["id"]))
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "pre_release_organic",
        "paid_ads": False,
        "live_trading": False,
        "source_status": {
            "experiments": experiments,
            "generation": generation,
            "mt5_validation_passed": mt5_passed,
            "mt5_validation_rejected": mt5_rejected,
            "robustness_passed": robustness_passed,
            "forward_collecting": forward_collecting,
            "release_candidates": release_candidates,
        },
        "items": items,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"generated": len(items), "output": str(OUT), "paid_ads": False, "live_trading": False}))


if __name__ == "__main__":
    main()

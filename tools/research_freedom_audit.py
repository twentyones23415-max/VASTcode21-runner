from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

VERSION = "1.0.0"

TEXT_EXTS = {".py", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".txt"}
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", "data", "reports", "artifacts"}

CLASSICAL_PATTERNS = {
    "ema": re.compile(r"\b(?:ema|exponential moving average)\b", re.I),
    "sma": re.compile(r"\b(?:sma|simple moving average)\b", re.I),
    "rsi": re.compile(r"\brsi\b", re.I),
    "macd": re.compile(r"\bmacd\b", re.I),
    "atr": re.compile(r"\batr\b", re.I),
    "bollinger": re.compile(r"\bbollinger\b", re.I),
    "stochastic": re.compile(r"\bstochastic\b", re.I),
    "ichimoku": re.compile(r"\bichimoku\b", re.I),
}

RESTRICTION_PATTERNS = {
    "indicator_whitelist": re.compile(r"(?:indicator|feature)[_-]?(?:white|allow)list|allowed[_-]?indicators", re.I),
    "strategy_whitelist": re.compile(r"strategy[_-]?(?:white|allow)list|allowed[_-]?strateg", re.I),
    "fixed_timeframe_list": re.compile(r"allowed[_-]?timeframes|timeframe[_-]?(?:white|allow)list", re.I),
    "fixed_parameter_family": re.compile(r"allowed[_-]?(?:parameters|params)|parameter[_-]?(?:white|allow)list", re.I),
    "classical_only_wording": re.compile(r"(?:only|must|required).{0,40}(?:ema|sma|rsi|macd|atr|bollinger|stochastic|ichimoku)", re.I),
}

CONTEXT_PATTERNS = {
    "news": re.compile(r"\bnews\b|headline|rss|article|event feed", re.I),
    "macro": re.compile(r"\bmacro\b|cpi|nfp|inflation|employment|gdp|fomc|federal reserve|central bank", re.I),
    "rates_fx": re.compile(r"yield|real rate|interest rate|dxy|usd|forex|fx", re.I),
    "cross_asset": re.compile(r"cross[-_ ]asset|correlation|lead[-_ ]lag|causal", re.I),
    "derivatives": re.compile(r"funding|open interest|liquidation|futures|options|basis", re.I),
    "onchain": re.compile(r"on[-_ ]?chain|exchange flow|miner|whale|stablecoin", re.I),
    "gold_flows": re.compile(r"gold.{0,30}(?:etf|flow|central bank|reserve|position)", re.I),
    "btc_etf": re.compile(r"(?:btc|bitcoin).{0,30}(?:etf|flow)", re.I),
    "geopolitics": re.compile(r"geopolit|war|sanction|systemic risk", re.I),
    "microstructure": re.compile(r"order book|market depth|spread|microstructure|tick volume", re.I),
}


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError(f"Expected JSON object: {path}")
    return data


def iter_text_files(root: Path):
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in TEXT_EXTS:
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        try:
            if p.stat().st_size > 2_000_000:
                continue
        except OSError:
            continue
        yield p


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("core", type=Path)
    parser.add_argument("freedom_contract", type=Path)
    parser.add_argument("context_contract", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    core = args.core.resolve()
    if not core.exists():
        raise SystemExit("ERROR: decrypted core directory not found")

    freedom = load_json(args.freedom_contract)
    context = load_json(args.context_contract)

    expected_assets = {"XAUUSD", "BTCUSD"}
    declared_assets = {str(x).upper() for x in freedom.get("tradable_assets", [])}
    context_assets = {str(x).upper() for x in context.get("execution_scope", [])}
    scope_ok = declared_assets == expected_assets and context_assets == expected_assets

    classical = {k: 0 for k in CLASSICAL_PATTERNS}
    restrictions = {k: 0 for k in RESTRICTION_PATTERNS}
    context_signals = {k: 0 for k in CONTEXT_PATTERNS}
    scanned = 0

    for path in iter_text_files(core):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        scanned += 1
        for name, rx in CLASSICAL_PATTERNS.items():
            classical[name] += len(rx.findall(text))
        for name, rx in RESTRICTION_PATTERNS.items():
            restrictions[name] += len(rx.findall(text))
        for name, rx in CONTEXT_PATTERNS.items():
            context_signals[name] += len(rx.findall(text))

    restriction_total = sum(restrictions.values())
    context_total = sum(context_signals.values())
    classical_total = sum(classical.values())

    payload = {
        "version": VERSION,
        "scope_contract_ok": scope_ok,
        "tradable_assets": ["XAUUSD", "BTCUSD"],
        "information_scope": "unbounded_relevant",
        "scanned_text_files": scanned,
        "freedom_status": "review_required" if restriction_total else "no_explicit_cage_detected",
        "explicit_restriction_signal_count": restriction_total,
        "restriction_signal_kinds": sorted([k for k, v in restrictions.items() if v]),
        "classical_indicator_reference_count": classical_total,
        "classical_indicator_families_referenced": sorted([k for k, v in classical.items() if v]),
        "context_intelligence_status": "signals_detected" if context_total else "no_static_context_signals_detected",
        "context_signal_count": context_total,
        "context_families_detected": sorted([k for k, v in context_signals.items() if v]),
        "privacy": "aggregate_only_no_private_paths_or_source_snippets",
        "note": "Classical-indicator references are not automatically a violation. Explicit whitelists/fixed search cages require review. Context families are examples, never a whitelist."
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    print("VASTcode21 RESEARCH FREEDOM AUDIT")
    print(f"Tradable scope contract: {'PASS' if scope_ok else 'FAIL'}")
    print(f"Private core files scanned: {scanned}")
    print(f"Explicit restriction signals: {restriction_total}")
    print(f"Context intelligence signals: {context_total}")
    print(f"Freedom status: {payload['freedom_status']}")
    print("Private source paths/snippets were not published.")
    return 0 if scope_ok else 4


if __name__ == "__main__":
    raise SystemExit(main())

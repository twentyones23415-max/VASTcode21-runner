from __future__ import annotations

import base64
import binascii
import json
import re
from dataclasses import dataclass
from typing import Any

MAX_IMAGE_BYTES = 8 * 1024 * 1024
ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp"}
DATA_URL_RE = re.compile(r"^data:(image/(?:png|jpeg|webp));base64,([A-Za-z0-9+/=\r\n]+)$")

PNG = b"\x89PNG\r\n\x1a\n"
JPEG = b"\xff\xd8\xff"
WEBP_RIFF = b"RIFF"
WEBP_TAG = b"WEBP"


class ContractError(ValueError):
    pass


@dataclass(frozen=True)
class ValidatedImage:
    mime: str
    raw: bytes
    data_url: str


def validate_image_data_url(value: str) -> ValidatedImage:
    if not isinstance(value, str):
        raise ContractError("image_data_url must be a string")
    match = DATA_URL_RE.fullmatch(value.strip())
    if not match:
        raise ContractError("Only PNG, JPEG or WEBP base64 data URLs are accepted")
    mime, encoded = match.groups()
    if mime not in ALLOWED_MIME:
        raise ContractError("Unsupported image type")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ContractError("Invalid base64 image payload") from exc
    if not raw:
        raise ContractError("Image is empty")
    if len(raw) > MAX_IMAGE_BYTES:
        raise ContractError("Image exceeds the 8 MB server-side limit")
    if mime == "image/png" and not raw.startswith(PNG):
        raise ContractError("PNG signature mismatch")
    if mime == "image/jpeg" and not raw.startswith(JPEG):
        raise ContractError("JPEG signature mismatch")
    if mime == "image/webp" and not (raw.startswith(WEBP_RIFF) and raw[8:12] == WEBP_TAG):
        raise ContractError("WEBP signature mismatch")
    return ValidatedImage(mime=mime, raw=raw, data_url=value.strip())


def build_analysis_instructions(context: dict[str, Any] | None = None) -> str:
    context = context or {}
    event = context.get("event_risk") if isinstance(context.get("event_risk"), dict) else {}
    market = context.get("market") if isinstance(context.get("market"), dict) else {}
    intelligence = context.get("market_intelligence") if isinstance(context.get("market_intelligence"), dict) else {}
    return "\n".join([
        "You are VAST Vision AI, an educational chart-review assistant.",
        "Analyze only evidence visible in the screenshot and explicitly supplied verified context.",
        "Never invent symbol, timeframe, prices, news, indicators, accuracy, entries, exits or position sizing.",
        "If symbol or timeframe is not visible, return 'unknown'.",
        "Treat market-intelligence items only as timestamped contextual information; never treat them as live price data or proof of chart direction.",
        "If any supplied context has status other than 'verified', treat that dependency as unavailable and say so rather than inferring missing facts.",
        "Return JSON only with keys: symbol, timeframe, visible_structure, scenarios, event_risk, market_context, uncertainty, educational_takeaway.",
        "scenarios must contain bullish, bearish and neutral objects; each has evidence and invalidation arrays.",
        "This is educational analysis, not a trade instruction.",
        f"Verified event context: {json.dumps(event, ensure_ascii=False, separators=(',', ':'))}",
        f"Verified market-price context: {json.dumps(market, ensure_ascii=False, separators=(',', ':'))}",
        f"Verified market-intelligence/news context: {json.dumps(intelligence, ensure_ascii=False, separators=(',', ':'))}",
    ])


def normalize_analysis(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ContractError("AI response must be a JSON object")
    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, dict):
        raise ContractError("AI response is missing scenarios")
    clean_scenarios: dict[str, dict[str, list[str]]] = {}
    for name in ("bullish", "bearish", "neutral"):
        item = scenarios.get(name)
        if not isinstance(item, dict):
            raise ContractError(f"AI response is missing {name} scenario")
        evidence = item.get("evidence")
        invalidation = item.get("invalidation")
        if not isinstance(evidence, list) or not isinstance(invalidation, list):
            raise ContractError(f"{name} scenario must contain evidence and invalidation arrays")
        clean_scenarios[name] = {
            "evidence": [str(x)[:500] for x in evidence[:8]],
            "invalidation": [str(x)[:500] for x in invalidation[:8]],
        }
    return {
        "symbol": str(payload.get("symbol") or "unknown")[:40],
        "timeframe": str(payload.get("timeframe") or "unknown")[:40],
        "visible_structure": str(payload.get("visible_structure") or "")[:3000],
        "scenarios": clean_scenarios,
        "event_risk": payload.get("event_risk") if isinstance(payload.get("event_risk"), dict) else {},
        "market_context": payload.get("market_context") if isinstance(payload.get("market_context"), dict) else {},
        "uncertainty": str(payload.get("uncertainty") or "Unknown information is intentionally left unknown.")[:1500],
        "educational_takeaway": str(payload.get("educational_takeaway") or "")[:2000],
    }

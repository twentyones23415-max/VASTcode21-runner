from __future__ import annotations

import base64
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from tutor_vision_contract import (  # noqa: E402
    ContractError,
    build_analysis_instructions,
    normalize_analysis,
    validate_image_data_url,
)


class TutorVisionContractTests(unittest.TestCase):
    def data_url(self, mime: str, raw: bytes) -> str:
        return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"

    def test_accepts_valid_png_signature(self):
        value = self.data_url("image/png", b"\x89PNG\r\n\x1a\n" + b"x" * 32)
        image = validate_image_data_url(value)
        self.assertEqual(image.mime, "image/png")
        self.assertGreater(len(image.raw), 8)

    def test_rejects_mime_signature_mismatch(self):
        value = self.data_url("image/png", b"\xff\xd8\xff" + b"x" * 32)
        with self.assertRaises(ContractError):
            validate_image_data_url(value)

    def test_rejects_non_image_data_url(self):
        value = "data:text/plain;base64," + base64.b64encode(b"hello").decode("ascii")
        with self.assertRaises(ContractError):
            validate_image_data_url(value)

    def test_analysis_instructions_include_verified_market_intelligence(self):
        context = {
            "event_risk": {"status": "verified", "nearest": {"title": "CPI"}},
            "market": {"status": "unavailable", "markets": {}},
            "market_intelligence": {
                "status": "verified",
                "updated_at": "2026-09-13T21:39:00+00:00",
                "items": [{"title": "Gold context headline", "source": "official"}],
            },
        }
        prompt = build_analysis_instructions(context)
        self.assertIn("Gold context headline", prompt)
        self.assertIn("Verified market-intelligence/news context", prompt)
        self.assertIn("never treat them as live price data", prompt)
        self.assertIn('"status":"unavailable"', prompt)

    def test_normalizes_required_scenario_shape(self):
        payload = {
            "symbol": "XAUUSD",
            "timeframe": "M15",
            "visible_structure": "Range with a visible rejection.",
            "scenarios": {
                "bullish": {"evidence": ["higher low"], "invalidation": ["break below range"]},
                "bearish": {"evidence": ["failed breakout"], "invalidation": ["close above high"]},
                "neutral": {"evidence": ["inside range"], "invalidation": ["clean breakout"]},
            },
            "uncertainty": "Price labels are partly obscured.",
            "educational_takeaway": "Separate evidence from prediction.",
        }
        clean = normalize_analysis(json.loads(json.dumps(payload)))
        self.assertEqual(clean["symbol"], "XAUUSD")
        self.assertEqual(set(clean["scenarios"]), {"bullish", "bearish", "neutral"})

    def test_rejects_incomplete_ai_shape(self):
        with self.assertRaises(ContractError):
            normalize_analysis({"scenarios": {"bullish": {"evidence": [], "invalidation": []}}})


if __name__ == "__main__":
    unittest.main()

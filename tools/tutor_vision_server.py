from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from tutor_vision_contract import ContractError, build_analysis_instructions, normalize_analysis, validate_image_data_url

ROOT = Path(__file__).resolve().parents[1]
EVENT_PATH = ROOT / "site" / "data" / "event_risk.json"
MARKET_PATH = ROOT / "site" / "data" / "market_feed.json"
MAX_BODY_BYTES = 12 * 1024 * 1024
OPENAI_URL = "https://api.openai.com/v1/responses"
MODEL = os.environ.get("VAST_VISION_MODEL", "gpt-5.6-luna")
ALLOWED_ORIGIN = os.environ.get("VAST_TUTOR_ORIGIN", "")


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def verified_context() -> dict[str, Any]:
    event = load_json(EVENT_PATH)
    market = load_json(MARKET_PATH)
    return {
        "event_risk": {
            "status": event.get("status", "unknown"),
            "updated_at": event.get("updated_at"),
            "nearest": event.get("nearest"),
            "urgent": event.get("urgent", []),
        },
        "market": {
            "status": market.get("status", "unknown"),
            "updated_at": market.get("updated_at"),
            "markets": market.get("markets", {}),
        },
    }


def extract_response_text(payload: dict[str, Any]) -> str:
    direct = payload.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    for item in payload.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and isinstance(content.get("text"), str):
                return content["text"].strip()
    raise RuntimeError("AI provider returned no text output")


def call_openai(image_data_url: str, context: dict[str, Any]) -> dict[str, Any]:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("VISION_BACKEND_NOT_CONFIGURED")
    body = {
        "model": MODEL,
        "input": [{
            "role": "user",
            "content": [
                {"type": "input_text", "text": build_analysis_instructions(context)},
                {"type": "input_image", "image_url": image_data_url},
            ],
        }],
    }
    request = urllib.request.Request(
        OPENAI_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "VASTcode21-TutorVision/0.1",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=75) as response:
            provider = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:800]
        raise RuntimeError(f"VISION_PROVIDER_HTTP_{exc.code}: {detail}") from exc
    text = extract_response_text(provider)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("VISION_PROVIDER_INVALID_JSON") from exc
    return normalize_analysis(parsed)


class Handler(BaseHTTPRequestHandler):
    server_version = "VASTTutorVision/0.1"

    def _headers(self, status: int, content_type: str = "application/json") -> None:
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        if ALLOWED_ORIGIN:
            self.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGIN)
            self.send_header("Vary", "Origin")
        self.end_headers()

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        self._headers(status)
        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        if ALLOWED_ORIGIN:
            self.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGIN)
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/healthz":
            configured = bool(os.environ.get("OPENAI_API_KEY", "").strip())
            self._json(HTTPStatus.OK, {"ok": True, "vision_provider_configured": configured, "model": MODEL})
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:
        if self.path != "/v1/vision/analyze":
            self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY_BYTES:
            self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "invalid_body_size"})
            return
        try:
            request = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(request, dict):
                raise ContractError("Request must be a JSON object")
            image = validate_image_data_url(request.get("image_data_url"))
            context = verified_context()
            result = call_openai(image.data_url, context)
            self._json(HTTPStatus.OK, {
                "version": "0.1",
                "analysis": result,
                "context": context,
                "privacy": {"stored": False, "retention": "request-memory-only"},
                "notice": "Educational chart review only; not a trade instruction or guarantee.",
            })
        except ContractError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid_request", "detail": str(exc)})
        except RuntimeError as exc:
            message = str(exc)
            if message == "VISION_BACKEND_NOT_CONFIGURED":
                self._json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "vision_backend_not_configured"})
            else:
                self._json(HTTPStatus.BAD_GATEWAY, {"error": "vision_provider_failure", "detail": message[:500]})
        except Exception:
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "internal_error"})

    def log_message(self, fmt: str, *args: Any) -> None:
        print("[VAST Tutor Vision] " + (fmt % args), flush=True)


def main() -> None:
    host = os.environ.get("VAST_TUTOR_HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", os.environ.get("VAST_TUTOR_PORT", "8787")))
    print(f"VAST Tutor Vision beta endpoint listening on {host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()

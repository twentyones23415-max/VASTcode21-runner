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
    changed = 0

    for item in payload.get("items", []):
        if not isinstance(item, dict):
            continue
        if str(item.get("pillar") or "").lower() != "services":
            continue

        caption = str(item.get("caption") or "")
        clean_lines = []
        for line in caption.splitlines():
            lower = line.lower()
            if "http://" in lower or "https://" in lower:
                continue
            clean_lines.append(line)
        clean_caption = "\n".join(clean_lines).strip()

        cta = "Research Brief, MT5 Audit and VAST Early Access — use the links in bio."
        if clean_caption != caption or item.get("cta") != cta or not item.get("bio_links_ready"):
            item["caption"] = clean_caption
            item["cta"] = cta
            item["bio_links_ready"] = True
            changed += 1

    QUEUE.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"service_items_updated": changed, "links_in_bio": True}))


if __name__ == "__main__":
    main()

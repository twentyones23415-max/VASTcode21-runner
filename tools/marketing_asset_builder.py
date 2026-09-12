from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "marketing" / "queue.json"
OUT = ROOT / "marketing" / "assets"
W, H = 1080, 1350


def font(size: int, bold: bool = False):
    paths = [
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
    ]
    for p in paths:
        if p.exists():
            return ImageFont.truetype(str(p), size=size)
    return ImageFont.load_default()


def fit_lines(draw: ImageDraw.ImageDraw, text: str, fnt, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    line = ""
    for word in words:
        trial = f"{line} {word}".strip()
        bbox = draw.textbbox((0, 0), trial, font=fnt)
        if bbox[2] - bbox[0] <= max_width:
            line = trial
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def draw_card(item: dict, path: Path) -> None:
    img = Image.new("RGB", (W, H), (8, 12, 22))
    px = img.load()
    for y in range(H):
        t = y / H
        base = int(12 + 18 * t)
        for x in range(W):
            glow = max(0, 1 - abs(x - W * 0.75) / (W * 0.75))
            px[x, y] = (8 + int(8 * glow), 12 + int(14 * glow), base + int(20 * glow))
    draw = ImageDraw.Draw(img)
    gold = (225, 186, 86)
    cyan = (74, 203, 255)
    white = (238, 243, 248)
    muted = (153, 166, 181)
    draw.rounded_rectangle((72, 70, 1008, 1280), radius=34, outline=(45, 58, 78), width=2, fill=(10, 16, 29))
    draw.rounded_rectangle((92, 92, 988, 210), radius=28, fill=(15, 25, 43))
    draw.text((120, 122), "VAST", font=font(64, True), fill=white)
    draw.text((300, 122), "code21", font=font(64, True), fill=cyan)
    pillar = str(item.get("pillar") or "research").upper().replace("_", " ")
    draw.text((120, 225), pillar, font=font(26, True), fill=gold)
    hook = str(item.get("hook") or "").strip()
    hook_font = font(58, True)
    y = 315
    for line in fit_lines(draw, hook, hook_font, 820)[:6]:
        draw.text((120, y), line, font=hook_font, fill=white)
        y += 76
    draw.line((120, y + 20, 920, y + 20), fill=(45, 58, 78), width=2)
    y += 62
    body = str(item.get("caption") or "").strip()
    body_font = font(30, False)
    body_lines = fit_lines(draw, body, body_font, 820)
    for line in body_lines[:9]:
        draw.text((120, y), line, font=body_font, fill=muted)
        y += 45
    footer_y = 1110
    draw.rounded_rectangle((120, footer_y, 960, footer_y + 76), radius=18, fill=(18, 31, 50))
    draw.text((150, footer_y + 20), "GOLD  •  BITCOIN  •  MT5  •  VALIDATION FIRST", font=font(25, True), fill=gold)
    draw.text((120, 1220), "Trading involves risk. Backtests do not guarantee future performance.", font=font(22), fill=(122, 136, 152))
    img.save(path, format="JPEG", quality=91, optimize=True)


def main() -> None:
    if not QUEUE.exists():
        raise SystemExit("marketing/queue.json not found")
    payload = json.loads(QUEUE.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    generated = 0
    for item in payload.get("items", []):
        if not isinstance(item, dict) or str(item.get("status")) != "ready_for_design":
            continue
        pid = str(item.get("id") or "").strip()
        if not pid:
            continue
        path = OUT / f"{pid}.jpg"
        draw_card(item, path)
        generated += 1
    print(json.dumps({"generated_assets": generated, "output": str(OUT)}))


if __name__ == "__main__":
    main()

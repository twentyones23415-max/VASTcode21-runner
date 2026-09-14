#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import random
import subprocess
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "marketing" / "assets"
QUEUE = ROOT / "marketing" / "queue.json"
W, H = 540, 960
FPS = 12
DURATION = 15.0
SR = 44100

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def font(size: int, bold: bool = False):
    try:
        return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)
    except Exception:
        return ImageFont.load_default()


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def ease(x: float) -> float:
    x = clamp(x)
    return x * x * (3 - 2 * x)


def fade_window(t: float, start: float, end: float, edge: float = 0.25) -> float:
    if t < start or t > end:
        return 0.0
    return min(ease((t - start) / edge), ease((end - t) / edge))


def centered(draw: ImageDraw.ImageDraw, text: str, y: int, fnt, fill, stroke=0, stroke_fill=None):
    box = draw.multiline_textbbox((0, 0), text, font=fnt, align="center", spacing=6, stroke_width=stroke)
    tw = box[2] - box[0]
    draw.multiline_text(((W - tw) / 2, y), text, font=fnt, fill=fill, align="center", spacing=6,
                        stroke_width=stroke, stroke_fill=stroke_fill)


def draw_chart(draw: ImageDraw.ImageDraw, t: float, y0: int, height: int, seed: int, bright=(245, 190, 58)):
    rnd = random.Random(seed)
    pts = []
    n = 26
    val = 0.52
    vals = []
    for i in range(n):
        val += rnd.uniform(-0.12, 0.12)
        val = max(0.12, min(0.88, val))
        vals.append(val)
    reveal = int((n - 1) * clamp((t % 4.0) / 2.4)) + 1
    for i in range(reveal):
        x = 24 + i * (W - 48) / (n - 1)
        y = y0 + height * (1.0 - vals[i])
        pts.append((x, y))
    for gy in range(5):
        yy = y0 + gy * height / 4
        draw.line((20, yy, W - 20, yy), fill=(38, 45, 58), width=1)
    if len(pts) > 1:
        draw.line(pts, fill=bright, width=5, joint="curve")
        x, y = pts[-1]
        r = 7 + int(4 * (0.5 + 0.5 * math.sin(t * 8)))
        draw.ellipse((x-r, y-r, x+r, y+r), fill=bright)


def base_frame(bg=(7, 10, 16)):
    return Image.new("RGB", (W, H), bg)


def render_xauusd(t: float) -> Image.Image:
    img = base_frame((8, 11, 18))
    d = ImageDraw.Draw(img)

    # Moving chart and ticker backdrop.
    draw_chart(d, t, 118, 250, seed=21, bright=(235, 190, 68))
    for i in range(8):
        x = int((i * 92 - (t * 48) % 92))
        d.line((x, 0, x, H), fill=(18, 22, 31), width=1)

    d.rounded_rectangle((18, 20, W-18, 78), radius=18, fill=(19, 24, 34))
    d.text((34, 37), "VASTcode21  •  GOLD / MT5", font=font(22, True), fill=(230, 232, 237))

    segments = [
        (0.0, 2.7, "3 XAUUSD MISTAKES\nBEFORE HIGH-IMPACT NEWS", (255, 235, 180)),
        (2.7, 5.7, "1", (255, 205, 78)),
        (5.7, 8.7, "2", (255, 205, 78)),
        (8.7, 11.7, "3", (255, 205, 78)),
        (11.7, 15.0, "SAVE THIS\nFOLLOW @vast.code21", (235, 240, 248)),
    ]
    alpha = 0.0
    for start, end, label, col in segments:
        if start <= t <= end:
            alpha = fade_window(t, start, end, 0.22)
            if label == "1":
                d.rounded_rectangle((34, 420, W-34, 690), radius=28, fill=(15, 19, 27), outline=(72, 62, 35), width=2)
                centered(d, "1", 440, font(70, True), (255, 205, 78))
                centered(d, "CHASING\nTHE FIRST SPIKE", 525, font(40, True), (238, 240, 244))
            elif label == "2":
                d.rounded_rectangle((34, 420, W-34, 690), radius=28, fill=(15, 19, 27), outline=(72, 62, 35), width=2)
                centered(d, "2", 440, font(70, True), (255, 205, 78))
                centered(d, "IGNORING\nSPREAD / LIQUIDITY", 525, font(37, True), (238, 240, 244))
            elif label == "3":
                d.rounded_rectangle((34, 420, W-34, 690), radius=28, fill=(15, 19, 27), outline=(72, 62, 35), width=2)
                centered(d, "3", 440, font(70, True), (255, 205, 78))
                centered(d, "FIRST MOVE ≠\nFINAL MOVE", 525, font(40, True), (238, 240, 244))
            else:
                # kinetic vertical offset on hook/CTA
                off = int((1 - alpha) * 42)
                if start < 1:
                    centered(d, label, 438 + off, font(42, True), col, stroke=2, stroke_fill=(0,0,0))
                    centered(d, "Fast moves punish slow thinking.", 575 + off, font(23), (178, 187, 201))
                else:
                    centered(d, label, 475 + off, font(43, True), col)
                    centered(d, "Educational context only • Trading involves risk", 720, font(17), (145, 152, 166))
            break
    return img


def render_build(t: float) -> Image.Image:
    img = base_frame((3, 8, 8))
    d = ImageDraw.Draw(img)

    # Terminal grid + scan line.
    for x in range(0, W, 36):
        d.line((x, 0, x, H), fill=(8, 22, 22), width=1)
    for y in range(0, H, 36):
        d.line((0, y, W, y), fill=(8, 22, 22), width=1)
    scan = int((t * 180) % H)
    d.rectangle((0, scan, W, min(H, scan+3)), fill=(16, 72, 63))

    d.text((24, 24), "VASTcode21 // LAB", font=font(22, True), fill=(87, 230, 198))
    d.text((24, 60), "validation_pipeline.log", font=font(16), fill=(88, 128, 121))

    # fake terminal feed, deliberately generic and non-performance related
    lines = [
        "[TEST] candidate loaded",
        "[CHECK] real-tick gate",
        "[FAIL] reject weak evidence",
        "[LOOP] mutate + retest",
        "[RULE] no hype / no guarantees",
    ]
    y = 130
    for i, line in enumerate(lines):
        if t > 0.6 + i * 0.35:
            d.text((30, y), line, font=font(19), fill=(113, 188, 169))
        y += 38

    if t < 3.0:
        centered(d, "MOST TRADING SYSTEMS\nSHOW THE WIN", 410, font(42, True), (226, 236, 233))
        centered(d, "We care about what fails too.", 545, font(22), (112, 174, 160))
    elif t < 6.0:
        d.rounded_rectangle((44, 390, W-44, 650), radius=24, fill=(8, 20, 19), outline=(35, 105, 91), width=2)
        centered(d, "WE SHOW\nTHE REJECTS TOO", 445, font(46, True), (91, 235, 199))
        d.rectangle((90, 598, W-90, 612), fill=(36, 66, 60))
        d.rectangle((90, 598, 90 + int((W-180)*clamp((t-3)/3)), 612), fill=(91, 235, 199))
    elif t < 11.0:
        steps = ["TEST", "REJECT", "IMPROVE", "RETEST"]
        centered(d, "BUILD LOOP", 350, font(28, True), (117, 173, 160))
        for i, s in enumerate(steps):
            yy = 420 + i * 88
            active = int((t - 6.0) / 1.15) >= i
            fill = (91, 235, 199) if active else (51, 78, 72)
            d.rounded_rectangle((88, yy, W-88, yy+58), radius=15, outline=fill, width=3)
            centered(d, s, yy+12, font(26, True), fill)
    else:
        centered(d, "FOLLOW THE BUILD,\nNOT THE HYPE", 430, font(48, True), (224, 239, 234))
        centered(d, "@vast.code21", 565, font(31, True), (91, 235, 199))
        centered(d, "Research & education only • Trading involves risk", 720, font(17), (119, 149, 142))
    return img


def write_music(path: Path, mood: str):
    random.seed(21 if mood == "gold" else 84)
    total = int(DURATION * SR)
    beat = 0.5 if mood == "gold" else 0.6
    scale = [55.0, 65.41, 73.42, 82.41] if mood == "gold" else [46.25, 55.0, 61.74, 69.30]
    data = bytearray()
    for n in range(total):
        t = n / SR
        bpos = t % beat
        kick = 0.0
        if bpos < 0.16:
            env = math.exp(-26*bpos)
            kick = math.sin(2*math.pi*(66 - 22*(bpos/0.16))*bpos) * env * 0.55
        hpos = t % (beat/2)
        hat = 0.0
        if hpos < 0.035:
            env = math.exp(-85*hpos)
            # deterministic metallic hat
            hat = (math.sin(2*math.pi*4200*t) + 0.6*math.sin(2*math.pi*6900*t)) * env * 0.08
        idx = int(t / (beat*2)) % len(scale)
        bass_f = scale[idx]
        bass = math.sin(2*math.pi*bass_f*t) * 0.14
        pulse = math.sin(2*math.pi*(bass_f*2)*t) * (0.06 if mood == "gold" else 0.04)
        pad = math.sin(2*math.pi*(220 if mood == "gold" else 174.61)*t) * 0.018
        glitch = 0.0
        if mood != "gold" and (int(t*4) % 8 == 7):
            glitch = math.sin(2*math.pi*1200*t) * 0.035
        sample = max(-0.92, min(0.92, kick + hat + bass + pulse + pad + glitch))
        iv = int(sample * 32767)
        data += int(iv).to_bytes(2, byteorder="little", signed=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(data)


def encode_reel(reel_id: str, renderer, mood: str):
    ASSETS.mkdir(parents=True, exist_ok=True)
    wav = ASSETS / f".{reel_id}.wav"
    out = ASSETS / f"{reel_id}.mp4"
    cover = ASSETS / f"{reel_id}.jpg"
    write_music(wav, mood)

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", str(wav), "-shortest",
        "-c:v", "libx264", "-preset", "medium", "-crf", "22", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    frames = int(DURATION * FPS)
    for i in range(frames):
        t = i / FPS
        frame = renderer(t)
        if i == int(1.0 * FPS):
            frame.save(cover, quality=92)
        proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    rc = proc.wait()
    wav.unlink(missing_ok=True)
    if rc != 0:
        raise SystemExit(f"ffmpeg failed for {reel_id}: {rc}")

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_name", "-of", "csv=p=0", str(out)],
        capture_output=True, text=True, check=True,
    )
    if "aac" not in probe.stdout.lower():
        raise SystemExit(f"audio verification failed for {reel_id}: {probe.stdout!r}")
    print(f"generated {out.name} with verified AAC audio")


def update_queue():
    q = json.loads(QUEUE.read_text(encoding="utf-8"))
    new_items = [
        {
            "id": "growth-xauusd-mistakes-v1",
            "pillar": "education",
            "hook": "3 XAUUSD mistakes before high-impact news.",
            "caption": "Fast news moves can punish rushed decisions. Three common mistakes to avoid: chasing the first spike, ignoring spread/liquidity, and assuming the first move is the final move.",
            "creative_brief": "Dynamic 9:16 GOLD Reel with animated chart motion, kinetic typography, fast cuts and original electronic background music.",
            "format": "reel",
            "platforms": ["Instagram"],
            "priority": 520,
            "status": "ready_for_design",
            "hashtags": ["#XAUUSD", "#GoldTrading", "#MT5", "#TradingEducation", "#RiskManagement", "#VASTcode21"],
            "cta": "Save this and follow @vast.code21 for practical GOLD / BTC / MT5 research.",
            "disclaimer": "Educational context only. Trading involves risk.",
            "audio": "embedded_original_electronic",
            "growth_hypothesis": "fast_hook_saveable_news_risk_education"
        },
        {
            "id": "growth-build-public-v1",
            "pillar": "build_in_public",
            "hook": "Most trading systems show the win. We show the rejects too.",
            "caption": "VASTcode21 is being built in public: test, reject weak evidence, improve, and retest. The goal is a stronger process—not hype.",
            "creative_brief": "9:16 engineering/terminal Reel with code-style visuals, test/reject stamps, glitch motion and original industrial-electronic music. Visually distinct from the GOLD Reel.",
            "format": "reel",
            "platforms": ["Instagram"],
            "priority": 510,
            "status": "ready_for_design",
            "hashtags": ["#VASTcode21", "#MetaTrader5", "#QuantTrading", "#SystematicTrading", "#TradingResearch", "#AlgoTrading"],
            "cta": "Follow @vast.code21 to watch the build—not the hype.",
            "disclaimer": "Research and education only. Trading involves risk.",
            "audio": "embedded_original_industrial",
            "growth_hypothesis": "transparent_build_in_public_follow_conversion"
        }
    ]
    ids = {x["id"] for x in new_items}
    old = [x for x in q.get("items", []) if x.get("id") not in ids]
    q["items"] = new_items + old
    q["mode"] = "zero_to_ten_growth_sprint"
    q.setdefault("growth_strategy", {})
    q["growth_strategy"].update({
        "stage": "zero_to_ten",
        "principle": "discovery_saves_shares_and_follow_conversion_before_sales",
        "creative_rotation": "do_not_repeat_same_visual_style_on_consecutive_posts",
        "reel_audio_required": True,
        "next_focus": ["XAUUSD risk education", "build in public", "MT5 practical education"]
    })
    QUEUE.write_text(json.dumps(q, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    encode_reel("growth-xauusd-mistakes-v1", render_xauusd, "gold")
    encode_reel("growth-build-public-v1", render_build, "industrial")
    update_queue()


if __name__ == "__main__":
    main()

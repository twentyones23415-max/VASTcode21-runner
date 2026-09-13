from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "marketing" / "queue.json"
OUT = ROOT / "marketing" / "assets"
W, H = 1080, 1350
RW, RH = 1080, 1920


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
    output: list[str] = []
    for paragraph in str(text).split("\n"):
        words = paragraph.split()
        line = ""
        if not words:
            output.append("")
            continue
        for word in words:
            trial = f"{line} {word}".strip()
            bbox = draw.textbbox((0, 0), trial, font=fnt)
            if bbox[2] - bbox[0] <= max_width:
                line = trial
            else:
                if line:
                    output.append(line)
                line = word
        if line:
            output.append(line)
    return output


def palette():
    return {
        "bg": (8, 12, 22),
        "panel": (10, 16, 29),
        "panel2": (15, 25, 43),
        "line": (45, 58, 78),
        "gold": (225, 186, 86),
        "cyan": (74, 203, 255),
        "white": (238, 243, 248),
        "muted": (153, 166, 181),
    }


def base_image(width: int, height: int) -> Image.Image:
    p = palette()
    img = Image.new("RGB", (width, height), p["bg"])
    draw = ImageDraw.Draw(img)
    for x in range(0, width, 80):
        draw.line((x, 0, x, height), fill=(11, 21, 34), width=1)
    for y in range(0, height, 80):
        draw.line((0, y, width, y), fill=(11, 21, 34), width=1)
    draw.rounded_rectangle((55, 55, width - 55, height - 55), radius=38, outline=p["line"], width=2, fill=p["panel"])
    draw.rounded_rectangle((78, 80, width - 78, 205), radius=28, fill=p["panel2"])
    draw.text((105, 112), "VAST", font=font(62, True), fill=p["white"])
    draw.text((287, 112), "code21", font=font(62, True), fill=p["cyan"])
    return img


def draw_cta(draw: ImageDraw.ImageDraw, y: int, width: int, text: str) -> None:
    p = palette()
    draw.rounded_rectangle((105, y, width - 105, y + 88), radius=20, fill=(18, 31, 50))
    lines = fit_lines(draw, text, font(25, True), width - 260)
    for i, line in enumerate(lines[:2]):
        draw.text((135, y + 15 + i * 31), line, font=font(25, True), fill=p["gold"])


def draw_card(item: dict, path: Path) -> None:
    p = palette()
    img = base_image(W, H)
    draw = ImageDraw.Draw(img)
    pillar = str(item.get("pillar") or "research").upper().replace("_", " ")
    draw.text((105, 230), pillar, font=font(25, True), fill=p["gold"])
    hook = str(item.get("hook") or "").strip()
    y = 310
    hook_font = font(55, True)
    for line in fit_lines(draw, hook, hook_font, 860)[:6]:
        draw.text((105, y), line, font=hook_font, fill=p["white"])
        y += 72
    draw.line((105, y + 20, 975, y + 20), fill=p["line"], width=2)
    y += 58
    body = str(item.get("caption") or "").strip()
    body_font = font(29)
    for line in fit_lines(draw, body, body_font, 860)[:8]:
        draw.text((105, y), line, font=body_font, fill=p["muted"])
        y += 43
    draw_cta(draw, 1090, W, str(item.get("cta") or "Follow @vast.code21 for transparent MT5 research."))
    draw.text((105, 1235), "GOLD  •  BITCOIN  •  MT5  •  VALIDATION FIRST", font=font(22, True), fill=p["gold"])
    draw.text((105, 1270), "Trading involves risk. Backtests do not guarantee future performance.", font=font(18), fill=(122, 136, 152))
    img.save(path, format="JPEG", quality=91, optimize=True)


def carousel_slide(item: dict, slide: int, path: Path) -> None:
    p = palette()
    img = base_image(W, H)
    draw = ImageDraw.Draw(img)
    pillar = str(item.get("pillar") or "education").upper().replace("_", " ")
    draw.text((105, 235), f"{pillar}  •  {slide}/3", font=font(24, True), fill=p["gold"])

    hook = str(item.get("hook") or "").strip()
    body = str(item.get("caption") or "").strip()
    if slide == 1:
        title = hook
        subtitle = "Swipe →"
    elif slide == 2:
        title = "THE CHECK"
        subtitle = body
    else:
        title = "SAVE THE PROCESS"
        subtitle = str(item.get("cta") or "Follow @vast.code21 for the next research update.")

    y = 355
    for line in fit_lines(draw, title, font(62, True), 850)[:6]:
        draw.text((105, y), line, font=font(62, True), fill=p["white"])
        y += 80
    y += 25
    for line in fit_lines(draw, subtitle, font(31), 850)[:10]:
        draw.text((105, y), line, font=font(31), fill=p["muted"])
        y += 47

    if slide == 3:
        draw_cta(draw, 1070, W, str(item.get("cta") or "Follow @vast.code21"))
    draw.text((105, 1240), "VASTcode21  •  GOLD  •  BITCOIN  •  MT5", font=font(22, True), fill=p["gold"])
    img.save(path, format="JPEG", quality=91, optimize=True)


def reel_frame(item: dict, slide: int, path: Path) -> None:
    p = palette()
    img = base_image(RW, RH)
    draw = ImageDraw.Draw(img)
    pillar = str(item.get("pillar") or "research").upper().replace("_", " ")
    draw.text((105, 245), f"{pillar}  •  {slide}/3", font=font(27, True), fill=p["gold"])

    script = item.get("reel_script") if isinstance(item.get("reel_script"), list) else []
    scripted = str(script[slide - 1]).strip() if len(script) >= slide else ""
    hook = str(item.get("hook") or "").strip()
    if scripted:
        title = scripted
    elif slide == 1:
        title = hook
    elif slide == 2:
        title = "CHECK THE EVIDENCE"
    else:
        title = "FOLLOW THE NEXT TEST"

    if slide == 1:
        subtitle = "VASTcode21 · research in public"
    elif slide == 2:
        subtitle = "GOLD · BITCOIN · MT5"
    else:
        subtitle = str(item.get("cta") or "Follow @vast.code21 for transparent MT5 research.")

    accent_y = 390
    draw.rounded_rectangle((105, accent_y, 295, accent_y + 12), radius=6, fill=p["cyan"])
    y = 500
    for line in fit_lines(draw, title, font(76, True), 850)[:7]:
        draw.text((105, y), line, font=font(76, True), fill=p["white"])
        y += 98
    y += 34
    for line in fit_lines(draw, subtitle, font(34), 850)[:7]:
        draw.text((105, y), line, font=font(34), fill=p["muted"])
        y += 52

    draw.rounded_rectangle((105, 1550, 975, 1730), radius=26, fill=(18, 31, 50), outline=p["line"], width=2)
    draw.text((135, 1590), "VAST PULSE", font=font(25, True), fill=p["cyan"])
    draw.text((135, 1640), "VALIDATION > HYPE", font=font(35, True), fill=p["gold"])
    draw.text((105, 1810), "@vast.code21", font=font(30, True), fill=p["cyan"])
    img.save(path, format="JPEG", quality=91, optimize=True)


def build_reel(item: dict, pid: str) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print(f"ffmpeg unavailable; reel {pid} will fall back to image publishing")
        return False

    frames: list[Path] = []
    clips: list[Path] = []
    for slide in range(1, 4):
        frame = OUT / f"{pid}-reel-{slide}.jpg"
        reel_frame(item, slide, frame)
        frames.append(frame)
        clip = OUT / f"{pid}-clip-{slide}.mp4"
        zoom = "min(zoom+0.0009,1.055)" if slide != 2 else "min(zoom+0.0006,1.04)"
        vf = f"scale=1080:1920,zoompan=z='{zoom}':d=90:s=1080x1920:fps=30,format=yuv420p"
        cmd = [
            ffmpeg, "-y", "-loglevel", "error", "-loop", "1", "-i", str(frame),
            "-t", "3", "-vf", vf, "-r", "30", "-c:v", "libx264", "-preset", "veryfast",
            "-movflags", "+faststart", str(clip),
        ]
        try:
            subprocess.run(cmd, check=True, timeout=120)
        except Exception as exc:
            print(f"Could not animate Reel frame {slide} for {pid}: {exc}")
            return False
        clips.append(clip)

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tf:
        concat_path = Path(tf.name)
        for clip in clips:
            tf.write(f"file '{clip.resolve()}'\n")

    out = OUT / f"{pid}.mp4"
    cmd = [
        ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat_path),
        "-c", "copy", "-movflags", "+faststart", str(out),
    ]
    try:
        subprocess.run(cmd, check=True, timeout=120)
        return out.exists() and out.stat().st_size > 0
    except Exception as exc:
        print(f"Could not build reel {pid}: {exc}")
        return False
    finally:
        concat_path.unlink(missing_ok=True)
        for clip in clips:
            clip.unlink(missing_ok=True)


def main() -> None:
    if not QUEUE.exists():
        raise SystemExit("marketing/queue.json not found")
    payload = json.loads(QUEUE.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)

    generated = 0
    reels = 0
    carousels = 0
    for item in payload.get("items", []):
        if not isinstance(item, dict) or str(item.get("status")) != "ready_for_design":
            continue
        pid = str(item.get("id") or "").strip()
        if not pid:
            continue

        draw_card(item, OUT / f"{pid}.jpg")
        generated += 1

        fmt = str(item.get("format") or "image").lower()
        if fmt == "carousel":
            for slide in range(1, 4):
                carousel_slide(item, slide, OUT / f"{pid}-{slide}.jpg")
            carousels += 1
        elif fmt == "reel":
            if build_reel(item, pid):
                reels += 1

    print(json.dumps({
        "generated_assets": generated,
        "reels": reels,
        "carousels": carousels,
        "output": str(OUT),
    }))


if __name__ == "__main__":
    main()

"""Gerador local de MP4 com efeitos — fallback garantido (sem billing)."""
from __future__ import annotations

import math
import random
import textwrap
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from effects import parse_effects_from_prompt

FPS = 12
MAX_FRAMES = 7200


def _fps_for(duration_s: int) -> int:
    """FPS adaptativo: vídeos longos renderizam mais rápido sem perder fluidez."""
    if duration_s <= 30:
        return 12
    if duration_s <= 180:
        return 10
    return 8


def _resolution_size(resolution: str, aspect: str) -> tuple[int, int]:
    if aspect == "9:16":
        return (360, 640) if resolution == "720p" else (540, 960)
    return (640, 360) if resolution == "720p" else (960, 540)


def _base_frame(w: int, h: int, t: float, rng: random.Random) -> np.ndarray:
    """Fundo cyberpunk animado: gradiente + sol + grade."""
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    x = np.linspace(0, 1, w, dtype=np.float32)[None, :]
    # Céu roxo→azul com pulsação sutil.
    pulse = 0.06 * math.sin(t * 1.7)
    wob = np.sin(t + x * 4)
    r = np.broadcast_to((18 + 40 * (1 - y) + 20 * pulse).clip(0, 255), (h, w))
    g = np.broadcast_to((8 + 24 * (1 - y) * x + 30 * y * (0.5 + 0.5 * wob)).clip(0, 255), (h, w))
    b = np.broadcast_to((46 + 120 * y + 30 * (0.5 + 0.5 * np.sin(t * 0.8 + y * 6))).clip(0, 255), (h, w))
    img = np.dstack([r, g, b]).astype(np.uint8)
    img = np.repeat(img, 1, axis=1) if img.shape[1] == w else img
    # Sol synthwave.
    cx, cy, rad = w // 2, int(h * 0.52), int(min(w, h) * 0.20)
    yy, xx = np.ogrid[:h, :w]
    dist = np.sqrt((xx - cx) ** 2 + ((yy - cy) * 1.25) ** 2)
    sun = (dist < rad).astype(np.float32)
    stripes = ((yy - cy + int(t * 22)) % max(7, h // 40) < 3).astype(np.float32)
    sun *= (0.75 + 0.25 * stripes)
    img = img.astype(np.float32)
    img[..., 0] += sun * 235
    img[..., 1] += sun * (60 + 40 * math.sin(t * 2))
    img[..., 2] += sun * 150    # Grade em perspectiva (metade inferior).
    horizon = int(h * 0.55)
    for i in range(8):
        yy_pos = horizon + int((h - horizon) * ((i / 8 + (t * 0.25) % (1 / 8)) * 8 % 8) / 8)
        yy_pos = min(h - 1, max(horizon, yy_pos))
        img[yy_pos - 1:yy_pos + 1, :, 0] += 90
        img[yy_pos - 1:yy_pos + 1, :, 2] += 160
    for i in range(-6, 7):
        xx_pos = int(cx + i * w / 14 + math.sin(t + i) * 6)
        if 0 <= xx_pos < w:
            img[horizon:, max(0, xx_pos - 1):xx_pos + 1, 1] += 110
            img[horizon:, max(0, xx_pos - 1):xx_pos + 1, 2] += 150
    return np.clip(img, 0, 255).astype(np.uint8)


def _apply_effects(frame: np.ndarray, effects: list[str], idx: int, t: float,
                   rng: random.Random, drops: list) -> np.ndarray:
    h, w, _ = frame.shape
    f = frame.astype(np.float32)
    E = set(effects)

    if "vignette" in E or "scanlines" in E or True:  # vinheta base sempre
        yy, xx = np.ogrid[:h, :w]
        mask = 1.0 - 0.45 * (((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2) / 2
        f *= np.clip(mask[..., None], 0.55, 1.0)
    if "scanlines" in E or "hologram" in E or "vhs" in E:
        f[::3] *= 0.82
    if "film_grain" in E or "noise" in E or "vhs" in E:
        f += rng.uniform(-14, 14)
    if "chromatic" in E or "glitch" in E:
        shift = 3 if "glitch" in E and idx % 6 == 0 else 2
        r = np.roll(f[..., 0], -shift, axis=1)
        b = np.roll(f[..., 2], shift, axis=1)
        f[..., 0], f[..., 2] = r, b
    if "glitch" in E and idx % 5 == 0:
        for _ in range(3):
            y0 = rng.randrange(0, h - 4)
            f[y0:y0 + 3] = np.roll(f[y0:y0 + 3], rng.randrange(-40, 40), axis=1)
    if "datamosh" in E and idx % 7 == 0:
        y0 = rng.randrange(0, h - 12)
        f[y0:y0 + 12] = np.roll(f[y0:y0 + 12], rng.randrange(-60, 60), axis=1)
    if "wave" in E or "plasma" in E or "aurora" in E:
        amp = 6 if "wave" in E else 3
        for y0 in range(0, h, 4):
            f[y0:y0 + 2] = np.roll(f[y0:y0 + 2], int(amp * math.sin(t * 3 + y0 * 0.08)), axis=1)
    if "shake" in E:
        dx, dy = rng.randrange(-5, 6), rng.randrange(-4, 5)
        f = np.roll(np.roll(f, dy, axis=0), dx, axis=1)
    if "zoom_pulse" in E or "dolly" in E or "tunnel" in E or "hyperdrive" in E or "slowmo" in E:
        if "hyperdrive" in E:
            speed, depth = 5.0, 0.22
        elif "tunnel" in E:
            speed, depth = 3.4, 0.15
        elif "zoom_pulse" in E:
            speed, depth = 2.2, 0.08
        elif "slowmo" in E:
            speed, depth = 0.45, 0.05
        else:
            speed, depth = 0.9, 0.08
        z = 1.0 + depth * (0.5 + 0.5 * math.sin(t * speed))
        nh, nw = int(h / z), int(w / z)
        y0, x0 = (h - nh) // 2, (w - nw) // 2
        crop = np.clip(f[y0:y0 + nh, x0:x0 + nw], 0, 255).astype(np.uint8)
        small = Image.fromarray(crop).resize((w, h), Image.BILINEAR)
        f = np.asarray(small).astype(np.float32)
    if "orbit" in E:
        f = np.roll(f, int(10 * math.sin(t * 1.2)), axis=1)
    if "mirror" in E or "kaleidoscope" in E:
        half = f[:, :w // 2][:, ::-1] if "kaleidoscope" in E else f[:, :w // 2]
        f[:, w // 2:] = half if half.shape[1] == w - w // 2 else np.resize(half, (h, w - w // 2, 3))
        if "kaleidoscope" in E:
            f = f[::-1] * 0.5 + f * 0.5
    if "pixelate" in E and idx < 18:
        small = Image.fromarray(np.clip(f, 0, 255).astype(np.uint8)).resize(
            (max(16, w // 12), max(16, h // 12)), Image.NEAREST).resize((w, h), Image.NEAREST)
        f = np.asarray(small).astype(np.float32)
    if ("strobe" in E or "storm" in E) and int(t * 4) % 4 == 3:
        f *= 1.5
    if "storm" in E and idx % 11 == 0:  # relâmpago: flash azul breve
        f += np.array([30, 50, 90], dtype=np.float32)
    if "fire" in E:  # brilho quente subindo da base
        heat = np.linspace(0, 1, h, dtype=np.float32)[:, None, None] ** 2
        f += heat * np.array([46, 14, 2], dtype=np.float32) * (0.8 + 0.2 * math.sin(t * 6))
    if "ice" in E:  # tom frio + cintilação
        f[..., 0] *= 0.82
        f[..., 2] *= 1.12
        f += 8 * (0.5 + 0.5 * math.sin(t * 9))
    if "golden_dust" in E:
        f[..., 0] += 10
        f[..., 1] += 7
    if "bloom" in E or "god_rays" in E or "lens_flare" in E or "billboard" in E:
        hi = np.clip((f.mean(axis=2, keepdims=True) - 150) / 105, 0, 1)
        f += hi * (50 if "bloom" in E else 80)
    if "hologram" in E:
        f[..., 0] *= 0.7
        f[..., 1] *= (0.9 + 0.1 * math.sin(t * 20))
        f[..., 2] *= 1.15
        if idx % 9 == 0:
            f *= 0.75
    if "vhs" in E and idx % 12 == 0:
        f[int(h * 0.3):int(h * 0.3) + 6] = np.roll(
            f[int(h * 0.3):int(h * 0.3) + 6], 30, axis=1)
    # Overlays: chuva / matrix / lasers / bokeh / vazamentos / aurora / fogo / tempestade.
    if E & {"neon_rain", "matrix_rain", "particles", "bokeh", "laser", "light_leak",
            "god_rays", "aurora", "lens_flare", "storm", "fire", "ice", "golden_dust", "billboard"}:
        rising = bool(E & {"fire", "golden_dust"})
        for (dx, dy, sp, col, ln) in drops:
            y0 = int((dy - t * sp * h) % h) if rising else int((dy + t * sp * h) % h)
            x0 = int((dx * w + (t * 8 if "neon_rain" in E else 0)) % w)
            y1 = min(h, y0 + ln)
            if "bokeh" in E:
                rr = ln
                f[max(0, y0 - rr):y1 + rr, max(0, x0 - rr):x0 + rr] += 18
            else:
                f[y0:y1, x0:x0 + 2] += np.array(col, dtype=np.float32) * 0.9
    if "laser" in E:
        for k in range(2):
            yy_pos = int((t * 120 * (k + 1)) % h)
            f[yy_pos:yy_pos + 2, :, 0] += 120
            f[yy_pos:yy_pos + 2, :, 2] += 90
    if "light_leak" in E:
        f[:, -w // 4:] += np.array([40, 18, 4], dtype=np.float32)
    return np.clip(f, 0, 255).astype(np.uint8)


_FONT_CACHE: dict[int, object] = {}


def _get_font(w: int):
    if w not in _FONT_CACHE:
        try:
            _FONT_CACHE[w] = ImageFont.load_default(size=max(14, w // 34))
        except TypeError:
            _FONT_CACHE[w] = ImageFont.load_default()
    return _FONT_CACHE[w]


def _overlay_text(frame: np.ndarray, lines: list[str], effects: list[str],
                  idx: int, total: int, font) -> np.ndarray:
    img = Image.fromarray(frame)
    d = ImageDraw.Draw(img, "RGBA")
    w, h = img.size
    # Barra de progresso cyberpunk.
    bar_w = int(w * 0.86)
    d.rounded_rectangle([w * 0.07, h - 26, w * 0.07 + bar_w, h - 14], 6, fill=(0, 0, 0, 150))
    d.rounded_rectangle([w * 0.07, h - 26, w * 0.07 + bar_w * (idx + 1) / max(total, 1), h - 14], 6,
                        fill=(0, 255, 238, 220))
    if lines:
        y0 = h - 30 - len(lines) * 20
        d.rectangle([10, y0 - 8, w - 10, h - 32], fill=(2, 0, 16, 170))
        for i, ln in enumerate(lines):
            d.text((18, y0 + i * 20), ln, font=font, fill=(230, 255, 252, 255))
    tag = " + ".join(effects[:3])
    d.text((12, 10), f"NETEZACK V2 // {tag}", font=font, fill=(0, 245, 212, 255))
    d.text((12, 30), f"frame {idx + 1}/{total}", font=font, fill=(255, 46, 136, 255))
    return np.asarray(img)


def render_local_mp4(prompt: str, effects: list[str] | None, duration_s: int,
                     resolution: str, aspect: str, out_path: Path,
                     seed: int = 7, on_frame=None) -> list[str]:
    """Gera MP4 local garantido. Retorna a lista final de efeitos usados.

    on_frame(i, total, frame_rgb) é chamado a cada quadro — usado pelo app
    para publicar preview JPEG ao vivo e progresso real (não simulado).
    """
    import imageio.v2 as imageio  # import tardio p/ cold start menor
    final_effects = parse_effects_from_prompt(prompt, effects)
    w, h = _resolution_size(resolution, aspect)
    fps = _fps_for(int(duration_s))
    n_frames = max(12, min(MAX_FRAMES, int(duration_s) * fps))
    font = _get_font(w)
    short = " ".join(prompt.split())[:160]
    lines = textwrap.wrap(short, width=42)[:3]
    rng = random.Random(seed)
    drops = [(rng.random(), rng.random(), rng.uniform(0.25, 0.9),
              rng.choice([(0, 255, 238), (255, 45, 150), (120, 255, 120), (255, 220, 120)]),
              rng.randint(4, 16)) for _ in range(46)]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    writer = imageio.get_writer(str(out_path), fps=fps, codec="libx264",
                                quality=8 if n_frames <= 600 else 6,
                                macro_block_size=None, pixelformat="yuv420p",
                                output_params=["-preset", "veryfast"])
    try:
        for i in range(n_frames):
            t = i / fps
            frame = _base_frame(w, h, t, rng)
            frame = _apply_effects(frame, final_effects, i, t, rng, drops)
            frame = _overlay_text(frame, lines, final_effects, i, n_frames, font)
            writer.append_data(frame)
            if on_frame:
                try:
                    on_frame(i, n_frames, frame)
                except Exception:
                    pass
    finally:
        writer.close()
    return final_effects

"""Vídeo por IA open-source: quadros FLUX (Pollinations) + Ken Burns + efeitos.

Qualquer falha de rede devolve None — o chamador cai no render procedural.
"""
from __future__ import annotations

import io
import math
import random
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

from effects import parse_effects_from_prompt
from video_fallback import _apply_effects, _get_font, _fps_for, _overlay_text

AI_MIN_DURATION = 4
AI_MAX_DURATION = 60
AI_TIMEOUT_SECONDS = 25
AI_DISABLE_SECONDS = 600  # apos falha, tenta de novo so em 10 min

_ai_down_until = 0.0
_last_error = ""


def ai_available(now: float | None = None) -> bool:
    import time
    return (now if now is not None else time.time()) >= _ai_down_until


def _mark_ai_down(err: Exception) -> None:
    global _ai_down_until, _last_error
    import time
    _ai_down_until = time.time() + AI_DISABLE_SECONDS
    _last_error = str(err)[:200]


def fetch_ai_frames(prompt: str, count: int, w: int, h: int) -> list[np.ndarray] | None:
    """Baixa `count` imagens FLUX. None em qualquer falha (fallback procedural)."""
    global _last_error
    if not ai_available():
        return None
    frames: list[np.ndarray] = []
    for i in range(count):
        url = (
            "https://image.pollinations.ai/prompt/"
            + urllib.parse.quote(prompt[:400] or "cyberpunk neon scene")
            + f"?width={w}&height={h}&nologo=true&model=flux&seed={1701 + i * 97}"
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "NetezackVideos/2.1"})
            with urllib.request.urlopen(req, timeout=AI_TIMEOUT_SECONDS) as resp:
                data = resp.read(15_000_000)
            img = Image.open(io.BytesIO(data)).convert("RGB")
            if img.size != (w, h):
                img = img.resize((w, h), Image.LANCZOS)
            frames.append(np.asarray(img, dtype=np.uint8))
        except Exception as exc:  # rede/timeout/decode — desliga IA por 10 min
            _last_error = str(exc)[:200]
            if i == 0:
                _mark_ai_down(exc)
            return None
    return frames or None


def _ken_burns(img: np.ndarray, zoom: float) -> np.ndarray:
    h, w, _ = img.shape
    nh, nw = max(2, int(h / zoom)), max(2, int(w / zoom))
    y0, x0 = (h - nh) // 2, (w - nw) // 2
    crop = img[y0:y0 + nh, x0:x0 + nw]
    pil = Image.fromarray(crop).resize((w, h), Image.BILINEAR)
    return np.asarray(pil, dtype=np.uint8)


def render_ai_mp4(prompt: str, effects: list[str] | None, duration_s: int,
                  resolution: str, aspect: str, out_path: Path,
                  seed: int = 7, on_frame=None) -> list[str] | None:
    """Gera MP4 com quadros de IA FLUX. None se a IA estiver indisponivel."""
    import imageio.v2 as imageio

    from video_fallback import _resolution_size

    if not (AI_MIN_DURATION <= int(duration_s) <= AI_MAX_DURATION):
        return None
    final_effects = parse_effects_from_prompt(prompt, effects)
    w, h = _resolution_size(resolution, aspect)
    count = min(8, max(2, int(duration_s) // 3))
    ai_frames = fetch_ai_frames(prompt, count, w, h)
    if not ai_frames:
        return None

    fps = _fps_for(int(duration_s))
    n_frames = max(12, min(7200, int(duration_s) * fps))
    font = _get_font(w)
    import textwrap
    lines = textwrap.wrap(" ".join(prompt.split())[:160], width=42)[:3]
    rng = random.Random(seed)
    drops = [(rng.random(), rng.random(), rng.uniform(0.25, 0.9),
              rng.choice([(0, 255, 238), (255, 45, 150), (120, 255, 120), (255, 220, 120)]),
              rng.randint(4, 16)) for _ in range(46)]

    seg_len = duration_s / count
    fade = min(0.7, seg_len / 3)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    writer = imageio.get_writer(str(out_path), fps=fps, codec="libx264",
                                quality=8 if n_frames <= 600 else 6,
                                macro_block_size=None, pixelformat="yuv420p",
                                output_params=["-preset", "veryfast"])
    try:
        for i in range(n_frames):
            t = i / fps
            seg = min(count - 1, int(t / seg_len))
            p = (t - seg * seg_len) / seg_len
            base = _ken_burns(ai_frames[seg], 1.0 + 0.10 * p)
            if seg > 0 and p * seg_len < fade:  # crossfade entre cenas
                prev = _ken_burns(ai_frames[seg - 1], 1.10)
                alpha = (p * seg_len) / fade
                base = (prev.astype(np.float32) * (1 - alpha)
                        + base.astype(np.float32) * alpha).astype(np.uint8)
            frame = _apply_effects(base, final_effects, i, t, rng, drops)
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


def ai_status() -> str:
    return _last_error or ("ok" if ai_available() else "indisponivel")

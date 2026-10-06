"""36 efeitos especiais — 100% open-source (numpy + Pillow + imageio-ffmpeg).

Render local via chat: sempre funciona, sem chave, sem API paga.

Gera MP4 animado com numpy + Pillow + imageio-ffmpeg.
Leve para Railway: 12fps, 640x360 (16:9) ou 360x640 (9:16).
"""
from __future__ import annotations

import math
from pathlib import Path

EFFECTS: dict[str, dict[str, str]] = {
    "neon_pulse": {"name": "Neon Pulse", "desc": "Pulso neon magenta/ciano"},
    "glitch": {"name": "Glitch Digital", "desc": "Falhas RGB estilo cyberpunk"},
    "cyber_grid": {"name": "Cyber Grid", "desc": "Grade perspectiva infinita"},
    "matrix_rain": {"name": "Matrix Rain", "desc": "Chuva de código verde"},
    "hologram": {"name": "Holograma", "desc": "Linhas + flicker holográfico"},
    "vaporwave": {"name": "Vaporwave", "desc": "Sol retrô + mar quadriculado"},
    "synthwave_sun": {"name": "Synthwave Sun", "desc": "Pôr-do-sol sintético listrado"},
    "plasma": {"name": "Plasma", "desc": "Neblina plasmática animada"},
    "particles": {"name": "Partículas", "desc": "Enxame de partículas neon"},
    "scanlines": {"name": "Scanlines CRT", "desc": "Tela retrô com varredura"},
    "chromatic": {"name": "Aberração Cromática", "desc": "Bordas RGB deslocadas"},
    "strobe": {"name": "Strobe", "desc": "Piscadas rítmicas de energia"},
    "warp_speed": {"name": "Warp Speed", "desc": "Túnel de dobra espacial"},
    "data_stream": {"name": "Data Stream", "desc": "Fluxo de dados vertical"},
    "aurora": {"name": "Aurora", "desc": "Cortinas de aurora boreal"},
    "electric_storm": {"name": "Tempestade Elétrica", "desc": "Raios + flashes"},
    "pixel_sort": {"name": "Pixel Sort", "desc": "Faixas deslizantes"},
    "kaleidoscope": {"name": "Caleidoscópio", "desc": "Simetria giratória"},
    "mirror": {"name": "Espelho", "desc": "Reflexo aquático"},
    "ripple": {"name": "Ripple", "desc": "Ondas concêntricas"},
    "fire": {"name": "Fogo Digital", "desc": "Chamas laranja/vermelho"},
    "ice_crystal": {"name": "Cristal de Gelo", "desc": "Brilhos ciano/branco"},
    "gold_dust": {"name": "Poeira de Ouro", "desc": "Partículas douradas"},
    "smoke": {"name": "Fumaça Neon", "desc": "Névoa roxa subindo"},
    "laser": {"name": "Laser Grid", "desc": "Raios laser cruzados"},
    "portal": {"name": "Portal", "desc": "Anéis concêntricos de energia"},
    "galaxy": {"name": "Galáxia", "desc": "Espiral estelar"},
    "cyber_rain": {"name": "Chuva Cyberpunk", "desc": "Chuva neon na cidade"},
    "bloom": {"name": "Bloom", "desc": "Brilho suave pulsante"},
    "vintage_film": {"name": "Filme Vintage", "desc": "Grão + vinheta retrô"},
    "circuit": {"name": "Circuit Board", "desc": "Trilhas de circuito pulsantes"},
    "solar_flare": {"name": "Solar Flare", "desc": "Explosão solar dourada"},
    "prism": {"name": "Prisma", "desc": "Refração arco-íris em movimento"},
    "time_warp": {"name": "Time Warp", "desc": "Distorção temporal em espiral"},
    "starfield": {"name": "Starfield", "desc": "Campo estelar em hiperespaço"},
    "dna_helix": {"name": "DNA Helix", "desc": "Dupla hélice de energia"},
}

EFFECT_IDS = list(EFFECTS.keys())


def list_effects() -> list[dict[str, str]]:
    return [{"id": k, **v} for k, v in EFFECTS.items()]


def _palette(effect: str, t: float):
    import math
    palettes = {
        "neon_pulse": ((255, 0, 200), (0, 255, 255)),
        "glitch": ((255, 0, 80), (0, 255, 120)),
        "cyber_grid": ((0, 255, 255), (120, 0, 255)),
        "matrix_rain": ((0, 255, 70), (0, 60, 20)),
        "hologram": ((120, 220, 255), (10, 40, 80)),
        "vaporwave": ((255, 110, 200), (60, 20, 120)),
        "synthwave_sun": ((255, 180, 40), (180, 0, 120)),
        "plasma": ((150, 0, 255), (0, 220, 255)),
        "particles": ((255, 220, 80), (20, 10, 60)),
        "scanlines": ((80, 255, 220), (5, 10, 25)),
        "chromatic": ((255, 60, 60), (60, 120, 255)),
        "strobe": ((255, 255, 255), (90, 0, 180)),
        "warp_speed": ((160, 200, 255), (5, 5, 20)),
        "data_stream": ((0, 255, 180), (0, 20, 40)),
        "aurora": ((0, 255, 170), (80, 0, 200)),
        "electric_storm": ((180, 220, 255), (20, 10, 60)),
        "pixel_sort": ((255, 0, 150), (0, 200, 255)),
        "kaleidoscope": ((255, 150, 0), (100, 0, 200)),
        "mirror": ((0, 180, 255), (5, 10, 40)),
        "ripple": ((100, 255, 220), (10, 20, 60)),
        "fire": ((255, 120, 0), (60, 5, 0)),
        "ice_crystal": ((200, 245, 255), (0, 80, 140)),
        "gold_dust": ((255, 210, 90), (40, 20, 0)),
        "smoke": ((190, 120, 255), (15, 5, 30)),
        "laser": ((255, 40, 40), (0, 10, 30)),
        "portal": ((0, 255, 220), (60, 0, 160)),
        "galaxy": ((220, 170, 255), (5, 5, 25)),
        "cyber_rain": ((0, 220, 255), (10, 5, 30)),
        "bloom": ((255, 200, 240), (30, 10, 50)),
        "vintage_film": ((230, 200, 150), (25, 18, 10)),
        "circuit": ((0, 255, 170), (10, 30, 60)),
        "solar_flare": ((255, 200, 60), (120, 20, 0)),
        "prism": ((255, 100, 220), (80, 200, 255)),
        "time_warp": ((170, 120, 255), (5, 5, 25)),
        "starfield": ((255, 255, 255), (5, 5, 20)),
        "dna_helix": ((0, 255, 200), (80, 0, 160)),
    }
    return palettes.get(effect, ((0, 255, 220), (10, 10, 30)))


QUALITY_SIZES = {
    # paisagem (16:9) e vertical (9:16) — 100% open-source
    "360p": ((640, 360), (360, 640)),
    "480p": ((854, 480), (480, 854)),
    "720p": ((1280, 720), (720, 1280)),
    "1080p": ((1920, 1080), (1080, 1920)),
}

QUALITY_IDS = list(QUALITY_SIZES.keys())


def render_effect_video(prompt: str, effect: str, destination: Path,
                        duration_seconds: int = 8, aspect_ratio: str = "16:9",
                        fps: int = 12, quality: str = "360p") -> Path:
    """Renderiza MP4 animado. Sempre funciona offline (fallback garantido).

    duration: 2..600s (até 10 min). quality: 360p/480p/720p/1080p.
    Vídeos longos usam fps reduzido para caber no Railway.
    """
    import numpy as np
    from PIL import Image, ImageDraw
    import imageio.v2 as imageio

    effect = effect if effect in EFFECTS else "neon_pulse"
    duration_seconds = max(2, min(600, int(duration_seconds or 8)))
    quality = quality if quality in QUALITY_SIZES else "360p"
    # vídeos longos: reduz fps para não estourar CPU/disco do Railway
    if duration_seconds > 60:
        fps = min(fps, 8)
    if duration_seconds > 180:
        fps = min(fps, 6)
    sizes = QUALITY_SIZES[quality]
    W, H = sizes[0] if aspect_ratio == "16:9" else sizes[1]
    n_frames = duration_seconds * fps
    c1, c2 = _palette(effect, 0.0)

    # gradiente base
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    xn, yn = xx / W, yy / H

    destination.parent.mkdir(parents=True, exist_ok=True)
    writer = imageio.get_writer(str(destination), fps=fps, codec="libx264", quality=7, macro_block_size=1)

    rng = np.random.default_rng(abs(hash(effect + prompt)) % (2 ** 31))
    dots = rng.random((90, 2))
    speeds = rng.random(90) * 0.6 + 0.2

    short = prompt.strip().replace("\n", " ")[:90]

    for i in range(n_frames):
        t = i / fps
        ph = t * 2.0
        # base animada: mistura de senos (cada efeito muda frequência/contraste)
        k = (abs(hash(effect)) % 7) + 2
        wave = (np.sin(xn * 6.28 * k + ph) + np.sin(yn * 6.28 * (k - 1) - ph * 1.4)
                + np.sin((xn + yn) * 6.28 + ph * 0.7)) / 3.0  # -1..1
        m = (wave * 0.5 + 0.5)
        if effect in ("glitch", "strobe", "electric_storm") and (i % 9 == 0):
            m = 1 - m  # inversão brusca
        if effect in ("warp_speed", "portal", "galaxy", "kaleidoscope"):
            cx, cy = (xn - 0.5), (yn - 0.5)
            r = np.sqrt(cx ** 2 + cy ** 2) + 1e-6
            m = (np.sin(r * 24 - ph * 4) * 0.5 + 0.5)
        if effect in ("matrix_rain", "data_stream", "cyber_rain"):
            m = ((yn + t * 0.7 + 0.05 * np.sin(xn * 40)) % 1.0)
            m = (m < 0.12).astype(float) * 0.9 + m * 0.25
        if effect in ("cyber_grid", "laser"):
            gx = np.abs(((xn + t * 0.15) % 0.1) - 0.05) < 0.003
            gy = np.abs(((yn + t * 0.10) % 0.1) - 0.05) < 0.004
            m = np.clip(m * 0.4 + (gx | gy).astype(float) * 0.9, 0, 1)
        if effect in ("ripple", "mirror"):
            m = (np.sin(np.sqrt((xn - 0.5) ** 2 + (yn - 0.5) ** 2) * 30 - ph * 3) * 0.5 + 0.5)
        if effect in ("fire", "smoke", "aurora"):
            m = np.clip(m * 0.6 + (1 - yn) * 0.5 + 0.15 * np.sin(xn * 20 + ph * 2), 0, 1)

        frame = np.zeros((H, W, 3), dtype=float)
        for ch in range(3):
            frame[:, :, ch] = c2[ch] + (c1[ch] - c2[ch]) * m

        # partículas
        px = ((dots[:, 0] + t * speeds * 0.15) % 1.0 * W).astype(int)
        py = ((dots[:, 1] + t * speeds * 0.10) % 1.0 * H).astype(int)
        glow = 0.5 + 0.5 * np.sin(ph * 2 + np.arange(90))
        for x0, y0, g in zip(px, py, glow):
            b = 90 + int(120 * g)
            y1, y2 = max(0, y0 - 2), min(H, y0 + 3)
            x1, x2 = max(0, x0 - 2), min(W, x0 + 3)
            frame[y1:y2, x1:x2, :] = np.clip(frame[y1:y2, x1:x2, :] + b * 0.35, 0, 255)

        # scanlines / vinheta
        if effect in ("scanlines", "hologram", "vintage_film"):
            frame[::3, :, :] *= 0.82
        if effect in ("vintage_film", "bloom"):
            # vinheta simples
            vig = 1 - np.clip(((xn - 0.5) ** 2 + (yn - 0.5) ** 2) * 1.1, 0, 0.5)
            frame *= vig[:, :, None]

        img = Image.fromarray(np.clip(frame, 0, 255).astype("uint8"))
        d = ImageDraw.Draw(img, "RGBA")
        # barra + título cyberpunk (escala com a qualidade)
        bar_h = max(56, H // 8)
        d.rectangle([0, H - bar_h, W, H], fill=(0, 0, 0, 170))
        d.text((12, H - bar_h + 10), EFFECTS[effect]["name"].upper(), fill=(0, 255, 220))
        # quebra o prompt em 2 linhas
        words, lines, cur = short.split(), [], ""
        for w in words:
            if len(cur) + len(w) + 1 > 42:
                lines.append(cur); cur = w
            else:
                cur = (cur + " " + w).strip()
        lines.append(cur)
        for li, line in enumerate(lines[:2]):
            d.text((12, H - bar_h + 28 + li * 14), line[:46], fill=(235, 240, 255))
        # mira / HUD (tempo total ajuda em vídeos de até 10 min)
        d.ellipse([W - 44, 12, W - 12, 44], outline=(0, 255, 220), width=2)
        mm, ss = divmod(t, 60)
        d.text((14, 12), f"REC {int(mm):02d}:{ss:04.1f}", fill=(255, 80, 120))
        writer.append_data(np.asarray(img))

    writer.close()
    return destination

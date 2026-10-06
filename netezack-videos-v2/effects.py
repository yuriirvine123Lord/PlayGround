"""Catálogo de 40 efeitos especiais + detecção por prompt (PT-BR)."""
from __future__ import annotations

EFFECTS: dict[str, dict[str, str]] = {
    "neon_grid": {"label": "Grade Neon", "desc": "Grade cyberpunk em perspectiva com brilho cyan/magenta."},
    "glitch": {"label": "Glitch Digital", "desc": "Fatiamento horizontal + deslocamento RGB de TV com defeito."},
    "chromatic": {"label": "Aberração Cromática", "desc": "Bordas RGB deslocadas estilo lente anamórfica."},
    "vhs": {"label": "VHS Retrô", "desc": "Tracking, ruído de fita e data OSD anos 80."},
    "scanlines": {"label": "Scanlines CRT", "desc": "Linhas de monitor tubo + vinheta suave."},
    "particles": {"label": "Partículas Neon", "desc": "Poeira luminosa flutuante sobre a cena."},
    "neon_rain": {"label": "Chuva Neon", "desc": "Chuva inclinada com reflexo de néon (Matrix rain curta)."},
    "cyber_grid": {"label": "Horizonte Synthwave", "desc": "Sol retrô + grade infinita ao pôr do sol."},
    "hologram": {"label": "Holograma", "desc": "Projeção translúcida com flicker e linhas de varredura."},
    "bloom": {"label": "Bloom Suave", "desc": "Brilho difuso nas altas luzes."},
    "lens_flare": {"label": "Lens Flare", "desc": "Reflexo de lente varrendo a cena."},
    "film_grain": {"label": "Grão de Filme", "desc": "Textura 35mm animada."},
    "shake": {"label": "Camera Shake", "desc": "Tremor de câmera de ação na batida."},
    "zoom_pulse": {"label": "Zoom Pulsante", "desc": "Dolly-in rítmico com o beat."},
    "dolly": {"label": "Dolly Cinemático", "desc": "Aproximação lenta e contínua."},
    "orbit": {"label": "Órbita", "desc": "Deriva lateral senoidal como drone."},
    "strobe": {"label": "Strobe Club", "desc": "Piscadas de luz de boate no clímax."},
    "matrix_rain": {"label": "Matrix Rain", "desc": "Cascata de glifos verdes caindo."},
    "plasma": {"label": "Plasma", "desc": "Neblina de plasma colorida em movimento."},
    "kaleidoscope": {"label": "Caleidoscópio", "desc": "Espelhamento radial psicodélico leve."},
    "mirror": {"label": "Espelho", "desc": "Simetria vertical cinematográfica."},
    "wave": {"label": "Onda", "desc": "Distorção ondulante de calor/água."},
    "pixelate": {"label": "Pixelate 8-bit", "desc": "Mosaico retrô que resolve para nítido."},
    "noise": {"label": "Ruído Digital", "desc": "Interferência de transmissão."},
    "vignette": {"label": "Vinheta Cinema", "desc": "Escurece bordas p/ foco central."},
    "light_leak": {"label": "Light Leak", "desc": "Vazamento de luz âmbar de película."},
    "god_rays": {"label": "God Rays", "desc": "Feixes volumétricos do topo."},
    "datamosh": {"label": "Datamosh", "desc": "Blocos comprimidos e arrasto de movimento."},
    "synthwave_sun": {"label": "Sol Synthwave", "desc": "Sol listrado gigante no horizonte."},
    "laser": {"label": "Lasers", "desc": "Varreduras de laser rosa/cyan."},
    "bokeh": {"label": "Bokeh Noturno", "desc": "Orbes desfocados de cidade à noite."},
    "aurora": {"label": "Aurora", "desc": "Cortinas de aurora boreal no céu."},
    "tunnel": {"label": "Túnel Neon", "desc": "Mergulho em alta velocidade por um túnel de luz."},
    "hyperdrive": {"label": "Hiperdrive", "desc": "Salto warp com estrias radiais de velocidade."},
    "fire": {"label": "Chamas", "desc": "Brilho quente e brasas subindo pela cena."},
    "ice": {"label": "Gelo Cristal", "desc": "Tom frio azulado com cintilação de cristal."},
    "storm": {"label": "Tempestade", "desc": "Relâmpagos + chuva forte de tormenta."},
    "golden_dust": {"label": "Poeira Dourada", "desc": "Partículas douradas cinematográficas flutuando."},
    "billboard": {"label": "Outdoors Neon", "desc": "Letreiros vibrantes de cidade cyberpunk."},
    "slowmo": {"label": "Câmera Lenta", "desc": "Deriva suave em slow motion dramático."},
}

DEFAULT_EFFECTS = ["neon_grid", "particles", "vignette"]

_KEYWORDS: dict[str, list[str]] = {
    "neon_grid": ["neon", "grade", "grid", "cyber"],
    "glitch": ["glitch"],
    "chromatic": ["cromat", "chromatic", "rgb"],
    "vhs": ["vhs", "retrô", "retro", "fita", "anos 80"],
    "scanlines": ["scanline", "crt", "tubo"],
    "particles": ["partícul", "poeira", "faísca", "faisca"],
    "neon_rain": ["chuva"],
    "cyber_grid": ["synthwave", "horizonte", "pôr do sol", "por do sol"],
    "hologram": ["hologr"],
    "bloom": ["bloom", "brilho"],
    "lens_flare": ["flare", "lente"],
    "film_grain": ["grão", "grao", "35mm", "filme"],
    "shake": ["shake", "tremor", "ação", "acao", "impacto"],
    "zoom_pulse": ["zoom", "pulso", "beat"],
    "dolly": ["dolly"],
    "orbit": ["órbita", "orbita", "drone", "360"],
    "strobe": ["strobe", "boate", "club", "pisc"],
    "matrix_rain": ["matrix"],
    "plasma": ["plasma", "neblina"],
    "kaleidoscope": ["caleidosc", "psicod"],
    "mirror": ["espelho", "simetr"],
    "wave": ["onda", "água", "agua", "calor"],
    "pixelate": ["pixel", "8-bit", "8bit", "game"],
    "noise": ["ruído", "ruido", "interfer"],
    "vignette": ["vinheta"],
    "light_leak": ["leak", "película", "pelicula", "âmbar", "ambar"],
    "god_rays": ["god ray", "volumétr", "feixe"],
    "datamosh": ["datamosh", "compress"],
    "synthwave_sun": ["sol ", "sunset"],
    "laser": ["laser"],
    "bokeh": ["bokeh", "orbe", "cidade à noite", "noturna"],
    "aurora": ["aurora", "boreal"],
    "tunnel": ["túnel", "tunel", "mergulho"],
    "hyperdrive": ["hiperdrive", "hyperdrive", "warp", "salto"],
    "fire": ["chama", "fogo", "brasa", "incêndio", "fire"],
    "ice": ["gelo", "cristal", "congel", "ice", "inverno"],
    "storm": ["tempestade", "tormenta", "relâmpago", "relampago", "trovão", "storm"],
    "golden_dust": ["dourad", "golden"],
    "billboard": ["outdoor", "letreiro", "billboard", "placa neon"],
    "slowmo": ["câmera lenta", "camera lenta", "slow motion", "slowmo"],
}


def list_effects() -> list[dict[str, str]]:
    return [{"id": eid, **info} for eid, info in EFFECTS.items()]


def parse_effects_from_prompt(prompt: str, explicit: list[str] | None = None) -> list[str]:
    """Se o usuário passou efeitos, valida. Senão, detecta palavras do prompt."""
    if explicit:
        cleaned: list[str] = []
        for e in explicit:
            e = str(e).strip().lower()
            if e in EFFECTS and e not in cleaned:
                cleaned.append(e)
            if len(cleaned) >= 40:
                break
        return cleaned or list(DEFAULT_EFFECTS)
    text = (prompt or "").lower()
    found: list[str] = []
    for eid, words in _KEYWORDS.items():
        if any(w in text for w in words):
            found.append(eid)
        if len(found) >= 5:
            break
    return found or list(DEFAULT_EFFECTS)

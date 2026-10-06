#!/usr/bin/env bash
# Gerador de Vídeo IA — start.sh (static preview build + foreground server)
# Builds a self-contained static snapshot into ./dist and serves it on $PORT.
set -euo pipefail

cd "$(dirname "$0")"
/usr/bin/time -p pwd
/usr/bin/time -p mkdir -p dist
/usr/bin/time -p mkdir -p "${OPENCODE_WEB_DIR:?}/startup-meta"
/usr/bin/time -p python3 - <<'PYEOF'
import json
from pathlib import Path

root = Path.cwd()
effects = [
    ("neon_pulse", "Neon Pulse"), ("glitch", "Glitch Digital"),
    ("cyber_grid", "Cyber Grid"), ("matrix_rain", "Matrix Rain"),
    ("hologram", "Holograma"), ("vaporwave", "Vaporwave"),
    ("synthwave_sun", "Synthwave Sun"), ("plasma", "Plasma"),
    ("particles", "Partículas"), ("scanlines", "Scanlines CRT"),
    ("chromatic", "Aberração Cromática"), ("strobe", "Strobe"),
    ("warp_speed", "Warp Speed"), ("data_stream", "Data Stream"),
    ("aurora", "Aurora"), ("electric_storm", "Tempestade Elétrica"),
    ("pixel_sort", "Pixel Sort"), ("kaleidoscope", "Caleidoscópio"),
    ("mirror", "Espelho"), ("ripple", "Ripple"),
    ("fire", "Fogo Digital"), ("ice_crystal", "Cristal de Gelo"),
    ("gold_dust", "Poeira de Ouro"), ("smoke", "Fumaça Neon"),
    ("laser", "Laser Grid"), ("portal", "Portal"),
    ("galaxy", "Galáxia"), ("cyber_rain", "Chuva Cyberpunk"),
    ("bloom", "Bloom"), ("vintage_film", "Filme Vintage"),
    ("circuit", "Circuit Board"), ("solar_flare", "Solar Flare"),
    ("prism", "Prisma"), ("time_warp", "Time Warp"),
    ("starfield", "Starfield"), ("dna_helix", "DNA Helix"),
]
buttons = "\n".join(
    f'<button class="fx{" on" if i == 0 else ""}">✦ {name}</button>'
    for i, (_, name) in enumerate(effects)
)
html = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GERADOR DE VÍDEO IA — Cyberpunk</title>
<style>
:root{{color-scheme:dark;--neon:#00ffd8;--pink:#ff2fb3;--bg:#070a16}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(1200px 600px at 20% -10%,#2b0a4a 0%,transparent 60%),radial-gradient(900px 500px at 110% 10%,#003b46 0%,transparent 55%),var(--bg);color:#eaf2ff;font-family:Inter,system-ui,Segoe UI,sans-serif;min-height:100vh}}
.wrap{{max-width:1060px;margin:0 auto;padding:26px 16px 70px}}
header{{display:flex;align-items:center;gap:14px}}
.logo{{width:46px;height:46px;border-radius:12px;background:linear-gradient(135deg,var(--neon),var(--pink));display:grid;place-items:center;font-size:24px;color:#031018;font-weight:900}}
h1{{margin:0;font-size:24px}}h1 span{{color:var(--neon)}}
.sub{{color:#93a0c4;margin:6px 0 0}}
.card{{background:#0d1329cc;border:1px solid #22315c;border-radius:16px;padding:18px;margin-top:16px}}
input,textarea,select{{width:100%;border:1px solid #2c3c68;background:#080d20;color:#f2f6ff;border-radius:10px;padding:11px;font:inherit}}
#chat{{min-height:200px;max-height:340px;overflow:auto;display:flex;flex-direction:column;gap:10px;background:#060a1acc;border:1px solid #22315c;border-radius:12px;padding:14px}}
.msg{{max-width:85%;padding:10px 13px;border-radius:12px;line-height:1.45}}
.me{{align-self:flex-end;background:linear-gradient(135deg,#00ffd833,#ff2fb333);border:1px solid #00ffd855}}
.ai{{align-self:flex-start;background:#101838;border:1px solid #2c3c68}}
.row{{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}}
button.cta{{border:0;border-radius:10px;padding:11px 16px;font-weight:800;cursor:pointer;background:linear-gradient(135deg,var(--neon),#4d7cff);color:#031018}}
button.ghost{{border:0;border-radius:10px;padding:11px 16px;font-weight:800;cursor:pointer;background:#22315c;color:#dfe7ff}}
button.pink{{border:0;border-radius:10px;padding:11px 16px;font-weight:800;cursor:pointer;background:linear-gradient(135deg,var(--pink),#ff7a3d);color:#1c0512}}
.effects{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px;margin-top:10px}}
.fx{{border:1px solid #2c3c68;background:#0a1028;color:#cfe3ff;border-radius:9px;padding:8px;font-size:12px;text-align:left}}
.fx.on{{border-color:var(--neon);box-shadow:0 0 12px #00ffd855;color:#fff}}
.badge{{display:inline-block;font-size:12px;padding:4px 10px;border-radius:99px;border:1px solid #2c3c68;color:#9fe8ff}}
.muted{{color:#8b96bd;font-size:12px}}
footer{{margin-top:18px;color:#66719a;font-size:12px;text-align:center}}
</style></head><body><div class="wrap">
<header><div class="logo">◈</div><div><h1>GERADOR DE VÍDEO <span>IA</span></h1>
<p class="sub">Digite e a IA faz — chat ou vídeo automático. Só cole a <b>API KEY</b>, o sistema identifica o provedor sozinho.</p></div></header>
<div class="card"><b>🔑 Chave (URLs dos provedores ficam escondidas no servidor)</b>
<div style="margin-top:10px"><input type="password" placeholder="Cole aqui: AIza… / sk-… / gsk_… / hf_… / r8_… qualquer uma"></div>
<div class="row"><span class="badge">provedor: auto-detect</span><span class="badge">36 efeitos open-source</span><span class="badge">● online</span></div>
<p class="muted">Google/Veo • OpenAI • Anthropic • Groq • Together • OpenRouter • DeepSeek • Hugging Face • Replicate • fal.ai + render local com numpy + Pillow + ffmpeg.</p></div>
<div class="card"><b>⚡ 36 efeitos especiais (open-source)</b><div class="effects">{buttons}</div></div>
<div class="card"><b>💬 Chat inteligente</b><p class="muted">Ex: “crie um vídeo neon de uma cidade chuvosa” → gera MP4. Qualquer outra frase → a IA responde.</p>
<div id="chat"><div class="msg ai">Bem-vindo ao modo cyberpunk 👾 Digite um prompt e escolha um dos 36 efeitos. Exemplo: “crie um vídeo cyberpunk de um dragão sobre a cidade”.</div><div class="msg me">crie um vídeo neon de uma cidade chuvosa</div><div class="msg ai">🎬 Gerando seu vídeo com efeito <b>Neon Pulse</b>… (prévia estática — o backend FastAPI gera o MP4 real)</div></div>
<div class="row"><button class="cta">▶ ENVIAR</button><button class="pink">🎬 GERAR VÍDEO DIRETO</button><button class="ghost">Limpar</button></div></div>
<footer>36 efeitos ativos • build estático de prévia • API FastAPI em app.py</footer>
</div></body></html>"""
dist = root / "dist"
(dist / "index.html").write_text(html, encoding="utf-8")
print(f"dist written: {dist / 'index.html'} ({len(html)} bytes, {len(effects)} effects)")
PYEOF
/usr/bin/time -p python3 -c "import json,os; d={'project': os.getcwd(), 'directory': os.path.join(os.getcwd(),'dist')}; open(os.path.join(os.environ['OPENCODE_WEB_DIR'],'deployment-output.json'),'w').write(json.dumps(d)); print(open(os.path.join(os.environ['OPENCODE_WEB_DIR'],'deployment-output.json')).read())"
PORT="${PORT:-3000}"
/usr/bin/time -p echo "serving dist on port $PORT (project: $(pwd))"
/usr/bin/time -p python3 -m http.server "$PORT" --directory dist --bind 0.0.0.0

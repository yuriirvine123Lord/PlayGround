#!/usr/bin/env python3
"""Build the static preview site into PROJECT_DIR/dist (stdlib only).

Reads netezack-videos-v2/effects.py as data so the effects shown on the
page always match the backend catalog. No third-party dependencies.
"""
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DIST = ROOT / "dist"


def load_effects():
    spec = importlib.util.spec_from_file_location(
        "site_effects", ROOT / "netezack-videos-v2" / "effects.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.list_effects()


PAGE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NEON STUDIO — Gerador de Vídeo por Prompt</title>
<style>
:root{color-scheme:dark;--bg:#05010f;--panel:#0d0730;--line:#2b1a5e;--cyan:#00ffee;--pink:#ff2d96;--violet:#8b5cf6;--txt:#eef2ff;--mut:#9aa3c7}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(1200px 500px at 20% -5%,#2b0a5e55,transparent),radial-gradient(1000px 500px at 90% 0%,#00ffee22,transparent),var(--bg);color:var(--txt);font-family:Inter,system-ui,Segoe UI,Roboto,sans-serif}
.wrap{max-width:1060px;margin:0 auto;padding:26px 16px 70px}
header{display:flex;align-items:center;gap:14px;flex-wrap:wrap}.logo{width:46px;height:46px;border-radius:13px;background:linear-gradient(135deg,var(--cyan),var(--violet),var(--pink));font-weight:900;display:grid;place-items:center;color:#030014;font-size:22px}
h1{margin:0;font-size:clamp(22px,4vw,30px)}h1 span{background:linear-gradient(90deg,var(--cyan),var(--pink));-webkit-background-clip:text;background-clip:text;color:transparent}
.sub{color:var(--mut);margin:6px 0 0;font-size:13px;max-width:70ch}
.card{background:linear-gradient(180deg,#0d0730,#08041c);border:1px solid var(--line);border-radius:16px;padding:18px;margin-top:16px}
.card h2{margin:0 0 4px;font-size:15px}.hint{color:var(--mut);font-size:12.5px;margin:0 0 6px}
label{display:block;margin:12px 0 6px;font-size:12.5px;color:#c6cdf3}
input,textarea{width:100%;border:1px solid #3b2a7a;background:#070313;color:var(--txt);border-radius:11px;padding:11px;font:inherit}
textarea{min-height:84px;resize:vertical}
.row{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}
button{border:0;border-radius:11px;padding:11px 16px;background:linear-gradient(90deg,var(--cyan),var(--violet));color:#04121a;font-weight:800;cursor:pointer}
button.pink{background:linear-gradient(90deg,var(--pink),var(--violet));color:#fff}
button.ghost{background:#1a1440;color:var(--txt);border:1px solid #3b2a7a}
.badge{display:inline-block;font-size:11px;padding:4px 10px;border-radius:99px;border:1px solid #3b2a7a;color:var(--cyan)}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.chip{font-size:11.5px;padding:7px 11px;border-radius:99px;border:1px solid #3b2a7a;background:#120a33;color:#d7dcff;cursor:pointer}
.chip.on{background:linear-gradient(90deg,#00ffee33,#ff2d9633);border-color:var(--cyan);color:#fff}
.chat{display:flex;flex-direction:column;gap:10px;margin-top:12px}
.msg{padding:11px 13px;border-radius:13px;font-size:13.5px;line-height:1.5}
.msg.user{background:#141b4d;border:1px solid #3342a0;align-self:flex-end;max-width:90%}
.msg.ai{background:#0e0a2b;border:1px solid var(--line);align-self:flex-start;max-width:95%}
.msg.ai b{color:var(--cyan)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:820px){.grid2{grid-template-columns:1fr}}
table{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:8px}td,th{border:1px solid #2b1a5e;padding:8px 10px;text-align:left}th{color:var(--cyan)}
.progress{height:10px;background:#160d38;border-radius:99px;overflow:hidden;border:1px solid #2b1a5e;margin-top:10px}
.progress i{display:block;height:100%;width:0;background:linear-gradient(90deg,var(--cyan),var(--pink));transition:width .3s}
footer{color:var(--mut);font-size:11.5px;margin-top:18px;text-align:center}
code{background:#160d38;padding:2px 7px;border-radius:6px;font-size:12px}
</style></head>
<body><div class="wrap">
<header><div class="logo">N</div><div><h1>NEON <span>STUDIO</span></h1>
<p class="sub">Digite e a IA faz — roteiro + vídeo cyberpunk. Cole só a <b>API key</b>: o sistema identifica o provedor sozinho (Google, OpenAI, Anthropic, Groq, HuggingFace e mais). Demonstração estática interativa.</p></div></header>

<div class="card"><h2>🔑 1 · Detecção automática <span class="badge">só a key, sem base URL</span></h2>
<p class="hint">O backend resolve o provedor por prefixo da chave + catálogo oficial. As URLs internas nunca aparecem no cliente.</p></div>

<div class="grid2">
<div class="card"><h2>💬 2 · Chat — peça o roteiro</h2>
<div class="chat" id="chatBox"><div class="msg ai">👾 <b>NEON:</b> fala o que você quer — eu expando num roteiro cinematográfico de 8s.</div></div>
<label>Sua ordem (prompt)</label><textarea id="chatPrompt" placeholder="Ex: rua neon chuvosa com perseguição…"></textarea>
<div class="row"><button id="chatBtn">Enviar</button></div></div>
<div class="card"><h2>🎬 3 · Vídeo — demo de efeitos</h2>
<p class="hint">Escolha até 5 efeitos e simule a fila de renderização.</p>
<div class="chips" id="fx">__EFFECT_CHIPS__</div>
<div class="row"><button id="genBtn" class="pink">⚡ SIMULAR GERAÇÃO</button></div>
<div class="progress"><i id="bar"></i></div>
<p class="hint" id="genMsg">Pronto para simular.</p></div>
</div>

<div class="card"><h2>🔌 4 · API (backend FastAPI)</h2>
<table><tr><th>Método</th><th>Rota</th><th>Uso</th></tr>
<tr><td><code>GET</code></td><td><code>/health</code></td><td>Saúde do serviço</td></tr>
<tr><td><code>GET</code></td><td><code>/v1/effects</code></td><td>Lista os 32 efeitos</td></tr>
<tr><td><code>POST</code></td><td><code>/v1/discover</code></td><td>Identifica provedor + catálogo ao vivo</td></tr>
<tr><td><code>POST</code></td><td><code>/v1/chat</code></td><td>Roteiro via prompt</td></tr>
<tr><td><code>POST</code></td><td><code>/v1/videos</code></td><td>Veo real ou fallback local com efeitos</td></tr></table></div>

<footer>NEON STUDIO · build estático de demonstração · backend completo em <code>neon-studio/</code></footer>
</div><script>
const box=document.getElementById('chatBox');
function bubble(who,text){const d=document.createElement('div');d.className='msg '+(who==='user'?'user':'ai');d.innerHTML=(who==='user'?'🧑 ':'👾 <b>NEON:</b> ')+text.replace(/</g,'&lt;');box.appendChild(d)}
document.getElementById('chatBtn').onclick=()=>{const t=document.getElementById('chatPrompt').value.trim();if(!t)return;bubble('user',t);bubble('ai','Roteiro 8s: dolly lento sobre a cena — "'+t.slice(0,80)+'", luz neon cyan/magenta, chuva fina, grão 35mm, sem texto na tela.')};
const chips=[...document.querySelectorAll('.chip')];
chips.forEach(c=>c.onclick=()=>{const on=document.querySelectorAll('.chip.on').length;if(!c.classList.contains('on')&&on>=5)return;c.classList.toggle('on')});
document.getElementById('genBtn').onclick=()=>{const bar=document.getElementById('bar'),msg=document.getElementById('genMsg');let p=0;msg.textContent='Renderizando…';const iv=setInterval(()=>{p=Math.min(100,p+7);bar.style.width=p+'%';if(p>=100){clearInterval(iv);const sel=[...document.querySelectorAll('.chip.on')].map(c=>c.textContent).slice(0,3).join(' + ')||'grade neon + partículas';msg.textContent='✅ Pronto (demo) com: '+sel;}},120)};
</script></body></html>
"""


def main():
    effects = load_effects()
    assert len(effects) >= 30, f"expected 30+ effects, got {len(effects)}"
    chips = "\n".join(
        f'<span class="chip" title="{e["id"]}">{e["label"]}</span>' for e in effects
    )
    DIST.mkdir(parents=True, exist_ok=True)
    (DIST / "index.html").write_text(PAGE.replace("__EFFECT_CHIPS__", chips), encoding="utf-8")
    (DIST / "effects.json").write_text(
        json.dumps({"count": len(effects), "effects": effects}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"built {DIST/'index.html'} with {len(effects)} effects")


if __name__ == "__main__":
    sys.exit(main())

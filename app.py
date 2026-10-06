from __future__ import annotations

import asyncio
import os
import re
import uuid
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from effects import EFFECT_IDS, list_effects, render_effect_video
from providers import (
    DiscoveryResult, ProviderError, auto_detect, build_provider,
    choose_chat_model, choose_video_model, infer_provider,
    public_providers, redact_key,
)

load_dotenv()

APP_DIR = Path(__file__).resolve().parent
MEDIA_DIR = Path(os.getenv("MEDIA_DIR", str(APP_DIR / "media"))).resolve()
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
POLL_INTERVAL = float(os.getenv("VEO_POLL_INTERVAL_SECONDS", "8"))
JOB_TIMEOUT = float(os.getenv("VEO_JOB_TIMEOUT_SECONDS", "900"))

app = FastAPI(title="Gerador de Vídeo IA — Cyberpunk", version="2.0.0",
              description="Chat inteligente: digite e a IA cria texto ou vídeo. Chave auto-detectada, URLs escondidas.")
app.add_middleware(CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")],
    allow_credentials=False, allow_methods=["*"], allow_headers=["*"])


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    api_key: SecretStr | None = Field(default=None, description="Só a chave. O servidor identifica o provedor sozinho.")
    provider: str = "auto"
    base_url: str | None = None


class DiscoverRequest(Credentials):
    model: str | None = None


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=100_000)


class ChatRequest(Credentials):
    model: str | None = None
    messages: list[ChatMessage] = Field(min_length=1, max_length=100)
    temperature: float = Field(default=0.7, ge=0, le=2)


class VideoRequest(Credentials):
    prompt: str = Field(min_length=1, max_length=20_000)
    model: str | None = None
    aspect_ratio: Literal["16:9", "9:16"] = "16:9"
    resolution: Literal["720p", "1080p"] = "720p"
    quality: Literal["360p", "480p", "720p", "1080p"] = "360p"
    duration_seconds: int | None = Field(default=8, ge=2, le=600)
    generate_audio: bool | None = True
    negative_prompt: str | None = Field(default=None, max_length=5_000)
    effect: str | None = Field(default="neon_pulse", description="Um dos 36 efeitos locais.")
    use_cloud: bool = Field(default=True, description="Tenta nuvem primeiro; se falhar, cai no render local.")
    image_base64: str | None = None
    image_mime_type: str | None = "image/png"

    @field_validator("prompt")
    @classmethod
    def prompt_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("prompt não pode ser vazio")
        return v.strip()

    @field_validator("effect")
    @classmethod
    def effect_valid(cls, v: str | None) -> str | None:
        if v is None:
            return "neon_pulse"
        if v not in EFFECT_IDS:
            raise ValueError(f"effect inválido. Use um de: {', '.join(EFFECT_IDS[:6])}... (30 no total)")
        return v


class SmartRequest(Credentials):
    message: str = Field(min_length=1, max_length=20_000)
    effect: str | None = "neon_pulse"
    aspect_ratio: Literal["16:9", "9:16"] = "16:9"
    quality: Literal["360p", "480p", "720p", "1080p"] = "360p"
    duration_seconds: int | None = Field(default=8, ge=2, le=600)


class JobState(BaseModel):
    job_id: str
    status: Literal["queued", "generating", "completed", "failed"]
    provider: str
    model: str | None = None
    operation_name: str | None = None
    download_url: str | None = None
    text: str | None = None
    error: str | None = None


jobs: dict[str, JobState] = {}

VIDEO_KEYWORDS = re.compile(r"(v[íi]deo|video|filme|curta|anima|animação|cena|cinemat|gere\b|gera\b|crie\b|cria\b|render|efeito|clip|reels|tiktok|shorts|veo|sora|kling|pika|runway|luma)", re.I)


def _env_key(provider: str) -> str | None:
    from providers import REGISTRY
    names: list[str] = list(REGISTRY.get(provider, {}).get("envs", ()))
    if provider in ("auto", "__probe__"):
        for info in REGISTRY.values():
            for n in info.get("envs", ()):
                if n not in names:
                    names.append(n)
    for n in names:
        v = os.getenv(n)
        if v and v.strip():
            return v.strip()
    return None


async def _resolve(provider_hint: str, raw_key: str | None, base_url: str | None):
    """Resolve provedor: regra local -> sondagem automática (URLs escondidas)."""
    if not raw_key:
        raise HTTPException(status_code=422, detail="Cole sua API KEY. Sem chave, uso o render local com efeitos (grátis).")
    hint = (provider_hint or "auto").strip() or "auto"
    if hint != "auto":
        try:
            prov = build_provider(infer_provider(raw_key, hint, base_url), raw_key, base_url)
            return raw_key, infer_provider(raw_key, hint, base_url), prov
        except ProviderError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    # auto: regra local primeiro
    try:
        guess = infer_provider(raw_key, "auto", base_url)
    except ProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    if guess != "__probe__":
        try:
            return raw_key, guess, build_provider(guess, raw_key, base_url)
        except ProviderError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    # sondagem na rede (timeout curto por provider)
    try:
        pid, _res = await asyncio.wait_for(auto_detect(raw_key), timeout=60)
        return raw_key, pid, build_provider(pid, raw_key, base_url)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=502, detail="Auto-detecção demorou demais. Tente de novo ou escolha o provedor.")
    except ProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


def _key_of(c: Credentials, provider_hint: str) -> str:
    raw = c.api_key.get_secret_value().strip() if c.api_key else ""
    return raw or (_env_key(provider_hint) or "")


@app.get("/health")
async def health():
    return {"ok": True, "service": "gerador-video-cyberpunk", "jobs": len(jobs), "effects": len(EFFECT_IDS)}


@app.get("/v1/providers")
async def providers_public():
    return {"providers": public_providers(), "detection": "auto — só cole a api_key, URLs ficam no servidor"}


@app.get("/v1/effects")
async def effects():
    return {"effects": list_effects(), "total": len(EFFECT_IDS)}


@app.post("/v1/discover")
async def discover(req: DiscoverRequest):
    raw = _key_of(req, req.provider)
    key, pid, prov = await _resolve(req.provider, raw, req.base_url)
    try:
        if pid == "local":
            raise ProviderError("Render local não precisa de descoberta.", 422)
        res: DiscoveryResult = await prov.discover()
        sel = req.model
        if sel is None:
            sel = choose_video_model(res.models) if res.capabilities.get("video") else choose_chat_model(pid, res.models)
        return {"provider": pid, "key_hint": redact_key(key), "selected_model": sel,
                "models": res.models, "capabilities": res.capabilities}
    except ProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@app.post("/v1/chat")
async def chat(req: ChatRequest):
    raw = _key_of(req, req.provider)
    key, pid, prov = await _resolve(req.provider, raw, req.base_url)
    try:
        model = req.model
        if not model:
            catalog = await prov.discover()
            model = choose_chat_model(pid, catalog.models)
        out = await prov.chat(model, [m.model_dump() for m in req.messages], req.temperature)
        return {"provider": pid, "model": out.get("model", model), "text": out["text"],
                "usage": out.get("usage"), "key_hint": redact_key(key)}
    except ProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


def _run_local_effect(job_id: str, prompt: str, effect: str, aspect: str, duration: int, quality: str = "360p"):
    job = jobs[job_id]
    try:
        job.status = "generating"
        target = MEDIA_DIR / f"{job_id}.mp4"
        render_effect_video(prompt, effect or "neon_pulse", target, duration, aspect, quality=quality or "360p")
        job.status = "completed"
        job.download_url = f"/v1/videos/{job_id}/download"
    except Exception as exc:
        job.status = "failed"
        job.error = f"Render local falhou: {exc.__class__.__name__}"


async def _run_video_job(job_id: str, req: VideoRequest, key: str, pid: str, prov: Any):
    job = jobs[job_id]
    try:
        # Provedores com vídeo em nuvem: google / replicate
        if req.use_cloud and pid in ("google", "replicate") and hasattr(prov, "start_video"):
            try:
                catalog = await prov.discover()
                model = choose_video_model(catalog.models, req.model) if pid == "google" else (req.model or "replicate-video")
                job.model = model
                job.status = "generating"
                op = await prov.start_video(model, req.model_dump(exclude={"api_key", "provider", "base_url"}))
                job.operation_name = op
                await prov.wait_and_download(op, MEDIA_DIR / f"{job_id}.mp4",
                                             poll_interval=POLL_INTERVAL, timeout_seconds=JOB_TIMEOUT)
                job.status = "completed"
                job.download_url = f"/v1/videos/{job_id}/download"
                return
            except ProviderError as cloud_err:
                # FALLBACK GARANTIDO: nunca deixa o usuário sem vídeo
                job.error = f"Nuvem falhou ({cloud_err}), gerando com efeito local…"
        job.model = f"local:{req.effect}"
        await asyncio.to_thread(_run_local_effect, job_id, req.prompt, req.effect or "neon_pulse",
                                req.aspect_ratio, int(req.duration_seconds or 8), req.quality or "360p")
    except Exception as exc:
        job.status = "failed"
        job.error = f"Erro interno controlado: {exc.__class__.__name__}"


@app.post("/v1/videos", status_code=202, response_model=JobState)
async def create_video(req: VideoRequest):
    # Sem chave -> render local direto (sempre gera!)
    raw = _key_of(req, req.provider) if req.api_key or _env_key(req.provider) else ""
    if not raw:
        job_id = uuid.uuid4().hex
        jobs[job_id] = JobState(job_id=job_id, status="queued", provider="local", model=f"local:{req.effect}")
        asyncio.create_task(asyncio.to_thread(_run_local_effect, job_id, req.prompt,
                                              req.effect or "neon_pulse", req.aspect_ratio, int(req.duration_seconds or 8), req.quality or "360p"))
        return jobs[job_id]
    key, pid, prov = await _resolve(req.provider, raw, req.base_url)
    if pid not in ("google", "replicate", "local") and req.use_cloud:
        # chat-only na nuvem -> vai direto pro efeito local (garante MP4)
        pid_for_job = "local"
        job_id = uuid.uuid4().hex
        jobs[job_id] = JobState(job_id=job_id, status="queued", provider=pid_for_job, model=f"local:{req.effect}")
        asyncio.create_task(_run_video_job(job_id, req, key, "local", None))
        return jobs[job_id]
    job_id = uuid.uuid4().hex
    jobs[job_id] = JobState(job_id=job_id, status="queued", provider=pid)
    asyncio.create_task(_run_video_job(job_id, req, key, pid, prov))
    return jobs[job_id]


@app.post("/v1/smart", status_code=202)
async def smart(req: SmartRequest):
    """Chat inteligente: digite qualquer coisa — a IA decide chat ou vídeo."""
    msg = req.message.strip()
    wants_video = bool(VIDEO_KEYWORDS.search(msg))
    raw = _key_of(req, req.provider) if req.api_key or _env_key(req.provider) else ""
    # 1) Sem chave: vídeo local ou eco de chat — sempre responde
    if not raw:
        if wants_video:
            vr = VideoRequest(prompt=msg, aspect_ratio=req.aspect_ratio, quality=req.quality or "360p",
                              duration_seconds=req.duration_seconds, effect=req.effect, use_cloud=False)
            job_id = uuid.uuid4().hex
            jobs[job_id] = JobState(job_id=job_id, status="queued", provider="local", model=f"local:{req.effect}")
            asyncio.create_task(asyncio.to_thread(_run_local_effect, job_id, msg, req.effect or "neon_pulse",
                                                  req.aspect_ratio, int(req.duration_seconds or 8), req.quality or "360p"))
            return {"mode": "video", "job": jobs[job_id].model_dump(), "text": "Gerando seu vídeo com efeito local (sem chave). Acompanhe o status."}
        return {"mode": "chat", "text": f"Entendi: “{msg[:300]}”. Cole uma API KEY acima para respostas com IA avançada, ou peça “crie um vídeo...” para gerar MP4 na hora com 1 dos 36 efeitos.", "provider": "local"}
    # 2) Com chave: identifica sozinho
    key, pid, prov = await _resolve(req.provider, raw, req.base_url)
    if wants_video:
        vr = VideoRequest(prompt=msg, provider=req.provider, aspect_ratio=req.aspect_ratio, quality=req.quality or "360p",
                          duration_seconds=req.duration_seconds, effect=req.effect, use_cloud=True)
        # propaga chave sem logar
        from pydantic import SecretStr
        vr.api_key = SecretStr(key)
        job_id = uuid.uuid4().hex
        jobs[job_id] = JobState(job_id=job_id, status="queued", provider=pid)
        asyncio.create_task(_run_video_job(job_id, vr, key, pid, prov))
        return {"mode": "video", "provider": pid, "job": jobs[job_id].model_dump(),
                "text": f"Provedor identificado: {pid}. Gerando vídeo…"}
    # chat normal com roteiro melhorado
    try:
        catalog = await prov.discover()
        if not catalog.capabilities.get("chat", True) and pid in ("replicate",):
            return {"mode": "chat", "provider": pid, "text": "Esta chave é de vídeo. Para conversar, use Google, OpenAI, Groq, etc. Mas posso gerar seu vídeo — peça “crie um vídeo...”."}
        model = choose_chat_model(pid, catalog.models)
        out = await prov.chat(model, [{"role": "system", "content": "Você é um diretor cyberpunk. Responda em pt-BR, direto e visual."},
                                      {"role": "user", "content": msg}], 0.7)
        return {"mode": "chat", "provider": pid, "model": model, "text": out["text"]}
    except ProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@app.get("/v1/videos/{job_id}", response_model=JobState)
async def get_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado nesta instância.")
    return job


@app.get("/v1/videos/{job_id}/download")
async def download(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado.")
    if job.status != "completed":
        raise HTTPException(status_code=409, detail=f"Vídeo ainda não pronto: {job.status}. {job.error or ''}")
    path = MEDIA_DIR / f"{job_id}.mp4"
    if not path.exists():
        raise HTTPException(status_code=410, detail="Arquivo expirado (disco efêmero). Gere de novo.")
    return FileResponse(path, media_type="video/mp4", filename=f"{job_id}.mp4")


HTML = r"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GERADOR DE VÍDEO IA — Cyberpunk</title>
<style>
:root{color-scheme:dark;--neon:#00ffd8;--pink:#ff2fb3;--bg:#070a16}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(1200px 600px at 20% -10%,#2b0a4a 0%,transparent 60%),radial-gradient(900px 500px at 110% 10%,#003b46 0%,transparent 55%),var(--bg);color:#eaf2ff;font-family:Inter,system-ui,Segoe UI,sans-serif;min-height:100vh}
.wrap{max-width:1060px;margin:0 auto;padding:26px 16px 70px}
header{display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.logo{width:46px;height:46px;border-radius:12px;background:linear-gradient(135deg,var(--neon),var(--pink));box-shadow:0 0 24px #00ffd866;display:grid;place-items:center;font-size:24px}
h1{margin:0;font-size:24px;letter-spacing:.5px}h1 span{color:var(--neon)}
.sub{color:#93a0c4;margin:6px 0 0}
.card{background:#0d1329cc;border:1px solid #22315c;border-radius:16px;padding:18px;margin-top:16px;backdrop-filter:blur(8px);box-shadow:0 0 0 1px #00ffd811 inset}
.keyrow{display:flex;gap:10px;flex-wrap:wrap}
input,select,textarea{width:100%;border:1px solid #2c3c68;background:#080d20;color:#f2f6ff;border-radius:10px;padding:11px;font:inherit}
input:focus,textarea:focus,select:focus{outline:2px solid var(--neon);border-color:var(--neon)}
#chat{height:340px;overflow:auto;display:flex;flex-direction:column;gap:10px;background:#060a1acc;border:1px solid #22315c;border-radius:12px;padding:14px}
.msg{max-width:85%;padding:10px 13px;border-radius:12px;line-height:1.45;white-space:pre-wrap;word-break:break-word}
.me{align-self:flex-end;background:linear-gradient(135deg,#00ffd833,#ff2fb333);border:1px solid #00ffd855}
.ai{align-self:flex-start;background:#101838;border:1px solid #2c3c68}
.sys{align-self:center;color:#8b96bd;font-size:12px}
.row{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}
button{border:0;border-radius:10px;padding:11px 16px;font-weight:800;cursor:pointer;background:linear-gradient(135deg,var(--neon),#4d7cff);color:#031018}
button.ghost{background:#22315c;color:#dfe7ff}button.pink{background:linear-gradient(135deg,var(--pink),#ff7a3d);color:#1c0512}
button:disabled{opacity:.6;cursor:wait}
.effects{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px;margin-top:10px;max-height:170px;overflow:auto}
.fx{border:1px solid #2c3c68;background:#0a1028;color:#cfe3ff;border-radius:9px;padding:8px;font-size:12px;cursor:pointer;text-align:left}
.fx.on{border-color:var(--neon);box-shadow:0 0 12px #00ffd855;color:#fff}
video{width:100%;border-radius:12px;border:1px solid #2c3c68;background:#000}
.badge{display:inline-block;font-size:12px;padding:4px 10px;border-radius:99px;border:1px solid #2c3c68;color:#9fe8ff}
.muted{color:#8b96bd;font-size:12px}.ok{color:#7dffa8}.err{color:#ff8ba0}
.composer{display:flex;gap:10px;margin-top:12px}.composer textarea{min-height:56px;resize:vertical}
footer{margin-top:18px;color:#66719a;font-size:12px;text-align:center}
</style></head><body><div class="wrap">
<header><div class="logo">◈</div><div><h1>GERADOR DE VÍDEO <span>IA</span></h1>
<p class="sub">Digite e a IA faz — chat ou vídeo automático. Só cole a <b>API KEY</b>, o sistema identifica o provedor sozinho.</p></div></header>

<div class="card"><b>🔑 Chave (nunca exibimos URLs nem sua chave)</b>
<div class="keyrow" style="margin-top:10px"><div style="flex:2;min-width:220px"><input id="key" type="password" placeholder="Cole aqui: AIza… / sk-… / gsk_… / hf_… / r8_… qualquer uma"></div>
<div style="flex:1;min-width:130px"><select id="aspect"><option value="16:9">16:9 paisagem</option><option value="9:16">9:16 vertical</option></select></div>
<div style="flex:1;min-width:130px"><select id="quality"><option value="360p">360p leve</option><option value="480p">480p</option><option value="720p">720p HD</option><option value="1080p">1080p Full</option></select></div>
<div style="flex:1;min-width:130px"><select id="dur"><option value="8">8s</option><option value="15">15s</option><option value="30">30s</option><option value="60">1 min</option><option value="180">3 min</option><option value="300">5 min</option><option value="600">10 min</option></select></div></div>
<div class="row"><span class="badge" id="prov">provedor: auto-detect</span><span class="badge" id="fxbadge">efeito: neon_pulse</span><span class="badge" id="health">…</span></div>
<p class="muted">Grátis e pagas suportadas: Google/Veo, OpenAI, Anthropic, Groq, Together, OpenRouter, DeepSeek, Mistral, HF, Replicate, fal, Fireworks, xAI… + render local com 36 efeitos (funciona sem chave, até 10 min).</p></div>

<div class="card"><b>⚡ 36 efeitos especiais</b><div class="effects" id="fx"></div></div>

<div class="card"><b>💬 Chat inteligente</b><p class="muted">Ex: “crie um vídeo neon de uma cidade chuvosa” → gera MP4. Qualquer outra frase → a IA responde.</p>
<div id="chat"><div class="sys">Bem-vindo ao modo cyberpunk. Digite abaixo 👇</div></div>
<div class="composer"><textarea id="msg" placeholder="Digite aqui… ex: crie um vídeo cyberpunk de um dragão sobre a cidade"></textarea></div>
<div class="row"><button id="send">▶ ENVIAR</button><button id="btnVideo" class="pink">🎬 GERAR VÍDEO DIRETO</button><button id="btnClear" class="ghost">Limpar</button></div>
<div id="player" style="margin-top:12px"></div></div>

<footer>Deploy Railway: use a variável PORT automática • <span id="fxcount"></span></footer>
</div><script>
let FX='neon_pulse', FXLIST=[];
const $=id=>document.getElementById(id);
async function api(p,b){const r=await fetch(p,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)});const j=await r.json().catch(()=>({}));if(!r.ok)throw new Error(j.detail||('HTTP '+r.status));return j}
function creds(){return{api_key:$('key').value||null,provider:'auto'}}
function bubble(who,text){const d=document.createElement('div');d.className='msg '+(who==='me'?'me':'ai');d.textContent=text;$('chat').appendChild(d);$('chat').scrollTop=99999;return d}
async function loadFx(){const r=await fetch('/v1/effects');const j=await r.json();FXLIST=j.effects;$('fxcount').textContent=j.total+' efeitos ativos';const box=$('fx');box.innerHTML='';j.effects.forEach(f=>{const b=document.createElement('button');b.className='fx'+(f.id===FX?' on':'');b.textContent='✦ '+f.name;b.title=f.desc;b.onclick=()=>{FX=f.id;$('fxbadge').textContent='efeito: '+FX;box.querySelectorAll('.fx').forEach(x=>x.classList.remove('on'));b.classList.add('on')};box.appendChild(b)})}
async function poll(job){while(job.status==='queued'||job.status==='generating'){await new Promise(r=>setTimeout(r,4000));const r=await fetch('/v1/videos/'+job.job_id);job=await r.json()}return job}
async function send(forceVideo){const t=$('msg').value.trim();if(!t)return;$('msg').value='';bubble('me',t);const w=bubble('ai','processando…');try{let body={...creds(),message:t,effect:FX,aspect_ratio:$('aspect').value,quality:$('quality').value,duration_seconds:parseInt($('dur').value||'8')};if(forceVideo)body.message='crie um vídeo: '+body.message;const j=await api('/v1/smart',body);if(j.mode==='video'){w.textContent='🎬 '+(j.text||'Gerando vídeo…');const done=await poll(j.job);if(done.status==='completed'){$('player').innerHTML='<video controls autoplay loop src="'+done.download_url+'"></video><div class="row"><a href="'+done.download_url+'" download><button>⬇ BAIXAR MP4</button></a></div>';w.textContent+=' ✅ pronto!'}else{w.textContent+=' ❌ '+(done.error||'falhou')}}else{w.textContent=j.text}}catch(e){w.textContent='❌ '+e.message}}
$('send').onclick=()=>send(false);$('btnVideo').onclick=()=>{if(!$('msg').value.trim())$('msg').value='crie um vídeo cyberpunk de uma cidade neon na chuva';send(true)};
$('btnClear').onclick=()=>{$('chat').innerHTML='';$('player').innerHTML=''};
$('msg').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send(false)}});
fetch('/health').then(r=>r.json()).then(j=>$('health').textContent='● online • '+j.effects+' efeitos').catch(()=>$('health').textContent='● offline');
loadFx();
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
async def home():
    return HTMLResponse(HTML)

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from providers import (
    DiscoveryResult,
    ProviderError,
    build_provider,
    choose_chat_model,
    choose_video_model,
    infer_provider,
    redact_key,
)

load_dotenv()

APP_DIR = Path(__file__).resolve().parent
MEDIA_DIR = Path(os.getenv("MEDIA_DIR", str(APP_DIR / "media"))).resolve()
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
POLL_INTERVAL = float(os.getenv("VEO_POLL_INTERVAL_SECONDS", "10"))
JOB_TIMEOUT = float(os.getenv("VEO_JOB_TIMEOUT_SECONDS", "900"))

app = FastAPI(
    title="Netzack Videos V2",
    version="2.0.0",
    description="Netzack Videos V2 — um chat só, um prompt só; só a chave API, com detecção automática de IA/modelo e geração de vídeo estilo Veo 3.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("CORS_ORIGINS", "*").split(",")],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


ProviderLiteral = Literal["auto", "google", "openai", "anthropic", "openai_compatible"]


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_key: SecretStr | None = Field(default=None, description="Nunca é persistida nem devolvida pela API.")
    provider: ProviderLiteral = "auto"
    base_url: str | None = Field(default=None, description="Obrigatória para endpoints compatíveis customizados.")


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
    resolution: Literal["720p", "1080p", "4k"] = "720p"
    duration_seconds: int | None = Field(default=8, ge=4, le=8)
    generate_audio: bool | None = True
    negative_prompt: str | None = Field(default=None, max_length=5_000)
    sample_count: int | None = Field(default=1, ge=1, le=4)
    image_base64: str | None = Field(default=None, description="Opcional: imagem de referência em Base64.")
    image_mime_type: str | None = Field(default="image/png", pattern=r"^image/[a-zA-Z0-9.+-]+$")

    @field_validator("prompt")
    @classmethod
    def prompt_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("prompt não pode ser vazio")
        return value.strip()


class JobState(BaseModel):
    job_id: str
    status: Literal["queued", "generating", "completed", "failed"]
    provider: str
    model: str | None = None
    operation_name: str | None = None
    download_url: str | None = None
    error: str | None = None


jobs: dict[str, JobState] = {}


def _env_key(provider: str) -> str | None:
    names = {
        "google": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        "openai": ("OPENAI_API_KEY",),
        "anthropic": ("ANTHROPIC_API_KEY",),
        "openai_compatible": ("OPENAI_COMPATIBLE_API_KEY",),
    }
    for name in names.get(provider, ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY")):
        value = os.getenv(name)
        if value:
            return value.strip()
    return None


def _credentials(credentials: Credentials) -> tuple[str, str, Any]:
    raw_key = credentials.api_key.get_secret_value() if credentials.api_key else None
    key = (raw_key or _env_key(credentials.provider))
    if not key:
        raise HTTPException(
            status_code=422,
            detail="Informe api_key no corpo ou configure a variável de ambiente do provedor.",
        )
    try:
        provider_name = infer_provider(key, credentials.provider, credentials.base_url)
        provider = build_provider(provider_name, key, credentials.base_url)
    except ProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return key, provider_name, provider


def _provider_error(exc: ProviderError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=str(exc))


def _public_discovery(result: DiscoveryResult, selected: str | None, key: str) -> dict[str, Any]:
    return {
        "provider": result.provider,
        "key_hint": redact_key(key),
        "selected_model": selected,
        "models": result.models,
        "capabilities": result.capabilities,
        "selection": "live_catalog_then_priority_fallback",
    }


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"ok": True, "service": "netzack-videos-v2", "jobs_in_memory": len(jobs)}


@app.post("/v1/discover")
async def discover(request: DiscoverRequest) -> dict[str, Any]:
    key, provider_name, provider = _credentials(request)
    try:
        result: DiscoveryResult = await provider.discover()
        selected = request.model
        if provider_name == "google" and request.model is None:
            selected = choose_video_model(result.models) if result.capabilities.get("video") else choose_chat_model(provider_name, result.models)
        elif request.model is None:
            selected = choose_chat_model(provider_name, result.models)
        return _public_discovery(result, selected, key)
    except ProviderError as exc:
        raise _provider_error(exc) from exc


@app.post("/v1/chat")
async def chat(request: ChatRequest) -> dict[str, Any]:
    key, provider_name, provider = _credentials(request)
    messages = [message.model_dump() for message in request.messages]
    try:
        model = request.model
        if not model:
            catalog = await provider.discover()
            model = choose_chat_model(provider_name, catalog.models)
        result = await provider.chat(model, messages, request.temperature)
        return {
            "provider": provider_name,
            "model": result.get("model", model),
            "text": result["text"],
            "usage": result.get("usage"),
            "key_hint": redact_key(key),
        }
    except ProviderError as exc:
        raise _provider_error(exc) from exc


async def _run_video_job(job_id: str, request: VideoRequest, key: str, provider_name: str, provider: Any) -> None:
    job = jobs[job_id]
    try:
        catalog = await provider.discover()
        model = choose_video_model(catalog.models, request.model)
        job.model = model
        job.status = "generating"
        operation_name = await provider.start_video(model, request.model_dump(exclude={"api_key", "provider", "base_url"}))
        job.operation_name = operation_name
        target = MEDIA_DIR / f"{job_id}.mp4"
        await provider.wait_and_download(
            operation_name,
            target,
            poll_interval=POLL_INTERVAL,
            timeout_seconds=JOB_TIMEOUT,
        )
        job.status = "completed"
        job.download_url = f"/v1/videos/{job_id}/download"
    except ProviderError as exc:
        job.status = "failed"
        job.error = str(exc)
    except Exception as exc:  # não deixa a task morrer sem status observável
        job.status = "failed"
        job.error = f"Erro interno controlado: {exc.__class__.__name__}"


@app.post("/v1/videos", status_code=202, response_model=JobState)
async def create_video(request: VideoRequest) -> JobState:
    key, provider_name, provider = _credentials(request)
    if provider_name != "google":
        raise HTTPException(
            status_code=422,
            detail="A geração Veo usa uma chave Google/Gemini. OpenAI, Anthropic e endpoints compatíveis ficam disponíveis para /v1/chat.",
        )
    job_id = uuid.uuid4().hex
    job = JobState(job_id=job_id, status="queued", provider=provider_name)
    jobs[job_id] = job
    asyncio.create_task(_run_video_job(job_id, request, key, provider_name, provider))
    return job


@app.get("/v1/videos/{job_id}", response_model=JobState)
async def get_video_job(job_id: str) -> JobState:
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado nesta instância.")
    return job


@app.get("/v1/videos/{job_id}/download")
async def download_video(job_id: str) -> FileResponse:
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado nesta instância.")
    if job.status != "completed":
        raise HTTPException(status_code=409, detail=f"Vídeo ainda não está pronto: {job.status}.")
    path = MEDIA_DIR / f"{job_id}.mp4"
    if not path.exists():
        raise HTTPException(status_code=410, detail="O arquivo do vídeo não está mais disponível.")
    return FileResponse(path, media_type="video/mp4", filename=f"{job_id}.mp4")


HTML = r"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Netzack Videos V2</title>
<style>
:root{color-scheme:dark;font-family:Inter,system-ui,sans-serif}body{margin:0;background:#0b1020;color:#e8ecf7}main{max-width:980px;margin:0 auto;padding:28px 18px 60px}h1{margin:0 0 8px;font-size:28px}p{color:#aeb8d4}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:760px){.grid{grid-template-columns:1fr}}section{background:#141b31;border:1px solid #283454;border-radius:14px;padding:18px;margin-top:16px}label{display:block;margin:12px 0 6px;font-size:13px;color:#b6c2df}input,textarea,select{width:100%;box-sizing:border-box;border:1px solid #344365;background:#0d1428;color:#f5f7ff;border-radius:9px;padding:10px;font:inherit}textarea{min-height:150px;resize:vertical}.row{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}button{border:0;border-radius:9px;padding:10px 14px;background:#6d7cff;color:white;font-weight:700;cursor:pointer}button.secondary{background:#2d3a5c}button:disabled{opacity:.6;cursor:wait}pre{white-space:pre-wrap;word-break:break-word;background:#0a1020;border:1px solid #293654;border-radius:9px;padding:14px;min-height:70px;overflow:auto}.muted{font-size:12px;color:#8794b7}.status{color:#aee7ba}.danger{color:#ff9eab}
</style></head>
<body><main>
<h1>Netzack Videos V2</h1>
<p>Descubra o provedor, converse com o modelo e envie um prompt de vídeo. A chave fica apenas no navegador e no request atual.</p>
<section><h2>1. Credenciais</h2>
<label>Chave API (não salve em produção)</label><input id="key" type="password" placeholder="AIza... / sk-... / sk-ant-...">
<label>Provedor</label><select id="provider"><option value="auto">Auto detectar</option><option value="google">Google / Gemini / Veo</option><option value="openai">OpenAI</option><option value="anthropic">Anthropic</option><option value="openai_compatible">OpenAI compatível</option></select>
<label>Base URL customizada (opcional)</label><input id="base" placeholder="https://seu-endpoint/v1">
<div class="row"><button id="discover">Descobrir modelos</button></div><pre id="discovery" class="muted">A descoberta consulta o catálogo oficial do provedor e não mostra sua chave.</pre></section>
<div class="grid"><section><h2>2. Chat / roteiro</h2><label>Mensagem</label><textarea id="chatPrompt" placeholder="Crie um roteiro cinematográfico curto para um vídeo de 8 segundos..."></textarea><label>Modelo (opcional)</label><input id="chatModel" placeholder="seleção automática pelo catálogo"><div class="row"><button id="chat">Enviar</button><button id="copyChat" class="secondary">Copiar resposta</button></div><pre id="chatOut">A resposta aparecerá aqui.</pre></section>
<section><h2>3. Vídeo Veo</h2><label>Prompt visual + áudio</label><textarea id="videoPrompt" placeholder="Uma tomada cinematográfica... incluindo diálogos e som ambiente."></textarea><label>Modelo (opcional)</label><input id="videoModel" placeholder="veo-3.1-generate-preview"><div class="row"><button id="video">Gerar vídeo</button></div><pre id="videoOut">O job assíncrono aparecerá aqui.</pre></section></div>
<p class="muted">Para produção, use HTTPS, autenticação própria, Redis/worker e nunca persista api_key. Este painel é um bloco local de teste/copiar e colar.</p>
</main><script>
const $=id=>document.getElementById(id); const creds=()=>({api_key:$('key').value||null,provider:$('provider').value,base_url:$('base').value||null});
async function call(path,body){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const j=await r.json();if(!r.ok)throw new Error(j.detail||'Erro HTTP '+r.status);return j}
$('discover').onclick=async()=>{const b=$('discover');b.disabled=true;$('discovery').textContent='Consultando...';try{$('discovery').textContent=JSON.stringify(await call('/v1/discover',creds()),null,2)}catch(e){$('discovery').textContent='Erro: '+e.message}finally{b.disabled=false}};
$('chat').onclick=async()=>{const b=$('chat');b.disabled=true;$('chatOut').textContent='Gerando resposta...';try{const body={...creds(),model:$('chatModel').value||null,messages:[{role:'user',content:$('chatPrompt').value}]};const j=await call('/v1/chat',body);$('chatOut').textContent=j.text}catch(e){$('chatOut').textContent='Erro: '+e.message}finally{b.disabled=false}};
$('copyChat').onclick=async()=>{await navigator.clipboard.writeText($('chatOut').textContent);$('copyChat').textContent='Copiado';setTimeout(()=>$('copyChat').textContent='Copiar resposta',1200)};
$('video').onclick=async()=>{const b=$('video');b.disabled=true;$('videoOut').textContent='Enfileirando...';try{const j=await call('/v1/videos',{...creds(),model:$('videoModel').value||null,prompt:$('videoPrompt').value});$('videoOut').textContent=JSON.stringify(j,null,2);let status=j;while(status.status==='queued'||status.status==='generating'){await new Promise(r=>setTimeout(r,5000));const r=await fetch('/v1/videos/'+j.job_id);status=await r.json();$('videoOut').textContent=JSON.stringify(status,null,2)}if(status.download_url)$('videoOut').textContent+='\n\nBaixar: '+location.origin+status.download_url}catch(e){$('videoOut').textContent='Erro: '+e.message}finally{b.disabled=false}};
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
async def home() -> HTMLResponse:
    return HTMLResponse(HTML)

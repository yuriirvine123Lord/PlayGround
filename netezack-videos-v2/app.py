from __future__ import annotations

import asyncio
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from effects import list_effects, parse_effects_from_prompt
from providers import (
    KEY_FORMAT_HINTS,
    DiscoveryResult,
    ProviderError,
    build_provider,
    choose_chat_model,
    choose_video_model,
    hidden_base_for,
    infer_provider,
    redact_key,
    smart_detect_provider,
)
from video_fallback import render_local_mp4
from ai_video import render_ai_mp4, AI_MIN_DURATION, AI_MAX_DURATION
from engines import ENGINE_ORDER, ORCHESTRATOR_URL, try_orchestrator, engines_status

load_dotenv()

APP_DIR = Path(__file__).resolve().parent
MEDIA_DIR = Path(os.getenv("MEDIA_DIR", str(APP_DIR / "media"))).resolve()
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
POLL_INTERVAL = float(os.getenv("VEO_POLL_INTERVAL_SECONDS", "10"))
JOB_TIMEOUT = float(os.getenv("VEO_JOB_TIMEOUT_SECONDS", "900"))
EXPAND_TIMEOUT = float(os.getenv("EXPAND_TIMEOUT_SECONDS", "20"))

# Porta primária (uvicorn CLI usa o mesmo ${PORT:-8080}).
PRIMARY_PORT = int(os.getenv("PORT", "8080"))


async def _pump(src: asyncio.StreamReader, dst: asyncio.StreamWriter) -> None:
    try:
        while True:
            data = await src.read(65536)
            if not data:
                break
            dst.write(data)
            await dst.drain()
    except Exception:
        pass
    finally:
        try:
            dst.close()
        except Exception:
            pass


_PROXY_SERVERS: list[asyncio.AbstractServer] = []


async def _start_proxy(listen_port: int, dest_port: int) -> asyncio.AbstractServer:
    """Serve também a outra porta padrão (8000/8080) — match do proxy Railway."""

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            up_reader, up_writer = await asyncio.open_connection("127.0.0.1", dest_port)
        except Exception:
            try:
                writer.close()
            except Exception:
                pass
            return
        try:
            await asyncio.gather(
                _pump(reader, up_writer),
                _pump(up_reader, writer),
                return_exceptions=True,
            )
        finally:
            for w in (up_writer, writer):
                try:
                    w.close()
                except Exception:
                    pass

    return await asyncio.start_server(handle, "0.0.0.0", listen_port)


@asynccontextmanager
async def lifespan(_: FastAPI):
    for port in (8000, 8080):
        if port == PRIMARY_PORT:
            continue
        try:
            _PROXY_SERVERS.append(await _start_proxy(port, PRIMARY_PORT))
        except OSError:
            pass
    yield
    for srv in _PROXY_SERVERS:
        try:
            srv.close()
        except Exception:
            pass


app = FastAPI(
    title="⚡Netezack Vídeos V2 ⚡",
    version="2.1.0",
    description="⚡Netezack Vídeos V2 ⚡ — chat prompt-driven com preview real de geração. "
                "Só a API key: o sistema identifica o provedor e as base URLs ficam no servidor.",
    lifespan=lifespan,
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
    base_url: str | None = Field(default=None, description="Avançado: endpoint customizado (a UI esconde este campo).")


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
    duration_seconds: int | None = Field(default=8, ge=2, le=600,
                                         description="2s a 600s (10 minutos).")
    generate_audio: bool | None = True
    negative_prompt: str | None = Field(default=None, max_length=5_000)
    sample_count: int | None = Field(default=1, ge=1, le=4)
    image_base64: str | None = Field(default=None, description="Opcional: imagem de referência em Base64.")
    image_mime_type: str | None = Field(default="image/png", pattern=r"^image/[a-zA-Z0-9.+-]+$")
    effects: list[str] | None = Field(default=None, description="Até 5 efeitos; vazio = IA detecta pelo prompt.")
    use_fallback: bool = Field(default=True, description="Se o Veo falhar, gera vídeo local com efeitos.")

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
    progress: int = 0
    stage: str | None = None
    effects: list[str] | None = None
    fallback_used: bool = False
    engine: str | None = None
    preview_url: str | None = None
    frames: int | None = None
    total_frames: int | None = None


jobs: dict[str, JobState] = {}


def _env_key(provider: str) -> str | None:
    names = {
        "google": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        "openai": ("OPENAI_API_KEY",),
        "anthropic": ("ANTHROPIC_API_KEY",),
        "openai_compatible": ("OPENAI_COMPATIBLE_API_KEY",),
    }
    envs: tuple[str, ...] = names.get(provider, ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"))
    if provider not in names:
        envs = (f"{provider.upper()}_API_KEY", *envs)
    for name in envs:
        value = os.getenv(name)
        if value:
            return value.strip()
    return None


async def _credentials(credentials: Credentials) -> tuple[str, str, Any]:
    raw_key = credentials.api_key.get_secret_value() if credentials.api_key else None
    key = (raw_key or _env_key(credentials.provider))
    if not key:
        raise HTTPException(
            status_code=422,
            detail="Cole sua API key no campo de chave. O sistema identifica o provedor sozinho.",
        )
    try:
        provider_name = infer_provider(key, credentials.provider, credentials.base_url)
        provider = build_provider(provider_name, key, credentials.base_url or hidden_base_for(provider_name))
    except ProviderError as exc:
        if credentials.provider == "auto" and not credentials.base_url and exc.status_code == 422:
            detected = await smart_detect_provider(key)
            if detected:
                provider_name, hidden_base = detected
                try:
                    provider = build_provider(provider_name, key, hidden_base)
                    return key, provider_name, provider
                except ProviderError:
                    pass
            raise HTTPException(
                status_code=422,
                detail=f"Não identifiquei esta chave automaticamente. Formatos aceitos: {KEY_FORMAT_HINTS}",
            ) from exc
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return key, provider_name, provider


def _provider_error(exc: ProviderError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=str(exc))


def _public_discovery(result: DiscoveryResult, selected: str | None, key: str) -> dict[str, Any]:
    # NUNCA devolve base_url ou a chave — só dica redatada.
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
    return {"ok": True, "service": "netezack-videos-v2", "jobs_in_memory": len(jobs)}


@app.get("/v1/effects")
async def effects() -> dict[str, Any]:
    items = list_effects()
    return {"count": len(items), "effects": items}


@app.get("/v1/engines")
async def engines() -> dict[str, Any]:
    """Cascata de motores de vídeo: orquestrador → veo → flux → local."""
    return engines_status()


@app.post("/v1/discover")
async def discover(request: DiscoverRequest) -> dict[str, Any]:
    key, provider_name, provider = await _credentials(request)
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
    key, provider_name, provider = await _credentials(request)
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


async def _expand_prompt_inner(provider: Any, provider_name: str, prompt: str, duration_s: int) -> str:
    """A IA transforma a ordem do usuário num roteiro visual rico (best effort)."""
    catalog = await provider.discover()
    model = choose_chat_model(provider_name, catalog.models)
    if duration_s <= 60:
        span = f"{duration_s} segundos"
    else:
        span = (f"{duration_s} segundos (~{duration_s // 60} min): divida em cenas curtas de ~8s "
                f"que mudam de plano, cor, movimento e luz para o vídeo não repetir")
    out = await provider.chat(model, [
        {"role": "system", "content": (
            "Você é um diretor de cinema cyberpunk. Expanda a ordem do usuário num roteiro "
            f"visual de {span}: ação, câmera, luz, cor e áudio. Responda em 1 parágrafo, "
            "em inglês, sem texto na tela.")},
        {"role": "user", "content": prompt},
    ], 0.7)
    text = str(out.get("text", "")).strip()
    return text[:1200] if text else prompt


async def _expand_prompt(provider: Any, provider_name: str, prompt: str, duration_s: int = 8) -> str:
    """Envolve a expansão num teto de 20s — rede lenta nunca trava o job de vídeo."""
    try:
        return await asyncio.wait_for(
            _expand_prompt_inner(provider, provider_name, prompt, duration_s),
            timeout=EXPAND_TIMEOUT,
        )
    except Exception:
        return prompt


def _set(job_id: str, **fields: Any) -> None:
    job = jobs.get(job_id)
    if not job:
        return
    for k, v in fields.items():
        setattr(job, k, v)


def _publish_preview(job_id: str, frame_idx: int, total: int, frame, write_jpeg: bool = True) -> None:
    """Publica progresso real por quadro; grava JPEG atômico (throttled em vídeos longos)."""
    fields: dict[str, Any] = {
        "frames": frame_idx + 1,
        "total_frames": total,
        "progress": min(95, 55 + int(40 * (frame_idx + 1) / max(total, 1))),
        "stage": f"renderizando quadro {frame_idx + 1}/{total}",
        "preview_url": f"/v1/videos/{job_id}/preview",
    }
    if write_jpeg:
        from PIL import Image

        preview = MEDIA_DIR / f"preview_{job_id}.jpg"
        tmp = MEDIA_DIR / f".preview_{job_id}.jpg.tmp"
        Image.fromarray(frame).save(tmp, format="JPEG", quality=72)
        os.replace(tmp, preview)
    _set(job_id, **fields)


def _on_frame_throttled(job_id: str):
    """Preview JPEG ~96 atualizações por job; progresso a cada quadro."""
    state = {"step": None}

    def _cb(frame_idx: int, total: int, frame) -> None:
        if state["step"] is None:
            state["step"] = 1 if total <= 96 else max(1, total // 96)
        write = (frame_idx % state["step"] == 0) or (frame_idx == total - 1)
        _publish_preview(job_id, frame_idx, total, frame, write_jpeg=write)

    return _cb


async def _run_video_job(job_id: str, request: VideoRequest, key: str, provider_name: str, provider: Any) -> None:
    job = jobs[job_id]
    effects = parse_effects_from_prompt(request.prompt, request.effects)
    duration = int(request.duration_seconds or 8)
    rich_prompt = request.prompt
    resolution = "1080p" if request.resolution == "4k" else (request.resolution or "720p")
    if duration > 120 and resolution == "1080p":
        resolution = "720p"  # vídeos longos: prioriza velocidade e tamanho
    target = MEDIA_DIR / f"{job_id}.mp4"
    _set(job_id, effects=effects, progress=5, stage="entendendo seu prompt", status="generating")
    try:
        # --- Motor 1: orquestrador próprio (Veo3 etc), se configurado ---
        if "orchestrator" in ENGINE_ORDER and ORCHESTRATOR_URL:
            _set(job_id, progress=12, stage="motor orquestrador próprio (Veo3)…")
            ok = await asyncio.to_thread(
                try_orchestrator, request.prompt, duration, request.aspect_ratio, resolution, target)
            if ok:
                _set(job_id, status="completed", progress=100, engine="orchestrator",
                     stage="pronto (orquestrador)", download_url=f"/v1/videos/{job_id}/download",
                     fallback_used=False)
                job.status = "completed"
                job.download_url = f"/v1/videos/{job_id}/download"
                return
            _set(job_id, progress=15, stage="orquestrador indisponível → próximo motor…")

        # --- Motor 2: Veo remoto (google, até 8s) ---
        use_veo = "veo" in ENGINE_ORDER and provider_name == "google" and duration <= 8
        if use_veo:
            _set(job_id, stage="expandindo roteiro com IA")
            rich_prompt = await _expand_prompt(provider, provider_name, request.prompt, duration)
            _set(job_id, progress=15, stage="consultando catálogo Veo")
            try:
                catalog = await provider.discover()
                model = choose_video_model(catalog.models, request.model)
                job.model = model
                _set(job_id, progress=25, stage=f"gerando no Veo ({model})")
                payload = request.model_dump(exclude={"api_key", "provider", "base_url"})
                payload["prompt"] = rich_prompt
                if payload.get("resolution") == "4k":
                    payload["resolution"] = "1080p"  # preview não aceita 4k
                operation_name = await provider.start_video(model, payload)
                job.operation_name = operation_name

                def _prog(pct: int) -> None:
                    _set(job_id, progress=min(95, 25 + int(pct * 0.7)), stage="Veo remoto renderizando…")

                await provider.wait_and_download(
                    operation_name, target,
                    poll_interval=POLL_INTERVAL, timeout_seconds=JOB_TIMEOUT,
                    on_progress=_prog,
                )
                _set(job_id, status="completed", progress=100, engine="veo",
                     stage="pronto (veo)", download_url=f"/v1/videos/{job_id}/download")
                job.status = "completed"
                job.download_url = f"/v1/videos/{job_id}/download"
                return
            except ProviderError as exc:
                if not request.use_fallback:
                    raise
                _set(job_id, stage=f"Veo indisponível ({str(exc)[:90]}…). Próximo motor…",
                     progress=40, fallback_used=True)
        else:
            # Outra API ou duração >8s: IA roteiriza o prompt pros motores locais.
            if provider_name == "google":
                _set(job_id, stage=f"duração {duration}s > limite Veo (8s): roteirizando com IA",
                     progress=20)
            else:
                _set(job_id, stage="roteirizando com IA", progress=20)
            rich_prompt = await _expand_prompt(provider, provider_name, request.prompt, duration)
            _set(job_id, fallback_used=True)

        final_effects = None
        # --- Motor 3: IA open-source FLUX (quadros) em vídeos de 4s..60s ---
        if "flux" in ENGINE_ORDER and AI_MIN_DURATION <= duration <= AI_MAX_DURATION:
            _set(job_id, progress=60, stage="motor IA FLUX (open-source) gerando quadros…")
            final_effects = await asyncio.to_thread(
                render_ai_mp4, rich_prompt, effects, duration, resolution,
                request.aspect_ratio, target, seed=7,
                on_frame=_on_frame_throttled(job_id),
            )
            if final_effects is not None:
                job.engine = "flux"
        # --- Motor 4: render local procedural (sempre disponível) ---
        if final_effects is None and "local" in ENGINE_ORDER:
            _set(job_id, progress=55,
                 stage=f"motor local: renderizando {duration}s em {resolution} com efeitos: {', '.join(effects[:3])}")
            final_effects = await asyncio.to_thread(
                render_local_mp4, rich_prompt,
                effects, duration, resolution,
                request.aspect_ratio, target,
                on_frame=_on_frame_throttled(job_id),
            )
            job.engine = "local"
        if final_effects is None:
            raise ProviderError(
                f"Nenhum motor de vídeo disponível na cascata: {', '.join(ENGINE_ORDER)}.", 503)
        _set(job_id, status="completed", progress=100, stage=f"pronto ({job.engine})",
              download_url=f"/v1/videos/{job_id}/download", effects=final_effects,
              fallback_used=(job.engine in ("flux", "local")))
        job.status = "completed"
        job.download_url = f"/v1/videos/{job_id}/download"
    except ProviderError as exc:
        job.status = "failed"
        job.error = str(exc)
        _set(job_id, stage="falhou")
    except Exception as exc:  # não deixa a task morrer sem status observável
        job.status = "failed"
        job.error = f"Erro interno controlado: {exc.__class__.__name__}"
        _set(job_id, stage="falhou")


@app.post("/v1/videos", status_code=202, response_model=JobState)
async def create_video(request: VideoRequest) -> JobState:
    key, provider_name, provider = await _credentials(request)
    # Qualquer provedor gera vídeo: google<=8s via Veo; demais via IA open-source
    # (quadros FLUX) + render local com efeitos. So bloqueia se o usuario exigir
    # provedor remoto sem fallback (nenhum deles, alem do Veo, gera vídeo).
    if provider_name != "google" and not request.use_fallback:
        raise HTTPException(
            status_code=422,
            detail=(f"O provedor {provider_name} não gera vídeo por API remota. "
                    "Mantenha use_fallback=true para gerar o vídeo com IA local, "
                    "ou use chave Google/Gemini para Veo."),
        )
    job_id = uuid.uuid4().hex
    job = JobState(job_id=job_id, status="queued", provider=provider_name,
                   effects=parse_effects_from_prompt(request.prompt, request.effects))
    jobs[job_id] = job
    asyncio.create_task(_run_video_job(job_id, request, key, provider_name, provider))
    return job


@app.get("/v1/videos/{job_id}", response_model=JobState)
async def get_video_job(job_id: str) -> JobState:
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado nesta instância.")
    return job


@app.get("/v1/videos/{job_id}/preview")
async def video_preview(job_id: str) -> FileResponse:
    """Frame real mais recente do render — preview ao vivo (JPEG)."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado nesta instância.")
    path = MEDIA_DIR / f"preview_{job_id}.jpg"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Preview ainda não disponível.")
    return FileResponse(path, media_type="image/jpeg",
                        headers={"Cache-Control": "no-store, max-age=0"})


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
<title>⚡Netezack Vídeos V2 ⚡</title>
<style>
:root{color-scheme:dark;--bg:#04060b;--panel:#070b14;--line:#12203f;--neon:#00f5d4;--mag:#ff2e88;--txt:#dfe7f5;--mut:#7d8db0}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--txt);font:14px/1.5 ui-monospace,"JetBrains Mono",Menlo,Consolas,monospace}
.wrap{max-width:1000px;margin:0 auto;padding:20px 14px 60px}
header{display:flex;gap:12px;align-items:center;border-bottom:1px solid var(--line);padding-bottom:14px}
.logo{width:40px;height:40px;border:1px solid var(--neon);border-radius:9px;display:grid;place-items:center;color:var(--neon);font-weight:800;box-shadow:0 0 14px #00f5d444}
h1{margin:0;font-size:19px;letter-spacing:2px;font-weight:700}
h1 em{font-style:normal;color:var(--neon)}
.sub{margin:2px 0 0;color:var(--mut);font-size:12px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px;margin-top:14px}
h2{margin:0 0 8px;font-size:13px;letter-spacing:1.5px;color:var(--neon);text-transform:uppercase}
label{display:block;margin:10px 0 5px;font-size:11.5px;color:var(--mut);letter-spacing:.5px}
input,textarea,select{width:100%;border:1px solid var(--line);background:#04070e;color:var(--txt);border-radius:7px;padding:10px;font:inherit}
input:focus,textarea:focus{outline:none;border-color:var(--neon);box-shadow:0 0 0 1px #00f5d455}
textarea{min-height:86px;resize:vertical}
.row{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px;align-items:center}
button{border:1px solid var(--neon);background:transparent;color:var(--neon);border-radius:7px;padding:9px 14px;font:inherit;font-weight:700;cursor:pointer;letter-spacing:.5px}
button:hover{background:#00f5d415}
button.mag{border-color:var(--mag);color:var(--mag)}
button.mag:hover{background:#ff2e8818}
button.ghost{border-color:var(--line);color:var(--mut)}
button:disabled{opacity:.45;cursor:wait}
.badge{font-size:11px;padding:3px 9px;border:1px solid var(--line);border-radius:99px;color:var(--mut)}
.badge.on{border-color:var(--neon);color:var(--neon)}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;max-height:118px;overflow:auto}
.chip{font-size:11px;padding:5px 9px;border:1px solid var(--line);border-radius:99px;color:var(--mut);cursor:pointer;user-select:none}
.chip.on{border-color:var(--mag);color:var(--mag);background:#ff2e8814}
.chat{display:flex;flex-direction:column;gap:8px;margin-top:10px;max-height:250px;overflow:auto}
.msg{padding:9px 11px;border-radius:8px;font-size:12.5px;white-space:pre-wrap;line-height:1.45}
.msg.user{background:#0b1226;border:1px solid #1b2c55;align-self:flex-end;max-width:92%}
.msg.ai{background:#060a12;border:1px solid var(--line);align-self:flex-start;max-width:97%}
pre{white-space:pre-wrap;word-break:break-word;background:#03050a;border:1px solid var(--line);border-radius:7px;padding:11px;min-height:44px;overflow:auto;font-size:11.5px;margin:10px 0 0;color:var(--mut)}
.progress{height:8px;background:#0a1120;border:1px solid var(--line);border-radius:99px;overflow:hidden;margin-top:12px}
.progress i{display:block;height:100%;width:0;background:linear-gradient(90deg,var(--neon),var(--mag));transition:width .35s}
#stage{font-size:11.5px;color:var(--neon);margin-top:7px;min-height:16px}
#previewBox{display:none;margin-top:10px;position:relative}
#previewBox img{width:100%;border:1px solid var(--neon);border-radius:8px;display:block;box-shadow:0 0 22px #00f5d422}
#previewTag{position:absolute;top:8px;left:8px;background:#04060bcc;border:1px solid var(--mag);color:var(--mag);font-size:10.5px;padding:3px 8px;border-radius:5px;letter-spacing:1px}
video{width:100%;border:1px solid var(--neon);border-radius:8px;background:#000;margin-top:10px;display:none}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:820px){.grid2{grid-template-columns:1fr}}
details{margin-top:10px;font-size:11.5px;color:var(--mut)}summary{cursor:pointer}
footer{color:var(--mut);font-size:11px;margin-top:16px;text-align:center}
.ok{color:var(--neon)}.err{color:var(--mag)}
</style></head>
<body><div class="wrap">
<header><div class="logo">N</div><div><h1>⚡NETEZACK <em>VÍDEOS V2</em> ⚡</h1><p class="sub">digite → a IA obedece → vídeo com preview real, quadro a quadro</p></div>
<span class="badge" id="provBadge">auto</span></header>

<div class="card"><h2>// chave</h2>
<label>API KEY — o servidor identifica o provedor sozinho, as base URLs ficam escondidas</label>
<div class="row" style="margin-top:5px"><input id="key" type="password" placeholder="AIza… / sk-… / sk-ant-… / gsk_… / hf_… / r8_…" autocomplete="off" style="flex:2">
<button id="discover">IDENTIFICAR</button><button id="clearKey" class="ghost">limpar</button></div>
<pre id="discovery">status: aguardando chave</pre>
<details><summary>avançado</summary>
<label>provedor</label><select id="provider"><option value="auto">auto detectar</option><option value="google">google / gemini / veo</option><option value="openai">openai</option><option value="anthropic">anthropic</option><option value="openai_compatible">openai compatível</option></select>
<label>base url customizada</label><input id="base" placeholder="deixe vazio na maioria das vezes"></details>
</div>

<div class="grid2">
<div class="card"><h2>// chat ia</h2>
<div class="chat" id="chatBox"><div class="msg ai">NEON online. fala o que você quer criar.</div></div>
<label>sua ordem</label><textarea id="chatPrompt" placeholder="crie um roteiro de 8s de rua neon chuvosa…"></textarea>
<div class="row"><button id="chat">ENVIAR</button><button id="copyChat" class="ghost">Copiar resposta</button><button id="sendToVideo" class="ghost">usar no vídeo</button></div>
<pre id="chatOut" style="display:none"></pre></div>

<div class="card"><h2>// gerar vídeo</h2>
<label>prompt do vídeo</label><textarea id="videoPrompt" placeholder="rua neon chuvosa à noite, dolly lento, glitch + chuva, sem texto…"></textarea>
<div class="row">
<select id="aspect" style="flex:1"><option value="16:9">16:9</option><option value="9:16">9:16</option></select>
<select id="res" style="flex:1"><option value="720p">720p</option><option value="1080p">1080p</option></select>
<select id="dur" style="flex:1"><option value="8">8s</option><option value="15">15s</option><option value="30">30s</option><option value="60">1 min</option><option value="120">2 min</option><option value="300">5 min</option><option value="600">10 min</option></select>
</div>
<label>efeitos (<span id="fxCount">0</span>/5 — vazio = IA escolhe)</label>
<div class="chips" id="fx"></div>
<div class="row"><button id="video" class="mag">GERAR VÍDEO</button></div>
<div class="progress"><i id="bar"></i></div>
<div id="stage"></div>
<div id="previewBox"><span id="previewTag">RENDER AO VIVO</span><img id="previewImg" alt="preview"></div>
<pre id="videoOut">o job aparece aqui com progresso real</pre>
<video id="player" controls playsinline></video>
<div class="row"><a id="dl" style="display:none" href="#"><button class="ghost">BAIXAR MP4</button></a></div>
</div></div>
<footer>⚡NETEZACK VÍDEOS V2⚡ · preview real (frames) · urls de API só no servidor</footer>
</div><script>
const $=id=>document.getElementById(id);
fetch('/v1/engines').then(r=>r.json()).then(j=>{const f=document.querySelector('footer');f.textContent='⚡NETEZACK VÍDEOS V2⚡ · motores: '+j.order.join(' → ')}).catch(()=>{});
let SEL=new Set();
const creds=()=>({api_key:$('key').value||null,provider:$('provider').value,base_url:$('base').value||null});
async function call(path,body){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const j=await r.json().catch(()=>({}));if(!r.ok)throw new Error(j.detail||('Erro HTTP '+r.status));return j}
function bubble(who,text){const d=document.createElement('div');d.className='msg '+(who==='user'?'user':'ai');d.textContent=text;$('chatBox').appendChild(d);$('chatBox').scrollTop=1e6}
async function loadFx(){try{const j=await (await fetch('/v1/effects')).json();const box=$('fx');box.innerHTML='';(j.effects||[]).forEach(f=>{const s=document.createElement('span');s.className='chip';s.textContent=f.label;s.title=f.id+' — '+f.desc;s.onclick=()=>{SEL.has(f.id)?SEL.delete(f.id):(SEL.size<5&&SEL.add(f.id));s.classList.toggle('on');$('fxCount').textContent=SEL.size};box.appendChild(s)})}catch(e){$('fx').textContent='erro ao carregar efeitos'}}
loadFx();
$('clearKey').onclick=()=>{$('key').value='';$('provBadge').textContent='auto';$('provBadge').classList.remove('on')};
$('discover').onclick=async()=>{const b=$('discover');b.disabled=true;$('discovery').textContent='identificando…';try{const j=await call('/v1/discover',creds());$('provBadge').textContent=j.provider+' · '+j.key_hint;$('provBadge').classList.add('on');$('discovery').textContent='provedor: '+j.provider+' ('+j.key_hint+')\nmodelo: '+j.selected_model+'\ncapacidades: '+JSON.stringify(j.capabilities)+'\nmodelos: '+(j.models||[]).slice(0,25).join(', ')}catch(e){$('discovery').textContent='erro: '+e.message}finally{b.disabled=false}};
$('chat').onclick=async()=>{const t=$('chatPrompt').value.trim();if(!t)return;bubble('user',t);const b=$('chat');b.disabled=true;try{const j=await call('/v1/chat',{...creds(),messages:[{role:'user',content:t}]});$('chatOut').textContent=j.text;$('chatOut').style.display='block';bubble('ai',j.text.slice(0,900))}catch(e){bubble('ai','erro: '+e.message)}finally{b.disabled=false}};
$('copyChat').onclick=async()=>{await navigator.clipboard.writeText($('chatOut').textContent||'');$('copyChat').textContent='Copiado ✓';setTimeout(()=>$('copyChat').textContent='Copiar resposta',1200)};
$('sendToVideo').onclick=()=>{$('videoPrompt').value=$('chatOut').textContent||$('chatPrompt').value};
$('video').onclick=async()=>{const b=$('video');b.disabled=true;$('player').style.display='none';$('dl').style.display='none';$('previewBox').style.display='none';$('videoOut').textContent='enfileirando…';try{const body={...creds(),prompt:$('videoPrompt').value,aspect_ratio:$('aspect').value,resolution:$('res').value,duration_seconds:parseInt($('dur').value,10),effects:[...SEL]};if(!body.prompt.trim())throw new Error('descreva o vídeo primeiro.');const j=await call('/v1/videos',body);let s=j;$('videoOut').textContent='job '+j.job_id+' · '+j.provider+' · efeitos: '+(j.effects||[]).join(', ');while(s.status==='queued'||s.status==='generating'){await new Promise(r=>setTimeout(r,1200));const r=await fetch('/v1/videos/'+j.job_id);s=await r.json();$('bar').style.width=(s.progress||0)+'%';$('stage').textContent=(s.stage||s.status)+'  ['+(s.progress||0)+'%]  '+(s.frames?(s.frames+'/'+s.total_frames+' quadros'):'');if(s.preview_url){$('previewBox').style.display='block';$('previewImg').src=location.origin+s.preview_url+'?t='+Date.now()}$('videoOut').textContent='job '+j.job_id+'\n'+(s.stage||s.status)+' ['+(s.progress||0)+'%]'+(s.frames?'\nframes: '+s.frames+'/'+s.total_frames:'')+'\nefeitos: '+(s.effects||[]).join(', ')+(s.engine?'\nmotor: '+s.engine:'')+(s.fallback_used?'\nmodo: IA open-source + efeitos (fallback local)':'\nmodo: veo')}$('bar').style.width='100%';if(s.status==='completed'&&s.download_url){const url=location.origin+s.download_url;$('player').src=url;$('player').style.display='block';$('dl').href=url;$('dl').style.display='inline';$('stage').textContent='concluído — vídeo pronto';$('videoOut').textContent+='\n\nPRONTO: '+url}else{$('stage').textContent='falhou';$('videoOut').textContent+='\n\nfalhou: '+(s.error||'desconhecido')}}catch(e){$('stage').textContent='erro';$('videoOut').textContent='erro: '+e.message}finally{b.disabled=false}};
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
async def home() -> HTMLResponse:
    return HTMLResponse(HTML)

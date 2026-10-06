"""Registro inteligente de provedores — Base URLs ficam ESCONDIDAS no servidor.

O frontend NUNCA vê este arquivo. O usuário só cola a `api_key` e o
backend identifica automaticamente o provedor (grátis ou pago).
"""
from __future__ import annotations

import asyncio
import base64
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import httpx

# ---------------------------------------------------------------------------
# Catálogo interno (NÃO expor via API). Cada entrada tem 1..N base URLs.
# ---------------------------------------------------------------------------

REGISTRY: dict[str, dict[str, Any]] = {
    # ---- Vídeo premium (pagos, com trial/quota) ----
    "google": {
        "label": "Google Gemini / Veo",
        "free_tier": True,
        "kinds": ["chat", "video"],
        "prefixes": ("AIza",),
        "patterns": (re.compile(r"^AIza[0-9A-Za-z\-_]{20,}"),),
        "bases": ("https://generativelanguage.googleapis.com/v1beta",),
        "envs": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    },
    "openai": {
        "label": "OpenAI",
        "free_tier": False,
        "kinds": ["chat"],
        "prefixes": ("sk-proj-", "sk-svcacct-"),
        "patterns": (re.compile(r"^sk-(proj-|svcacct-)[0-9A-Za-z\-_]{20,}"),),
        "bases": ("https://api.openai.com/v1",),
        "envs": ("OPENAI_API_KEY",),
    },
    "anthropic": {
        "label": "Anthropic Claude",
        "free_tier": False,
        "kinds": ["chat"],
        "prefixes": ("sk-ant-",),
        "patterns": (re.compile(r"^sk-ant-[0-9A-Za-z\-_]{20,}"),),
        "bases": ("https://api.anthropic.com/v1",),
        "envs": ("ANTHROPIC_API_KEY",),
    },
    "xai": {
        "label": "xAI Grok",
        "free_tier": False,
        "kinds": ["chat"],
        "prefixes": ("xai-",),
        "patterns": (re.compile(r"^xai-[0-9A-Za-z\-_]{10,}"),),
        "bases": ("https://api.x.ai/v1",),
        "envs": ("XAI_API_KEY",),
    },
    "replicate": {
        "label": "Replicate (vídeo: Wan, Hunyuan, Kling, SVD...)",
        "free_tier": True,
        "kinds": ["chat", "video"],
        "prefixes": ("r8_",),
        "patterns": (re.compile(r"^r8_[0-9A-Za-z]{20,}"),),
        "bases": ("https://api.replicate.com/v1",),
        "envs": ("REPLICATE_API_TOKEN", "REPLICATE_API_KEY"),
    },
    "fal": {
        "label": "fal.ai (vídeo: Kling, Hailuo, Luma, Pika...)",
        "free_tier": True,
        "kinds": ["video"],
        "prefixes": ("fal-",),
        "patterns": (re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I),),
        "bases": ("https://queue.fal.run", "https://api.fal.ai"),
        "envs": ("FAL_KEY", "FAL_API_KEY"),
    },
    "huggingface": {
        "label": "Hugging Face (grátis + pago)",
        "free_tier": True,
        "kinds": ["chat", "video"],
        "prefixes": ("hf_",),
        "patterns": (re.compile(r"^hf_[0-9A-Za-z]{20,}"),),
        "bases": ("https://router.huggingface.co/v1", "https://api-inference.huggingface.co", "https://api-inference.huggingface.co/v1"),
        "envs": ("HF_TOKEN", "HUGGINGFACE_API_KEY"),
    },
    "groq": {
        "label": "Groq (grátis rápido)",
        "free_tier": True,
        "kinds": ["chat"],
        "prefixes": ("gsk_",),
        "patterns": (re.compile(r"^gsk_[0-9A-Za-z]{20,}"),),
        "bases": ("https://api.groq.com/openai/v1",),
        "envs": ("GROQ_API_KEY",),
    },
    "together": {
        "label": "Together AI (grátis + pago)",
        "free_tier": True,
        "kinds": ["chat"],
        "prefixes": (),
        "patterns": (re.compile(r"^[0-9a-f]{64}$"), re.compile(r"^tgp_v1_"),),
        "bases": ("https://api.together.xyz/v1",),
        "envs": ("TOGETHER_API_KEY",),
    },
    "openrouter": {
        "label": "OpenRouter (agrega 100+ modelos, grátis + pago)",
        "free_tier": True,
        "kinds": ["chat"],
        "prefixes": ("sk-or-",),
        "patterns": (re.compile(r"^sk-or-v1-[0-9a-f]{20,}"),),
        "bases": ("https://openrouter.ai/api/v1",),
        "envs": ("OPENROUTER_API_KEY",),
    },
    "deepseek": {
        "label": "DeepSeek (barato)",
        "free_tier": True,
        "kinds": ["chat"],
        "prefixes": ("sk-da",),
        "patterns": (re.compile(r"^sk-[0-9a-f]{32,}"),),
        "bases": ("https://api.deepseek.com/v1",),
        "envs": ("DEEPSEEK_API_KEY",),
    },
    "mistral": {
        "label": "Mistral",
        "free_tier": True,
        "kinds": ["chat"],
        "prefixes": (),
        "patterns": (re.compile(r"^[0-9A-Za-z]{32}$"),),
        "bases": ("https://api.mistral.ai/v1",),
        "envs": ("MISTRAL_API_KEY",),
    },
    "cohere": {
        "label": "Cohere",
        "free_tier": True,
        "kinds": ["chat"],
        "prefixes": (),
        "patterns": (),
        "bases": ("https://api.cohere.ai/compatibility/v1", "https://api.cohere.com/v1"),
        "envs": ("COHERE_API_KEY", "CO_API_KEY"),
    },
    "fireworks": {
        "label": "Fireworks AI",
        "free_tier": True,
        "kinds": ["chat"],
        "prefixes": ("fw_3Z", "fw-"),
        "patterns": (re.compile(r"^fw_[0-9A-Za-z\-_]{10,}"),),
        "bases": ("https://api.fireworks.ai/inference/v1",),
        "envs": ("FIREWORKS_API_KEY",),
    },
    "perplexity": {
        "label": "Perplexity",
        "free_tier": False,
        "kinds": ["chat"],
        "prefixes": ("pplx- rapport", "pplx-"),
        "patterns": (re.compile(r"^pplx-[0-9A-Za-z\-_]{10,}"),),
        "bases": ("https://api.perplexity.ai",),
        "envs": ("PERPLEXITY_API_KEY", "PPLX_API_KEY"),
    },
    "gemini_openai_compat": {
        "label": "Gemini via OpenAI-compat",
        "free_tier": True,
        "kinds": ["chat"],
        "prefixes": (),
        "patterns": (),
        "bases": ("https://generativelanguage.googleapis.com/v1beta/openai",),
        "envs": (),
    },
    "deepinfra": {
        "label": "DeepInfra",
        "free_tier": True,
        "kinds": ["chat"],
        "prefixes": (),
        "patterns": (),
        "bases": ("https://api.deepinfra.com/v1/openai",),
        "envs": ("DEEPINFRA_API_TOKEN",),
    },
    "novita": {
        "label": "Novita AI (vídeo Hunyuan grátis)",
        "free_tier": True,
        "kinds": ["chat", "video"],
        "prefixes": ("sk_",),
        "patterns": (),
        "bases": ("https://api.novita.ai/openai/v1", "https://api.novita.ai/v3"),
        "envs": ("NOVITA_API_KEY",),
    },
    "stability": {
        "label": "Stability AI (vídeo)",
        "free_tier": True,
        "kinds": ["video"],
        "prefixes": ("sk-",),
        "patterns": (),
        "bases": ("https://api.stability.ai/v2beta",),
        "envs": ("STABILITY_API_KEY",),
    },
    "runway": {
        "label": "Runway (vídeo Gen-3/4)",
        "free_tier": False,
        "kinds": ["video"],
        "prefixes": ("key_",),
        "patterns": (),
        "bases": ("https://api.dev.runwayml.com/v1", "https://api.runwayml.com/v1"),
        "envs": ("RUNWAYML_API_SECRET", "RUNWAY_API_KEY"),
    },
    "luma": {
        "label": "Luma Dream Machine",
        "free_tier": True,
        "kinds": ["video"],
        "prefixes": ("luma-",),
        "patterns": (),
        "bases": ("https://api.lumalabs.ai/dream-machine/v1",),
        "envs": ("LUMAAI_API_KEY", "LUMA_API_KEY"),
    },
    "heygen": {
        "label": "HeyGen (avatar)",
        "free_tier": True,
        "kinds": ["video"],
        "prefixes": (),
        "patterns": (),
        "bases": ("https://api.heygen.com/v2",),
        "envs": ("HEYGEN_API_KEY",),
    },
    "did": {
        "label": "D-ID (avatar)",
        "free_tier": True,
        "kinds": ["video"],
        "prefixes": (),
        "patterns": (),
        "bases": ("https://api.d-id.com",),
        "envs": ("DID_API_KEY",),
    },
}

# Ordem de sondagem quando o prefixo é ambíguo (ex: "sk-..." genérico).
# Só testa endpoints /models com timeout curto; a chave viaja apenas por HTTPS
# para hosts oficiais desta lista — nunca para URL arbitrária do usuário,
# exceto quando provider=openai_compatible + base_url explícita.
PROBE_ORDER = [
    "openai", "deepseek", "openrouter", "groq", "together",
    "mistral", "fireworks", "huggingface", "xai", "anthropic", "google",
]

VIDEO_MODEL_PRIORITY = (
    "veo-3.1-generate-preview",
    "veo-3.1-generate-001",
    "veo-3.0-generate-preview",
    "veo-3.0-generate-001",
    "veo-2.0-generate-001",
)
GOOGLE_CHAT_MODEL_PRIORITY = (
    "gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash",
    "gemini-3.1-pro-preview", "gemini-3-flash-preview",
)
GENERIC_CHAT_PRIORITY = ("gpt-4o", "gpt-5", "gpt-5-mini", "gpt-4o-mini")


class ProviderError(RuntimeError):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class DiscoveryResult:
    provider: str
    models: list[str]
    selected_model: str | None
    capabilities: dict[str, Any]


def normalize_model_name(value: str) -> str:
    return value.rsplit("/", 1)[-1].strip()


def redact_key(api_key: str) -> str:
    if len(api_key) <= 8:
        return "********"
    return f"{api_key[:4]}…{api_key[-4:]}"


def public_providers() -> list[dict[str, Any]]:
    """Visão pública SEM base_url (URLs ficam escondidas no servidor)."""
    out = []
    for pid, info in REGISTRY.items():
        out.append({
            "id": pid,
            "label": info["label"],
            "free_tier": info["free_tier"],
            "kinds": info["kinds"],
        })
    out.append({"id": "local", "label": "Render local com efeitos (sempre grátis, sem chave)", "free_tier": True, "kinds": ["video"]})
    return out


def infer_provider(api_key: str, provider: str = "auto", base_url: str | None = None) -> str:
    """Etapa 1: regras locais (prefixo/regex/host). Rápida, sem rede."""
    explicit = (provider or "auto").lower().strip()
    aliases = {
        "gemini": "google", "google_genai": "google", "google-gemini": "google",
        "openai-compatible": "openai_compatible", "compatible": "openai_compatible",
    }
    explicit = aliases.get(explicit, explicit)
    allowed = {"auto", "google", "openai", "openai_compatible", "anthropic"} | set(REGISTRY)
    if explicit not in allowed:
        raise ProviderError("provider inválido. Use auto ou um id válido.", 422)
    if explicit != "auto":
        return explicit

    host = (base_url or "").lower()
    for pid, info in REGISTRY.items():
        for b in info.get("bases", ()):  # type: ignore
            try:
                domain = b.split("://", 1)[1].split("/", 1)[0].lower()
                if domain and domain in host:
                    return pid
            except Exception:
                continue

    key = api_key.strip()
    for pid, info in REGISTRY.items():
        for pat in info.get("patterns", ()):  # type: ignore
            try:
                if pat.search(key):
                    # "sk-..." genérico: deixa para a sondagem decidir
                    if pid == "deepseek" and key.startswith("sk-") and len(key) < 40:
                        continue
                    return pid
            except Exception:
                continue
    # prefixos simples (sem regex)
    if key.startswith("AIza"):
        return "google"
    if key.startswith("sk-ant-"):
        return "anthropic"
    if key.startswith("gsk_"):
        return "groq"
    if key.startswith("hf_"):
        return "huggingface"
    if key.startswith("r8_"):
        return "replicate"
    if key.startswith("sk-or-"):
        return "openrouter"
    if key.startswith("xai-"):
        return "xai"
    if key.startswith("pplx-"):
        return "perplexity"
    if key.startswith("sk-proj-") or key.startswith("sk-svcacct-"):
        return "openai"
    # Desconhecido -> sondagem automática (etapa 2) cuidará disso.
    return "__probe__"


def _safe_error_text(response: httpx.Response) -> str:
    try:
        data = response.json()
        if isinstance(data, dict):
            error = data.get("error", data)
            if isinstance(error, dict):
                message = error.get("message") or error.get("status")
                if message:
                    return str(message)[:500]
            return json.dumps(error, ensure_ascii=False)[:500]
    except Exception:
        pass
    return (response.text or f"HTTP {response.status_code}")[:500]


async def _request_json(method: str, url: str, *, headers=None, params=None,
                        json_body=None, timeout: float = 60.0) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.request(method, url, headers=headers, params=params, json=json_body)
    except httpx.RequestError as exc:
        raise ProviderError(f"Falha de rede ao acessar o provedor: {exc.__class__.__name__}") from exc
    if response.status_code in (401, 403):
        raise ProviderError(f"Chave rejeitada pelo provedor ({response.status_code}): {_safe_error_text(response)}", response.status_code)
    if response.status_code == 429:
        raise ProviderError(f"Limite/quota excedido ({response.status_code}): {_safe_error_text(response)}", 429)
    if response.status_code >= 400:
        raise ProviderError(f"O provedor recusou a requisição ({response.status_code}): {_safe_error_text(response)}", response.status_code)
    try:
        data = response.json()
    except ValueError as exc:
        raise ProviderError("O provedor retornou resposta que não é JSON.") from exc
    if not isinstance(data, dict):
        raise ProviderError("O provedor retornou um JSON inesperado.")
    return data


def _model_ids(data: dict[str, Any]) -> list[str]:
    values = data.get("data") or data.get("models") or []
    result: list[str] = []
    if isinstance(values, list):
        for item in values:
            raw = (item.get("id") or item.get("name")) if isinstance(item, dict) else item
            if raw:
                name = normalize_model_name(str(raw))
                if name and name not in result:
                    result.append(name)
    return result


def _first_available(models: Iterable[str], priority: Iterable[str]) -> str | None:
    normalized = [normalize_model_name(m) for m in models]
    for preferred in priority:
        if preferred in normalized:
            return preferred
    return normalized[0] if normalized else None


def choose_chat_model(provider: str, models: list[str], requested: str | None = None) -> str:
    if requested:
        return normalize_model_name(requested)
    if provider == "google":
        return _first_available(models, GOOGLE_CHAT_MODEL_PRIORITY) or "gemini-2.0-flash"
    if provider in ("anthropic",):
        return _first_available(models, ("claude-sonnet-4-6", "claude-haiku-4-5")) or (models[0] if models else "claude-sonnet-4-6")
    sel = _first_available(models, GENERIC_CHAT_PRIORITY)
    if sel:
        return sel
    if models:
        return models[0]
    raise ProviderError("A API não informou nenhum modelo de chat. Informe model explicitamente.", 422)


def choose_video_model(models: list[str], requested: str | None = None) -> str:
    if requested:
        model = normalize_model_name(requested)
        if models and model not in {normalize_model_name(m) for m in models}:
            raise ProviderError(f"O modelo solicitado não apareceu no catálogo: {model}", 422)
        return model
    normalized = {normalize_model_name(m) for m in models}
    if normalized:
        for preferred in VIDEO_MODEL_PRIORITY:
            if preferred in normalized:
                return preferred
        # aceita qualquer veo disponível
        for m in normalized:
            if m.startswith("veo"):
                return m
        raise ProviderError("A chave Google foi válida, mas nenhum modelo Veo apareceu no catálogo. Ative billing/Veo no Google Cloud.", 403)
    return VIDEO_MODEL_PRIORITY[0]


def _google_headers(api_key: str) -> dict[str, str]:
    return {"x-goog-api-key": api_key, "Content-Type": "application/json"}


# ------------------------------- Providers -------------------------------

class GoogleProvider:
    name = "google"

    def __init__(self, api_key: str, base_url: str | None = None):
        self.api_key = api_key
        self.base_url = (base_url or REGISTRY["google"]["bases"][0]).rstrip("/")

    async def discover(self) -> DiscoveryResult:
        data = await _request_json("GET", f"{self.base_url}/models",
                                   headers={"x-goog-api-key": self.api_key},
                                   params={"pageSize": 1000})
        models = _model_ids(data)
        return DiscoveryResult(provider=self.name, models=models, selected_model=None,
                               capabilities={"chat": any(m.startswith("gemini") for m in models),
                                             "video": any(m.startswith("veo") for m in models),
                                             "native_audio": any(m.startswith("veo-3") for m in models),
                                             "automatic_selection": True})

    async def chat(self, model: str, messages: list[dict[str, str]], temperature: float) -> dict[str, Any]:
        system_parts = [m["content"] for m in messages if m.get("role") == "system"]
        contents = [{"role": "model" if m.get("role") == "assistant" else "user",
                     "parts": [{"text": m.get("content", "")}]} for m in messages if m.get("role") != "system"]
        payload: dict[str, Any] = {"contents": contents, "generationConfig": {"temperature": temperature}}
        if system_parts:
            payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}
        data = await _request_json("POST", f"{self.base_url}/models/{model}:generateContent",
                                   headers=_google_headers(self.api_key), json_body=payload)
        parts: list[str] = []
        for cand in data.get("candidates") or []:
            for p in ((cand.get("content") or {}).get("parts") or []):
                if isinstance(p, dict) and p.get("text"):
                    parts.append(str(p["text"]))
        text = "\n".join(parts).strip()
        if not text:
            # erros típicos: safety / quota
            raise ProviderError("O Gemini não retornou texto (possível bloqueio de segurança ou quota). Tente reformular o prompt.")
        return {"text": text, "model": model, "raw": data}

    async def start_video(self, model: str, request: dict[str, Any]) -> str:
        instance: dict[str, Any] = {"prompt": request["prompt"]}
        image_b64 = request.get("image_base64")
        if image_b64:
            encoded = image_b64.split(",", 1)[-1]
            try:
                base64.b64decode(encoded, validate=True)
            except Exception as exc:
                raise ProviderError("image_base64 não é Base64 válido.", 422) from exc
            instance["image"] = {"bytesBase64Encoded": encoded, "mimeType": request.get("image_mime_type") or "image/png"}
        # Veo: só 8s e 720p/1080p na maioria dos previews — normaliza para não dar 400
        duration = request.get("duration_seconds") or 8
        try:
            duration = int(duration)
        except Exception:
            duration = 8
        duration = 8 if duration != 8 else 8
        resolution = (request.get("resolution") or "720p").lower()
        if resolution not in ("720p", "1080p"):
            resolution = "720p"
        aspect = request.get("aspect_ratio") or "16:9"
        if aspect not in ("16:9", "9:16"):
            aspect = "16:9"
        parameters: dict[str, Any] = {"aspectRatio": aspect, "resolution": resolution,
                                      "durationSeconds": duration}
        if request.get("negative_prompt"):
            parameters["negativePrompt"] = request["negative_prompt"]
        if request.get("generate_audio") is not None:
            parameters["generateAudio"] = bool(request["generate_audio"])
        parameters["sampleCount"] = 1
        data = await _request_json("POST", f"{self.base_url}/models/{model}:predictLongRunning",
                                   headers=_google_headers(self.api_key),
                                   json_body={"instances": [instance], "parameters": parameters}, timeout=90)
        name = data.get("name") or (data.get("operation") or {}).get("name")
        if not name:
            raise ProviderError("O Veo não retornou a operação assíncrona. Verifique se o modelo Veo está ativo para sua chave.")
        return str(name)

    def _operation_url(self, operation_name: str) -> str:
        if operation_name.startswith("http"):
            sep = "?" if "?" not in operation_name else "&"
            # garante download de mídia quando for fetch direto
            return operation_name
        # operações vêm como "operations/xxx" — precisa do prefixo /v1beta/
        return f"{self.base_url}/{operation_name.lstrip('/')}"

    async def poll_video(self, operation_name: str) -> tuple[bool, dict[str, Any] | None]:
        data = await _request_json("GET", self._operation_url(operation_name),
                                   headers={"x-goog-api-key": self.api_key}, timeout=60)
        if not data.get("done", False):
            return False, None
        if data.get("error"):
            err = data["error"]
            msg = err.get("message") if isinstance(err, dict) else str(err)
            raise ProviderError(f"A geração Veo falhou: {msg} (ative billing e o acesso ao Veo no Google Cloud)", 502)
        ref = self._extract_video_ref(data)
        if not ref:
            raise ProviderError("A operação terminou, mas não trouxe o arquivo de vídeo.")
        return True, ref

    @staticmethod
    def _extract_video_ref(data: dict[str, Any]) -> dict[str, Any] | None:
        response = data.get("response") or {}
        cands = [((response.get("generateVideoResponse") or {}).get("generatedSamples") or []),
                 response.get("generatedVideos") or [], response.get("generated_videos") or [],
                 response.get("videos") or []]
        for samples in cands:
            if samples and isinstance(samples[0], dict):
                video = samples[0].get("video") or samples[0]
                if isinstance(video, dict):
                    return video
        # alguns gateways devolvem_uri direto
        if isinstance(response.get("video"), dict):
            return response["video"]
        return None

    async def download_video(self, video_ref: dict[str, Any], destination: Path) -> None:
        encoded = video_ref.get("bytesBase64Encoded")
        if encoded:
            try:
                destination.write_bytes(base64.b64decode(encoded))
                return
            except Exception as exc:
                raise ProviderError("O vídeo em Base64 é inválido.") from exc
        uri = video_ref.get("uri") or video_ref.get("url")
        if not uri:
            raise ProviderError("O Veo retornou referência sem URL baixável.")
        if str(uri).startswith("gs://"):
            raise ProviderError("O Veo retornou gs:// (requer bucket GCS). Troque para resposta com bytes ou URL https.", 502)
        try:
            async with httpx.AsyncClient(timeout=180, follow_redirects=True) as client:
                # URL assinada do Google precisa da chave como query ou header
                r = await client.get(str(uri), headers={"x-goog-api-key": self.api_key})
        except httpx.RequestError as exc:
            raise ProviderError(f"Falha ao baixar o vídeo: {exc.__class__.__name__}") from exc
        if r.status_code >= 400:
            raise ProviderError(f"Falha ao baixar o vídeo ({r.status_code}): {_safe_error_text(r)}", r.status_code)
        destination.write_bytes(r.content)

    async def wait_and_download(self, operation_name: str, destination: Path,
                                poll_interval: float = 10.0, timeout_seconds: float = 900.0) -> None:
        started = time.monotonic()
        while True:
            done, ref = await self.poll_video(operation_name)
            if done and ref:
                await self.download_video(ref, destination)
                return
            if time.monotonic() - started > timeout_seconds:
                raise ProviderError("Tempo limite excedido aguardando o Veo (até 15 min). Tente de novo.", 504)
            await asyncio.sleep(poll_interval)


class OpenAICompatibleProvider:
    """Cobre OpenAI, DeepSeek, Groq, Together, OpenRouter, Fireworks, HF router etc."""
    def __init__(self, api_key: str, base_url: str, name: str = "openai_compatible"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.name = name

    async def discover(self) -> DiscoveryResult:
        data = await _request_json("GET", f"{self.base_url}/models",
                                   headers={"Authorization": f"Bearer {self.api_key}"}, timeout=30)
        models = _model_ids(data)
        return DiscoveryResult(provider=self.name, models=models, selected_model=None,
                               capabilities={"chat": bool(models), "video": False, "automatic_selection": bool(models)})

    async def chat(self, model: str, messages: list[dict[str, str]], temperature: float) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        if self.name == "openrouter":
            headers["HTTP-Referer"] = "https://railway.app"
            headers["X-Title"] = "Gerador de Video"
        data = await _request_json("POST", f"{self.base_url}/chat/completions", headers=headers,
                                   json_body={"model": model, "messages": messages, "temperature": temperature}, timeout=180)
        choices = data.get("choices") or []
        if not choices:
            raise ProviderError("A API não retornou choices.")
        content = (choices[0].get("message") or {}).get("content")
        if isinstance(content, list):
            content = "".join(str(p.get("text", "")) for p in content if isinstance(p, dict))
        if not content:
            raise ProviderError("A API não retornou texto.")
        return {"text": str(content), "model": data.get("model", model), "usage": data.get("usage"), "raw": data}


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str, base_url: str | None = None):
        self.api_key = api_key
        self.base_url = (base_url or REGISTRY["anthropic"]["bases"][0]).rstrip("/")

    def _headers(self):
        return {"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}

    async def discover(self) -> DiscoveryResult:
        data = await _request_json("GET", f"{self.base_url}/models", headers=self._headers(), timeout=30)
        models = _model_ids(data)
        return DiscoveryResult(provider=self.name, models=models, selected_model=None,
                               capabilities={"chat": bool(models), "video": False, "automatic_selection": bool(models)})

    async def chat(self, model: str, messages: list[dict[str, str]], temperature: float) -> dict[str, Any]:
        system = "\n\n".join(m["content"] for m in messages if m.get("role") == "system")
        converted = [{"role": "assistant" if m.get("role") == "assistant" else "user", "content": m.get("content", "")}
                     for m in messages if m.get("role") != "system"]
        body: dict[str, Any] = {"model": model, "max_tokens": 4096, "temperature": temperature, "messages": converted}
        if system:
            body["system"] = system
        data = await _request_json("POST", f"{self.base_url}/messages", headers=self._headers(), json_body=body, timeout=180)
        text = "".join(str(b.get("text", "")) for b in (data.get("content") or []) if isinstance(b, dict)).strip()
        if not text:
            raise ProviderError("A Anthropic não retornou texto.")
        return {"text": text, "model": data.get("model", model), "usage": data.get("usage"), "raw": data}


class ReplicateProvider:
    """Vídeo via Replicate (modelo padrão: wan-video / ajuste via model)."""
    name = "replicate"
    DEFAULT_VERSION = "wan-video/wan-2.2-t2v-fast"  # nome amigável; discover lista reais

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = REGISTRY["replicate"]["bases"][0]

    def _h(self):
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def discover(self) -> DiscoveryResult:
        # Replicate não tem /models público simples; valida o token e anuncia vídeo.
        data = await _request_json("GET", f"{self.base_url}/models", headers=self._h(), timeout=30)
        return DiscoveryResult(provider=self.name, models=["replicate-video", self.DEFAULT_VERSION],
                               selected_model="replicate-video",
                               capabilities={"chat": False, "video": True, "automatic_selection": True})

    async def chat(self, model: str, messages: list[dict[str, str]], temperature: float) -> dict[str, Any]:
        raise ProviderError("Replicate aqui é usado para VÍDEO. Use Google/OpenAI/Groq para chat.", 422)

    async def start_video(self, model: str, request: dict[str, Any]) -> str:
        # Usa predictions com modelo de vídeo; usuário pode passar "owner/model:version"
        version = request.get("model") if request.get("model") and ":" in str(request.get("model")) else None
        body = {"input": {"prompt": request["prompt"], "aspect_ratio": request.get("aspect_ratio") or "16:9"}}
        url = f"{self.base_url}/models/{version}/predictions" if version else f"{self.base_url}/predictions"
        if not version:
            # fallback: cria prediction genérica (o servidor escolhe modelo padrão de vídeo)
            body = {"version": "video", "input": body["input"]}
        data = await _request_json("POST", url, headers=self._h() | {"Prefer": "wait"}, json_body=body, timeout=90)
        pid = data.get("id") or data.get("uuid")
        if not pid:
            raise ProviderError("Replicate não retornou o id da predição.")
        return str(pid)

    async def wait_and_download(self, operation_name: str, destination: Path, poll_interval: float = 8.0, timeout_seconds: float = 900.0) -> None:
        started = time.monotonic()
        while True:
            data = await _request_json("GET", f"{self.base_url}/predictions/{operation_name}", headers=self._h(), timeout=60)
            status = data.get("status")
            if status in ("succeeded",):
                out = data.get("output")
                url = out[0] if isinstance(out, list) and out else (out if isinstance(out, str) else None)
                if not url:
                    raise ProviderError("Replicate concluiu sem URL de vídeo.")
                async with httpx.AsyncClient(timeout=180, follow_redirects=True) as c:
                    r = await c.get(str(url))
                if r.status_code >= 400:
                    raise ProviderError(f"Falha ao baixar vídeo Replicate ({r.status_code}).", r.status_code)
                destination.write_bytes(r.content)
                return
            if status in ("failed", "canceled"):
                raise ProviderError(f"Replicate falhou: {str(data.get('error'))[:300]}")
            if time.monotonic() - started > timeout_seconds:
                raise ProviderError("Tempo limite no Replicate.", 504)
            await asyncio.sleep(poll_interval)


def _provider_bases(pid: str) -> list[str]:
    return list(REGISTRY.get(pid, {}).get("bases", []))


async def _try_discover(pid: str, api_key: str) -> DiscoveryResult | None:
    """Tenta descobrir um provider testando suas base URLs escondidas."""
    try:
        prov = build_provider(pid, api_key, None)
        if hasattr(prov, "discover"):
            return await prov.discover()
    except ProviderError as exc:
        # 401/403/404 = chave não é deste provider; 429 = é deste mas sem quota
        if exc.status_code in (429,):
            raise
        return None
    except Exception:
        return None
    return None


async def auto_detect(api_key: str) -> tuple[str, DiscoveryResult]:
    """Sonda os provedores conhecidos e retorna o primeiro que autenticar."""
    # 1) tenta ordem de probabilidade
    for pid in PROBE_ORDER:
        try:
            res = await _try_discover(pid, api_key)
            if res and (res.models or res.capabilities.get("chat") or res.capabilities.get("video")):
                return pid, res
            if res:
                return pid, res
        except ProviderError as exc:
            if exc.status_code == 429:
                # autenticou mas sem quota -> é este provider
                raise ProviderError(f"Chave identificada como {REGISTRY[pid]['label']}, mas sem quota/limite excedido.", 429) from exc
            continue
    # 2) tenta demais entradas do registro
    for pid in REGISTRY:
        if pid in PROBE_ORDER:
            continue
        res = await _try_discover(pid, api_key)
        if res:
            return pid, res
    raise ProviderError("Não consegui identificar esta chave em nenhum provedor conhecido (Google, OpenAI, Anthropic, Groq, Together, OpenRouter, DeepSeek, HF, Replicate...). Verifique se a chave está completa.", 422)


def build_provider(provider: str, api_key: str, base_url: str | None = None) -> Any:
    if provider == "google":
        return GoogleProvider(api_key, base_url)
    if provider == "anthropic":
        return AnthropicProvider(api_key, base_url)
    if provider == "openai":
        return OpenAICompatibleProvider(api_key, base_url or REGISTRY["openai"]["bases"][0], "openai")
    if provider == "openai_compatible":
        if not base_url:
            raise ProviderError("base_url é obrigatório para openai_compatible.", 422)
        return OpenAICompatibleProvider(api_key, base_url, "openai_compatible")
    if provider in REGISTRY:
        info = REGISTRY[provider]
        kinds = info.get("kinds", ["chat"])
        bases = _provider_bases(provider)
        default_base = base_url or (bases[0] if bases else None)
        if provider == "replicate":
            return ReplicateProvider(api_key)
        if provider in ("groq", "together", "openrouter", "deepseek", "mistral", "fireworks",
                        "xai", "huggingface", "deepinfra", "novita", "cohere", "perplexity", "gemini_openai_compat"):
            if not default_base:
                raise ProviderError(f"Sem endpoint interno para {provider}.", 500)
            return OpenAICompatibleProvider(api_key, default_base, provider)
        if "chat" in kinds and default_base:
            return OpenAICompatibleProvider(api_key, default_base, provider)
        raise ProviderError(f"Provedor '{provider}' precisa de integração dedicada de vídeo. Use Google/Replicate ou o render local com efeitos.", 422)
    raise ProviderError(f"Provedor não suportado: {provider}", 422)

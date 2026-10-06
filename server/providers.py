from __future__ import annotations

import asyncio
import base64
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin

import httpx


GOOGLE_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
OPENAI_BASE_URL = "https://api.openai.com/v1"
ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1"

VIDEO_MODEL_PRIORITY = (
    "veo-3.1-generate-preview",
    "veo-3.1-generate-001",
    "veo-3.0-generate-preview",
    "veo-3.0-generate-001",
    "veo-2.0-generate-001",
)
GOOGLE_CHAT_MODEL_PRIORITY = (
    "gemini-3.1-pro-preview",
    "gemini-3-flash-preview",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
)
OPENAI_CHAT_MODEL_PRIORITY = ("gpt-5.5", "gpt-5", "gpt-5-mini", "gpt-4o")
ANTHROPIC_CHAT_MODEL_PRIORITY = (
    "claude-opus-4-7",
    "claude-opus-4-6",
    "claude-sonnet-4-6",
    "claude-haiku-4-5",
)


class ProviderError(RuntimeError):
    """Erro seguro para devolver ao cliente sem incluir a chave da API."""

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


def infer_provider(api_key: str, provider: str = "auto", base_url: str | None = None) -> str:
    """Infere o provedor sem enviar a chave para endpoints aleatórios.

    Chaves não carregam um padrão universal. Prefixos conhecidos e o host informado
    permitem a detecção segura; para uma chave desconhecida, o cliente deve informar
    provider/base_url explicitamente.
    """
    explicit = (provider or "auto").lower().strip()
    aliases = {
        "gemini": "google",
        "google_genai": "google",
        "google-gemini": "google",
        "openai-compatible": "openai_compatible",
        "compatible": "openai_compatible",
        "anthropic": "anthropic",
    }
    explicit = aliases.get(explicit, explicit)
    allowed = {"auto", "google", "openai", "openai_compatible", "anthropic"}
    if explicit not in allowed:
        raise ProviderError(
            "provider inválido. Use auto, google, openai, anthropic ou openai_compatible.",
            422,
        )
    if explicit != "auto":
        return explicit

    host = (base_url or "").lower()
    if "generativelanguage.googleapis.com" in host or "aiplatform.googleapis.com" in host:
        return "google"
    if "anthropic.com" in host:
        return "anthropic"
    if "api.openai.com" in host:
        return "openai"

    key = api_key.strip()
    if key.startswith("AIza"):
        return "google"
    if key.startswith("sk-ant-"):
        return "anthropic"
    if key.startswith("sk-"):
        return "openai"

    raise ProviderError(
        "Não foi possível identificar esta chave com segurança. Informe provider e base_url; "
        "uma chave desconhecida não possui um prefixo universal.",
        422,
    )


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
    return response.text[:500] or f"HTTP {response.status_code}"


async def _request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    timeout: float = 60.0,
    follow_redirects: bool = False,
) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=follow_redirects) as client:
            response = await client.request(
                method,
                url,
                headers=headers,
                params=params,
                json=json_body,
            )
    except httpx.RequestError as exc:
        raise ProviderError(f"Falha de rede ao acessar o provedor: {exc.__class__.__name__}") from exc

    if response.status_code >= 400:
        raise ProviderError(
            f"O provedor recusou a requisição ({response.status_code}): {_safe_error_text(response)}",
            response.status_code,
        )
    try:
        data = response.json()
    except ValueError as exc:
        raise ProviderError("O provedor retornou uma resposta que não é JSON.") from exc
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
        selected = _first_available(models, GOOGLE_CHAT_MODEL_PRIORITY)
        return selected or "gemini-3.1-pro-preview"
    if provider == "anthropic":
        selected = _first_available(models, ANTHROPIC_CHAT_MODEL_PRIORITY)
        return selected or "claude-sonnet-4-6"
    selected = _first_available(models, OPENAI_CHAT_MODEL_PRIORITY)
    if selected:
        return selected
    raise ProviderError(
        "A API não informou nenhum modelo de chat. Informe model explicitamente.",
        422,
    )


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
        raise ProviderError(
            "A chave Google foi válida, mas nenhum modelo Veo disponível apareceu no catálogo.",
            403,
        )
    # Fallback para endpoints que não expõem a listagem de modelos.
    return VIDEO_MODEL_PRIORITY[0]


def _google_headers(api_key: str) -> dict[str, str]:
    return {"x-goog-api-key": api_key, "Content-Type": "application/json"}


class GoogleProvider:
    name = "google"

    def __init__(self, api_key: str, base_url: str | None = None):
        self.api_key = api_key
        self.base_url = (base_url or GOOGLE_BASE_URL).rstrip("/")

    async def discover(self) -> DiscoveryResult:
        data = await _request_json(
            "GET",
            f"{self.base_url}/models",
            headers={"x-goog-api-key": self.api_key},
            params={"pageSize": 1000},
        )
        models = _model_ids(data)
        return DiscoveryResult(
            provider=self.name,
            models=models,
            selected_model=None,
            capabilities={
                "chat": any(m.startswith("gemini") for m in models),
                "video": any(m.startswith("veo") for m in models),
                "native_audio": any(m.startswith("veo-3") for m in models),
                "automatic_selection": True,
            },
        )

    async def chat(self, model: str, messages: list[dict[str, str]], temperature: float) -> dict[str, Any]:
        system_parts = [m["content"] for m in messages if m.get("role") == "system"]
        contents = []
        for message in messages:
            role = message.get("role", "user")
            if role == "system":
                continue
            contents.append(
                {
                    "role": "model" if role == "assistant" else "user",
                    "parts": [{"text": message.get("content", "")}],
                }
            )
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }
        if system_parts:
            payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}
        data = await _request_json(
            "POST",
            f"{self.base_url}/models/{model}:generateContent",
            headers=_google_headers(self.api_key),
            json_body=payload,
        )
        candidates = data.get("candidates") or []
        text_parts: list[str] = []
        if candidates:
            content = candidates[0].get("content") or {}
            for part in content.get("parts") or []:
                if isinstance(part, dict) and part.get("text"):
                    text_parts.append(str(part["text"]))
        text = "\n".join(text_parts).strip()
        if not text:
            raise ProviderError("O Gemini não retornou texto na resposta.")
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
            instance["image"] = {
                "bytesBase64Encoded": encoded,
                "mimeType": request.get("image_mime_type") or "image/png",
            }

        parameters: dict[str, Any] = {
            "aspectRatio": request.get("aspect_ratio") or "16:9",
            "resolution": request.get("resolution") or "720p",
        }
        for key in ("duration_seconds", "generate_audio", "negative_prompt", "sample_count"):
            value = request.get(key)
            if value is not None:
                api_key = {
                    "duration_seconds": "durationSeconds",
                    "generate_audio": "generateAudio",
                    "negative_prompt": "negativePrompt",
                    "sample_count": "sampleCount",
                }[key]
                parameters[api_key] = value

        data = await _request_json(
            "POST",
            f"{self.base_url}/models/{model}:predictLongRunning",
            headers=_google_headers(self.api_key),
            json_body={"instances": [instance], "parameters": parameters},
            timeout=90,
        )
        operation_name = data.get("name")
        if not operation_name:
            # Alguns gateways devolvem a operação aninhada.
            operation_name = (data.get("operation") or {}).get("name")
        if not operation_name:
            raise ProviderError("O Veo não retornou o nome da operação assíncrona.")
        return str(operation_name)

    def _operation_url(self, operation_name: str) -> str:
        if operation_name.startswith("http://") or operation_name.startswith("https://"):
            return operation_name
        return urljoin(f"{self.base_url}/", operation_name.lstrip("/"))

    async def poll_video(self, operation_name: str) -> tuple[bool, dict[str, Any] | None]:
        data = await _request_json(
            "GET",
            self._operation_url(operation_name),
            headers={"x-goog-api-key": self.api_key},
            timeout=60,
        )
        if not data.get("done", False):
            return False, None
        if data.get("error"):
            error = data["error"]
            message = error.get("message") if isinstance(error, dict) else str(error)
            raise ProviderError(f"A geração Veo falhou: {message}", 502)
        video_ref = self._extract_video_ref(data)
        if not video_ref:
            raise ProviderError("A operação terminou, mas não trouxe o arquivo de vídeo.")
        return True, video_ref

    @staticmethod
    def _extract_video_ref(data: dict[str, Any]) -> dict[str, Any] | None:
        response = data.get("response") or {}
        candidates = [
            ((response.get("generateVideoResponse") or {}).get("generatedSamples") or []),
            response.get("generatedVideos") or [],
            response.get("generated_videos") or [],
        ]
        for samples in candidates:
            if not samples:
                continue
            first = samples[0]
            if isinstance(first, dict):
                video = first.get("video") or first
                if isinstance(video, dict):
                    return video
        return None

    async def download_video(self, video_ref: dict[str, Any], destination: Path) -> None:
        encoded = video_ref.get("bytesBase64Encoded")
        if encoded:
            try:
                destination.write_bytes(base64.b64decode(encoded))
                return
            except Exception as exc:
                raise ProviderError("O vídeo retornado em Base64 é inválido.") from exc
        uri = video_ref.get("uri") or video_ref.get("url")
        if not uri or str(uri).startswith("gs://"):
            raise ProviderError("O Veo retornou um URI que não pode ser baixado diretamente pela API.")
        try:
            async with httpx.AsyncClient(timeout=180, follow_redirects=True) as client:
                response = await client.get(str(uri), headers={"x-goog-api-key": self.api_key})
        except httpx.RequestError as exc:
            raise ProviderError(f"Falha ao baixar o vídeo: {exc.__class__.__name__}") from exc
        if response.status_code >= 400:
            raise ProviderError(
                f"Falha ao baixar o vídeo ({response.status_code}): {_safe_error_text(response)}",
                response.status_code,
            )
        destination.write_bytes(response.content)

    async def wait_and_download(
        self,
        operation_name: str,
        destination: Path,
        poll_interval: float = 10.0,
        timeout_seconds: float = 900.0,
    ) -> None:
        started = time.monotonic()
        while True:
            done, video_ref = await self.poll_video(operation_name)
            if done and video_ref:
                await self.download_video(video_ref, destination)
                return
            if time.monotonic() - started > timeout_seconds:
                raise ProviderError("Tempo limite excedido aguardando o Veo.", 504)
            await asyncio.sleep(poll_interval)


class OpenAICompatibleProvider:
    name = "openai_compatible"

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    async def discover(self) -> DiscoveryResult:
        data = await _request_json(
            "GET",
            f"{self.base_url}/models",
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        models = _model_ids(data)
        return DiscoveryResult(
            provider=self.name,
            models=models,
            selected_model=None,
            capabilities={"chat": bool(models), "video": False, "automatic_selection": bool(models)},
        )

    async def chat(self, model: str, messages: list[dict[str, str]], temperature: float) -> dict[str, Any]:
        data = await _request_json(
            "POST",
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json_body={"model": model, "messages": messages, "temperature": temperature},
            timeout=180,
        )
        choices = data.get("choices") or []
        if not choices:
            raise ProviderError("A API compatível não retornou choices.")
        message = choices[0].get("message") or {}
        text = message.get("content")
        if isinstance(text, list):
            text = "".join(str(part.get("text", "")) for part in text if isinstance(part, dict))
        if not text:
            raise ProviderError("A API compatível não retornou texto.")
        return {"text": str(text), "model": data.get("model", model), "usage": data.get("usage"), "raw": data}


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str, base_url: str | None = None):
        self.api_key = api_key
        self.base_url = (base_url or ANTHROPIC_BASE_URL).rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

    async def discover(self) -> DiscoveryResult:
        data = await _request_json("GET", f"{self.base_url}/models", headers=self._headers())
        models = _model_ids(data)
        return DiscoveryResult(
            provider=self.name,
            models=models,
            selected_model=None,
            capabilities={"chat": bool(models), "video": False, "automatic_selection": bool(models)},
        )

    async def chat(self, model: str, messages: list[dict[str, str]], temperature: float) -> dict[str, Any]:
        system = "\n\n".join(m["content"] for m in messages if m.get("role") == "system")
        converted = [
            {"role": "assistant" if m.get("role") == "assistant" else "user", "content": m.get("content", "")}
            for m in messages
            if m.get("role") != "system"
        ]
        body: dict[str, Any] = {
            "model": model,
            "max_tokens": 4096,
            "temperature": temperature,
            "messages": converted,
        }
        if system:
            body["system"] = system
        data = await _request_json(
            "POST",
            f"{self.base_url}/messages",
            headers=self._headers(),
            json_body=body,
            timeout=180,
        )
        text = "".join(
            str(block.get("text", "")) for block in (data.get("content") or []) if isinstance(block, dict)
        ).strip()
        if not text:
            raise ProviderError("A Anthropic não retornou texto.")
        return {"text": text, "model": data.get("model", model), "usage": data.get("usage"), "raw": data}


def build_provider(provider: str, api_key: str, base_url: str | None = None) -> Any:
    if provider == "google":
        return GoogleProvider(api_key, base_url)
    if provider == "anthropic":
        return AnthropicProvider(api_key, base_url)
    if provider == "openai":
        return OpenAICompatibleProvider(api_key, base_url or OPENAI_BASE_URL)
    if provider == "openai_compatible":
        if not base_url:
            raise ProviderError("base_url é obrigatório para openai_compatible.", 422)
        return OpenAICompatibleProvider(api_key, base_url)
    raise ProviderError(f"Provedor não suportado: {provider}", 422)

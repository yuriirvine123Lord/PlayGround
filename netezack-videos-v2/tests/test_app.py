from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

import app as app_module
from providers import choose_video_model, infer_provider


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)
        self.content = self.text.encode()

    def json(self):
        return self._payload


class FakeAsyncClient:
    last_requests = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def request(self, method, url, **kwargs):
        self.__class__.last_requests.append((method, url, kwargs))
        if method == "GET" and url.endswith("/models"):
            return FakeResponse(
                {
                    "models": [
                        {"name": "models/gemini-3.1-pro-preview"},
                        {"name": "models/veo-3.1-generate-preview"},
                    ]
                }
            )
        if method == "POST" and url.endswith(":generateContent"):
            return FakeResponse(
                {
                    "candidates": [
                        {"content": {"parts": [{"text": "Roteiro pronto para gravação."}]}}
                    ]
                }
            )
        raise AssertionError(f"request inesperado: {method} {url}")

    async def get(self, url, **kwargs):
        return await self.request("GET", url, **kwargs)


@pytest.fixture
def client(monkeypatch):
    FakeAsyncClient.last_requests = []
    monkeypatch.setattr("providers.httpx.AsyncClient", FakeAsyncClient)
    return TestClient(app_module.app)


def test_infer_provider_known_prefixes():
    assert infer_provider("AIza" + "x" * 20) == "google"
    assert infer_provider("sk-ant-" + "x" * 20) == "anthropic"
    assert infer_provider("sk-" + "x" * 20) == "openai"


def test_unknown_key_requires_explicit_provider():
    with pytest.raises(Exception) as exc:
        infer_provider("custom-secret-123456", "auto")
    assert "provider" in str(exc.value)


def test_video_model_priority_prefers_veo_31():
    assert choose_video_model(
        ["veo-2.0-generate-001", "veo-3.1-generate-preview", "gemini-3-flash-preview"]
    ) == "veo-3.1-generate-preview"


def test_health_and_ui(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    ui = client.get("/")
    assert ui.status_code == 200
    assert "Copiar resposta" in ui.text
    assert "netezack" in ui.text.lower()
    assert "identificar" in ui.text.lower()


def test_preview_endpoint_unknown_job_404(client):
    response = client.get("/v1/videos/naoexiste/preview")
    assert response.status_code == 404


def test_discover_does_not_return_raw_key(client):
    key = "AIza" + "secret-value-123456"
    response = client.post("/v1/discover", json={"api_key": key, "provider": "google"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["selected_model"] == "veo-3.1-generate-preview"
    assert key not in response.text
    assert body["key_hint"] == "AIza…3456"


def test_chat_uses_live_catalog_and_google_endpoint(client):
    key = "AIza" + "secret-value-123456"
    response = client.post(
        "/v1/chat",
        json={
            "api_key": key,
            "provider": "google",
            "messages": [{"role": "user", "content": "Crie uma ideia curta."}],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["text"] == "Roteiro pronto para gravação."
    assert body["model"] == "gemini-3.1-pro-preview"
    assert any(url.endswith(":generateContent") for _, url, _ in FakeAsyncClient.last_requests)


def test_video_endpoint_is_async_and_does_not_call_other_providers(client, monkeypatch):
    created = []

    def fake_create_task(coro):
        coro.close()
        created.append(True)
        return None

    monkeypatch.setattr(app_module.asyncio, "create_task", fake_create_task)
    FakeAsyncClient.last_requests = []
    response = client.post(
        "/v1/videos",
        json={
            "api_key": "sk-" + "x" * 25,
            "provider": "openai",
            "prompt": "Uma cena cinematográfica",
        },
    )
    # Qualquer provedor e aceito: vídeo sai via IA open-source + render local.
    assert response.status_code == 202, response.text
    assert response.json()["provider"] == "openai"
    assert created == [True]
    # Assincrono: nenhuma chamada HTTP acontece durante o request.
    assert FakeAsyncClient.last_requests == []


def test_video_accepts_openai_compatible_explicit_provider(client, monkeypatch):
    monkeypatch.setattr(app_module.asyncio, "create_task",
                        lambda coro: (coro.close(), None)[1])
    response = client.post(
        "/v1/videos",
        json={
            "api_key": "gsk_" + "x" * 25,
            "provider": "openai_compatible",
            "base_url": "https://api.groq.com/openai/v1",
            "prompt": "cena neon",
            "duration_seconds": 8,
        },
    )
    assert response.status_code == 202, response.text


def test_video_without_fallback_non_google_422(client, monkeypatch):
    monkeypatch.setattr(app_module.asyncio, "create_task",
                        lambda coro: (coro.close(), None)[1])
    response = client.post(
        "/v1/videos",
        json={
            "api_key": "sk-" + "x" * 25,
            "provider": "openai",
            "prompt": "cena neon",
            "use_fallback": False,
        },
    )
    assert response.status_code == 422
    assert "fallback" in response.json()["detail"]


def test_chat_model_skips_audio_models():
    from providers import choose_chat_model

    models = ["whisper-large-v3-turbo", "orpheus-arabic-saudi", "qwen3.8-27b",
              "llama-prompt-guard-2-86m", "allam-2-7b", "gpt-oss-20b"]
    assert choose_chat_model("openai_compatible", models) in {"qwen3.8-27b", "allam-2-7b", "gpt-oss-20b"}


def test_ai_video_falls_back_when_network_fails(monkeypatch):
    import ai_video

    def boom(*args, **kwargs):
        raise OSError("sem rede")

    monkeypatch.setattr(ai_video.urllib.request, "urlopen", boom)
    ai_video._ai_down_until = 0.0
    assert ai_video.fetch_ai_frames("teste", 2, 64, 36) is None
    # apos a 1a falha, IA fica desligada por 10 min (nao trava o job)
    assert ai_video.ai_available() is False
    assert ai_video.render_ai_mp4("x", None, 8, "720p", "16:9",
                                  app_module.MEDIA_DIR / "nao_deve.mp4") is None
    ai_video._ai_down_until = 0.0


def test_openapi_contains_core_routes(client):
    schema = client.get("/openapi.json").json()
    assert "/v1/discover" in schema["paths"]
    assert "/v1/chat" in schema["paths"]
    assert "/v1/videos" in schema["paths"]


def test_duration_allows_up_to_10_minutes():
    import pydantic

    from app import VideoRequest

    assert VideoRequest(prompt="cena neon", duration_seconds=600).duration_seconds == 600
    assert VideoRequest(prompt="cena neon").duration_seconds == 8
    for bad in (601, 1, 0):
        with pytest.raises(pydantic.ValidationError):
            VideoRequest(prompt="cena neon", duration_seconds=bad)


def test_ui_offers_10_minutes(client):
    ui = client.get("/")
    assert 'value="600"' in ui.text
    assert "10 min" in ui.text


def test_engines_endpoint_shows_cascade(client):
    r = client.get("/v1/engines")
    assert r.status_code == 200
    body = r.json()
    assert "local" in body["order"] and "flux" in body["order"]
    assert body["local"]["always"] is True


def test_orchestrator_accepts_json_base64_and_fails_safe(monkeypatch, tmp_path):
    import base64 as b64mod
    import json as jsonmod

    import engines

    fake_mp4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 2048

    class FakeResp:
        headers = {"content-type": "application/json"}

        def __init__(self, payload):
            self._p = payload

        def read(self, *a):
            return self._p

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(engines, "ORCHESTRATOR_URL", "http://orchestrator.local/v1/generate")
    monkeypatch.setattr(engines, "ORCHESTRATOR_API_KEY", "token")
    monkeypatch.setattr(engines.urllib.request, "urlopen",
                        lambda req, timeout=None: FakeResp(
                            jsonmod.dumps({"video_base64": b64mod.b64encode(fake_mp4).decode()}).encode()))
    target = tmp_path / "out.mp4"
    assert engines.try_orchestrator("prompt", 8, "16:9", "720p", target) is True
    assert target.read_bytes() == fake_mp4

    def boom(*a, **k):
        raise OSError("orchestrador caiu")

    monkeypatch.setattr(engines.urllib.request, "urlopen", boom)
    assert engines.try_orchestrator("prompt", 8, "16:9", "720p", tmp_path / "x.mp4") is False

    monkeypatch.setattr(engines, "ORCHESTRATOR_URL", "")
    assert engines.try_orchestrator("prompt", 8, "16:9", "720p", tmp_path / "y.mp4") is False


def test_all_key_prefixes_identified():
    from providers import infer_provider

    matrix = {
        "AIzaSyTeste1234567890": "google",
        "sk-ant-api-teste": "anthropic",
        "sk-or-v1-abc123": "openrouter",
        "sk-or-abc123": "openrouter",
        "pplx-abc123": "perplexity",
        "fw_abc123": "fireworks",
        "csk-abc123": "cerebras",
        "nvapi-abc123": "nvidia",
        "gsk_teste_chave": "groq",
        "hf_teste": "huggingface",
        "r8_teste": "replicate",
        "xai-teste": "xai",
        "sk-proj-teste": "openai",
    }
    for key, want in matrix.items():
        assert infer_provider(key) == want, f"{key[:10]} -> {infer_provider(key)} != {want}"


def test_every_registry_base_url_identified():
    from providers import _HIDDEN_BASES, infer_provider

    for name, entry in _HIDDEN_BASES.items():
        base = entry["base"]
        got = infer_provider("chave_qualquer", base_url=base)
        assert got == name, f"base {base} -> {got} != {name}"


def test_unknown_base_url_maps_to_openai_compatible():
    from providers import infer_provider

    assert infer_provider("chave_x", base_url="https://meu-proxy.empresa.local/v1") == "openai_compatible"


def test_explicit_provider_names_accepted_by_schema():
    from app import VideoRequest, DiscoverRequest

    for name in ("openrouter", "groq", "deepseek", "mistral", "xai", "perplexity",
                 "cerebras", "nvidia", "together", "fireworks", "cohere",
                 "huggingface", "replicate", "stability", "moonshot", "siliconflow"):
        assert VideoRequest(prompt="cena", provider=name).provider == name
        assert DiscoverRequest(api_key="x", provider=name).provider == name


def test_ui_selector_shows_ai_names(client):
    ui = client.get("/")
    for brand in ("Google — Gemini", "OpenAI — GPT", "Anthropic — Claude",
                  "OpenRouter", "Groq", "DeepSeek", "Mistral AI", "xAI — Grok"):
        assert brand in ui.text, f"seletor sem: {brand}"


def test_provider_dropdown_values_accepted_via_api(client):
    r = client.post("/v1/discover", json={"api_key": "sk-or-v1-fake", "provider": "openrouter"})
    # valida schema (não 422 de Literal); pode cair em erro de rede/chave depois
    assert r.status_code != 422 or "provider" not in str(r.json().get("detail", "")), r.text[:200]
    assert r.status_code in (200, 401, 403, 429, 502, 503), f"status inesperado {r.status_code}: {r.text[:200]}"

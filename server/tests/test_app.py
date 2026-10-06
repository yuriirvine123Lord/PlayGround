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
    assert "Descobrir modelos" in ui.text


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
    response = client.post(
        "/v1/videos",
        json={
            "api_key": "sk-" + "x" * 25,
            "provider": "openai",
            "prompt": "Uma cena cinematográfica",
        },
    )
    assert response.status_code == 422
    assert "chave Google" in response.json()["detail"]
    assert not created


def test_openapi_contains_core_routes(client):
    schema = client.get("/openapi.json").json()
    assert "/v1/discover" in schema["paths"]
    assert "/v1/chat" in schema["paths"]
    assert "/v1/videos" in schema["paths"]

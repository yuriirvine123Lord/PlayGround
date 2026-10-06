from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

import app as app_module
from effects import EFFECT_IDS
from providers import choose_video_model, infer_provider, public_providers


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

    async def __aexit__(self, *a):
        return False

    async def request(self, method, url, **kwargs):
        self.__class__.last_requests.append((method, url, kwargs))
        if method == "GET" and url.endswith("/models"):
            if "generativelanguage" in url:
                return FakeResponse({"models": [{"name": "models/gemini-2.0-flash"},
                                                {"name": "models/veo-3.1-generate-preview"}]})
            return FakeResponse({"data": [{"id": "gpt-4o"}, {"id": "gpt-4o-mini"}]})
        if method == "POST" and url.endswith(":generateContent"):
            return FakeResponse({"candidates": [{"content": {"parts": [{"text": "Roteiro pronto."}]}}]})
        if method == "POST" and url.endswith("/chat/completions"):
            return FakeResponse({"model": "gpt-4o", "choices": [{"message": {"content": "Olá, diretor!"}}]})
        raise AssertionError(f"request inesperado: {method} {url}")

    async def get(self, url, **kwargs):
        return await self.request("GET", url, **kwargs)


@pytest.fixture
def client(monkeypatch):
    FakeAsyncClient.last_requests = []
    monkeypatch.setattr("providers.httpx.AsyncClient", FakeAsyncClient)
    return TestClient(app_module.app)


def test_prefix_detection():
    assert infer_provider("AIza" + "x" * 30) == "google"
    assert infer_provider("sk-ant-" + "x" * 30) == "anthropic"
    assert infer_provider("gsk_" + "x" * 30) == "groq"
    assert infer_provider("hf_" + "x" * 30) == "huggingface"
    assert infer_provider("r8_" + "x" * 30) == "replicate"
    assert infer_provider("sk-or-v1-" + "a" * 40) == "openrouter"
    # desconhecida -> sondagem
    assert infer_provider("chave-totalmente-diferente-zzz") == "__probe__"


def test_30_effects():
    assert len(EFFECT_IDS) >= 30


def test_public_providers_hide_urls(client):
    r = client.get("/v1/providers")
    assert r.status_code == 200
    body = r.text
    assert "generativelanguage" not in body
    assert "api.openai.com" not in body
    assert len(r.json()["providers"]) >= 10


def test_effects_endpoint(client):
    r = client.get("/v1/effects")
    assert r.json()["total"] >= 30


def test_discover_hides_key(client):
    key = "AIza" + "secret-value-12345678901234567890"
    r = client.post("/v1/discover", json={"api_key": key, "provider": "google"})
    assert r.status_code == 200, r.text
    assert key not in r.text
    assert r.json()["selected_model"] == "veo-3.1-generate-preview"


def test_chat_google(client):
    key = "AIza" + "secret-value-12345678901234567890"
    r = client.post("/v1/chat", json={"api_key": key, "provider": "google",
                                      "messages": [{"role": "user", "content": "ideia curta"}]})
    assert r.status_code == 200, r.text
    assert r.json()["text"] == "Roteiro pronto."


def test_smart_chat_without_key(client):
    r = client.post("/v1/smart", json={"message": "olá, me ajude com um roteiro"})
    assert r.status_code in (200, 202), r.text
    assert r.json()["mode"] == "chat"


def test_local_video_always_renders(client):
    r = client.post("/v1/videos", json={"prompt": "cidade neon na chuva", "effect": "glitch",
                                        "duration_seconds": 2, "use_cloud": False})
    assert r.status_code == 202, r.text
    job_id = r.json()["job_id"]
    import time
    for _ in range(30):
        time.sleep(1)
        s = client.get(f"/v1/videos/{job_id}").json()
        if s["status"] in ("completed", "failed"):
            break
    assert s["status"] == "completed", s
    d = client.get(f"/v1/videos/{job_id}/download")
    assert d.status_code == 200
    assert len(d.content) > 5000


def test_all_qualities_render_short(client):
    import time
    for quality in ["360p", "480p", "720p"]:
        r = client.post("/v1/videos", json={"prompt": f"teste {quality}", "effect": "neon_pulse",
                                             "duration_seconds": 2, "quality": quality,
                                             "aspect_ratio": "16:9", "use_cloud": False})
        assert r.status_code == 202, (quality, r.text)
        job_id = r.json()["job_id"]
        s = {}
        for _ in range(40):
            time.sleep(1)
            s = client.get(f"/v1/videos/{job_id}").json()
            if s["status"] in ("completed", "failed"):
                break
        assert s["status"] == "completed", (quality, s)
        d = client.get(f"/v1/videos/{job_id}/download")
        assert d.status_code == 200 and len(d.content) > 5000, quality


def test_vertical_and_smart_video(client):
    import time
    r = client.post("/v1/videos", json={"prompt": "vertical teste", "effect": "portal",
                                         "duration_seconds": 2, "aspect_ratio": "9:16",
                                         "quality": "360p", "use_cloud": False})
    assert r.status_code == 202, r.text
    jid = r.json()["job_id"]
    for _ in range(30):
        time.sleep(1)
        s = client.get(f"/v1/videos/{jid}").json()
        if s["status"] in ("completed", "failed"):
            break
    assert s["status"] == "completed", s
    r = client.post("/v1/smart", json={"message": "crie um vídeo teste de 2s",
                                       "effect": "matrix_rain", "duration_seconds": 2, "quality": "360p"})
    assert r.status_code == 202, r.text
    assert r.json()["mode"] == "video"
    jid = r.json()["job"]["job_id"]
    for _ in range(30):
        time.sleep(1)
        s = client.get(f"/v1/videos/{jid}").json()
        if s["status"] in ("completed", "failed"):
            break
    assert s["status"] == "completed", s


def test_ten_minutes_accepted():
    from app import VideoRequest, SmartRequest
    v = VideoRequest(prompt="filme longo", duration_seconds=600, quality="720p")
    assert v.duration_seconds == 600
    s = SmartRequest(message="crie um vídeo de 10 minutos", duration_seconds=600, quality="1080p")
    assert s.duration_seconds == 600
    import pytest
    with pytest.raises(Exception):
        VideoRequest(prompt="x", duration_seconds=601)
    # renderer limita sem estourar (não renderiza 600s no teste)
    from effects import QUALITY_SIZES
    assert set(QUALITY_SIZES) == {"360p", "480p", "720p", "1080p"}

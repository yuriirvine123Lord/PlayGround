"""Teste fim-a-fim (mockado) do fluxo de vídeo: cria job, acompanha até
completed e baixa o MP4. Serve para caçar bugs no caminho assíncrono."""
from __future__ import annotations

import base64
import json
import time

import pytest
from fastapi.testclient import TestClient

import app as app_module

FAKE_MP4 = b"FAKE-MP4-BYTES-NETZACK-V2"


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


class FakeVideoClient:
    """Simula: /models -> predictLongRunning -> operation done com vídeo base64."""

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def request(self, method, url, **kwargs):
        if method == "GET" and url.endswith("/models"):
            return FakeResponse(
                {
                    "models": [
                        {"name": "models/gemini-3.1-pro-preview"},
                        {"name": "models/veo-3.1-generate-preview"},
                    ]
                }
            )
        if method == "POST" and url.endswith(":predictLongRunning"):
            body = kwargs.get("json") or {}
            assert body["instances"][0]["prompt"], "prompt vazio chegou ao Veo"
            return FakeResponse({"name": "operations/fake-op-123"})
        if method == "GET" and "operations/fake-op-123" in url:
            return FakeResponse(
                {
                    "done": True,
                    "response": {
                        "generateVideoResponse": {
                            "generatedSamples": [
                                {
                                    "video": {
                                        "bytesBase64Encoded": base64.b64encode(FAKE_MP4).decode()
                                    }
                                }
                            ]
                        }
                    },
                }
            )
        raise AssertionError(f"request inesperado: {method} {url}")


class FakeNoVeoClient(FakeVideoClient):
    async def request(self, method, url, **kwargs):
        if method == "GET" and url.endswith("/models"):
            return FakeResponse({"models": [{"name": "models/gemini-3.1-pro-preview"}]})
        raise AssertionError(f"request inesperado: {method} {url}")


@pytest.fixture
def video_client(monkeypatch):
    monkeypatch.setattr("providers.httpx.AsyncClient", FakeVideoClient)
    app_module.jobs.clear()
    return TestClient(app_module.app)


def _wait_job(client, job_id, timeout=15.0):
    deadline = time.time() + timeout
    last = {}
    while time.time() < deadline:
        r = client.get(f"/v1/videos/{job_id}")
        assert r.status_code == 200, r.text
        last = r.json()
        if last["status"] in ("completed", "failed"):
            return last
        time.sleep(0.2)
    raise TimeoutError(f"job não terminou: {last}")


def test_video_flow_completes_and_downloads(video_client):
    key = "AIza" + "video-key-1234567890"
    r = video_client.post(
        "/v1/videos",
        json={"api_key": key, "provider": "auto", "prompt": "Uma cena de teste"},
    )
    assert r.status_code == 202, r.text
    job_id = r.json()["job_id"]

    final = _wait_job(video_client, job_id)
    assert final["status"] == "completed", final
    assert final["model"] == "veo-3.1-generate-preview", final
    assert final["download_url"] == f"/v1/videos/{job_id}/download"

    dl = video_client.get(f"/v1/videos/{job_id}/download")
    assert dl.status_code == 200, dl.text
    assert dl.content == FAKE_MP4


def test_video_without_veo_fails_with_clear_error(monkeypatch):
    monkeypatch.setattr("providers.httpx.AsyncClient", FakeNoVeoClient)
    app_module.jobs.clear()
    client = TestClient(app_module.app)
    r = client.post(
        "/v1/videos",
        json={"api_key": "AIza" + "no-veo-key-1234567890", "prompt": "x" * 10},
    )
    assert r.status_code == 202, r.text
    final = _wait_job(client, r.json()["job_id"])
    assert final["status"] == "failed", final
    assert "Veo" in (final["error"] or ""), final

"""Cascata de motores de vídeo — unifica orquestrador Veo3, Veo Google, IA FLUX e local.

Ordem (VIDEO_ENGINES, padrão "orchestrator,veo,flux,local"):
  orchestrator — endpoint HTTP proprio (ORCHESTRATOR_URL): aceita a resposta
                 flexivel {video_url|url|video_base64} ou MP4 direto.
  veo          — Google Veo (chave Google, ate 8s).
  flux         — quadros IA open-source (Pollinations FLUX) + Ken Burns + efeitos.
  local        — render procedural cyberpunk com efeitos (sempre funciona).

Qualquer motor que falhe cai automaticamente pro proximo.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.request
from pathlib import Path

ENGINE_ORDER = [e.strip().lower()
                for e in os.getenv("VIDEO_ENGINES", "orchestrator,veo,flux,local").split(",")
                if e.strip()]
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "").strip()
ORCHESTRATOR_API_KEY = os.getenv("ORCHESTRATOR_API_KEY", "").strip()
ORCHESTRATOR_TIMEOUT = float(os.getenv("ORCHESTRATOR_TIMEOUT", "60"))


def engines_status() -> dict:
    return {
        "order": ENGINE_ORDER,
        "orchestrator": {"configured": bool(ORCHESTRATOR_URL),
                         "url_host": (ORCHESTRATOR_URL.split("/")[2] if "://" in ORCHESTRATOR_URL else None),
                         "auth": bool(ORCHESTRATOR_API_KEY)},
        "veo": {"requires": "chave Google/Gemini", "max_seconds": 8},
        "flux": {"requires": "internet (Pollinations)", "window_seconds": [4, 60]},
        "local": {"always": True, "max_seconds": 600},
    }


def _extract_video(resp_data: bytes, content_type: str, target: Path) -> bool:
    """Aceita MP4 direto ou JSON com video_url/video_base64."""
    if content_type.startswith("video/") or resp_data[:6].find(b"ftyp") != -1:
        target.write_bytes(resp_data)
        return True
    try:
        payload = json.loads(resp_data.decode("utf-8", "replace"))
    except Exception:
        return False
    if not isinstance(payload, dict):
        return False
    b64 = payload.get("video_base64") or payload.get("video_base64_data") or payload.get("b64")
    if b64:
        raw = base64.b64decode(str(b64).split(",")[-1])
        if b"ftyp" in raw[:64]:
            target.write_bytes(raw)
            return True
    for key in ("video_url", "url", "download_url", "output_url"):
        v = payload.get(key)
        if isinstance(v, str) and v.startswith("http"):
            try:
                req = urllib.request.Request(v, headers={"User-Agent": "NetezackVideos/2.1"})
                with urllib.request.urlopen(req, timeout=ORCHESTRATOR_TIMEOUT) as r2:
                    data = r2.read(80_000_000)
                if b"ftyp" in data[:64] or (r2.headers.get("content-type", "").startswith("video/")):
                    target.write_bytes(data)
                    return True
            except Exception:
                continue
    return False


def try_orchestrator(prompt: str, duration_s: int, aspect: str, resolution: str,
                     target: Path) -> bool:
    """POST no orquestrador proprio (Veo3 etc). True se o MP4 estiver em `target`."""
    if not ORCHESTRATOR_URL:
        return False
    body = json.dumps({
        "prompt": prompt,
        "duration_seconds": duration_s,
        "aspect_ratio": aspect,
        "resolution": resolution,
        "negative_prompt": None,
    }).encode()
    headers = {"Content-Type": "application/json", "User-Agent": "NetezackVideos/2.1"}
    if ORCHESTRATOR_API_KEY:
        headers["Authorization"] = f"Bearer {ORCHESTRATOR_API_KEY}"
    try:
        req = urllib.request.Request(ORCHESTRATOR_URL, data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=ORCHESTRATOR_TIMEOUT) as resp:
            return _extract_video(resp.read(80_000_000),
                                  resp.headers.get("content-type", ""), target)
    except Exception:
        if target.exists():
            target.unlink(missing_ok=True)
        return False

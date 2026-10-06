# ⚡Netezack Vídeos V2 ⚡

Aplicativo de geração de vídeo por prompt com IA — chat visual cyberpunk limpo.

- **Prompt-driven**: você digita, a IA roteiriza e gera o vídeo.
- **40 efeitos especiais** com detecção automática pelo prompt.
- **Preview real**: quadro a quadro durante a renderização (não simulado).
- **Auto-detect de API**: só cola a chave (Google/Gemini, OpenAI, Anthropic, Groq,
  DeepSeek, Together, HuggingFace, Replicate, xAI, Mistral, OpenRouter…).
  Todas as base URLs ficam **escondidas no servidor** — nunca aparecem no cliente.
- **Fallback garantido**: sem billing/Veo → gera MP4 local com efeitos.
- **Railway**: escuta `$PORT` e serve também 8000/8080 (proxy interno à prova de 502).

## Rodar

```bash
pip install -r requirements.txt
pytest -q                       # 9 testes
uvicorn app:app --port 8080     # UI em /
```

Endpoints: `/health`, `/v1/effects`, `/v1/discover`, `/v1/chat`, `/v1/videos`,
`/v1/videos/{id}`, `/v1/videos/{id}/preview`, `/v1/videos/{id}/download`.

## Deploy Railway

```bash
railway link -p <projeto> -e production
railway up --detach
```

---

**Produzida Por Yuri Lord && Agente Falcão ⚡**

# Netzack Videos V2 — App Android

App Android nativo (Kotlin) + backend FastAPI. Um chat só, um prompt só:
só a chave API — detecção 100% automática de IA e modelo.

## Nome / pacote
- Nome: **Netzack Videos V2**
- Pacote: `com.netzack.videos` (mantido para atualizar por cima da v1)
- Versão: 2.0.0 (versionCode 2)

## O que o app faz (V2: tudo automático, prompt único)
1. **Só a chave API** — sem escolher provedor nem modelo (`provider=auto`, `model=null` sempre):
   - `AIza…` → Google / Gemini / Veo
   - `sk-ant-…` → Anthropic
   - `sk-…` → OpenAI
   - chave desconhecida → erro claro pedindo endpoint próprio (sem adivinhar)
2. **Testar servidor**: `GET /health` — diagnostica conexão antes de gerar (a causa nº 1 de "não gera").
3. **Identificar IA e modelo**: `POST /v1/discover` — mostra provedor + modelo detectados, nunca exibe a chave.
4. **Prompt único** para tudo: **Conversar** (`POST /v1/chat` → roteiro) ou **Gerar vídeo** (`POST /v1/videos` → polling → MP4 → `VideoView`).
5. **Vídeo estilo Veo 3 ou melhor** + 11 **efeitos especiais** (`Effects.kt`): Cinema Épico, Neon Chuvoso, Drone Aéreo, Slow 120fps, Anime, Sci-Fi Holográfico, VHS 80s, Terror, Macro Natureza, Ação Zoom, Original.
6. **Erros claros**: se o vídeo falhar, o app mostra o motivo (ex: chave sem acesso ao Veo, servidor fora do ar).

## Download do APK
- **Lançamentos (recomendado)**: https://github.com/yuriirvine123Lord/PlayGround/releases
  - v2.0.0: `Netzack-Videos-V2-v2.0.0-debug.apk` (6,1 MB)
- **Local (esta máquina)**: `android/app/build/outputs/apk/debug/app-debug.apk`
- **GitHub**: aba `Actions` → workflow `Netzack Videos — Android APK` → `Artifacts` → `Netzack-Videos-debug-apk`

## Rodar o backend (obrigatório p/ vídeo real)
```bash
cd server
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # GEMINI_API_KEY=sua_chave
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

No app, em **Servidor**, use:
- Emulador Android: `http://10.0.2.2:8000`
- Celular físico na mesma rede: `http://SEU_IP:8000` (ex: `http://192.168.0.10:8000`)

## Build local
```bash
cd android
./gradlew :app:testDebugUnitTest
./gradlew :app:assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk
```

Requisitos: JDK 17, Android SDK (platform 34, build-tools), Gradle wrapper 8.7 (já incluso).

## Segurança
- A chave fica só na tela + request atual (SharedPreferences guarda só o servidor).
- Sem log de chave; descoberta retorna só `key_hint`.
- Para produção: HTTPS, auth própria (JWT), rate limit, Redis/worker (jobs hoje são em memória, 1 instância).

## Levar para o repo Gerador-de-video
Copie `android/` + `server/` + `.github/workflows/android.yml` para lá, ou rode:
```bash
# dentro do clone do Gerador-de-video:
# cp -r /caminho/deste/repo/android .
# cp -r /caminho/deste/repo/server/* .
```

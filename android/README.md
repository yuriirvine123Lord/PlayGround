# Netzack Videos — App Android

App Android nativo (Kotlin) + backend FastAPI multi-IA com detecção automática.

## Nome / pacote
- Nome: **Netzack Videos**
- Pacote: `com.netzack.videos`
- Versão: 1.0.0 (versionCode 1)

## O que o app faz
1. **Multi-IA automática** (`ProviderDetector.kt` = mesma regra do `server/providers.py`):
   - `AIza…` → Google / Gemini / Veo
   - `sk-ant-…` → Anthropic
   - `sk-…` → OpenAI
   - host `generativelanguage…` / `anthropic…` / `api.openai…` → provedor pelo `base_url`
   - chave desconhecida → exige `provider` + `base_url` explícitos (sem adivinhar endpoint)
2. **Descobrir modelos**: `POST /v1/discover` — mostra catálogo ao vivo, nunca exibe a chave (só `AIza…3456`).
3. **Chat / roteiro**: `POST /v1/chat` — gera roteiro e permite copiar.
4. **Vídeo estilo Veo 3 ou melhor**:
   - `POST /v1/videos` → polling `GET /v1/videos/{id}` → download MP4 → `VideoView`
   - 11 **efeitos especiais** (`Effects.kt`): Cinema Épico, Neon Chuvoso, Drone Aéreo, Slow 120fps, Anime, Sci-Fi Holográfico, VHS 80s, Terror, Macro Natureza, Ação Zoom, Original
   - Controles: 16:9 / 9:16, 720p / 1080p / 4k, 4s / 6s / 8s, gerar áudio, negative prompt automático

## Download do APK
- **Local (esta máquina)**: `android/app/build/outputs/apk/debug/app-debug.apk` (6.1 MB)
- **GitHub**: aba `Actions` → workflow `Netzack Videos — Android APK` → `Artifacts` → `Netzack-Videos-debug-apk`
- Em `Release` publicada, o APK também pode ser anexado manualmente como `Netzack-Videos-v1.0.0-debug.apk`.

Cópia pronta para anexar em release:
- `Netzack-Videos-v1.0.0-debug.apk` (gerado no CI a partir do `app-debug.apk`)

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

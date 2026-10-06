# Netzack Videos V2 — App Android

App Android nativo (Kotlin) que fala DIRETO com as IAs — **sem servidor, sem base URL**.
Só colar a chave API: endpoints oficiais e modelos já vêm embarcados.

## Nome / pacote
- Nome: **Netzack Videos V2**
- Pacote: `com.netzack.videos` (mantido para atualizar por cima das anteriores)
- Versão: 2.3.0 (versionCode 5, tema cyberpunk, qualquer IA + 10 min de vídeo)

## O que o app faz (v2.1.0: direto na IA, prompt único)
Tudo em `DirectAI.kt` — sem `server/`, sem configurar URL nenhuma:
0. **Tema cyberpunk limpo**: fundo abismo, neon ciano/magenta, cards, gradiente no botão Gerar vídeo.
1. **Qualquer API do mercado**: 15 provedores com endpoints EMBUTIDOS e escondidos (Google, OpenAI, Anthropic, DeepSeek, Groq, xAI, Mistral, Together, Cerebras, OpenRouter, SiliconFlow, Moonshot, Fireworks, Gemini-compat, Perplexity). Colou a chave → o app testa quem aceita (com dica de prefixo) e identifica sozinho — a URL nunca aparece na tela.
2. **Vídeo até 10 minutos**: o app fatia o tempo em pedaços válidos (Veo: 4/6/8 s; Sora: 4/8/12 s), gera um a um com progresso e **une em um MP4** (`VideoStitcher`); se a união falhar, toca os pedaços em sequência.
3. **Identificar IA e modelo**: consulta o catálogo ao vivo da sua conta e escolhe sozinho (Veo 3.1 p/ vídeo, melhor modelo p/ chat).
4. **Prompt único** para tudo: **Conversar** (roteiro) ou **Gerar vídeo**.
5. **Vídeo estilo Veo 3 / Sora** + 11 **efeitos especiais** (`Effects.kt`).
6. **Erros claros**: mostra o motivo real (ex: chave sem Veo, chave inválida).

## Download do APK
- **Lançamentos (recomendado)**: https://github.com/yuriirvine123Lord/PlayGround/releases
  - v2.3.0: `Netzack-Videos-V2-v2.3.0-debug.apk` (qualquer IA + vídeo até 10 min)
- **Local (esta máquina)**: `android/app/build/outputs/apk/debug/app-debug.apk`
- **GitHub**: aba `Actions` → workflow `Netzack Videos — Android APK` → `Artifacts` → `Netzack-Videos-debug-apk`

## Como usar (não precisa de servidor!)
1. Instale o APK e abra o app.
2. Cole **só a chave API** — de qualquer provedor do mercado (o app identifica sozinho, sem mostrar URL nenhuma).
3. Toque **Identificar IA e modelo** para confirmar (mostra IA + modelos da sua conta).
4. Digite o **prompt único** → **Conversar** ou **Gerar vídeo** (duração até 10 min).

## Rodar o backend (opcional, modo avançado)
A pasta `server/` continua no repo para quem quiser o modo via servidor próprio:
```bash
cd server
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # GEMINI_API_KEY=sua_chave
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

## Build local
```bash
cd android
./gradlew :app:testDebugUnitTest
./gradlew :app:assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk
```

Requisitos: JDK 17, Android SDK (platform 34, build-tools), Gradle wrapper 8.7 (já incluso).

## Segurança
- A chave fica só na tela e nas chamadas diretas à IA (nada é salvo em arquivo).
- Sem log de chave; a tela mostra só `AIza…3456`.
- A chave Google com Veo gera custo/cota na sua conta Google — acompanhe o uso no console.

## Levar para o repo Gerador-de-video
Copie `android/` + `server/` + `.github/workflows/android.yml` para lá, ou rode:
```bash
# dentro do clone do Gerador-de-video:
# cp -r /caminho/deste/repo/android .
# cp -r /caminho/deste/repo/server/* .
```

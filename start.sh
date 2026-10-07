#!/usr/bin/env bash
# Netezack V2 — preview estático de validação.
# Constrói web/ -> dist/ quando preciso, publica deployment-output.json e
# serve dist/ em primeiro plano na $PORT (padrão 3000).
# Usa o `time` do bash (mede builtins como `command`/`test`); /usr/bin/time
# não executa builtins e quebrava o boot com `set -e`.
set -euo pipefail
time -p cd "$(dirname "$0")"
PROJECT_ROOT="$PWD"
PORT="${PORT:-3000}"
WEB_DIR="${OPENCODE_WEB_DIR:-/home/runner/work/_temp/omgithub-web}"
DIST="$PROJECT_ROOT/dist"
time -p mkdir -p "$DIST" "$WEB_DIR"
time -p test -f "$PROJECT_ROOT/web/index.html"
time -p command -v python3
# Build quando preciso: copia a página se dist estiver ausente ou desatualizada.
if time -p test "$PROJECT_ROOT/dist/index.html" -ot "$PROJECT_ROOT/web/index.html" 2>/dev/null; then
  time -p cp "$PROJECT_ROOT/web/index.html" "$PROJECT_ROOT/dist/index.html"
elif ! time -p test -f "$PROJECT_ROOT/dist/index.html"; then
  time -p cp "$PROJECT_ROOT/web/index.html" "$PROJECT_ROOT/dist/index.html"
fi
time -p test -f "$PROJECT_ROOT/dist/index.html"
time -p bash -c "printf '%s' '{\"project\":\"$PROJECT_ROOT\",\"directory\":\"$DIST\"}' > \"$WEB_DIR/deployment-output.json\""
time -p cat "$WEB_DIR/deployment-output.json"
echo
exec python3 -m http.server "$PORT" --directory "$DIST" --bind 0.0.0.0

#!/usr/bin/env bash
# Captura desktop + mobile da URL exata em CAPTURE_URL para CAPTURE_DIR.
# Usa o próprio navegador (playwright), fecha ao final e mantém o app rodando.
# Saída 75 = falha temporária de navegação/infra; 1 = defeito de script/render.
# Usa o `time` do bash (mede builtins); /usr/bin/time não executa builtins.
set -euo pipefail
time -p cd "$(dirname "$0")"
if [[ -z "${CAPTURE_URL:-}" || -z "${CAPTURE_DIR:-}" ]]; then
  echo "Defina CAPTURE_URL e CAPTURE_DIR." >&2
  exit 1
fi
time -p mkdir -p "$CAPTURE_DIR"
time -p command -v node
time -p test -f "${RUNTIME_DIR:?}/scripts/default-capture.mjs"
set +e
time -p node "${RUNTIME_DIR}/scripts/default-capture.mjs"
status=$?
set -e
if [[ $status -ne 0 ]]; then
  echo "capture falhou com saída $status" >&2
  exit "$status"
fi
time -p test -f "$CAPTURE_DIR/final-desktop.png"
time -p test -f "$CAPTURE_DIR/final-mobile.png"
time -p test -s "$CAPTURE_DIR/final-desktop.png"
time -p test -s "$CAPTURE_DIR/final-mobile.png"
echo "capturas OK em $CAPTURE_DIR"

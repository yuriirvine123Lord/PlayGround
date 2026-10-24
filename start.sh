#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
PORT="${PORT:-3000}"
export PORT
export PROJECT_DIR

# Dependencies: this static site needs none, but honour a package project if one appears.
if [[ -f package.json ]]; then
  /usr/bin/time -p npm install --no-audit --no-fund
fi

/usr/bin/time -p node --version
/usr/bin/time -p rm -rf dist
/usr/bin/time -p mkdir -p dist
/usr/bin/time -p cp -R site/. dist/
/usr/bin/time -p test -f dist/index.html

if [[ -n "${OPENCODE_WEB_DIR:-}" ]]; then
  /usr/bin/time -p mkdir -p "$OPENCODE_WEB_DIR"
  /usr/bin/time -p printf '{"project":"%s","directory":"%s"}\n' "$PROJECT_DIR" "$PROJECT_DIR/dist" > "$OPENCODE_WEB_DIR/deployment-output.json"
  /usr/bin/time -p cat "$OPENCODE_WEB_DIR/deployment-output.json"
fi

echo "serving $PROJECT_DIR/dist on port $PORT"
exec /usr/bin/time -p node scripts/serve.mjs

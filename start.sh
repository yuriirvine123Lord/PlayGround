#!/usr/bin/env bash
# Gerador de Vídeo (static) — build dist/ inside PROJECT_DIR and serve on PORT.
set -euo pipefail
/usr/bin/time -p bash -c 'cd "$(dirname "$0")" && pwd'
cd "$(dirname "$0")"
/usr/bin/time -p pwd
PROJECT_DIR="$(/usr/bin/time -p pwd)"
PORT="${PORT:-3000}"
SRC_DIR="$PROJECT_DIR/src"
DIST_DIR="$PROJECT_DIR/dist"
WEB_DIR="${OPENCODE_WEB_DIR:-/home/runner/work/_temp/omgithub-web}"
DEPLOY_OUT="$WEB_DIR/deployment-output.json"
/usr/bin/time -p mkdir -p "$SRC_DIR" "$DIST_DIR" "$WEB_DIR"
/usr/bin/time -p bash -c '
  if [ -f package.json ]; then
    if [ -f package-lock.json ]; then npm ci --no-audit --no-fund; else npm install --no-audit --no-fund; fi
  else
    echo "No package.json — no dependencies to install (static HTML app)."
  fi
'
/usr/bin/time -p bash -c '
  src="$1"; dist="$2"
  if [ ! -f "$src/index.html" ]; then echo "Missing source: $src/index.html" >&2; exit 1; fi
  if [ ! -f "$dist/index.html" ] || [ "$src/index.html" -nt "$dist/index.html" ]; then
    cp "$src/index.html" "$dist/index.html"
    echo "Built $dist/index.html from $src/index.html"
  else
    echo "Build output is up to date: $dist/index.html"
  fi
' _ "$SRC_DIR" "$DIST_DIR"
/usr/bin/time -p test -f "$DIST_DIR/index.html"
/usr/bin/time -p bash -c '
  project="$1"; directory="$2"; out="$3"
  mkdir -p "$(dirname "$out")"
  python3 - "$project" "$directory" "$out" <<'"'"'PYEOF'"'"'
import json, sys
project, directory, out = sys.argv[1], sys.argv[2], sys.argv[3]
with open(out, "w") as fh:
    json.dump({"project": project, "directory": directory}, fh)
print("Wrote " + out)
PYEOF
  cat "$out"
' _ "$PROJECT_DIR" "$DIST_DIR" "$DEPLOY_OUT"
echo "Serving $DIST_DIR on 0.0.0.0:$PORT (foreground)"
/usr/bin/time -p python3 -u -m http.server "$PORT" --bind 0.0.0.0 --directory "$DIST_DIR"

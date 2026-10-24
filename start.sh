#!/usr/bin/env bash
set -euo pipefail

# Per-command timing for build and startup diagnostics.
run() { /usr/bin/time -p "$@"; }

cd "$(dirname "$0")"
PROJECT_DIR="$(pwd -P)"
PORT="${PORT:-3000}"
export PORT

WEB_DIR="${OPENCODE_WEB_DIR:-/home/runner/work/_temp/omgithub-web}"
APP_FILE="$PROJECT_DIR/netezack-videos-v2/app.py"
DIST_DIR="$PROJECT_DIR/dist"

run mkdir -p "$WEB_DIR"
run rm -rf "$DIST_DIR"
run mkdir -p "$DIST_DIR"

# Build a self-contained static bundle from the HTML served by the FastAPI app.
run python3 - "$APP_FILE" "$DIST_DIR/index.html" <<'PY'
import re
import sys

source_path, output_path = sys.argv[1:3]
source = open(source_path, encoding="utf-8").read()
match = re.search(r'HTML\s*=\s*r"""(.*?)"""', source, re.S)
if not match:
    raise SystemExit("Could not locate the HTML template in app.py")
html = match.group(1)
if "<!doctype html" not in html.lower() or "</html>" not in html.lower():
    raise SystemExit("Extracted HTML is incomplete")
with open(output_path, "w", encoding="utf-8") as handle:
    handle.write(html)
PY

# Expose the effects catalog as a static endpoint so the UI renders without a backend.
run python3 - "$PROJECT_DIR/netezack-videos-v2" "$DIST_DIR/v1/effects" <<'PY'
import importlib.util
import json
import os
import sys

source_dir, output_path = sys.argv[1:3]
spec = importlib.util.spec_from_file_location("effects", os.path.join(source_dir, "effects.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
items = module.list_effects()
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, "w", encoding="utf-8") as handle:
    json.dump({"count": len(items), "effects": items}, handle)
PY

run test -s "$DIST_DIR/index.html"
run test -s "$DIST_DIR/v1/effects"

# Publish worker metadata after the static output exists.
run python3 - "$WEB_DIR/deployment-output.json" "$PROJECT_DIR" "$DIST_DIR" <<'PY'
import json
import sys

output_path, project_dir, directory = sys.argv[1:4]
with open(output_path, "w", encoding="utf-8") as handle:
    json.dump({"project": project_dir, "directory": directory}, handle)
    handle.write("\n")
PY

echo "Serving $DIST_DIR on 0.0.0.0:$PORT"
run python3 -m http.server "$PORT" --bind 0.0.0.0 --directory "$DIST_DIR"

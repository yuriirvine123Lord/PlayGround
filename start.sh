#!/usr/bin/env bash
set -euo pipefail
time -p cd "$(dirname "$0")"
/usr/bin/time -p pwd
PROJECT_DIR="$(/usr/bin/time -p pwd)"
PORT="${PORT:-3000}"
DIST="$PROJECT_DIR/dist"
WEB_DIR="${OPENCODE_WEB_DIR:-/home/runner/work/_temp/omgithub-web}"
/usr/bin/time -p mkdir -p "$DIST" "$WEB_DIR"
/usr/bin/time -p bash -c 'test ! -f package.json || npm install --no-audit --no-fund'
/usr/bin/time -p python3 - "$PROJECT_DIR" "$DIST" <<'PY'
import re, sys
from pathlib import Path
project = Path(sys.argv[1])
dist = Path(sys.argv[2])
src = project / "netezack-videos-v2" / "app.py"
out = dist / "index.html"
rebuild = True
if out.exists() and src.exists():
    rebuild = src.stat().st_mtime > out.stat().st_mtime
if rebuild:
    html = None
    if src.exists():
        text = src.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'HTML = r"""(.*?)"""\n\n\n@app.get', text, re.S)
        if m:
            html = m.group(1)
    if html is None:
        html = "<!doctype html><html><body><h1>Netezack Videos V2</h1></body></html>"
    out.write_text(html, encoding="utf-8")
    print(f"built {out} ({len(html)} bytes)")
else:
    print(f"reuse {out}")
PY
/usr/bin/time -p test -f "$DIST/index.html"
/usr/bin/time -p python3 - "$PROJECT_DIR" "$DIST" "$WEB_DIR" <<'PY'
import json, sys
from pathlib import Path
project, directory, web = sys.argv[1], sys.argv[2], sys.argv[3]
Path(web).mkdir(parents=True, exist_ok=True)
payload = {"project": project, "directory": directory}
(Path(web) / "deployment-output.json").write_text(json.dumps(payload), encoding="utf-8")
print(json.dumps(payload))
PY
echo "serving $DIST on 0.0.0.0:$PORT"
/usr/bin/time -p python3 -m http.server "$PORT" --directory "$DIST" --bind 0.0.0.0

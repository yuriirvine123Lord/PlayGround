#!/usr/bin/env bash
# NEON STUDIO preview server.
# Builds the static site into PROJECT_DIR/dist when needed, writes the
# deployment-output.json metadata, then serves dist/ in the FOREGROUND on
# PORT (default 3000). Every command is timed with /usr/bin/time -p
# (shell keyword `time -p` for the cd builtin, which must run in-process).
set -euo pipefail

# cd must affect this shell, so use the keyword form (same real/user/sys output).
time -p cd "$(dirname "$0")"
/usr/bin/time -p test -x /usr/bin/python3
/usr/bin/time -p mkdir -p dist
# Rebuild when the generator or its data source changed (or output missing).
if /usr/bin/time -p test dist/index.html -nt scripts/build_dist.py && /usr/bin/time -p test dist/index.html -nt neon-studio/effects.py; then
  /usr/bin/time -p echo "dist up to date, skipping build"
else
  /usr/bin/time -p python3 scripts/build_dist.py
fi
/usr/bin/time -p test -s dist/index.html
PROJECT_ROOT="$PWD"
/usr/bin/time -p printf '%s' "{\"project\":\"$PROJECT_ROOT\",\"directory\":\"$PROJECT_ROOT/dist\"}" > "${OPENCODE_WEB_DIR:-/home/runner/work/_temp/omgithub-web}/deployment-output.json"
if [ "${OPENCODE_WEB_DIR:-/home/runner/work/_temp/omgithub-web}" != "/home/runner/work/_temp/omgithub-web" ]; then
  /usr/bin/time -p cp "${OPENCODE_WEB_DIR}/deployment-output.json" /home/runner/work/_temp/omgithub-web/deployment-output.json
fi
/usr/bin/time -p python3 -c "import json;print(json.load(open('/home/runner/work/_temp/omgithub-web/deployment-output.json')))"
# Foreground server (controller reuses it while healthy; do not background).
/usr/bin/time -p python3 -m http.server "${PORT:-3000}" --directory dist --bind 0.0.0.0

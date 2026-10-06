#!/usr/bin/env bash
set -euo pipefail
time -p cd "$(dirname "$0")"
: "${CAPTURE_URL:?Set CAPTURE_URL to the exact preview URL.}"
: "${CAPTURE_DIR:?Set CAPTURE_DIR to the output directory.}"
/usr/bin/time -p mkdir -p "$CAPTURE_DIR"
/usr/bin/time -p bash -n "$0"
if [[ -z "${RUNTIME_DIR:-}" ]]; then
  export RUNTIME_DIR="/home/runner/work/_temp/omgithub-runtime"
fi
echo "capturing $CAPTURE_URL -> $CAPTURE_DIR"
/usr/bin/time -p node "$RUNTIME_DIR/scripts/default-capture.mjs"
status=$?
/usr/bin/time -p ls -l "$CAPTURE_DIR"
if [[ $status -ne 0 ]]; then
  exit "$status"
fi
/usr/bin/time -p test -f "$CAPTURE_DIR/final-desktop.png"
/usr/bin/time -p test -f "$CAPTURE_DIR/final-mobile.png"

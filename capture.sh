#!/usr/bin/env bash
# Capture desktop + mobile screenshots of the exact $CAPTURE_URL into
# $CAPTURE_DIR as final-desktop.png / final-mobile.png.
# Delegates browser work to the runtime's default-capture (headed Chromium on
# the worker Xvfb display), then verifies both artifacts.
# Exit 75 = temporary navigation/browser infrastructure failure.
# Exit  1 = script misuse or rendering/output defects.
# Leaves the app server running. Every command timed (/usr/bin/time -p,
# shell keyword `time -p` for the cd builtin).
set -euo pipefail

time -p cd "$(dirname "$0")"
/usr/bin/time -p test -n "${CAPTURE_URL:-}"
/usr/bin/time -p test -n "${CAPTURE_DIR:-}"
/usr/bin/time -p test -n "${RUNTIME_DIR:-}"
/usr/bin/time -p mkdir -p "$CAPTURE_DIR"
set +e
/usr/bin/time -p node "$RUNTIME_DIR/scripts/default-capture.mjs"
rc=$?
set -e
if [ "$rc" -ne 0 ]; then
  exit "$rc"
fi
/usr/bin/time -p test -s "$CAPTURE_DIR/final-desktop.png"
/usr/bin/time -p test -s "$CAPTURE_DIR/final-mobile.png"
/usr/bin/time -p ls -l "$CAPTURE_DIR/final-desktop.png" "$CAPTURE_DIR/final-mobile.png"

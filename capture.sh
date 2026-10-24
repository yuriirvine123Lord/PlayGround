#!/usr/bin/env bash
set -euo pipefail

# Per-command timing for capture diagnostics.
run() { /usr/bin/time -p "$@"; }

cd "$(dirname "$0")"

: "${CAPTURE_URL:?Set CAPTURE_URL to the preview URL to capture.}"
: "${CAPTURE_DIR:?Set CAPTURE_DIR to an output directory outside the project.}"

RUNTIME_DIR="${RUNTIME_DIR:-/home/runner/work/_temp/omgithub-runtime}"

run mkdir -p "$CAPTURE_DIR"
run node "$RUNTIME_DIR/scripts/default-capture.mjs"
run test -s "$CAPTURE_DIR/final-desktop.png"
run test -s "$CAPTURE_DIR/final-mobile.png"

echo "Captured desktop and mobile screenshots in $CAPTURE_DIR"

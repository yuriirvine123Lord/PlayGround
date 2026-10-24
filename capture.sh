#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

: "${CAPTURE_URL:?Set CAPTURE_URL}"
: "${CAPTURE_DIR:?Set CAPTURE_DIR}"
export CAPTURE_URL CAPTURE_DIR

/usr/bin/time -p mkdir -p "$CAPTURE_DIR"
/usr/bin/time -p node scripts/capture.mjs
/usr/bin/time -p test -s "$CAPTURE_DIR/final-desktop.png"
/usr/bin/time -p test -s "$CAPTURE_DIR/final-mobile.png"

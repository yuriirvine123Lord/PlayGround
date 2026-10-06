#!/usr/bin/env bash
# Capture desktop + mobile screenshots of CAPTURE_URL into CAPTURE_DIR.
# Exit 75 = temporary navigation/browser infrastructure failure.
# Exit 1  = script or rendering defect. Leaves the app server running.
set -euo pipefail
/usr/bin/time -p bash -c 'cd "$(dirname "$0")" && pwd'
cd "$(dirname "$0")"
/usr/bin/time -p pwd
/usr/bin/time -p bash -c ': "${CAPTURE_URL:?Set CAPTURE_URL to the exact preview URL.}"'
/usr/bin/time -p bash -c ': "${CAPTURE_DIR:?Set CAPTURE_DIR to the output directory.}"'
/usr/bin/time -p mkdir -p "$CAPTURE_DIR"
/usr/bin/time -p test -f scripts/capture.mjs
/usr/bin/time -p node --version
set +e
/usr/bin/time -p node scripts/capture.mjs
capture_status=$?
set -e
/usr/bin/time -p bash -c '
  dir="$1"
  for name in desktop mobile; do
    f="$dir/final-$name.png"
    if [ ! -s "$f" ]; then echo "Missing capture output: $f" >&2; exit 1; fi
    echo "OK $f ($(wc -c < "$f") bytes)"
  done
' _ "$CAPTURE_DIR"
if [ "$capture_status" -ne 0 ]; then
  echo "capture.mjs exited with status $capture_status" >&2
  exit "$capture_status"
fi
echo "Captures written to $CAPTURE_DIR (app left running)."

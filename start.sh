#!/usr/bin/env bash
# Netzack Videos / Veo static preview — serves PROJECT_DIR/dist on $PORT.
# Writes deployment-output.json {project, directory} for the controller.
set -euo pipefail

cd "$(dirname "$0")"

/usr/bin/time -p bash -c 'true'

PORT="${PORT:-3000}"
if ! [[ "$PORT" =~ ^[1-9][0-9]*$ ]] || (( PORT > 65535 )); then
  echo "PORT must be a valid port number, got: $PORT" >&2
  exit 1
fi
export PORT

PROJECT_DIR="$(/usr/bin/time -p pwd)"
DIST_DIR="$PROJECT_DIR/dist"

/usr/bin/time -p test -f "$DIST_DIR/index.html" || {
  echo "Static deployment output must contain index.html (expected $DIST_DIR/index.html)." >&2
  exit 1
}

# Optional npm build: only when a package.json exists at the project root.
if [[ -f "$PROJECT_DIR/package.json" ]]; then
  if [[ -f "$PROJECT_DIR/package-lock.json" ]]; then
    /usr/bin/time -p npm ci --no-audit --no-fund --prefix "$PROJECT_DIR"
  else
    /usr/bin/time -p npm install --no-audit --no-fund --prefix "$PROJECT_DIR"
  fi
  if /usr/bin/time -p node -e "const p=require('./package.json');process.exit(p.scripts&&p.scripts.build?0:1)"; then
    /usr/bin/time -p npm run build --prefix "$PROJECT_DIR"
    /usr/bin/time -p test -f "$DIST_DIR/index.html"
  fi
fi

# Deployment metadata: OPENCODE_WEB_DIR is worker metadata, never the build output.
WEB_DIR="${OPENCODE_WEB_DIR:-/home/runner/work/_temp/omgithub-web}"
/usr/bin/time -p mkdir -p "$WEB_DIR"
/usr/bin/time -p bash -c 'printf "%s" "$1" > "$2"' _ \
  "$(node -e 'console.log(JSON.stringify({project:process.argv[1],directory:process.argv[2]}))' "$PROJECT_DIR" "$DIST_DIR")" \
  "$WEB_DIR/deployment-output.json"
/usr/bin/time -p cat "$WEB_DIR/deployment-output.json"
echo ""

# Serve the built static directory in the foreground (controller owns the tmux session).
exec /usr/bin/time -p node -e '
const {createServer} = require("node:http");
const {readFileSync, existsSync, statSync} = require("node:fs");
const {join, resolve, extname} = require("node:path");
const root = resolve(process.argv[1]);
const port = Number(process.env.PORT || "3000");
const mime = {".html":"text/html; charset=utf-8",".js":"application/javascript; charset=utf-8",".css":"text/css; charset=utf-8",".json":"application/json",".svg":"image/svg+xml",".png":"image/png",".jpg":"image/jpeg",".jpeg":"image/jpeg",".webp":"image/webp",".ico":"image/x-icon",".woff2":"font/woff2",".woff":"font/woff",".mp4":"video/mp4"};
const server = createServer((req, res) => {
  try {
    const url = new URL(req.url || "/", "http://localhost");
    let path = resolve(root, "." + decodeURIComponent(url.pathname));
    if (path !== root && !path.startsWith(root + "/")) { res.writeHead(404); res.end("Not found"); return; }
    if (existsSync(path) && statSync(path).isDirectory()) path = join(path, "index.html");
    if (!existsSync(path)) path = join(root, "index.html");
    res.setHeader("Content-Type", mime[extname(path)] || "application/octet-stream");
    res.setHeader("Cache-Control", "no-cache");
    res.end(readFileSync(path));
  } catch (e) { res.writeHead(404); res.end("Not found"); }
});
server.listen(port, "0.0.0.0", () => console.log("Serving " + root + " on port " + port));
' "$DIST_DIR"

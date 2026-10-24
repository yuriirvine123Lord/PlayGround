import { createServer } from "node:http";
import { stat, watch } from "node:fs/promises";
import { createReadStream, existsSync } from "node:fs";
import { extname, join, normalize, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const here = fileURLToPath(new URL(".", import.meta.url));
const root = resolve(process.env.SERVE_DIR || join(here, "..", "dist"));
const port = Number(process.env.PORT || 3000);
const host = process.env.HOST || "0.0.0.0";

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".mjs": "application/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
  ".txt": "text/plain; charset=utf-8",
  ".wasm": "application/wasm",
  ".mp4": "video/mp4",
};

if (!existsSync(join(root, "index.html"))) {
  console.error(`[serve] missing index.html in ${root}`);
  process.exit(1);
}

const clients = new Set();
let debounce;
try {
  const watcher = watch(root, { recursive: true });
  (async () => {
    for await (const _ of watcher) {
      clearTimeout(debounce);
      debounce = setTimeout(() => {
        for (const client of clients) client.write("event: change\ndata: changed\n\n");
      }, 200);
    }
  })().catch(() => {});
} catch {
  /* recursive watch unsupported: live reload degrades gracefully */
}

const safePath = (urlPath) => {
  const decoded = decodeURIComponent(urlPath.split("?")[0]);
  const target = normalize(join(root, decoded));
  if (target !== root && !target.startsWith(root + sep)) return null;
  return target;
};

const serveFile = async (req, res, file) => {
  let info;
  try {
    info = await stat(file);
    if (info.isDirectory()) file = join(file, "index.html");
    info = await stat(file);
  } catch {
    res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    res.end("404 Not found");
    return;
  }
  res.setHeader("Content-Type", MIME[extname(file)] || "application/octet-stream");
  res.setHeader("Content-Length", info.size);
  res.setHeader("Cache-Control", extname(file) === ".html" ? "no-cache" : "public, max-age=3600");
  res.setHeader("X-Content-Type-Options", "nosniff");
  if (req.method === "HEAD") {
    res.writeHead(200);
    res.end();
    return;
  }
  res.writeHead(200);
  createReadStream(file).pipe(res);
};

const server = createServer(async (req, res) => {
  const url = new URL(req.url || "/", "http://localhost");
  if (url.pathname === "/__omgithub/live") {
    res.writeHead(200, {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    });
    res.write(": connected\n\n");
    clients.add(res);
    req.on("close", () => clients.delete(res));
    return;
  }
  if (url.pathname === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ status: "ok", root }));
    return;
  }
  const file = safePath(url.pathname === "/" ? "/index.html" : url.pathname);
  if (!file) {
    res.writeHead(403, { "Content-Type": "text/plain; charset=utf-8" });
    res.end("Forbidden");
    return;
  }
  await serveFile(req, res, file);
});

server.listen(port, host, () => {
  console.log(`[serve] http://${host}:${port}/  (root: ${root})`);
});

for (const sig of ["SIGINT", "SIGTERM"]) {
  process.on(sig, () => server.close(() => process.exit(0)));
}

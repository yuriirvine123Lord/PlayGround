import { createRequire } from "node:module";
import { readFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";

const runtimeDir = process.env.OMGITHUB_PLAYWRIGHT_ROOT || join(process.env.HOME, ".local/share/omgithub-playwright");
const outDir = process.env.CAPTURE_DIR;
const url = process.env.CAPTURE_URL;

if (!url || !outDir) {
  console.error("Set CAPTURE_URL and CAPTURE_DIR.");
  process.exit(1);
}
mkdirSync(outDir, { recursive: true });

const require = createRequire(join(runtimeDir, "package.json"));
let chromium;
try {
  ({ chromium } = require("playwright"));
} catch (error) {
  console.error(`playwright unavailable in ${runtimeDir}: ${error.message}`);
  process.exit(75);
}

let config = { browser: { launchOptions: {} } };
try {
  config = JSON.parse(readFileSync(join(runtimeDir, process.platform === "darwin" ? "metal.json" : "linux.json"), "utf8"));
} catch {
  /* fall back to default launch options */
}
if (process.platform === "linux" && !process.env.DISPLAY) {
  try {
    process.env.DISPLAY = ":" + readFileSync(join(runtimeDir, "display"), "utf8").trim();
  } catch {
    /* xvfb display file optional */
  }
}

const viewports = [
  ["desktop", 1440, 900],
  ["mobile", 390, 844],
];

const transient = (error) => {
  error.exitCode = 75;
  throw error;
};

let browser;
let exitCode = 0;
try {
  browser = await chromium.launch({ ...config.browser?.launchOptions, timeout: 30000 }).catch(transient);
  for (const [name, width, height] of viewports) {
    const page = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 1 }).then((ctx) => ctx.newPage()).catch(transient);
    page.setDefaultTimeout(30000);
    page.on("pageerror", (error) => console.error(`[${name}] pageerror: ${error.message}`));
    const response = await page.goto(url, { waitUntil: "load", timeout: 45000 }).catch(transient);
    const status = response?.status();
    if (!response || !response.ok()) {
      const code = !response || [408, 429, 500, 502, 503, 504].includes(status) ? 75 : 1;
      const error = new Error(`HTTP ${status} loading ${url}`);
      error.exitCode = code;
      throw error;
    }
    await page.locator("body").waitFor({ state: "visible" });
    await page.waitForFunction(() => document.fonts && document.fonts.status === "loaded").catch(() => {});
    await page.waitForTimeout(1200);
    await page.screenshot({ path: join(outDir, `final-${name}.png`), timeout: 30000 }).catch((error) => {
      if (error.name === "TimeoutError" || !browser.isConnected()) transient(error);
      throw error;
    });
    console.log(`captured final-${name}.png at ${width}x${height}`);
    await page.close();
  }
} catch (error) {
  console.error(error?.stack || String(error));
  exitCode = error?.exitCode || 1;
} finally {
  await browser?.close().catch((error) => {
    console.error(error?.message || String(error));
    exitCode ||= 75;
  });
}
process.exit(exitCode);

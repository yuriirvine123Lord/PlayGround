import { readFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { createRequire } from 'node:module';

// Capture helper: opens the exact CAPTURE_URL, waits for rendered content,
// and writes final-desktop.png + final-mobile.png into CAPTURE_DIR.
// Exit 75 = temporary navigation/browser infrastructure failure.
// Exit 1  = script or rendering defect.
const url = process.env.CAPTURE_URL;
const output = process.env.CAPTURE_DIR;
if (!url || !output) {
  console.error('Set CAPTURE_URL and CAPTURE_DIR.');
  process.exit(1);
}
try {
  new URL(url);
} catch {
  console.error(`Invalid CAPTURE_URL: ${url}`);
  process.exit(1);
}
mkdirSync(output, { recursive: true });

const runtime = join(process.env.HOME || '/home/runner', '.local/share/omgithub-playwright');
const require = createRequire(join(runtime, 'package.json'));
const { chromium } = require('playwright');

let config;
try {
  const name = process.platform === 'darwin' ? 'metal.json' : 'linux.json';
  config = JSON.parse(readFileSync(join(runtime, name), 'utf8'));
} catch (error) {
  console.error(`Failed to read browser config: ${error.message}`);
  process.exit(1);
}
if (process.platform === 'linux' && !process.env.DISPLAY) {
  try {
    process.env.DISPLAY = ':' + readFileSync(join(runtime, 'display'), 'utf8').trim();
  } catch (error) {
    console.error(`Failed to determine X display: ${error.message}`);
    process.exit(75);
  }
}

const transient = (error) => {
  throw Object.assign(error instanceof Error ? error : new Error(String(error)), { exitCode: 75 });
};
const TRANSIENT_STATUS = new Set([408, 429, 500, 502, 503, 504]);

let browser;
try {
  browser = await chromium.launch({ ...config.browser.launchOptions, timeout: 30000 }).catch(transient);
  for (const [name, width, height] of [['desktop', 1440, 900], ['mobile', 390, 844]]) {
    const page = await browser.newPage({ viewport: { width, height } }).catch(transient);
    try {
      page.setDefaultTimeout(30000);
      page.on('pageerror', (error) => console.error(`[${name}] pageerror: ${error.message}`));
      const response = await page.goto(url, { waitUntil: 'load', timeout: 45000 }).catch(transient);
      const status = response?.status();
      if (!response || !response.ok()) {
        const exitCode = !response || !status || TRANSIENT_STATUS.has(status) ? 75 : 1;
        throw Object.assign(new Error(`HTTP ${status ?? 'no-response'} loading preview (${name})`), { exitCode });
      }
      try {
        await page.locator(process.env.CAPTURE_READY_SELECTOR || 'body').waitFor({ state: 'visible', timeout: 30000 });
      } catch (error) {
        throw Object.assign(new Error(`Rendered content not visible (${name}): ${error.message}`), { exitCode: 1 });
      }
      try {
        await page.waitForFunction(() => document.fonts.status === 'loaded', { timeout: 10000 });
      } catch {}
      await page.waitForTimeout(1500);
      const path = join(output, `final-${name}.png`);
      await page.screenshot({ path, timeout: 30000 }).catch((error) => {
        if (error?.name === 'TimeoutError' || !browser.isConnected()) transient(error);
        throw error;
      });
      console.log(`Captured ${name}: ${path}`);
    } finally {
      await page.close().catch(() => {});
    }
  }
} catch (error) {
  console.error(error?.message || error);
  process.exitCode = error?.exitCode || 1;
} finally {
  await browser?.close().catch((error) => {
    console.error(`Browser close failed: ${error.message}`);
    process.exitCode ||= 75;
  });
}

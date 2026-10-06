#!/usr/bin/env bash
# Capture desktop + mobile screenshots of $CAPTURE_URL into $CAPTURE_DIR.
# Exit 75 = temporary navigation/browser infrastructure failure.
# Exit 1  = script usage error or rendering defect.
set -euo pipefail

/usr/bin/time -p test -n "${CAPTURE_URL:-}" || { echo 'Set CAPTURE_URL.' >&2; exit 1; }
/usr/bin/time -p test -n "${CAPTURE_DIR:-}" || { echo 'Set CAPTURE_DIR.' >&2; exit 1; }
/usr/bin/time -p mkdir -p "$CAPTURE_DIR"
/usr/bin/time -p node --version
/usr/bin/time -p node - "$CAPTURE_URL" "$CAPTURE_DIR" <<'NODEEOF'
import { readFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { createRequire } from 'node:module';

const url = process.argv[2];
const output = process.argv[3];
if (!url || !output) { console.error('Set CAPTURE_URL and CAPTURE_DIR.'); process.exit(1); }
mkdirSync(output, { recursive: true });

const runtime = join(process.env.HOME, '.local/share/omgithub-playwright');
const require = createRequire(join(runtime, 'package.json'));
const { chromium } = require('playwright');
const config = JSON.parse(readFileSync(join(runtime, 'linux.json'), 'utf8'));
if (process.platform === 'linux') {
  try { process.env.DISPLAY ||= ':' + readFileSync(join(runtime, 'display'), 'utf8').trim(); }
  catch (error) { console.error(error); process.exit(75); }
}

const transient = (error) => { console.error(error?.message || error); process.exit(75); };
let browser;
try {
  browser = await chromium.launch({ ...config.browser.launchOptions, timeout: 30000 }).catch(transient);
  for (const [name, width, height] of [['desktop', 1440, 900], ['mobile', 390, 844]]) {
    const page = await browser.newPage({ viewport: { width, height } }).catch(transient);
    try {
      page.setDefaultTimeout(30000);
      const response = await page.goto(url, { waitUntil: 'load', timeout: 45000 }).catch(transient);
      if (!response?.ok()) {
        const status = response?.status();
        console.error(`HTTP ${status} loading preview`);
        process.exit(!response || [408, 429, 500, 502, 503, 504].includes(status) ? 75 : 1);
      }
      await page.locator('body').waitFor({ state: 'visible', timeout: 30000 }).catch(transient);
      await page.waitForFunction(() => document.fonts.status === 'loaded', null, { timeout: 30000 }).catch(() => {});
      await page.waitForTimeout(1500);
      const text = await page.locator('body').innerText().catch(() => '');
      if (!text || text.trim().length < 20) {
        console.error('Rendering defect: page body has no visible content.');
        process.exit(1);
      }
      await page.screenshot({ path: join(output, `final-${name}.png`), timeout: 30000 }).catch((error) => {
        if (error?.name === 'TimeoutError' || !browser.isConnected()) transient(error);
        console.error(error); process.exit(1);
      });
      console.log(`captured final-${name}.png (${text.trim().length} chars visible)`);
    } finally { await page.close().catch(() => {}); }
  }
} catch (error) {
  console.error(error?.message || error);
  process.exit(error?.exitCode === 75 ? 75 : 1);
} finally {
  await browser?.close().catch((error) => { console.error(error); process.exitCode ||= 75; });
}
NODEEOF
/usr/bin/time -p test -f "$CAPTURE_DIR/final-desktop.png"
/usr/bin/time -p test -f "$CAPTURE_DIR/final-mobile.png"
/usr/bin/time -p echo "capture complete: $CAPTURE_DIR"

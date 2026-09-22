/** Capture the controller-battery concept's real DOM for the README GIF. */
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..");
const source = await fs.readFile(path.join(root, "assets/controller-battery-demo.html"), "utf8");
const output = path.join(root, "assets/readme-gifs/controller-battery.gif");
const scratch = await fs.mkdtemp(path.join(os.tmpdir(), "signalbar-controller-gif-"));
const browser = await chromium.launch({ headless: true });
const interval = 125;

try {
  const page = await browser.newPage({ viewport: { width: 1024, height: 730 }, deviceScaleFactor: 1 });
  await page.setContent('<!doctype html><html><body style="margin:0"><iframe sandbox="allow-scripts" style="display:block;border:0;width:100%;height:710px"></iframe></body></html>');
  await page.locator("iframe").evaluate((iframe, html) => {
    iframe.srcdoc = `<!doctype html><html><head><meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'"><style>html,body{margin:0}#sb-battery-v2 .variant-area{display:none}#sb-battery-v2 .visual{align-self:start}</style></head><body>${html}</body></html>`;
  }, source);
  const frame = page.frameLocator("iframe");
  const crop = frame.locator(".visual");
  await crop.waitFor();
  let count = 0;
  for (const [scene, variant, duration] of [["connect", 0, 3000], ["low", 1, 3000], ["duo", 0, 3000]]) {
    await frame.locator(`[data-scene="${scene}"]`).click();
    // Variant buttons remain selectable even though only the visual is captured.
    await frame.locator(".variant").nth(variant).evaluate((button) => button.click());
    const started = Date.now();
    for (let elapsed = 0; elapsed < duration; elapsed += interval) {
      const wait = started + elapsed - Date.now();
      if (wait > 0) await new Promise((resolve) => setTimeout(resolve, wait));
      await crop.screenshot({ path: path.join(scratch, `${String(count++).padStart(4, "0")}.png`) });
    }
  }
  execFileSync("python3", [path.join(root, "scripts/encode_readme_gif.py"), scratch, output, String(interval)], { stdio: "inherit" });
  console.log(output);
} finally {
  await browser.close();
  await fs.rm(scratch, { recursive: true, force: true });
}

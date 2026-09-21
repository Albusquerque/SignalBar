/** Capture the original SignalBar mockup DOM, cropped to its machine and LED preview. */
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";

const [variantsPath, languagePath, outputPath] = process.argv.slice(2);
if (!variantsPath || !languagePath || !outputPath) {
  throw new Error("Usage: node scripts/capture_readme_gifs.mjs <variants.html> <language.html> <output-dir>");
}

const INTERVAL_MS = 125;
const CAPTURE_CSP = "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; font-src data:; connect-src 'none'; frame-src 'none'; object-src 'none'";
const targetDir = path.resolve(outputPath);
await fs.mkdir(targetDir, { recursive: true });
const scratch = await fs.mkdtemp(path.join(os.tmpdir(), "signalbar-readme-capture-"));
const browser = await chromium.launch({ headless: true });

async function loadMockup(source, viewportWidth, staticBase = false) {
  const page = await browser.newPage({ viewport: { width: viewportWidth, height: 760 }, deviceScaleFactor: 1 });
  await page.setContent('<!doctype html><html><body style="margin:0"><iframe sandbox="allow-scripts" style="display:block;border:0;width:100%;height:740px"></iframe></body></html>');
  const sourceHtml = await fs.readFile(source, "utf8");
  const fragment = staticBase ? sourceHtml.replace(/<script>[\s\S]*?<\/script>/g, "") : sourceHtml;
  await page.locator("iframe").evaluate((iframe, { html, csp }) => {
    iframe.srcdoc = `<!doctype html><html><head><meta http-equiv="Content-Security-Policy" content="${csp}"><style>html,body{margin:0}</style></head><body>${html}</body></html>`;
  }, { html: fragment, csp: CAPTURE_CSP });
  // The frame is sandboxed, just like the published original mockup.
  const frame = page.frameLocator("iframe");
  await frame.locator(".sb-machine").waitFor();
  return { page, frame };
}

async function captureFrames(locator, durationMs, folder, startIndex = 0) {
  await fs.mkdir(folder, { recursive: true });
  const count = Math.ceil(durationMs / INTERVAL_MS);
  const started = Date.now();
  for (let i = 0; i < count; i++) {
    const wait = started + i * INTERVAL_MS - Date.now();
    if (wait > 0) await new Promise((resolve) => setTimeout(resolve, wait));
    await locator.screenshot({ path: path.join(folder, `${String(startIndex + i).padStart(4, "0")}.png`) });
  }
  return count;
}

function encode(name, folder) {
  const output = path.join(targetDir, `${name}.gif`);
  execFileSync("python3", [path.join(import.meta.dirname, "encode_readme_gif.py"), folder, output, String(INTERVAL_MS)], { stdio: "inherit" });
  console.log(output);
}

async function captureVariant(source, variant, durationMs, name) {
  const { page, frame } = await loadMockup(source, 1040);
  const folder = path.join(scratch, name);
  await frame.locator(`[data-variant="${variant}"]`).click();
  await frame.locator(".sb-preview-head").evaluate((header) => {
    const [label, state] = header.children;
    label.textContent = "Logical Decky preview · 17 LEDs";
    state.style.fontSize = "0";
    const style = document.createElement("style");
    style.textContent = ".sb-state::after{content:'Playing';font-size:12px}";
    document.head.appendChild(style);
  });
  await captureFrames(frame.locator(".sb-left"), durationMs + 500, folder);
  encode(name, folder);
  await page.close();
}

async function captureRecording(source) {
  const { page, frame } = await loadMockup(source, 1000);
  const folder = path.join(scratch, "recording");
  const crop = frame.locator(".sb-stage-column");
  await frame.locator("#sb-alerts-background").selectOption("off");
  await frame.locator('[data-scene="record-start"]').click();
  let index = await captureFrames(crop, 1350, folder);
  index += await captureFrames(crop, 750, folder, index);
  await frame.locator('[data-scene="record-stop"]').click();
  await captureFrames(crop, 1200, folder, index);
  encode("recording", folder);
  await page.close();
}

function lerp(a, b, t) { return Math.round(a + (b - a) * t); }
function mix(a, b, t) { return a.map((value, i) => lerp(value, b[i], t)); }

function performanceFrame(t) {
  const cpu = Math.max(0, Math.min(1, .38 + .13 * Math.sin(t * 4.2) + .1 * Math.sin(t * 1.1)));
  const gpu = Math.max(0, Math.min(1, .73 + .10 * Math.sin(t * 2.1 + .5)));
  const cpuLit = Math.round(cpu * 8);
  const gpuLit = Math.round(gpu * 8);
  const color = mix([49, 208, 220], [252, 184, 70], .35 + .23 * Math.sin(t * 1.4));
  return Array.from({ length: 17 }, (_, i) => i === 8 ? [0, 0, 0]
    : i < 8 ? i < cpuLit ? color : [0, 0, 0]
      : i - 9 < gpuLit ? mix([246, 154, 55], [245, 83, 73], .20 + .25 * Math.sin(t * 1.2)) : [0, 0, 0]);
}

function countdownFrame(t) {
  const progress = Math.min(1, t / 4.8);
  const lit = Math.max(1, 17 - Math.round(progress * 16));
  const base = progress < .65 ? mix([69, 211, 226], [253, 176, 61], progress / .65)
    : mix([253, 176, 61], [235, 49, 64], (progress - .65) / .35);
  const comet = Math.round(16 - (t * 5.5) % 17);
  return Array.from({ length: 17 }, (_, i) => i < lit
    ? i === comet ? mix(base, [255, 245, 224], .32) : base
    : [0, 0, 0]);
}

async function captureBase(source, name, makeFrame, durationMs) {
  const { page, frame } = await loadMockup(source, 1000, true);
  // Preserve the mockup's exact HTML/CSS scene; pause its own alert loop, which
  // has no animated Performance or Countdown state, and drive only its 17 LEDs.
  await frame.locator(".sb-machine").waitFor();
  await frame.locator(".sb-center-marker").evaluate((marker) => { marker.style.display = "none"; });
  const folder = path.join(scratch, name);
  await fs.mkdir(folder, { recursive: true });
  const count = Math.ceil(durationMs / INTERVAL_MS);
  for (let i = 0; i < count; i++) {
    const colors = makeFrame(i * INTERVAL_MS / 1000);
    await frame.locator(".sb-stage-column").evaluate((column, rgb) => {
      const cellsHost = column.querySelector(".sb-logic");
      if (!cellsHost.children.length) for (let index = 0; index < 17; index++) cellsHost.appendChild(document.createElement("span"));
      const gradient = `linear-gradient(90deg, ${rgb.map((color, index) => `rgb(${color.join(",")}) ${((index + .5) / 17 * 100).toFixed(2)}%`).join(",")})`;
      column.querySelector(".sb-light-core").style.background = gradient;
      column.querySelector(".sb-light-bloom").style.background = gradient;
      [...cellsHost.children].forEach((cell, index) => { cell.style.background = `rgb(${rgb[index].join(",")})`; });
      column.querySelector("#sb-alerts-status").textContent = "";
    }, colors);
    await frame.locator(".sb-stage-column").screenshot({ path: path.join(folder, `${String(i).padStart(4, "0")}.png`) });
  }
  encode(name, folder);
  await page.close();
}

try {
  await captureVariant(variantsPath, "notification-ample", 3600, "notification");
  await captureVariant(variantsPath, "screenshot-bloom", 3250, "screenshot");
  await captureVariant(variantsPath, "achievement-twoway", 4850, "achievement");
  await captureRecording(languagePath);
  await captureBase(languagePath, "performance", performanceFrame, 4000);
  await captureBase(languagePath, "countdown", countdownFrame, 4800);
} finally {
  await browser.close();
  await fs.rm(scratch, { recursive: true, force: true });
}

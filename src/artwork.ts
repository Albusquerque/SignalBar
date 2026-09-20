import type { ArtworkMode, RGB } from "./types";

export const LED_COUNT = 17;
export const AUTO_ROWS = [0.35, 0.45, 0.55, 0.65, 0.75, 0.82] as const;

const clamp = (value: number, low = 0, high = 1) => Math.max(low, Math.min(high, value));

function hsvStats([red, green, blue]: RGB) {
  const r = red / 255;
  const g = green / 255;
  const b = blue / 255;
  const high = Math.max(r, g, b);
  const low = Math.min(r, g, b);
  return { saturation: high <= 0 ? 0 : (high - low) / high, value: high };
}

export function scoreBand(colors: RGB[]): number {
  if (colors.length === 0) return Number.NEGATIVE_INFINITY;
  const hsv = colors.map(hsvStats);
  const meanS = hsv.reduce((sum, pixel) => sum + pixel.saturation, 0) / hsv.length;
  const meanV = hsv.reduce((sum, pixel) => sum + pixel.value, 0) / hsv.length;
  const contrast = Math.sqrt(
    hsv.reduce((sum, pixel) => sum + (pixel.value - meanV) ** 2, 0) / hsv.length,
  );
  const black = hsv.filter((pixel) => pixel.value < 0.10).length / hsv.length;
  const white = hsv.filter((pixel) => pixel.value > 0.92 && pixel.saturation < 0.10).length / hsv.length;
  let diversity = 0;
  for (let index = 1; index < colors.length; index += 1) {
    const left = colors[index - 1];
    const right = colors[index];
    diversity += Math.hypot(left[0] - right[0], left[1] - right[1], left[2] - right[2]) / 441.67;
  }
  diversity /= Math.max(1, colors.length - 1);
  const uniformityPenalty = diversity < 0.025 ? (0.025 - diversity) * 4 : 0;
  return meanS * 0.40 + diversity * 0.28 + contrast * 0.18 + Math.min(meanV, 0.75) * 0.14
    - black * 0.42 - white * 0.20 - uniformityPenalty;
}

export function perceptualCorrection([red, green, blue]: RGB): RGB {
  // Mild contrast/saturation lift; preserves composition without neon clipping.
  const channels = [red, green, blue];
  const average = (red + green + blue) / 3;
  return channels.map((channel) => {
    const saturated = average + (channel - average) * 1.08;
    const contrasted = 128 + (saturated - 128) * 1.04;
    return Math.round(clamp(contrasted, 0, 255));
  }) as RGB;
}

export function averageBand(
  data: Uint8ClampedArray,
  width: number,
  height: number,
  centerY: number,
): RGB[] {
  const bandHeight = Math.max(3, Math.round(height * 0.055));
  const center = Math.round(clamp(centerY) * (height - 1));
  const top = Math.max(0, Math.min(height - bandHeight, center - Math.floor(bandHeight / 2)));
  const output: RGB[] = [];
  for (let led = 0; led < LED_COUNT; led += 1) {
    const x0 = Math.floor((led * width) / LED_COUNT);
    const x1 = Math.max(x0 + 1, Math.floor(((led + 1) * width) / LED_COUNT));
    let red = 0;
    let green = 0;
    let blue = 0;
    let count = 0;
    for (let y = top; y < top + bandHeight; y += 1) {
      for (let x = x0; x < x1; x += 1) {
        const offset = (y * width + x) * 4;
        if (data[offset + 3] < 8) continue;
        red += data[offset];
        green += data[offset + 1];
        blue += data[offset + 2];
        count += 1;
      }
    }
    const raw: RGB = count ? [red / count, green / count, blue / count] : [0, 0, 0];
    output.push(perceptualCorrection(raw));
  }
  return output;
}

function loadImage(dataUri: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("Steam Library Hero could not be decoded"));
    image.src = dataUri;
  });
}

export async function sampleArtwork(dataUri: string, mode: ArtworkMode, manualY: number) {
  const image = await loadImage(dataUri);
  const sourceWidth = Math.max(1, image.naturalWidth || image.width);
  const sourceHeight = Math.max(1, image.naturalHeight || image.height);
  const width = Math.min(680, sourceWidth);
  const height = Math.max(32, Math.round((sourceHeight / sourceWidth) * width));
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d", { willReadFrequently: true });
  if (!context) throw new Error("Canvas 2D is unavailable");
  context.drawImage(image, 0, 0, width, height);
  const pixels = context.getImageData(0, 0, width, height).data;
  const rows = mode === "center" ? [0.5]
    : mode === "lower" ? [0.76]
      : mode === "manual" ? [clamp(manualY, 0.15, 0.90)]
        : [...AUTO_ROWS];
  const candidates = rows.map((y) => {
    const colors = averageBand(pixels, width, height, y);
    return { y, colors, score: scoreBand(colors) };
  });
  return candidates.reduce((best, candidate) => candidate.score > best.score ? candidate : best);
}


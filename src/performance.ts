import type { RGB, Status, TemperaturePalette } from "./types";

const PALETTES: Record<Exclude<TemperaturePalette, "custom">, [RGB, RGB, RGB]> = {
  thermal: [[30, 180, 230], [245, 180, 45], [235, 45, 55]],
  classic: [[35, 205, 95], [245, 205, 45], [235, 45, 55]],
  icefire: [[45, 105, 245], [170, 75, 220], [245, 55, 95]],
};

const lerp = (left: number, right: number, amount: number) => Math.round(left + (right - left) * amount);

export function temperatureColor(
  temperature: number,
  coolTemperature: number,
  hotTemperature: number,
  palette: TemperaturePalette,
  customPalette?: [RGB, RGB, RGB],
): RGB {
  const [cool, middle, hot] = palette === "custom" && customPalette
    ? customPalette
    : PALETTES[palette as Exclude<TemperaturePalette, "custom">] ?? PALETTES.thermal;
  const heat = Math.max(0, Math.min(1, (temperature - coolTemperature) / Math.max(1, hotTemperature - coolTemperature)));
  const left = heat <= 0.5 ? cool : middle;
  const right = heat <= 0.5 ? middle : hot;
  const amount = heat <= 0.5 ? heat * 2 : (heat - 0.5) * 2;
  return left.map((channel, index) => lerp(channel, right[index], amount)) as RGB;
}

function meter(load: number | null, temperature: number | null, count: number, status: Status): RGB[] {
  const safeLoad = Math.max(0, Math.min(100, load ?? 0));
  const lit = Math.round((count * safeLoad) / 100);
  const color = temperatureColor(
    temperature ?? status.cool_temp_c,
    status.cool_temp_c,
    status.hot_temp_c,
    status.temperature_palette,
    [status.temperature_custom_cool, status.temperature_custom_middle, status.temperature_custom_hot],
  );
  return [...Array.from({ length: lit }, () => color), ...Array.from({ length: count - lit }, () => [0, 0, 0] as RGB)];
}

export function rgbToHsl([red, green, blue]: RGB): [number, number, number] {
  const r = red / 255;
  const g = green / 255;
  const b = blue / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const lightness = (max + min) / 2;
  if (max === min) return [0, 0, Math.round(lightness * 100)];
  const delta = max - min;
  const saturation = delta / (1 - Math.abs(2 * lightness - 1));
  const hue = max === r
    ? 60 * (((g - b) / delta) % 6)
    : max === g
      ? 60 * ((b - r) / delta + 2)
      : 60 * ((r - g) / delta + 4);
  return [Math.round((hue + 360) % 360), Math.round(saturation * 100), Math.round(lightness * 100)];
}

export function hslStringToRgb(value: string): RGB | null {
  const match = value.match(/hsla?\(\s*([\d.]+)\s*,\s*([\d.]+)%\s*,\s*([\d.]+)%/i);
  if (!match) return null;
  const hue = ((Number(match[1]) % 360) + 360) % 360;
  const saturation = Math.max(0, Math.min(100, Number(match[2]))) / 100;
  const lightness = Math.max(0, Math.min(100, Number(match[3]))) / 100;
  const chroma = (1 - Math.abs(2 * lightness - 1)) * saturation;
  const secondary = chroma * (1 - Math.abs(((hue / 60) % 2) - 1));
  const offset = lightness - chroma / 2;
  const [r, g, b] = hue < 60 ? [chroma, secondary, 0]
    : hue < 120 ? [secondary, chroma, 0]
      : hue < 180 ? [0, chroma, secondary]
        : hue < 240 ? [0, secondary, chroma]
          : hue < 300 ? [secondary, 0, chroma]
            : [chroma, 0, secondary];
  return [r, g, b].map((channel) => Math.round((channel + offset) * 255)) as RGB;
}

export function performancePreview(status: Status): RGB[] {
  if (status.performance_metric === "cpu") {
    return meter(status.performance.cpu_load, status.performance.cpu_temperature, 17, status);
  }
  if (status.performance_metric === "mixed") {
    const cpu = meter(status.performance.cpu_load, status.performance.cpu_temperature, 8, status);
    const gpu = meter(status.performance.gpu_load, status.performance.gpu_temperature, 8, status);
    if (status.mixed_direction === "mirrored") gpu.reverse();
    return [...cpu, [0, 0, 0] as RGB, ...gpu];
  }
  return meter(status.performance.gpu_load, status.performance.gpu_temperature, 17, status);
}

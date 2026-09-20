import type { RGB, Status, TemperaturePalette } from "./types";

const PALETTES: Record<TemperaturePalette, [RGB, RGB, RGB]> = {
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
): RGB {
  const [cool, middle, hot] = PALETTES[palette] ?? PALETTES.thermal;
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
  );
  return [...Array.from({ length: lit }, () => color), ...Array.from({ length: count - lit }, () => [0, 0, 0] as RGB)];
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

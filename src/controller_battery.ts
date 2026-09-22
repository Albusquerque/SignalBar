import type { ControllerBatteryUpdate } from "./api";

type UnknownRecord = Record<string, unknown>;

function record(value: unknown): UnknownRecord | null {
  return value && typeof value === "object" && !Array.isArray(value) ? value as UnknownRecord : null;
}

function numeric(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function controllerIndex(value: unknown): number | null {
  const item = record(value);
  const index = numeric(item?.nControllerIndex ?? item?.unControllerIndex ?? item?.controllerIndex);
  return index != null && Number.isInteger(index) && index >= 0 && index < 32 ? index : null;
}

export function batteryPercent(value: unknown): number | null {
  const item = record(value);
  if (!item) return null;
  // Steam's callback payload is not typed by Decky. Only explicitly named
  // percentages or plausibly percentage-scale state values are displayed.
  for (const key of ["nBatteryPercentage", "nBatteryPercent", "batteryPercent", "battery_percent", "percent", "nChargePercent", "ucBatteryLevel"]) {
    const candidate = numeric(item[key]);
    if (candidate != null && candidate >= 0 && candidate <= 100) return Math.round(candidate);
  }
  const fraction = numeric(item.flBatteryLevel);
  if (fraction != null && fraction >= 0 && fraction <= 1) return Math.round(fraction * 100);
  for (const key of ["sBatteryLevel", "nBatteryLevel", "batteryLevel"]) {
    const candidate = numeric(item[key]);
    // 0-4 is often a coarse enumeration, not an exact percentage.
    if (candidate != null && candidate >= 5 && candidate <= 100) return Math.round(candidate);
  }
  return null;
}

/**
 * SteamUI's controller-battery callback returns an array whose positions match
 * the most recent controller-list callback. It does not return an index/value
 * pair. Keep this parser separate from batteryChange so a single payload cannot
 * accidentally be interpreted as a controller state object.
 */
export function batteryLevelList(value: unknown): (number | null)[] | null {
  if (!Array.isArray(value)) return null;
  return value.map((entry) => {
    const direct = numeric(entry);
    if (direct != null) return direct >= 0 && direct <= 100 ? Math.round(direct) : null;
    return batteryPercent(entry);
  });
}

export function mergeOrderedBatteryLevels(
  controllers: ControllerBatteryUpdate[],
  levels: (number | null)[],
): ControllerBatteryUpdate[] {
  return controllers.map((controller, position) => {
    const percent = levels[position];
    return percent == null || controller.percent === percent
      ? controller
      : { ...controller, percent, level: null };
  });
}

export function batteryLevel(value: unknown): number | null {
  const item = record(value);
  if (!item) return null;
  for (const key of ["eBatteryLevel", "nBatteryLevel", "sBatteryLevel", "batteryLevel"]) {
    const candidate = numeric(item[key]);
    if (candidate != null && Number.isInteger(candidate) && candidate >= 1 && candidate <= 4) return candidate;
  }
  return null;
}

export function batteryCharging(value: unknown): boolean | null {
  const item = record(value);
  if (!item) return null;
  for (const key of ["bCharging", "bIsCharging", "charging", "isCharging"]) {
    if (typeof item[key] === "boolean") return item[key] as boolean;
  }
  return null;
}

export function controllerList(value: unknown): ControllerBatteryUpdate[] | null {
  if (!Array.isArray(value)) return null;
  const seen = new Set<number>();
  const result: ControllerBatteryUpdate[] = [];
  for (const entry of value) {
    const index = controllerIndex(entry);
    if (index == null || seen.has(index)) continue;
    seen.add(index);
    const item = record(entry)!;
    result.push({
      id: `steam:${index}`,
      name: typeof item.strName === "string" && item.strName ? item.strName : `Controller ${index + 1}`,
      percent: batteryPercent(entry),
      level: batteryLevel(entry),
      charging: batteryCharging(entry),
    });
  }
  return result.slice(0, 8);
}

export function batteryChange(args: unknown[]): { index: number; percent: number | null; level: number | null; charging: boolean | null } | null {
  const first = record(args[0]);
  if (first) {
    const index = controllerIndex(first);
    if (index == null) return null;
    return { index, percent: batteryPercent(first), level: batteryLevel(first), charging: batteryCharging(first) };
  }
  const index = numeric(args[0]);
  if (index == null || !Number.isInteger(index) || index < 0 || index >= 32) return null;
  const second = record(args[1]);
  if (second) return { index, percent: batteryPercent(second), level: batteryLevel(second), charging: batteryCharging(second) };
  const level = numeric(args[1]);
  return {
    index,
    percent: level != null && level >= 5 && level <= 100 ? Math.round(level) : null,
    level: level != null && Number.isInteger(level) && level >= 1 && level <= 4 ? level : null,
    charging: typeof args[2] === "boolean" ? args[2] : null,
  };
}

import type { ControllerBatteryUpdate } from "./api";

export type ControllerRecord = Record<string, unknown>;

export function controllerRecord(value: unknown): ControllerRecord | null {
  return value && typeof value === "object" && !Array.isArray(value) ? value as ControllerRecord : null;
}

export function controllerIndex(value: ControllerRecord): number | null {
  const index = value.controller_index;
  return typeof index === "number" && Number.isInteger(index) && index >= 0 && index < 0xffffffff ? index : null;
}

export function batteryPercent(value: unknown): number | null {
  // SteamInputManager reports percentages, including 0 and 1, not an enum.
  return typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 100
    ? Math.round(value) : null;
}

function identity(value: string): string {
  // Stable identity without exposing serial numbers in status/debug.
  let hash = 2166136261;
  for (let i = 0; i < value.length; i++) hash = Math.imul(hash ^ value.charCodeAt(i), 16777619);
  return (hash >>> 0).toString(16);
}

export function controllerItem(raw: ControllerRecord): ControllerBatteryUpdate | null {
  const index = controllerIndex(raw);
  if (index == null) return null;
  // Exclude built-in handheld input, headset-paired and mobile touch input,
  // plus keyboard/mouse pseudo-devices. Keep both generations of Steam pad.
  if ([4, 21, 43, 100, 101, 102, 120, 130, 400, 800].includes(Number(raw.controller_type))) return null;
  if (raw.is_remote_device === true) return null;
  const serial = typeof raw.serial_number === "string" ? raw.serial_number : "";
  const name = typeof raw.name === "string" && raw.name ? raw.name : `Controller ${index + 1}`;
  const charging = typeof raw.is_charging === "boolean" ? raw.is_charging : null;
  let percent = batteryPercent(raw.battery_level);
  // Wired devices without a battery can supply protobuf's default zero.
  if (percent === 0 && raw.is_bluetooth === false && raw.is_wireless_steam_dongle === false && charging !== true) percent = null;
  return { id: serial ? `steam:serial:${identity(serial)}` : `steam:${index}:${identity(name)}`,
    name, percent, level: null, charging };
}

export function messageBody(message: unknown): ControllerRecord {
  const wrapped = message as { Body?: () => { toObject?: () => unknown } } | null;
  const body = controllerRecord(wrapped?.Body?.()?.toObject?.());
  if (!body) throw new Error("SteamInputManager returned an unreadable message");
  return body;
}

export interface SteamControllerStore {
  GetControllers: () => unknown;
  GetController: (index: number) => unknown;
  fnOnControllerBatteryState: (...args: unknown[]) => unknown;
}

export function isSteamControllerStore(value: unknown): value is SteamControllerStore {
  const store = value as SteamControllerStore | null;
  return typeof store?.GetControllers === "function" && typeof store.GetController === "function"
    && typeof store.fnOnControllerBatteryState === "function";
}

export function storeControllerItem(value: unknown): { index: number; item: ControllerBatteryUpdate } | null {
  const raw = controllerRecord(value);
  if (!raw) return null;
  const mapped = { controller_index: raw.nControllerIndex, name: raw.strName, serial_number: raw.strSerialNumber,
    controller_type: raw.eControllerType, is_remote_device: raw.bRemoteDevice,
    battery_level: raw.ucBatteryLevel, is_charging: raw.bCharging,
    is_bluetooth: raw.bBluetooth, is_wireless_steam_dongle: raw.bWireless };
  const index = controllerIndex(mapped);
  const item = controllerItem(mapped);
  return index != null && item ? { index, item } : null;
}

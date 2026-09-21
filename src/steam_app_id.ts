/** Normalize Steam's signed shortcut IDs to the unsigned AppID used by grid files. */
export function normalizeAppId(value: unknown): number {
  const number = Number(value ?? 0);
  if (!Number.isFinite(number) || !Number.isInteger(number)) return 0;
  if (number > 0 && number <= 0xFFFFFFFF) return number;
  if (number < -1 && number >= -0x80000000) return number >>> 0;
  return 0;
}

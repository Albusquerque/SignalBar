export type Mode = "artwork" | "performance" | "disabled";
export type ArtworkMode = "auto" | "center" | "lower" | "manual";
export type ArtworkSource = "hero" | "header" | "capsule";
export type PerformanceMetric = "cpu" | "gpu" | "mixed";
export type MixedDirection = "same" | "mirrored";
export type TemperaturePalette = "thermal" | "classic" | "icefire";
export type RGB = [number, number, number];

export interface Status {
  version: string;
  available: boolean;
  active: boolean;
  owner: "Valve" | "SignalBar";
  provider: string;
  suspension_reason: string;
  error: string;
  mode: Mode;
  performance_metric: PerformanceMetric;
  mixed_direction: MixedDirection;
  temperature_palette: TemperaturePalette;
  artwork_mode: ArtworkMode;
  artwork_manual_y: number;
  artwork_source: ArtworkSource;
  artwork_custom: boolean;
  cool_temp_c: number;
  hot_temp_c: number;
  reverse_led_order: boolean;
  game: { appid: number; title: string };
  performance: {
    gpu_load: number | null;
    gpu_temperature: number | null;
    cpu_load: number | null;
    cpu_temperature: number | null;
  };
  artwork: { sample_y?: number; filename?: string; colors?: RGB[] };
  debug: {
    led_path: string;
    last_write: number;
    writes: number;
    last_external: number;
    cooldown_remaining: number;
    reverse_led_order: boolean;
  };
}

export interface ArtworkPayload {
  found: boolean;
  appid: number;
  mime?: string;
  filename?: string;
  fingerprint?: string;
  data_uri?: string;
  cached?: boolean;
  source?: ArtworkSource;
  source_label?: string;
}

export type Mode = "artwork" | "performance" | "disabled";
export type ArtworkMode = "auto" | "center" | "lower" | "manual";
export type ArtworkSource = "hero" | "header" | "capsule";
export type PerformanceMetric = "cpu" | "gpu" | "mixed";
export type PerformanceSmoothing = "responsive" | "balanced" | "smooth";
export type MixedDirection = "same" | "mirrored";
export type TemperaturePalette = "thermal" | "classic" | "icefire";
export type CountdownColour = "cyan" | "green" | "amber" | "violet" | "white";
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
  performance_smoothing: PerformanceSmoothing;
  mixed_direction: MixedDirection;
  temperature_palette: TemperaturePalette;
  artwork_mode: ArtworkMode;
  artwork_manual_y: number;
  artwork_source: ArtworkSource;
  artwork_custom: boolean;
  cool_temp_c: number;
  hot_temp_c: number;
  reverse_led_order: boolean;
  parental_countdown_enabled: boolean;
  countdown_colour: CountdownColour;
  countdown_full_bar_minutes: 0 | 60 | 120 | 180 | 240;
  countdown_dark_edge_compensation: number;
  free_timer_minutes: number;
  game: { appid: number; title: string };
  performance: {
    gpu_load: number | null;
    gpu_temperature: number | null;
    cpu_load: number | null;
    cpu_temperature: number | null;
    logical_lit: number;
    physical_lit: number;
  };
  artwork: { sample_y?: number; filename?: string; colors?: RGB[] };
  countdown: {
    active: boolean;
    source: "" | "parental" | "free" | "preview";
    label: string;
    remaining_seconds: number;
    total_seconds: number;
    scale_seconds: number;
    alerting: boolean;
    logical_lit: number;
    physical_lit: number;
    colors: RGB[];
  };
  debug: {
    led_path: string;
    last_write: number;
    last_write_age_s: number | null;
    writes: number;
    last_external: number;
    last_external_age_s: number | null;
    cooldown_remaining: number;
    stable_remaining: number;
    guard_state: "ready" | "blocked";
    guard_reason: string;
    reverse_led_order: boolean;
    appid: number;
    game_detection_source: string;
    game_sync_ms: number | null;
    parental_callback_state: "idle" | "disabled" | "waiting" | "received";
    parental_callback_delay_ms: number | null;
    parental_wait_s: number | null;
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

import { callable } from "@decky/api";
import type { ArtworkPayload, Status } from "./types";

export const getStatus = callable<[], Status>("get_status");
export const setMode = callable<[mode: string], Status>("set_mode");
export const setSetting = callable<[key: string, value: unknown], Status>("set_setting");
export const setArtworkSetting = callable<[appid: number, key: string, value: unknown], Status>("set_artwork_setting");
export const gameChanged = callable<[appid: number, title: string], Status>("game_changed");
export const getArtwork = callable<[appid: number, source: string], ArtworkPayload>("get_artwork");
export const submitArtwork = callable<[
  appid: number,
  fingerprint: string,
  colors: number[][],
  sampleY: number,
  filename: string,
  source: string,
], Status>("submit_artwork");
export const setSteamActivity = callable<[active: boolean, reason: string], boolean>("set_steam_activity");
export const reportRuntimeDiagnostic = callable<[
  event: string,
  appid: number,
  source: string,
  durationMs: number,
], boolean>("report_runtime_diagnostic");
export const reportParentalMinutes = callable<[minutes: number], Status>("report_parental_minutes");
export const startFreeTimer = callable<[minutes: number], Status>("start_free_timer");
export const stopFreeTimer = callable<[], Status>("stop_free_timer");
export const previewCountdown = callable<[], Status>("preview_countdown");
export const triggerEvent = callable<[kind: string, preview: boolean, variant: string], boolean>("trigger_event");

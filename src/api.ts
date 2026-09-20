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

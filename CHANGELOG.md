# Changelog

## 0.2.1 — 2026-09-20

- Replaced Automatic with explicit Artwork, Performance and Disabled modes;
  existing Automatic settings migrate without losing their former priority.
- Added per-game Library Hero, Header or Capsule selection and replaced the
  technical cache filename in the panel with the running game's title.
- Added two mixed CPU/GPU fill layouts: both halves left-to-right, or mirrored
  from the outside edges toward the black centre separator.

## 0.2.0 — 2026-09-20

- Persisted Artwork row mode and manual position independently for every AppID;
  untouched games continue to use the global default.
- Corrected the official Steam Machine's physical LED direction while keeping
  software previews left-to-right, with a Debug override.
- Added CPU, GPU and mixed performance displays. Mixed is CPU 8 + black centre
  separator + GPU 8, with both halves growing inward.
- Added three temperature colour palettes and renamed the ambiguous Cool/Hot
  colour controls to Cool/Hot temperature with inline explanations.
- Made Automatic's Performance-over-Artwork priority explicit in the UI.
- Replaced the inaccessible native Debug details element with a focusable
  SteamOS toggle in the top Status section.

## 0.1.0 — 2026-09-20

- Added Valve-first Vanilla Guard with external-change detection, cooldown and
  stable-window recovery.
- Added the Providers → Arbiter → Renderer backend architecture.
- Added local Library Hero discovery, automatic/manual band selection,
  17-colour preview and persistent artwork cache.
- Added a GPU load/temperature meter using local DRM and AMDGPU hwmon data.
- Added compact Decky status, mode, artwork, performance and debug sections.
- Added fail-closed hardware handling, settings persistence, targeted tests and
  reproducible Decky ZIP packaging.

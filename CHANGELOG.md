# Changelog

## 0.3.1 — 2026-09-20

- Extend the existing **Extra dark LEDs** optical calibration to Performance
  as well as Playtime Countdown, retaining the default value of three.
- Keep Decky's Performance preview logical while writing the compensated LED
  count to hardware; e.g. 12 cells in the preview become 9 physical LEDs with
  compensation 3.
- Share one compensation across the two halves of the mixed CPU/GPU meter
  instead of subtracting it independently from each half. Each active half
  retains at least one physical LED. Artwork remains unchanged.
- Show the live logical-to-physical Performance mapping in Debug.
- Add Responsive, Balanced and Smooth meter-response profiles for CPU and GPU,
  with Balanced as the default.
- Filter the displayed percentage and LED length from the same value. Balanced
  limits movement over time, accepts sustained rises progressively, requires
  two lower samples before falling and then decays more slowly to prevent
  one-sample spikes from making the bar oscillate.

## 0.3.0 — 2026-09-20

- Start game detection, Artwork sampling, Performance activation, Steam
  Families observation, download ownership and suspend/resume handling as soon
  as Decky loads the plugin; opening SignalBar's settings is no longer required.

- Re-register Steam Families remaining-time observation when a game launches,
  keep parental time above personal timers and both base display modes, and
  hide parental time while no game is running.
- Cancel parental state immediately when its setting is disabled, the game is
  closed or another game starts, including during the final flash sequence.
- Clear stale running-game state on termination and resume from suspend instead
  of restoring Artwork from the last game.
- Move Playtime countdown below Performance in the Decky panel.
- Use constant pure red during the final five minutes and keep only the
  right-to-left circulation, avoiding two simultaneous animations.
- Repeat three brief full-white flashes during the final eight seconds of a
  countdown, then return immediately to the selected base provider at zero.
- Add optical dark-edge compensation for the Steam Machine's diffused light
  guide while retaining all 17 pixels at a full countdown.
- Make that physical compensation persistent and adjustable from 0–6 under
  Debug. The Decky preview retains the logical count: 12 shown with a value of
  3 writes 9 lit LEDs to the hardware. It applies only to countdown frames,
  never Artwork or Performance.
- Add a selectable countdown scale: start full, or map the full 17-pixel bar to
  1, 2, 3 or 4 hours. Longer remaining times stay full until that window.
- Move Debug to the bottom and replace raw monotonic values with useful ages,
  separate cooldown/stability timers, game detection source, backend sync time
  and Steam Families callback waiting/received latency.

- Added a temporary playtime countdown that automatically returns to the
  selected Artwork or Performance display when it ends.
- Added Steam Families remaining-time support through SteamUI's parental
  playtime callback, with an independent enable/disable setting.
- Added a free 5–240 minute personal timer that continues while the Decky
  panel is closed, plus a non-destructive 15-second preview.
- Added five starting colours, a shrinking right edge and a right-to-left
  travelling highlight. The signal turns amber below 15 minutes, then pure red
  below five minutes while circulation continues at constant brightness.
- Added deterministic provider, priority, direction, colour and persistence
  tests for the countdown feature.

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

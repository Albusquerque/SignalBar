# Changelog

## 0.4.0 - 2026-09-21

- Add opt-in Light events for Steam notifications, achievements, screenshots,
  and recording start/stop, with 14 selectable notification, achievement, and
  screenshot animations plus local previews beside every control.
- Detect every valid Steam notification type, use the achievement notification
  for unlock celebrations, watch for newly written screenshots, and track
  recording state through SteamClient callbacks.
- Let short event animations run outside games, interrupt them on a new native
  LED write, and restore the verified live display afterward.
- Protect the final five countdown minutes from transient events and preserve
  the existing Steam Families, personal timer, and selected base-display
  priority rules.
- Keep a pure red centre LED visible while recording over Artwork or
  Performance. Neighbour isolation is enabled by default to prevent diffuser
  bleed, and the marker never modifies a countdown or another event animation.
- Reorganize settings into dedicated Artwork, Performance, Playtime, Light
  events, and Advanced pages with a compact quick-access status panel.
- Remove duplicate Performance previews from the quick panel. Show CPU/GPU
  load and temperature with one logical preview, and only show the game image
  when Artwork is selected.
- Place the Artwork image and source label directly above its logical preview.
  Preserve the full Hero, Header, or Capsule aspect ratio without cropping.
- Draw a red horizontal guide over the Artwork image while adjusting a manual
  sample row.
- Prefer locally installed Steam custom-grid artwork, including SteamGridDB
  replacements, and support Hero, Header, or Capsule artwork for non-Steam
  shortcuts without requiring an API key or network request.
- Add an optional always-on Performance mode for the Steam home screen while
  retaining native LED ownership protection.
- Add Responsive, Balanced, and Smooth meter filtering, CPU/GPU/mixed layouts,
  selectable mixed fill direction, and shared physical diffuser compensation.
- Add custom Cool, Middle, and Hot performance colours through Decky's native
  colour picker alongside the three built-in temperature palettes.
- Show active Steam Families and personal countdown time with a live 17-LED
  preview at the top of the Playtime page.
- Change the default Extra dark LEDs calibration from three to two and replace
  the quick-access Wi-Fi-like icon with the stock Tabler `TbCubeSpark` icon.
- Replace the README with the new visual presentation and animated examples for
  Performance, Countdown, Notifications, Screenshots, Achievements, and
  Recording.

## 0.4.0-beta.4 — 2026-09-21

- Restore live CPU/GPU load and temperature readings in the quick Decky panel
  whenever Performance is the selected base display.
- Move an active Steam Families or personal countdown to a prominent live
  preview at the top of the Playtime page, including its remaining time.
- Put a local live LED preview beside every Light events preview control so
  animations remain visible even at the bottom of the settings page.
- Keep the recording marker as a pure red centre LED over Artwork or
  Performance, never over countdowns or transient event animations.
- Add an optional recording-marker isolation setting that turns the two
  neighbouring LEDs black to reduce optical colour bleed.

## 0.4.0-beta.3 — 2026-09-21

- Show the running game's artwork in the quick Decky panel, regardless of the
  selected LED display mode.
- Preserve the full image in Artwork settings and the quick panel, including
  wide headers and vertical capsules; neither preview crops the source image.
- Ignore late artwork responses from a previous game or image-source selection.
- Build and automated tests pass; the revised layout still needs a Steam
  Machine/Decky visual check.

## 0.4.0-beta.2 — 2026-09-21

- Add all 14 notification, achievement and screenshot variants from the two
  animation mockups, while retaining the three beta.1 patterns as choices.
- Save one animation selection per event category and keep queued events on
  the variant that was selected when they arrived.
- Make previews play immediately without enabling live events or changing the
  saved selection; recording previews do not change recording state.
- Split the Decky UI into a quick mode/status panel and dedicated Artwork,
  Performance, Playtime, Light events and Advanced settings pages.
- Keep the existing event priority, protected final five countdown minutes,
  native-write interruption and physical LED ownership safeguards.
- Automated tests cover each 17-LED variant and settings persistence; hardware
  behaviour still needs verification on an official Steam Machine.

## 0.4.0-beta.1 — 2026-09-21

- Signal every valid Steam notification type, including Community comments and
  types added later. Do not suppress later notifications because Steam reused a
  list index, and do not ignore real events during plugin startup.
- Add short, exclusive light signals for Steam notifications, unlocked
  achievements, newly written screenshots, and recording start/stop events.
- Make cyan notifications traverse all 17 LEDs; make achievements celebrate with
  three amber beats, a white-gold burst, an outward sweep and a full-bar glow.
- Temporarily suspend the base Artwork, Performance or playtime display while
  an animation plays, then restore its current frame without pausing its timer.
- Keep the final five minutes of every countdown protected: transient events
  are skipped instead of hiding the red warning or last-eight-second flashes.
- Keep the centre LED red while recording over Artwork or Performance, never
  over a countdown. Add an opt-in master switch, per-category switches and
  local preview buttons.
- Play light events outside games and let them briefly take over a stable
  Valve/system LED frame. Restore that exact frame afterward if still owned;
  cancel the animation if a new native write occurs. Disabled still wins.
- Sample active animations at 60 ms intervals (normal providers remain at
  100 ms) so the cyan crossing can reach the full 17-pixel span.
- Add animation, Steam-event mapping, priority and recording-state tests.
- Beta limitation: SteamClient event callbacks still need verification on the
  official Steam Machine; this build is not a stable release.

## 0.3.2-beta.1 — 2026-09-21

- Prefer artwork installed locally through Steam's custom grid (including
  SteamGridDB) over the unmodified Store image for the same game.
- Support custom Hero, Header and Capsule images for non-Steam shortcuts, with
  an available custom image as fallback when the selected role is missing.
- Read the active Steam account's custom grid when known, without showing
  another account's images; accept signed 32-bit shortcut AppIDs from SteamUI.
- Keep artwork discovery local and read-only; no SteamGridDB API key or network
  request is required.

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

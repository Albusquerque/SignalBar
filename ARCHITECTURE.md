# SignalBar architecture

## Pipeline

`Providers → Arbiter → Renderer`

- **Providers** collect or hold facts and produce optional 17-pixel frames.
  `PerformanceProvider` reads local CPU/GPU Linux metrics at 2 Hz,
  `ArtworkProvider` owns validated/cacheable browser samples,
  `CountdownProvider` owns independent parental/free/preview deadlines, and
  `IdleProvider` deliberately emits no frame (Vanilla).
- **Arbiter** is pure policy. Disabled is an explicit user stop. Otherwise
  Valve/explicit Steam activity is above every SignalBar provider, Steam
  Families is above the personal timer, and an active timer is above the
  user's explicit Artwork or Performance provider.
- **Renderer** is the only production component holding the hardware adapter.
  It validates exactly 17 RGB pixels, serializes access, coalesces identical
  frames, rate-limits writes, reads back the actual signature and fails closed.

## Startup lifecycle

Decky's one-time frontend plugin initializer starts a background SignalBar
runtime immediately when the bundle loads. That runtime reports the already
running game, polls as a fallback, subscribes to game lifetime, Steam Families,
download and resume events, and samples local Artwork without waiting for the
settings panel to mount. Backend calls that race plugin startup are retried.
The panel is only a view and settings surface; closing or never opening it does
not stop providers. `onDismount` unregisters every Steam callback and timer.

## Vanilla Guard

The backend polls all `multi_intensity` and `brightness` attributes. After a
SignalBar write, Renderer records the read-back signature. A later signature
that differs from that verified value is treated as external ownership:

1. abandon SignalBar's remembered frame without restoring it;
2. report Valve as owner;
3. renew a cooldown on further changes;
4. require both cooldown expiry and a stable observation window;
5. only then allow Arbiter to select a SignalBar provider again.

Native download callbacks in the Decky frontend create short renewable Steam
activity leases so the backend can yield before or during a known transition.
The lease expires automatically if the frontend vanishes.

No kernel module, Steam hook, read-only OS modification, animation emulation or
ownership fight is used.

## Artwork flow

The backend locates the selected cached Library Hero, Header or Capsule for the
AppID and returns local bytes as a data URI. Steam's browser decodes the image using Canvas, evaluates
5.5%-high bands around 35, 45, 55, 65, 75 and 82 percent, then scores
saturation, contrast, adjacent colour diversity, black/white excess and
uniformity. The selected band is horizontally reduced to 17 zones with a mild
perceptual correction. Results are cached by AppID, artwork fingerprint and row
setting; no service or network is involved. Image source, row mode and manual
position are stored per AppID. Games without a profile use the global default
and never inherit the previously running game's custom Artwork choices. The
Library Logo is not sampled because it is a transparent overlay rather than a
complete backdrop.

## Performance layouts and orientation

CPU and GPU full-bar modes map 0–100% load to 0–17 pixels. Mixed maps CPU to
the left 8 pixels, keeps the centre pixel black, and maps GPU to the right 8.
The user can make both halves grow left-to-right, or mirror the GPU half so the
two signals grow from the outside edges toward the separator. Colour comes
from a selected three-stop palette and blends continuously between configurable
Cool and Hot temperature thresholds.

Frames are always logical left-to-right. The hardware adapter reverses the
physical sysfs path order by default for the official Steam Machine, so UI
previews and the user's physical viewpoint agree without contaminating provider
logic.

## Countdown signals

Parental, free and preview timers keep separate monotonic deadlines. Preview
has deliberate short-lived priority; otherwise Steam Families is authoritative
over the personal timer and appears only while a game is active. The frontend
re-registers Steam's remaining-time callback on each game launch. The callback
is registered only after the backend accepts the new AppID, because
Steam may answer synchronously. Disabling parental display, leaving the game or
switching AppID deletes that session's parental state, including its final alert.
The lit portion occupies the logical left side, so its disappearing edge moves
right-to-left. A persisted 0–6 physical dark-edge compensation counters
light-guide bloom; it defaults to three and is applied only by CountdownProvider.
Artwork and Performance frames bypass it. Status exposes the uncompensated logical
frame for Decky plus logical/physical lit counts, while Renderer receives the
compensated frame. Full bars remain 17 pixels and a running timer retains at
least one physical pixel.
A rendering scale of zero uses the timer's initial duration. Fixed 1–4 hour
scales map that remaining window to 17 pixels and clamp longer durations to a
full bar. Preview deliberately ignores the fixed scale.
A brighter highlight circulates right-to-left. Below five minutes the palette
becomes constant pure red; circulation remains the sole animation until the
final eight seconds. Then a three-white-flash pattern repeats until zero before
the arbiter returns immediately to the unchanged base provider.

## Runtime diagnostics

Frontend lifecycle milestones are reported to the backend without influencing
provider policy. Debug exposes the game detection source, backend RPC latency,
and elapsed time waiting for Steam's parental callback. Renderer retains the
last successful-write timestamp across relinquish operations. Vanilla Guard
reports cooldown and stable-window time independently, avoiding a misleading
zero cooldown while stability is still pending. Debug is rendered last in the
Decky panel.

## Extending providers

A provider returns `ProviderOutput(name, frame, reason)`. New providers should
collect data at their natural low frequency, never import hardware code, and
leave priority/order to Arbiter. Renderer remains unchanged.

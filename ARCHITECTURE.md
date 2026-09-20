# SignalBar architecture

## Pipeline

`Providers → Arbiter → Renderer`

- **Providers** collect or hold facts and produce optional 17-pixel frames.
  `PerformanceProvider` reads local CPU/GPU Linux metrics at 2 Hz,
  `ArtworkProvider` owns validated/cacheable browser samples, and
  `IdleProvider` deliberately emits no frame (Vanilla).
- **Arbiter** is pure policy. Valve/explicit Steam activity is above every
  SignalBar provider. The user's explicit Artwork or Performance mode selects
  that provider; Disabled selects Idle and returns control to Valve.
- **Renderer** is the only production component holding the hardware adapter.
  It validates exactly 17 RGB pixels, serializes access, coalesces identical
  frames, rate-limits writes, reads back the actual signature and fails closed.

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

## Extending providers

A provider returns `ProviderOutput(name, frame, reason)`. New providers should
collect data at their natural low frequency, never import hardware code, and
leave priority/order to Arbiter. Renderer remains unchanged.

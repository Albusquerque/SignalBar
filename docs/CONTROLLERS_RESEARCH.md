# Controller telemetry: investigation and hardware test protocol

Investigated during the 0.5.0 beta cycle, 2026-09-22 to 2026-09-23.
The final implementation is included in SignalBar 0.5.0.

## Battery overwrite report and repair

During beta testing, the second controller's real 41% (also visible in Steam
settings) appeared correctly for one or two seconds, then became 100%. This
timing matched the two-second roster poll.
The prior collector cleared its notification cache after every query, allowing
the following list snapshot to overwrite live state. The current collector retains that live
state for the device's connection, not the controller-list position, and clears
it when the device disconnects.

Startup can read SteamUI's existing controller-store instance through its
`GetControllers()` method. The object is found by the methods `GetControllers`,
`GetController` and `fnOnControllerBatteryState`, never by a numerical module ID.
Its `ucBatteryLevel` seeds a matched device before our first live notification.
We never initialise, mutate, or invoke a React hook on that store. Neither this
seed nor a later roster query may overwrite our live battery event. Device-level
debug reports all three values independently, including source and event age.

Regression tests reproduce 96%/41% followed by repeated 96%/100% list snapshots,
including a stale UI snapshot, reordering, changed input indices, disconnection
and reconnection. This explains and guards the overwrite in automated tests;
report any controller/connection where the physical readings still disagree.

## Report and diagnosis

The user tested beta.2 on a Steam Machine with a Steam Controller connected.
The panel remained on "No controller reported by Steam yet". That establishes
that SignalBar had not received its roster, before any animation or charge
threshold could be evaluated. It does not establish a hardware LED fault.

Beta.1/2 listened to `SteamClient.Input.RegisterForControllerListChanges` and
`RegisterForControllerBatteryChanges`. Optional chaining hid absent methods.
The beta.2 array correction targeted an older SteamUI implementation, not the
current generated service. Tests of that array parser could pass without any
working subscription on the target Steam build.

## Primary evidence inspected

- The actual installed Steam `steamui/chunk~2dcc5aaf7.js` bundle, including
  SteamUI's controller store and its `DoControllerListQuery`,
  `fnOnControllerListChanged`, and `fnOnControllerBatteryState` methods.
- The bundle's generated SteamInputManager namespace. Steam itself invokes
  `GetControllerList({})`, checks `BSuccess()`, then reads
  `Body().toObject().controllers`.
- SteamUI's header uses `ucBatteryLevel / 100` for its battery icon, and the
  raw-to-UI mapper assigns `battery_level` and `is_charging` to that state.
- SteamTracking's copies of Valve's generated schemas:
  [webuimessages_steaminput.proto](https://github.com/SteamTracking/Protobufs/blob/master/steam/webuimessages_steaminput.proto)
  and [service_steaminputmanager.proto](https://github.com/SteamTracking/Protobufs/blob/master/webui/service_steaminputmanager.proto).
- [ControllerTools](https://github.com/jfernandez/ControllerTools) was examined
  as a comparison. It uses a separate Rust HID/BlueZ path, not proof of the
  obsolete Steam callbacks. Its device-specific implementation was not copied.
- Decky UI's installed `webpack.js` supports semantic export discovery through
  `findModuleExport`. No numerical module ID is needed in the plugin.

The locally inspected client is on macOS, not the target Steam Machine. Its
service contract is concrete evidence, but the target client's service loading,
transport and real device reporting still require on-machine validation.

## Contract used

| Operation | Payload / result |
| --- | --- |
| `SteamInputManager.GetControllerList#1` | request `{}`, response `controllers[]` |
| Controller item | `controller_index`, `name`, `serial_number`, `controller_type`, `battery_level`, `is_charging`, `is_bluetooth`, `is_wireless_steam_dongle`, `is_remote_device` |
| `NotifyControllerListChanged#1` | roster invalidation; query again |
| `NotifyControllerBatteryState#1` | `controller_index`, `battery_level`, `charging` |
| `NotifyControllerDisconnected#1` | `controller_index`; remove immediately and query again |

Notification handlers return Steam's success result `1`, matching its current
store. Unregister only our own handlers. There are no pairing, input feed,
calibration or firmware calls. Battery samples do not require an open panel.

## Behaviour and limits

- Read on plugin startup and resume; poll every two seconds. Missing hooks and
  discovery are retried. Failed/timed-out reads are not treated as an empty list.
- A first successful roster is a baseline, not a fake connection event. An
  already-low battery can warn once; a later genuine connection plays its style.
- Live alerts and the permanent gauge remain separate. Off for the gauge does
  not disable connection/low/charging alerts. Location settings remain enforced.
- Unknown and sentinel values remain unknown; real 0 and 1 are percentages.
  A wired non-charging default zero is treated as unavailable rather than a
  false flat battery. Wireless/Bluetooth zero remains a valid empty sample.
- Device serials are hashed for stable IDs and are not exposed in diagnostics.
  Built-in handheld, headset-paired, touch and keyboard/mouse pseudo-input are
  excluded, as are remote devices. Both Steam Controller generations remain
  eligible; their actual battery reporting must still be confirmed.
- Old in-flight responses cannot reintroduce a disconnected roster or overwrite
  a newer battery event. Polls renew a ten-second backend lease; stale gauges
  disappear when the collector stops reporting.
- Low warnings rearm after charge recovery (threshold + 5), charging or a new
  connection. Disabled/context-blocked/critical-countdown warnings are not
  marked as delivered. Repeated low samples do not create repeated flashes.
- Charging can only signal when Steam reports charging. Powering a device over
  USB is not assumed to charge its batteries. SignalBar cannot manufacture
  telemetry that the controller/driver does not provide.
- Private SteamUI APIs can change. A missing service is reported, not disguised
  as "no controller". No fallback to an unverified callback signature is used.

## Automated validation

`npm test` covers the collector's startup, events, queries, timeouts, missing
registry, backend retries, races and cleanup, plus provider/context/priority
behaviour. An engine test uses a fake LED device and checks that connection
and low alerts reach the renderer on Home and in a game.

An additional optional test loads the actual installed Steam webpack chunk in
a JavaScript VM, locates its generated service export, checks real protobuf
metadata, registers/unregisters handlers and routes a battery notification
through the new collector. The transport is simulated. No client state changes
and no Valve source is bundled in SignalBar.

```bash
SIGNALBAR_STEAM_UI_BUNDLE='/absolute/path/to/steamui/chunk~2dcc5aaf7.js' \
  npx tsx --test tests/frontend/controller_steam_contract.test.ts
```

## Hardware compatibility test

1. Install `SignalBar-v0.5.0.zip` from the release in Decky Developer settings.
   Restart Decky. Settings should show **0.5.0**.
2. With the Steam Controller already on, open Controllers after a few seconds.
   Expect its name, a percentage or explicit "battery unavailable", and
   `Steam connection: ready`. `0/3` hooks with successful queries still permits
   detection through polling. Capture the service error if not ready.
3. Set permanent gauge **Everywhere**, then **On Home**. Verify the first works
   at Home/in game and the second yields to the chosen game display. Unknown
   battery must not produce an invented gauge.
4. Set gauge **Off**, brief alerts enabled, location **Home + in game**. Turn the
   controller off, wait a few seconds and turn it on. Verify the welcome then
   restoration of the current display. Repeat in game without opening settings.
5. Preview Low battery to check physical output separately. Real low detection
   must be checked with a genuinely low reading; do not assume a preview proves
   interception. Charging similarly needs a supported charging device/state.
6. Test a second controller, reconnection, suspend/resume, and location switches.
   Check final-countdown protection and Disabled mode. No animation should keep
   replaying merely because the two-second poll ran again.
7. If it fails, report **Steam connection**, **hooks**, **queries**, **events**,
   **devices**, **query ms**, last-reading age, displayed controller/battery,
   Steam client version/channel, connection type (dongle/Bluetooth/USB), and
   whether a Preview lights the physical bar.

This protocol helps expand the compatibility list. Successful previews and
automated tests do not prove that every controller reports battery or charging.

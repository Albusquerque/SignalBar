# PongBar alpha — local hardware trial

This ZIP is **SignalBar 0.7.0-alpha.4**, a local test build. PongBar is an optional page in Detailed settings and is inactive until you start a session. The public stable download in the main README remains 0.6.0.

## Play

1. Install the local `SignalBar-v0.7.0-alpha.4.zip` in Decky Developer settings, then restart Decky. Confirm version `0.7.0-alpha.4` in SignalBar.
2. Stay on Steam Home. Connect one or two controllers and open **SignalBar → Detailed settings → PongBar alpha**. Leave **Controller input** on **Steam controller events**.
3. Press any button once on each controller. The controller list should show a separate index and the last button event for each. Choose Solo or Duel and assign the controller(s). If no controller appears, report whether the page says “Steam input is ready” or “Steam controller input is not ready”.
4. Leave **Return button** on **Right trigger**, then start the session. Press it when the white ball enters your two-LED end zone. Cyan is player 1; pink is player 2. Every five returns changes the field colour and speeds up the ball. If the diagnostic shows another button number when you press the trigger, report that number.
5. **Start full game without controller** uses the same game rules and LED rendering with on-screen Hit buttons. It requires the Decky panel to stay open for input.

## Dot matrix score display

The PongBar page and the SignalBar quick panel show an animated 40 × 18 dot matrix during play. **Open full-screen scoreboard** opens a dedicated Steam screen with the matrix enlarged. For touch play, that screen also has Hit buttons. The matrix keeps the numerical score visible during serve, return, perfect hit, level jackpot, point and winner sequences. Solo shows return count, best streak and lives; duel shows both scores. A small 17-dot row mirrors the logical LED frame. This is an on-screen companion to the physical LED game, not a claim that the Steam Machine light bar itself has a two-dimensional display.

## Live input diagnostics

The **Live input diagnostics** section works before starting a game. Each button press shows the last Steam button code, a press count, the most recent backend response in milliseconds, and the average and maximum over the last 20 responses. Outside a game, the timing is a small RPC probe. During play, it is the actual hit request. **Probe backend** measures the same RPC path without a controller; **Clear** starts a fresh local measurement series. The on-screen Hit buttons are measured during touch play. The optional browser-controller path is measured during play.

After an accepted hit, a second figure shows the time from backend hit processing to the completed PongBar write to the LED device. A rejected or mistimed press cannot produce that figure. Neither figure measures the moment the light becomes visible through the diffuser. The per-controller timing begins when SteamUI delivers the button event, so it also cannot measure delay inside the controller or before SteamUI.

Solo gives three lives and saves the best return streak locally. Duel ends at five points. An important SignalBar signal pauses the game; a Steam game launch or plugin unload ends it. Experimental vibration is off by default and is attempted only on the optional **Browser Gamepad API** input path when that API exposes an actuator. There is no vibration on the Steam controller events path yet.

## Report from the Steam Machine

- Controller model and connection type for each player.
- Whether both controllers appear, whether the right trigger registers as button 29, and whether it also triggers Steam navigation.
- The latest, average and maximum backend response for each controller, and the accepted hit → LED write timing. Note any RPC errors.
- Whether play continues when the Decky panel is closed, including a one-minute rally. If input disappears, reopen PongBar and report the pause reason.
- Whether the ball and colour steps are legible through the diffuser, and whether the hit window feels fair.
- If the Browser Gamepad API exposes a controller, try Experimental vibration and report which controller receives a pulse on a hit or point.

The SteamUI input path and vibration have been checked in code and off-device builds, not on the physical Steam Machine. The alpha should not be described as hardware-validated until these observations are recorded.

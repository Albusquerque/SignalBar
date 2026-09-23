# SignalBar 0.6.0

Weather is here. Pick a city, then let the Steam Machine's light bar reflect
the local sky. This release adds 16 selectable loops across clear skies, rain,
clouds, partly cloudy day and night, snow, and thunderstorms. Each scene can be
previewed offline. **Snow takes hold** is the default snow animation.

Weather can stay on Home, appear in games, or run everywhere. It shares the
persistent-display slot with the controller battery gauge, so selecting one
turns the other off. The gauge stays the fresh-install default until you choose
a weather city. Playtime countdowns and brief alerts still take priority.

An optional **experimental SteamOS top-bar indicator** puts a weather icon and
temperature near the clock, in °C or °F. It works independently of the LED
weather scene. It has been confirmed on one Steam Machine, but Steam UI changes
could affect its placement. Temperature is text only; the LEDs show the sky,
not a temperature colour scale.

Weather uses Open-Meteo after you manually select a city or postal code, with
an optional country. There is no geolocation, API key or SignalBar account.
Current conditions refresh about every fifteen minutes, and an expired reading
does not stay on the bar. This release also fixes a SteamOS certificate-chain
failure by using the operating system's trusted CA bundle while keeping HTTPS
verification enabled.

In **Advanced / debug**, you can now import a previously exported configuration
JSON or reset to the shipped defaults. Both actions require confirmation; bad
imports leave your current settings alone. Import and reset stop a personal
timer and temporary previews, but do not delete your export file or artwork
cache. Fresh-install defaults reflect the approved configuration, without
shipping anyone's personal per-game profiles. Existing installations keep
their saved choices.

The Weather colour treatment was refined against the physical diffuser, with
brightness and faint-LED cutoff controls. The README now includes a weather
animation and a real photo of the top-bar indicator. The
[interactive concept simulator](https://albusquerque.github.io/signalbar-concept/)
also includes all 16 final weather loops.

Install the attached `SignalBar-v0.6.0.zip` through **Decky Settings →
Developer → Install Plugin from ZIP**. Do not extract it first.

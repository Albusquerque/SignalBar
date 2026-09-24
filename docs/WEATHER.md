# Weather in SignalBar 0.6.1

This document describes Weather in the published release.

In **SignalBar settings → Weather**, search for a city (and optional country using its full name, not a two-letter code), choose a result, then enable weather **On Home**, **In game**, or **Everywhere**. Location is never detected automatically. Current conditions come from Open-Meteo, refresh about every 15 minutes, and are discarded after one hour without a successful refresh. No API key is required. A preview works without a city or network but does not test live weather.

Permanent weather and the permanent controller battery gauge are mutually exclusive. The controller gauge remains the fresh-install default; choosing weather turns it off, and choosing the gauge turns weather off. Brief controller alerts, light events, countdowns, and Steam's LED ownership guard keep their existing priorities.

## Animations

The loops offer eighteen choices: two sun, two moon-and-stars, two rain, four cloud, two partly-cloudy day, two partly-cloudy night, two snow, and two storm animations. **Cross & gather** crosses two pairs at a relaxed pace, then lets a three-LED cloud gather smaller clouds; it is the fresh-install Cloud choice. **Slow convergence** grows into a single eight-LED cloud, drifts to the left edge, returns to the right edge, then leaves the bar. The two earlier Cloud patterns remain selectable, and saved choices survive the update. Bluewater holds a blue field. Pearl rain uses a dimmer white field and an extra blue accent at each impact. The original **Sun/Moon through clouds** loops remain selectable. Each has an additional **fading clouds** variant: neutral-white cloud LEDs dim to off while the yellow sun or pale moon appears, then return. No dark brown or blue cloud colour is introduced. Melting snowfall uses paired and single melt-and-refill gaps; Snow takes hold accumulates white flakes until the bar is covered, then restarts. Snow takes hold is the fresh-install snow choice. Pulse and echoes has two lightning phrases. The new Cloud loops last twenty and forty-eight seconds respectively, including in the preview. All other loops last eight seconds.

Weather brightness and faint-LED cutoff still apply. The removed temperature colour signatures, thermometer, Soft weather halos and Fixed colour test no longer appear in the settings or rendering path. The °C/°F choice applies only to the SteamOS top-bar number. Existing values for removed LED settings are discarded on the next settings save. Existing selected Rain, Moon and Storm variants migrate to the retained versions where possible. This is a software palette, not a measured hardware colour calibration.

## SteamOS top bar (experimental)

Choose a city, then enable **SteamOS top-bar weather (experimental)** and choose Celsius or Fahrenheit. The icon and current temperature are inserted immediately before the clock when SignalBar recognizes Steam's top bar. If the clock markup differs, it tries the compact top-right icon row. If neither is found, it shows nothing rather than floating over the interface. This option is independent of the weather LED display and the controller gauge. It requests temperature only to show the number in SteamOS; no temperature pixels return to the light bar.

The reading updates with the usual Open-Meteo refresh. The indicator hides when the reading is unavailable or over an hour old, when the city is removed, when the option is turned off, and when the plugin unloads. It worked on the user's Steam Machine, but **this is not a documented Decky top-bar slot**: like FriendsBar, it depends on Steam's current UI structure, and a Steam update may break its placement.

## Testing

Select each animation in the Weather tab and press **Preview this animation**. Compare the logical preview with the physical bar, especially sun rays, rain echoes, silver night, snow white, and storm flashes. Steam's master brightness and the diffuser can still change the perceived colours. Automated software tests pass, but physical colour and timing need real Steam Machine confirmation.

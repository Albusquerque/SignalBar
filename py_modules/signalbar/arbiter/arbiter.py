"""Policy-only selection of the active provider."""

from __future__ import annotations

from signalbar.models import ProviderOutput, normalize_frame
from signalbar.providers.events import RED


class Arbiter:
    def choose(self, *, mode, guard_allows, game, performance, artwork, idle,
               signal=None, event=None, signal_critical=False, recording_marker=False,
               recording_marker_isolation=False, performance_always=False,
               controller_event=None, controller_base=None):
        if mode == "disabled":
            return ProviderOutput("none", None, "SignalBar disabled")
        # Short, opted-in effects can briefly use an otherwise native-owned bar.
        # The runtime still yields if it detects a new external write mid-effect.
        if controller_event is not None and controller_event.frame is not None and not signal_critical and controller_event.provider == "controller:low":
            return controller_event
        if event is not None and event.frame is not None and not signal_critical:
            return event
        if controller_event is not None and controller_event.frame is not None and not signal_critical:
            return controller_event
        if not guard_allows:
            return ProviderOutput("valve", None, "Valve/system owns the bar")

        if signal_critical and signal is not None and signal.frame is not None:
            return signal
        if signal is not None and signal.frame is not None:
            return signal

        if controller_base is not None and controller_base.frame is not None:
            return controller_base

        if mode == "performance":
            base = performance if (game.running or performance_always) and performance.frame else ProviderOutput("none", None, "performance unavailable")
        elif mode == "artwork":
            base = artwork if game.running and artwork.frame else ProviderOutput("none", None, "artwork unavailable")
        elif game.running and performance.frame:
            base = performance
        elif game.running and artwork.frame:
            base = artwork
        else:
            base = idle

        if recording_marker and base.frame is not None and base.provider in {"performance", "artwork"}:
            pixels = list(base.frame)
            if recording_marker_isolation:
                pixels[7] = (0, 0, 0)
                pixels[9] = (0, 0, 0)
            pixels[8] = RED
            return ProviderOutput(base.provider + "+recording", normalize_frame(pixels), base.reason)
        return base

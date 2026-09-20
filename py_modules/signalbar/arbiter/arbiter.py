"""Policy-only selection of the active provider."""

from __future__ import annotations

from signalbar.models import ProviderOutput


class Arbiter:
    def choose(self, *, mode, guard_allows, game, performance, artwork, idle, signal=None):
        if mode == "disabled":
            return ProviderOutput("none", None, "SignalBar disabled")
        if not guard_allows:
            return ProviderOutput("valve", None, "Valve/system owns the bar")

        if signal is not None and signal.frame is not None:
            return signal

        if mode == "performance":
            return performance if game.running and performance.frame else ProviderOutput("none", None, "performance unavailable")
        if mode == "artwork":
            return artwork if game.running and artwork.frame else ProviderOutput("none", None, "artwork unavailable")

        if game.running and performance.frame:
            return performance
        if game.running and artwork.frame:
            return artwork
        return idle

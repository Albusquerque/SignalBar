"""Userspace ownership detection for Valve-first LED coexistence."""

from __future__ import annotations

import time


class VanillaGuard:
    def __init__(self, cooldown_s=5.0, stable_s=2.0, clock=time.monotonic):
        self.cooldown_s = float(cooldown_s)
        self.stable_s = float(stable_s)
        self._clock = clock
        now = self._clock()
        self._last_observed = None
        self._last_change_at = now
        self._blocked_until = now + self.stable_s
        self._reason = "startup settle"
        self._external_at = 0.0

    @property
    def reason(self):
        return self._reason

    @property
    def last_external_at(self):
        return self._external_at

    def block(self, reason: str):
        now = self._clock()
        self._reason = str(reason or "Steam/system activity")
        self._external_at = now
        self._last_change_at = now
        self._blocked_until = max(self._blocked_until, now + self.cooldown_s)

    def observe(self, signature, expected_signature=None, explicit_active=False, explicit_reason=""):
        now = self._clock()
        if explicit_active:
            self.block(explicit_reason or "Steam/system activity")

        changed = self._last_observed is not None and signature != self._last_observed
        self._last_observed = signature
        if changed:
            self._last_change_at = now
            if expected_signature is not None and signature != expected_signature:
                self.block("external LED change detected")

        stable = now - self._last_change_at >= self.stable_s
        if now >= self._blocked_until and stable and not explicit_active:
            self._reason = ""
            return True
        return False

    def note_own_write(self, signature):
        self._last_observed = signature

    def remaining(self):
        return max(0.0, self._blocked_until - self._clock())


class ManualClock:
    """Tiny deterministic clock used by tests."""
    def __init__(self, value=0.0):
        self.value = float(value)

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += float(seconds)


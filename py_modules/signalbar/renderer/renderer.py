"""The sole production writer for the LED hardware."""

from __future__ import annotations

import threading
import time
from typing import Optional

from signalbar.models import Frame, normalize_frame


class Renderer:
    def __init__(self, hardware, min_interval_s: float = 0.05, clock=time.monotonic):
        self.hardware = hardware
        self.min_interval_s = max(0.05, float(min_interval_s))
        self._clock = clock
        self._lock = threading.RLock()
        self._last_frame: Optional[Frame] = None
        self._last_signature = None
        self._last_write_at = 0.0
        self._last_successful_write_at = 0.0
        self._saved_frame: Optional[Frame] = None
        self._failed = False
        self._writes = 0

    @property
    def failed(self):
        return self._failed

    @property
    def last_frame(self):
        return self._last_frame

    @property
    def last_signature(self):
        return self._last_signature

    @property
    def last_write_at(self):
        return self._last_write_at

    @property
    def last_successful_write_at(self):
        return self._last_successful_write_at

    @property
    def writes(self):
        return self._writes

    def render(self, frame) -> bool:
        clean = normalize_frame(frame)
        with self._lock:
            if self._failed or clean == self._last_frame:
                return False
            now = self._clock()
            if self._last_write_at and now - self._last_write_at < self.min_interval_s:
                return False
            try:
                if self._saved_frame is None:
                    self._saved_frame = self.hardware.read_frame()
                self.hardware.write_frame(clean)
                self._last_signature = self.hardware.read_signature()
            except OSError:
                self._failed = True
                self._last_frame = None
                self._last_signature = None
                raise
            self._last_frame = clean
            self._last_write_at = now
            self._last_successful_write_at = now
            self._writes += 1
            return True

    def relinquish(self, restore_if_owned: bool = True) -> bool:
        """Stop owning the bar; restore only when nobody changed our frame."""
        with self._lock:
            restored = False
            if restore_if_owned and self._saved_frame is not None and self._last_signature is not None:
                try:
                    if self.hardware.read_signature() == self._last_signature:
                        self.hardware.try_restore(self._saved_frame)
                        restored = True
                except OSError:
                    self._failed = True
            self._last_frame = None
            self._last_signature = None
            self._saved_frame = None
            self._last_write_at = 0.0
            return restored

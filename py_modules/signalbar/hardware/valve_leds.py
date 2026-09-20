"""Minimal sysfs adapter for the official Steam Machine light bar.

This module performs raw I/O but never decides when to write. Only Renderer
owns an instance in production.
"""

from __future__ import annotations

import glob
import os
import re
import threading
from typing import Optional

from signalbar.models import Frame, LED_COUNT, normalize_frame

LED_GLOB = "/sys/class/leds/valve-leds[[]*[]]"


def _index(path: str) -> int:
    match = re.search(r"\[(\d+)\]$", path)
    return int(match.group(1)) if match else -1


def discover_paths(pattern: str = LED_GLOB):
    return sorted(glob.glob(pattern), key=_index)


class ValveLedHardware:
    def __init__(self, paths=None):
        self.paths = list(paths) if paths is not None else discover_paths()
        if len(self.paths) != LED_COUNT:
            raise RuntimeError(f"expected {LED_COUNT} valve-leds devices, found {len(self.paths)}")
        self._io_lock = threading.RLock()
        self._reverse = False

    @property
    def device_path(self) -> str:
        if not self.paths:
            return LED_GLOB
        return os.path.commonpath(self.paths)

    @property
    def reverse(self) -> bool:
        return self._reverse

    def set_reverse(self, reverse: bool):
        with self._io_lock:
            changed = self._reverse != bool(reverse)
            self._reverse = bool(reverse)
            return changed

    def _logical_paths(self):
        return list(reversed(self.paths)) if self._reverse else self.paths

    @staticmethod
    def _read(path: str, name: str) -> str:
        with open(os.path.join(path, name), encoding="ascii") as handle:
            return handle.read().strip()

    @staticmethod
    def _write(path: str, name: str, value: str):
        with open(os.path.join(path, name), "w", encoding="ascii") as handle:
            handle.write(value)

    def read_frame(self) -> Frame:
        with self._io_lock:
            values = []
            for path in self._logical_paths():
                raw = self._read(path, "multi_intensity")
                parts = raw.split()
                if len(parts) != 3:
                    raise OSError(f"unexpected multi_intensity value at {path}")
                values.append(tuple(int(part) for part in parts))
            return normalize_frame(values)

    def read_signature(self):
        """Include master brightness so Valve slider changes trigger a yield."""
        with self._io_lock:
            return tuple(
                (self._read(path, "multi_intensity"), self._read(path, "brightness"))
                for path in self.paths
            )

    def write_frame(self, frame: Frame):
        frame = normalize_frame(frame)
        with self._io_lock:
            for path, (red, green, blue) in zip(self._logical_paths(), frame):
                self._write(path, "multi_intensity", f"{red} {green} {blue}")

    def try_restore(self, frame: Optional[Frame]):
        if frame is not None:
            self.write_frame(frame)

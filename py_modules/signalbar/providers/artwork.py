"""Artwork palette state and disk cache.

Image decoding happens in Steam's browser canvas; this provider owns validated
17-pixel results and persists them by AppID, artwork fingerprint, and row mode.
"""

from __future__ import annotations

import json
import os
import threading

from signalbar.models import ProviderOutput, normalize_frame


class ArtworkProvider:
    name = "artwork"

    def __init__(self, cache_path):
        self.cache_path = cache_path
        self._lock = threading.RLock()
        self._cache = {}
        self._current = None
        self._load()

    @staticmethod
    def key(appid, fingerprint, mode, manual_y):
        suffix = f"{float(manual_y):.3f}" if mode == "manual" else "-"
        return f"{int(appid)}:{fingerprint}:{mode}:{suffix}"

    def _load(self):
        try:
            with open(self.cache_path, encoding="utf-8") as handle:
                raw = json.load(handle)
            if isinstance(raw, dict):
                self._cache = raw
        except (OSError, ValueError, TypeError):
            self._cache = {}

    def _save(self):
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        temporary = self.cache_path + ".tmp"
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(self._cache, handle, separators=(",", ":"), sort_keys=True)
        os.replace(temporary, self.cache_path)

    def activate_cached(self, appid, fingerprint, mode, manual_y):
        with self._lock:
            entry = self._cache.get(self.key(appid, fingerprint, mode, manual_y))
            if not isinstance(entry, dict):
                self._current = None
                return False
            try:
                frame = normalize_frame(entry.get("colors"))
            except (ValueError, TypeError):
                self._current = None
                return False
            self._current = {**entry, "frame": frame, "appid": int(appid)}
            return True

    def submit(self, appid, fingerprint, mode, manual_y, colors, sample_y, filename="", source="hero"):
        frame = normalize_frame(colors)
        entry = {
            "colors": [list(pixel) for pixel in frame],
            "sample_y": float(sample_y),
            "filename": os.path.basename(str(filename or "")),
            "source": str(source or "hero"),
        }
        with self._lock:
            self._cache[self.key(appid, fingerprint, mode, manual_y)] = entry
            # Bound cache growth without adding a database.
            while len(self._cache) > 256:
                self._cache.pop(next(iter(self._cache)))
            self._save()
            self._current = {**entry, "frame": frame, "appid": int(appid)}

    def clear(self):
        with self._lock:
            self._current = None

    def output(self, appid):
        with self._lock:
            if not self._current or self._current.get("appid") != int(appid or 0):
                return ProviderOutput(self.name, None, "artwork not sampled")
            return ProviderOutput(self.name, self._current["frame"], "Steam Library artwork")

    def status(self):
        with self._lock:
            if not self._current:
                return {}
            return {
                "sample_y": self._current["sample_y"],
                "filename": self._current["filename"],
                "source": self._current.get("source", "hero"),
                "colors": [list(pixel) for pixel in self._current["frame"]],
            }

"""Atomic, schema-limited JSON settings persistence."""

from __future__ import annotations

import json
import os
import threading

DEFAULTS = {
    "mode": "artwork",
    # Retained only to migrate v0.1/v0.2 Automatic configurations.
    "performance_enabled": True,
    "performance_metric": "gpu",
    "mixed_direction": "mirrored",
    "temperature_palette": "thermal",
    "artwork_mode": "auto",
    "artwork_manual_y": 0.72,
    "artwork_source": "hero",
    "artwork_profiles": {},
    "cool_temp_c": 50.0,
    "hot_temp_c": 90.0,
    "reverse_led_order": True,
    "parental_countdown_enabled": True,
    "countdown_colour": "cyan",
    # 0 follows the timer's initial duration; otherwise this is fixed minutes.
    "countdown_full_bar_minutes": 0,
    "countdown_dark_edge_compensation": 3,
    "free_timer_minutes": 60,
    "guard_cooldown_s": 5.0,
    "guard_stable_s": 2.0,
}

VALID_MODES = {"artwork", "performance", "disabled"}
VALID_ARTWORK_MODES = {"auto", "center", "lower", "manual"}
VALID_ARTWORK_SOURCES = {"hero", "header", "capsule"}
VALID_PERFORMANCE_METRICS = {"cpu", "gpu", "mixed"}
VALID_MIXED_DIRECTIONS = {"same", "mirrored"}
VALID_TEMPERATURE_PALETTES = {"thermal", "classic", "icefire"}
VALID_COUNTDOWN_COLOURS = {"cyan", "green", "amber", "violet", "white"}


class SettingsStore:
    def __init__(self, path: str):
        self.path = path
        self._lock = threading.RLock()
        self._data = dict(DEFAULTS)
        self.load()

    def load(self):
        with self._lock:
            try:
                with open(self.path, encoding="utf-8") as handle:
                    raw = json.load(handle)
                if isinstance(raw, dict):
                    for key in DEFAULTS:
                        if key in raw:
                            self._data[key] = raw[key]
            except (OSError, ValueError, TypeError):
                pass
            self._validate()
            return dict(self._data)

    def _validate(self):
        self._data["performance_enabled"] = bool(self._data["performance_enabled"])
        if self._data["mode"] == "automatic":
            self._data["mode"] = "performance" if self._data["performance_enabled"] else "artwork"
        elif self._data["mode"] not in VALID_MODES:
            self._data["mode"] = DEFAULTS["mode"]
        if self._data["artwork_mode"] not in VALID_ARTWORK_MODES:
            self._data["artwork_mode"] = DEFAULTS["artwork_mode"]
        if self._data["artwork_source"] not in VALID_ARTWORK_SOURCES:
            self._data["artwork_source"] = DEFAULTS["artwork_source"]
        if self._data["performance_metric"] not in VALID_PERFORMANCE_METRICS:
            self._data["performance_metric"] = DEFAULTS["performance_metric"]
        if self._data["mixed_direction"] not in VALID_MIXED_DIRECTIONS:
            self._data["mixed_direction"] = DEFAULTS["mixed_direction"]
        if self._data["temperature_palette"] not in VALID_TEMPERATURE_PALETTES:
            self._data["temperature_palette"] = DEFAULTS["temperature_palette"]
        self._data["reverse_led_order"] = bool(self._data["reverse_led_order"])
        self._data["parental_countdown_enabled"] = bool(self._data["parental_countdown_enabled"])
        if self._data["countdown_colour"] not in VALID_COUNTDOWN_COLOURS:
            self._data["countdown_colour"] = DEFAULTS["countdown_colour"]
        try:
            full_bar_minutes = int(round(float(self._data["countdown_full_bar_minutes"])))
            self._data["countdown_full_bar_minutes"] = (
                full_bar_minutes if full_bar_minutes in {0, 60, 120, 180, 240} else 0
            )
        except (TypeError, ValueError):
            self._data["countdown_full_bar_minutes"] = DEFAULTS["countdown_full_bar_minutes"]
        try:
            self._data["countdown_dark_edge_compensation"] = max(
                0, min(6, int(round(float(self._data["countdown_dark_edge_compensation"]))))
            )
        except (TypeError, ValueError):
            self._data["countdown_dark_edge_compensation"] = DEFAULTS["countdown_dark_edge_compensation"]
        try:
            self._data["free_timer_minutes"] = max(5, min(240, int(round(float(self._data["free_timer_minutes"])))))
        except (TypeError, ValueError):
            self._data["free_timer_minutes"] = DEFAULTS["free_timer_minutes"]
        self._data["artwork_manual_y"] = max(0.15, min(0.90, float(self._data["artwork_manual_y"])))
        self._data["cool_temp_c"] = max(20.0, min(100.0, float(self._data["cool_temp_c"])))
        self._data["hot_temp_c"] = max(self._data["cool_temp_c"] + 1.0, min(120.0, float(self._data["hot_temp_c"])))
        self._data["guard_cooldown_s"] = max(1.0, min(30.0, float(self._data["guard_cooldown_s"])))
        self._data["guard_stable_s"] = max(0.5, min(10.0, float(self._data["guard_stable_s"])))
        raw_profiles = self._data.get("artwork_profiles")
        profiles = {}
        if isinstance(raw_profiles, dict):
            for raw_appid, raw_profile in list(raw_profiles.items())[:512]:
                try:
                    appid = str(int(raw_appid))
                except (TypeError, ValueError):
                    continue
                if int(appid) <= 0 or not isinstance(raw_profile, dict):
                    continue
                mode = raw_profile.get("mode", DEFAULTS["artwork_mode"])
                if mode not in VALID_ARTWORK_MODES:
                    mode = DEFAULTS["artwork_mode"]
                source = raw_profile.get("source", DEFAULTS["artwork_source"])
                if source not in VALID_ARTWORK_SOURCES:
                    source = DEFAULTS["artwork_source"]
                try:
                    manual_y = max(0.15, min(0.90, float(raw_profile.get("manual_y", DEFAULTS["artwork_manual_y"]))))
                except (TypeError, ValueError):
                    manual_y = DEFAULTS["artwork_manual_y"]
                profiles[appid] = {"mode": mode, "manual_y": manual_y, "source": source}
        self._data["artwork_profiles"] = profiles

    def all(self):
        with self._lock:
            return dict(self._data)

    def update(self, changes: dict):
        with self._lock:
            for key, value in changes.items():
                if key in DEFAULTS:
                    self._data[key] = value
            self._validate()
            self.save()
            return dict(self._data)

    def artwork_for(self, appid=0):
        with self._lock:
            appid = int(appid or 0)
            profile = self._data["artwork_profiles"].get(str(appid), {}) if appid > 0 else {}
            return {
                "mode": profile.get("mode", self._data["artwork_mode"]),
                "manual_y": profile.get("manual_y", self._data["artwork_manual_y"]),
                "source": profile.get("source", self._data["artwork_source"]),
                "custom": bool(profile),
            }

    def update_artwork(self, appid, changes):
        with self._lock:
            appid = int(appid or 0)
            if appid <= 0:
                mapped = {}
                if "mode" in changes:
                    mapped["artwork_mode"] = changes["mode"]
                if "manual_y" in changes:
                    mapped["artwork_manual_y"] = changes["manual_y"]
                if "source" in changes:
                    mapped["artwork_source"] = changes["source"]
                return self.update(mapped)

            profiles = dict(self._data["artwork_profiles"])
            profile = dict(profiles.get(str(appid), self.artwork_for(0)))
            profile.pop("custom", None)
            if "mode" in changes:
                profile["mode"] = changes["mode"]
            if "manual_y" in changes:
                profile["manual_y"] = changes["manual_y"]
            if "source" in changes:
                profile["source"] = changes["source"]
            profiles[str(appid)] = profile
            self._data["artwork_profiles"] = profiles
            self._validate()
            self.save()
            return self.artwork_for(appid)

    def save(self):
        directory = os.path.dirname(self.path)
        os.makedirs(directory, exist_ok=True)
        temporary = self.path + ".tmp"
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(self._data, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, self.path)

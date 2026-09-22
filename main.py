"""Decky backend entry point for SignalBar."""

import os
import sys

import decky

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PLUGIN_DIR, "py_modules"))

from signalbar.backend import Engine  # noqa: E402
from signalbar.settings import SettingsStore  # noqa: E402
from signalbar.steam import get_library_artwork  # noqa: E402


class Plugin:
    async def _main(self):
        settings_path = os.path.join(decky.DECKY_PLUGIN_SETTINGS_DIR, "config.json")
        cache_path = os.path.join(decky.DECKY_PLUGIN_SETTINGS_DIR, "artwork-cache.json")
        self.engine = Engine(SettingsStore(settings_path), cache_path, decky.logger)
        self.engine.start()
        decky.logger.info("[SignalBar] loaded")

    async def _unload(self):
        self.engine.stop()
        decky.logger.info("[SignalBar] unloaded; LED ownership released")

    async def _uninstall(self):
        self.engine.stop()

    async def get_status(self):
        return self.engine.status()

    async def set_mode(self, mode: str):
        self.engine.update_settings({"mode": mode})
        return self.engine.status()

    async def set_game_display(self, appid: int, mode: str):
        self.engine.settings.update_display(appid, mode)
        return self.engine.status()

    async def set_setting(self, key: str, value):
        self.engine.update_settings({key: value})
        return self.engine.status()

    async def set_artwork_setting(self, appid: int, key: str, value):
        changes = {}
        if key == "mode":
            changes["mode"] = value
        elif key == "manual_y":
            changes["manual_y"] = value
        elif key == "source":
            changes["source"] = value
        self.engine.update_artwork_settings(appid, changes)
        return self.engine.status()

    async def game_changed(self, appid: int = 0, title: str = ""):
        self.engine.set_game(appid, title)
        return self.engine.status()

    async def get_artwork(self, appid: int = 0, source: str = "hero"):
        result = get_library_artwork(appid, source)
        if result.get("found"):
            result["cached"] = self.engine.prepare_artwork(
                result["appid"], result["fingerprint"], result["filename"], result["source"]
            )
        return result

    async def submit_artwork(self, appid: int, fingerprint: str, colors, sample_y: float,
                             filename: str = "", source: str = "hero"):
        self.engine.submit_artwork(appid, fingerprint, colors, sample_y, filename, source)
        return self.engine.status()

    async def set_steam_activity(self, active: bool, reason: str = "Steam event"):
        self.engine.set_steam_activity(active, reason)
        return True

    async def report_runtime_diagnostic(self, event: str, appid: int = 0,
                                        source: str = "", duration_ms: float = -1):
        self.engine.report_runtime_diagnostic(event, appid, source, duration_ms)
        return True

    async def report_parental_minutes(self, minutes: float):
        self.engine.report_parental_minutes(minutes)
        return self.engine.status()

    async def start_free_timer(self, minutes: int):
        self.engine.start_free_timer(minutes)
        return self.engine.status()

    async def stop_free_timer(self):
        self.engine.stop_free_timer()
        return self.engine.status()

    async def preview_countdown(self):
        self.engine.preview_countdown()
        return self.engine.status()

    async def trigger_event(self, kind: str, preview: bool = False, variant: str = ""):
        return self.engine.trigger_event(kind, preview, variant)

    async def update_controllers(self, controllers, source: str = "Steam callback"):
        self.engine.update_controllers(controllers, source)
        return True

    async def reset_controllers(self):
        self.engine.reset_controllers()
        return True

    async def report_controller_telemetry(self, state):
        self.engine.report_controller_telemetry(state)
        return True

    async def preview_controller(self, kind: str, variant: str = ""):
        return self.engine.preview_controller(kind, variant)

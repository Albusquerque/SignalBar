"""SignalBar runtime orchestration.

Data collection stays in providers, ownership policy in Arbiter/VanillaGuard,
and all sysfs writes in Renderer.
"""

from __future__ import annotations

import threading
import time

from signalbar.arbiter import Arbiter, VanillaGuard
from signalbar.hardware import ValveLedHardware
from signalbar.models import GameState
from signalbar.providers import ArtworkProvider, IdleProvider, PerformanceProvider
from signalbar.renderer import Renderer


class Engine:
    def __init__(self, settings, cache_path, logger=None, hardware_factory=ValveLedHardware):
        self.settings = settings
        self.log = logger
        self.hardware_factory = hardware_factory
        self.artwork = ArtworkProvider(cache_path)
        self.performance = PerformanceProvider()
        self.idle = IdleProvider()
        self.arbiter = Arbiter()
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread = None
        self._game = GameState()
        self._artwork_identity = None
        self._steam_active_until = 0.0
        self._steam_reason = ""
        self._renderer = None
        self._guard = None
        self._decision = "none"
        self._owner = "Valve"
        self._suspension_reason = "starting"
        self._error = ""
        self._available = False

    def _info(self, message):
        if self.log:
            self.log.info(f"[SignalBar] {message}")

    def _warn(self, message):
        if self.log:
            self.log.warning(f"[SignalBar] {message}")

    def start(self):
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(target=self._run, name="signalbar-engine", daemon=True)
            self._thread.start()

    def stop(self):
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=2.0)
        with self._lock:
            if self._renderer:
                self._renderer.relinquish(restore_if_owned=True)
            self._owner = "Valve"
            self._decision = "none"

    def set_game(self, appid=0, title=""):
        try:
            appid = max(0, int(appid or 0))
        except (TypeError, ValueError):
            appid = 0
        with self._lock:
            changed = appid != self._game.appid
            self._game = GameState(appid, str(title or ""))
            if changed or not self._game.running:
                self.artwork.clear()
                self._artwork_identity = None

    def prepare_artwork(self, appid, fingerprint, filename="", source="hero"):
        artwork_settings = self.settings.artwork_for(appid)
        identity = (int(appid), str(fingerprint), str(filename or ""), str(source or "hero"))
        with self._lock:
            self._artwork_identity = identity
            return self.artwork.activate_cached(
                identity[0], identity[1], artwork_settings["mode"], artwork_settings["manual_y"]
            )

    def submit_artwork(self, appid, fingerprint, colors, sample_y, filename="", source="hero"):
        artwork_settings = self.settings.artwork_for(appid)
        self.artwork.submit(
            appid, fingerprint, artwork_settings["mode"], artwork_settings["manual_y"],
            colors, sample_y, filename, source,
        )

    def update_artwork_settings(self, appid, changes):
        artwork_settings = self.settings.update_artwork(appid, changes)
        with self._lock:
            if self._artwork_identity and int(appid or 0) == self._artwork_identity[0]:
                identity_appid, fingerprint, _, _ = self._artwork_identity
                self.artwork.activate_cached(
                    identity_appid, fingerprint,
                    artwork_settings["mode"], artwork_settings["manual_y"],
                )
        return artwork_settings

    def set_steam_activity(self, active, reason="Steam event"):
        with self._lock:
            if active:
                # Lease prevents a vanished frontend from suspending forever.
                self._steam_active_until = time.monotonic() + 3.0
                self._steam_reason = str(reason or "Steam event")
            else:
                self._steam_active_until = 0.0
                self._steam_reason = ""

    def update_settings(self, changes):
        values = self.settings.update(changes)
        with self._lock:
            if self._guard:
                self._guard.cooldown_s = values["guard_cooldown_s"]
                self._guard.stable_s = values["guard_stable_s"]
        return values

    def _run(self):
        hardware = None
        renderer = None
        guard = None
        while not self._stop.is_set():
            if hardware is None:
                try:
                    hardware = self.hardware_factory()
                    values = self.settings.all()
                    renderer = Renderer(hardware)
                    guard = VanillaGuard(values["guard_cooldown_s"], values["guard_stable_s"])
                    with self._lock:
                        self._renderer, self._guard = renderer, guard
                        self._available = True
                        self._error = ""
                        self._suspension_reason = "startup settle"
                    self._info("17 valve-leds detected; conservative startup settle begun")
                except Exception as error:
                    with self._lock:
                        self._available = False
                        self._error = str(error)
                        self._suspension_reason = "hardware unavailable; retrying"
                    if self._stop.wait(2.0):
                        break
                    continue

            if self._stop.wait(0.10):
                break
            try:
                now = time.monotonic()
                values = self.settings.all()
                if hardware.reverse != values["reverse_led_order"]:
                    # Restore with the old mapping before changing orientation;
                    # otherwise a later shutdown would restore the snapshot backwards.
                    if renderer.last_frame is not None:
                        renderer.relinquish(restore_if_owned=True)
                    hardware.set_reverse(values["reverse_led_order"])
                with self._lock:
                    game = self._game
                    explicit = now < self._steam_active_until
                    explicit_reason = self._steam_reason
                signature = hardware.read_signature()
                allowed = guard.observe(
                    signature,
                    expected_signature=renderer.last_signature,
                    explicit_active=explicit,
                    explicit_reason=explicit_reason,
                )
                performance = self.performance.output(
                    metric=values["performance_metric"],
                    cool_c=values["cool_temp_c"],
                    hot_c=values["hot_temp_c"],
                    palette=values["temperature_palette"],
                    direction=values["mixed_direction"],
                    enabled=(values["mode"] == "performance"),
                )
                artwork = self.artwork.output(game.appid)
                decision = self.arbiter.choose(
                    mode=values["mode"], guard_allows=allowed, game=game,
                    performance=performance, artwork=artwork, idle=self.idle.output(),
                )

                if decision.frame is not None:
                    wrote = renderer.render(decision.frame)
                    if wrote:
                        guard.note_own_write(renderer.last_signature)
                    owner = "SignalBar"
                    suspension = ""
                else:
                    externally_blocked = decision.provider == "valve"
                    if renderer.last_frame is not None:
                        renderer.relinquish(restore_if_owned=not externally_blocked)
                    owner = "Valve"
                    suspension = guard.reason if externally_blocked else decision.reason

                with self._lock:
                    self._decision = decision.provider
                    self._owner = owner
                    self._suspension_reason = suspension
                    self._error = ""
            except Exception as error:
                renderer.relinquish(restore_if_owned=False)
                with self._lock:
                    self._owner = "Valve"
                    self._decision = "none"
                    self._suspension_reason = "renderer failure; yielded to Valve"
                    self._error = str(error)
                self._warn(f"render loop stopped after failure: {error}")
                return

        if renderer is not None:
            renderer.relinquish(restore_if_owned=True)

    def status(self):
        values = self.settings.all()
        sample = self.performance.sample
        art = self.artwork.status()
        with self._lock:
            artwork_settings = self.settings.artwork_for(self._game.appid)
            renderer = self._renderer
            guard = self._guard
            return {
                "version": "0.2.1",
                "available": self._available,
                "active": self._owner == "SignalBar",
                "owner": self._owner,
                "provider": self._decision,
                "suspension_reason": self._suspension_reason,
                "error": self._error,
                "mode": values["mode"],
                "performance_metric": values["performance_metric"],
                "mixed_direction": values["mixed_direction"],
                "temperature_palette": values["temperature_palette"],
                "artwork_mode": artwork_settings["mode"],
                "artwork_manual_y": artwork_settings["manual_y"],
                "artwork_source": artwork_settings["source"],
                "artwork_custom": artwork_settings["custom"],
                "cool_temp_c": values["cool_temp_c"],
                "hot_temp_c": values["hot_temp_c"],
                "reverse_led_order": values["reverse_led_order"],
                "game": {"appid": self._game.appid, "title": self._game.title},
                "performance": {
                    "gpu_load": sample.gpu_load,
                    "gpu_temperature": sample.gpu_temp_c,
                    "cpu_load": sample.cpu_load,
                    "cpu_temperature": sample.cpu_temp_c,
                },
                "artwork": art,
                "debug": {
                    "led_path": renderer.hardware.device_path if renderer else "/sys/class/leds/valve-leds[*]",
                    "last_write": renderer.last_write_at if renderer else 0.0,
                    "writes": renderer.writes if renderer else 0,
                    "last_external": guard.last_external_at if guard else 0.0,
                    "cooldown_remaining": guard.remaining() if guard else 0.0,
                    "reverse_led_order": values["reverse_led_order"],
                },
            }

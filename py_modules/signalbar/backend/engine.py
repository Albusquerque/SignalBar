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
from signalbar.providers import ArtworkProvider, CountdownProvider, EventProvider, IdleProvider, PerformanceProvider
from signalbar.renderer import Renderer


class Engine:
    def __init__(self, settings, cache_path, logger=None, hardware_factory=ValveLedHardware):
        self.settings = settings
        self.log = logger
        self.hardware_factory = hardware_factory
        self.artwork = ArtworkProvider(cache_path)
        self.countdown = CountdownProvider()
        self.performance = PerformanceProvider()
        self.events = EventProvider()
        self.events.set_variants(settings.all())
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
        self._runtime_debug = {
            "appid": 0,
            "game_detection_source": "startup",
            "game_sync_ms": None,
            "parental_callback_state": "idle",
            "parental_callback_delay_ms": None,
            "parental_wait_started_at": 0.0,
        }

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
            self.events.clear_transients()
            self.events.clear_recording()
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
            if changed:
                # A Steam Families deadline belongs to the game session that
                # produced it. Never leak it into the next game or after exit.
                self.countdown.stop("parental")
                self.events.clear_recording()
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

    def report_runtime_diagnostic(self, event, appid=0, source="", duration_ms=-1):
        """Record frontend lifecycle timings without affecting provider policy."""
        try:
            appid = max(0, int(appid or 0))
            duration_ms = max(0.0, float(duration_ms))
        except (TypeError, ValueError):
            return
        event = str(event or "")
        now = time.monotonic()
        with self._lock:
            if event == "game_synced":
                self._runtime_debug.update({
                    "appid": appid,
                    "game_detection_source": str(source or "unknown")[:48],
                    "game_sync_ms": duration_ms,
                    "parental_callback_state": (
                        "waiting" if appid > 0 and self.settings.all()["parental_countdown_enabled"]
                        else "disabled" if appid > 0 else "idle"
                    ),
                    "parental_callback_delay_ms": None,
                    "parental_wait_started_at": now if appid > 0 else 0.0,
                })
            elif event == "parental_received" and appid == self._runtime_debug["appid"]:
                self._runtime_debug.update({
                    "parental_callback_state": "received",
                    "parental_callback_delay_ms": duration_ms,
                    "parental_wait_started_at": 0.0,
                })

    def report_parental_minutes(self, minutes):
        try:
            minutes = float(minutes)
        except (TypeError, ValueError):
            return
        values = self.settings.all()
        with self._lock:
            game_running = self._game.running
        if not values["parental_countdown_enabled"] or not game_running:
            self.countdown.stop("parental")
            return
        # SteamUI uses values above one day as the no-active-limit sentinel.
        if minutes <= 0:
            self.countdown.stop("parental")
            return
        if minutes > 1440:
            self.countdown.stop("parental")
            return
        self.countdown.start(
            "parental", minutes * 60.0,
            label="Steam Families",
        )

    def start_free_timer(self, minutes):
        values = self.settings.update({"free_timer_minutes": minutes})
        duration = values["free_timer_minutes"] * 60.0
        self.countdown.start("free", duration, total_seconds=duration, label="Free timer")

    def stop_free_timer(self):
        self.countdown.stop("free")

    def preview_countdown(self):
        self.countdown.start("preview", 15.0, total_seconds=15.0, label="Preview")

    def trigger_event(self, kind, preview=False, variant=""):
        values = self.settings.all()
        kind = str(kind or "")
        if values["mode"] == "disabled":
            return False
        if not preview:
            setting = {
                "notification": "event_notifications_enabled",
                "achievement": "event_achievements_enabled",
                "screenshot": "event_screenshots_enabled",
                "record-start": "event_recording_enabled",
                "record-stop": "event_recording_enabled",
            }.get(kind)
            if not values["events_enabled"] or not setting or not values[setting]:
                return False
        with self._lock:
            game_running = self._game.running
        countdown = self.countdown.status(
            allow_parental=values["parental_countdown_enabled"] and game_running,
        )
        if countdown["active"] and countdown["remaining_seconds"] <= 300:
            # Recording state still follows Steam, but the warning is never
            # visually interrupted, even for a fraction of one render tick.
            if kind in {"record-start", "record-stop"} and not preview:
                self.events.trigger(kind)
                self.events.clear_transients()
            return False
        return self.events.trigger(kind, preview=bool(preview), variant=variant)

    def update_settings(self, changes):
        values = self.settings.update(changes)
        self.events.set_variants(values)
        if not values["events_enabled"] or not values["event_recording_enabled"]:
            self.events.clear_recording()
        if not values["events_enabled"]:
            self.events.clear_transients()
        elif values["mode"] == "disabled":
            self.events.clear_transients()
        else:
            for key, kinds in (
                ("event_notifications_enabled", ("notification",)),
                ("event_achievements_enabled", ("achievement",)),
                ("event_screenshots_enabled", ("screenshot",)),
                ("event_recording_enabled", ("record-start", "record-stop")),
            ):
                if key in changes and not values[key]:
                    self.events.cancel_kinds(kinds)
        if "parental_countdown_enabled" in changes and not values["parental_countdown_enabled"]:
            # Turning the feature off is an immediate cancellation, not only
            # a visual filter. Later callbacks are ignored until re-enabled.
            self.countdown.stop("parental")
            with self._lock:
                self._runtime_debug["parental_callback_state"] = "disabled"
                self._runtime_debug["parental_wait_started_at"] = 0.0
        elif "parental_countdown_enabled" in changes:
            with self._lock:
                if self._game.running:
                    self._runtime_debug["parental_callback_state"] = "waiting"
                    self._runtime_debug["parental_callback_delay_ms"] = None
                    self._runtime_debug["parental_wait_started_at"] = time.monotonic()
        with self._lock:
            if self._guard:
                self._guard.cooldown_s = values["guard_cooldown_s"]
                self._guard.stable_s = values["guard_stable_s"]
        return values

    def _run(self):
        hardware = None
        renderer = None
        guard = None
        interval = 0.10
        event_was_active = False
        event_preempted_valve = False
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

            if self._stop.wait(interval):
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
                # A new native write during our animation ends that animation
                # immediately; otherwise the two writers would fight each tick.
                event_interrupted = (
                    event_was_active and renderer.last_signature is not None
                    and signature != renderer.last_signature
                )
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
                    dark_edge_compensation=values["countdown_dark_edge_compensation"],
                    smoothing=values["performance_smoothing"],
                    enabled=(values["mode"] == "performance"),
                    custom_palette=(
                        values["temperature_custom_cool"],
                        values["temperature_custom_middle"],
                        values["temperature_custom_hot"],
                    ),
                )
                artwork = self.artwork.output(game.appid)
                signal = self.countdown.output(
                    colour=values["countdown_colour"],
                    dark_edge_compensation=values["countdown_dark_edge_compensation"],
                    full_bar_seconds=values["countdown_full_bar_minutes"] * 60.0,
                    allow_parental=(
                        values["parental_countdown_enabled"] and game.running
                    ),
                )
                countdown_state = self.countdown.status(
                    allow_parental=values["parental_countdown_enabled"] and game.running,
                )
                signal_critical = (
                    countdown_state["active"] and countdown_state["remaining_seconds"] <= 300
                )
                if signal_critical:
                    self.events.clear_transients()
                if event_interrupted:
                    self.events.clear_transients()
                event = self.events.output()
                # Moving event waves need more than ten samples per second to
                # visibly visit all 17 positions. Normal providers stay at
                # the conservative 10 Hz cadence.
                interval = 0.06 if event.frame is not None else 0.10
                decision = self.arbiter.choose(
                    mode=values["mode"], guard_allows=allowed, game=game,
                    performance=performance, artwork=artwork, idle=self.idle.output(),
                    signal=signal, event=event, signal_critical=signal_critical,
                    recording_marker=(
                        self.events.recording and values["events_enabled"]
                        and values["event_recording_enabled"]
                    ),
                    recording_marker_isolation=values["recording_marker_isolation"],
                    performance_always=values["performance_always"],
                )

                if decision.frame is not None:
                    is_event = decision.provider.startswith("event:")
                    if is_event and not allowed:
                        event_preempted_valve = True
                    elif not is_event:
                        event_preempted_valve = False
                    wrote = renderer.render(decision.frame)
                    if wrote:
                        guard.note_own_write(renderer.last_signature)
                    owner = "SignalBar"
                    suspension = ""
                    event_was_active = is_event
                else:
                    externally_blocked = decision.provider == "valve"
                    if renderer.last_frame is not None:
                        # After a short event over a stable Valve frame, put
                        # that exact frame back. Renderer verifies ownership
                        # first, so a concurrent native write is never undone.
                        renderer.relinquish(
                            restore_if_owned=not externally_blocked or event_preempted_valve
                        )
                    event_was_active = False
                    event_preempted_valve = False
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
        now = time.monotonic()
        sample = self.performance.sample
        art = self.artwork.status()
        with self._lock:
            artwork_settings = self.settings.artwork_for(self._game.appid)
            countdown = self.countdown.status(
                colour=values["countdown_colour"],
                dark_edge_compensation=values["countdown_dark_edge_compensation"],
                full_bar_seconds=values["countdown_full_bar_minutes"] * 60.0,
                allow_parental=(
                    values["parental_countdown_enabled"] and self._game.running
                ),
            )
            renderer = self._renderer
            guard = self._guard
            last_write_at = renderer.last_successful_write_at if renderer else 0.0
            last_external_at = guard.last_external_at if guard else 0.0
            guard_debug = guard.debug_status() if guard else {
                "ready": False,
                "reason": "not initialized",
                "cooldown_remaining": 0.0,
                "stable_remaining": 0.0,
            }
            runtime_debug = dict(self._runtime_debug)
            wait_started = runtime_debug.pop("parental_wait_started_at", 0.0)
            runtime_debug["parental_wait_s"] = (
                max(0.0, now - wait_started) if wait_started else None
            )
            logical_performance = self.performance.frame(
                metric=values["performance_metric"],
                cool_c=values["cool_temp_c"],
                hot_c=values["hot_temp_c"],
                palette=values["temperature_palette"],
                direction=values["mixed_direction"],
                dark_edge_compensation=0,
                custom_palette=(
                    values["temperature_custom_cool"],
                    values["temperature_custom_middle"],
                    values["temperature_custom_hot"],
                ),
            )
            physical_performance = self.performance.frame(
                metric=values["performance_metric"],
                cool_c=values["cool_temp_c"],
                hot_c=values["hot_temp_c"],
                palette=values["temperature_palette"],
                direction=values["mixed_direction"],
                dark_edge_compensation=values["countdown_dark_edge_compensation"],
                custom_palette=(
                    values["temperature_custom_cool"],
                    values["temperature_custom_middle"],
                    values["temperature_custom_hot"],
                ),
            )
            return {
                "version": "0.4.0",
                "available": self._available,
                "active": self._owner == "SignalBar",
                "owner": self._owner,
                "provider": self._decision,
                "suspension_reason": self._suspension_reason,
                "error": self._error,
                "mode": values["mode"],
                "performance_metric": values["performance_metric"],
                "performance_smoothing": values["performance_smoothing"],
                "performance_always": values["performance_always"],
                "mixed_direction": values["mixed_direction"],
                "temperature_palette": values["temperature_palette"],
                "temperature_custom_cool": values["temperature_custom_cool"],
                "temperature_custom_middle": values["temperature_custom_middle"],
                "temperature_custom_hot": values["temperature_custom_hot"],
                "artwork_mode": artwork_settings["mode"],
                "artwork_manual_y": artwork_settings["manual_y"],
                "artwork_source": artwork_settings["source"],
                "artwork_custom": artwork_settings["custom"],
                "cool_temp_c": values["cool_temp_c"],
                "hot_temp_c": values["hot_temp_c"],
                "reverse_led_order": values["reverse_led_order"],
                "parental_countdown_enabled": values["parental_countdown_enabled"],
                "countdown_colour": values["countdown_colour"],
                "countdown_full_bar_minutes": values["countdown_full_bar_minutes"],
                "countdown_dark_edge_compensation": values["countdown_dark_edge_compensation"],
                "free_timer_minutes": values["free_timer_minutes"],
                "events_enabled": values["events_enabled"],
                "event_notifications_enabled": values["event_notifications_enabled"],
                "event_achievements_enabled": values["event_achievements_enabled"],
                "event_screenshots_enabled": values["event_screenshots_enabled"],
                "event_recording_enabled": values["event_recording_enabled"],
                "recording_marker_isolation": values["recording_marker_isolation"],
                "event_notification_variant": values["event_notification_variant"],
                "event_achievement_variant": values["event_achievement_variant"],
                "event_screenshot_variant": values["event_screenshot_variant"],
                "events": self.events.status(),
                "game": {"appid": self._game.appid, "title": self._game.title},
                "performance": {
                    "gpu_load": sample.gpu_load,
                    "gpu_temperature": sample.gpu_temp_c,
                    "cpu_load": sample.cpu_load,
                    "cpu_temperature": sample.cpu_temp_c,
                    "logical_lit": sum(pixel != (0, 0, 0) for pixel in logical_performance),
                    "physical_lit": sum(pixel != (0, 0, 0) for pixel in physical_performance),
                },
                "artwork": art,
                "countdown": countdown,
                "debug": {
                    "led_path": renderer.hardware.device_path if renderer else "/sys/class/leds/valve-leds[*]",
                    "last_write": renderer.last_write_at if renderer else 0.0,
                    "last_write_age_s": max(0.0, now - last_write_at) if last_write_at else None,
                    "writes": renderer.writes if renderer else 0,
                    "last_external": guard.last_external_at if guard else 0.0,
                    "last_external_age_s": max(0.0, now - last_external_at) if last_external_at else None,
                    "cooldown_remaining": guard_debug["cooldown_remaining"],
                    "stable_remaining": guard_debug["stable_remaining"],
                    "guard_state": "ready" if guard_debug["ready"] else "blocked",
                    "guard_reason": guard_debug["reason"],
                    "reverse_led_order": values["reverse_led_order"],
                    **runtime_debug,
                },
            }

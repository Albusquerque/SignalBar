"""Controller-battery gauges and short, exclusive 17-pixel signals."""

from __future__ import annotations

import math
import threading
import time

from signalbar.models import LED_COUNT, ProviderOutput, normalize_frame

BLACK = (0, 0, 0)
CYAN = (67, 214, 225)
GREEN = (124, 224, 174)
AMBER = (255, 198, 110)
RED = (255, 92, 108)
WHITE = (246, 249, 255)

VARIANTS = {
    "connect": ("welcome", "orbit", "handshake"),
    "persistent": ("clean", "tip", "horizon"),
    "low": ("beacon", "drain", "heartbeat"),
    "charging": ("current", "breath", "spark"),
    "duo": ("twin", "focus", "double-welcome"),
}
DURATIONS = {"connect": 2.7, "low": 3.0, "charging": 2.8, "persistent": 3.0, "duo": 3.0}


def _colour(percent):
    return RED if percent <= 20 else AMBER if percent <= 35 else GREEN


def _render_percent(item):
    """Coarse Steam levels drive a gauge, never a displayed exact percent."""
    if item["percent"] is not None:
        return item["percent"]
    if item["level"] is not None:
        return item["level"] * 25
    return None


def _fill(frame, start, end, colour):
    for index in range(max(0, start), min(LED_COUNT - 1, end) + 1):
        frame[index] = colour


def _scaled(colour, factor):
    return tuple(round(channel * factor) for channel in colour)


def _gauge(percent, *, width=17, start=0, from_right=False, colour=None):
    frame = [BLACK] * LED_COUNT
    if percent is None:
        return frame
    count = min(width, max(1 if percent > 0 else 0, round(percent * width / 100)))
    chosen = colour or _colour(percent)
    if from_right:
        _fill(frame, start + width - count, start + width - 1, chosen)
    else:
        _fill(frame, start, start + count - 1, chosen)
    return frame


def _duo(first, second, variant, elapsed, intro_age=None):
    frame = _gauge(first, width=8, start=0)
    right = _gauge(second, width=8, start=9, from_right=True)
    for index in range(9, 17):
        frame[index] = right[index]
    frame[8] = BLACK
    if variant == "focus":
        dim_left = int(elapsed / 1.3) % 2 == 1
        for index in list(range(8) if dim_left else range(9, 17)):
            frame[index] = _scaled(frame[index], .45)
    elif variant == "double-welcome" and intro_age is not None and intro_age < 1.4:
        left = min(8, math.ceil(intro_age * 8 / 1.4))
        right_count = min(8, math.ceil(intro_age * 8 / 1.4))
        for index in range(left, 8):
            frame[index] = BLACK
        for index in range(9, 17 - right_count):
            frame[index] = BLACK
    return frame


def controller_frame(kind, variant, elapsed, percent=74, second_percent=25, *, intro_age=None):
    """Pure renderer. Unknown battery levels never become invented percentages."""
    if kind not in VARIANTS or variant not in VARIANTS[kind]:
        raise ValueError("unknown controller signal variant")
    t = max(0.0, float(elapsed))
    frame = [BLACK] * LED_COUNT
    if kind == "duo":
        return normalize_frame(_duo(percent, second_percent, variant, t, intro_age))
    if kind == "persistent":
        frame = _gauge(percent)
        if variant == "tip" and any(frame):
            frame[max(index for index, pixel in enumerate(frame) if pixel != BLACK)] = WHITE
        elif variant == "horizon":
            frame = [_scaled(pixel, .58) for pixel in frame]
        return normalize_frame(frame)
    if t >= DURATIONS[kind]:
        return normalize_frame(frame)
    if kind == "connect":
        if t < 1.35:
            if variant == "welcome":
                step = min(3, int(t / .34))
                _fill(frame, step * 2, step * 2 + 1, CYAN)
                _fill(frame, 15 - step * 2, 16 - step * 2, CYAN)
            elif variant == "orbit":
                index = min(16, int(t / 1.35 * 17))
                frame[index] = WHITE
                if index:
                    frame[index - 1] = CYAN
            else:
                step = min(8, int(t / 1.35 * 9))
                frame[step] = CYAN
                frame[16 - step] = CYAN
        elif t < 1.65 and variant != "orbit":
            _fill(frame, 6, 10, WHITE)
        else:
            frame = _gauge(percent)
    elif kind == "low":
        if variant == "beacon" and t < 1.65 and int(t / .38) % 2 == 0:
            _fill(frame, 0, 3, RED)
            _fill(frame, 13, 16, RED)
        elif variant == "drain" and t < 1.65:
            _fill(frame, 0, 16 - int(t / 1.65 * 15), RED)
        elif variant == "heartbeat" and t < 1.7:
            bright = t % .85 < .21 or .34 < t % .85 < .54
            frame = _gauge(percent, colour=RED if bright else _scaled(RED, .35))
            if bright:
                frame[7] = RED
                frame[9] = RED
        else:
            frame = _gauge(percent, colour=RED)
    elif kind == "charging":
        frame = _gauge(percent, colour=CYAN)
        lit = [index for index, pixel in enumerate(frame) if pixel != BLACK]
        if variant == "current" and lit:
            frame[lit[int(t / .28) % len(lit)]] = WHITE
        elif variant == "breath":
            frame = [_scaled(pixel, .58 + .42 * (1 + math.sin(t * 3)) / 2) for pixel in frame]
        elif variant == "spark" and lit:
            if t < 1.9:
                frame[lit[min(len(lit) - 1, int(t / 1.9 * len(lit)))]] = WHITE
            else:
                frame[lit[-1]] = GREEN
    return normalize_frame(frame)


def _normalise_controllers(raw):
    result = {}
    if not isinstance(raw, list):
        return result
    for item in raw[:8]:
        if not isinstance(item, dict):
            continue
        identifier = str(item.get("id", ""))[:96]
        if not identifier or identifier in result:
            continue
        percent = item.get("percent")
        if isinstance(percent, bool) or not isinstance(percent, (int, float)) or not math.isfinite(percent) or not 0 <= percent <= 100:
            percent = None
        else:
            percent = round(percent)
        charging = item.get("charging")
        level = item.get("level")
        if isinstance(level, bool) or not isinstance(level, int) or not 1 <= level <= 4:
            level = None
        result[identifier] = {
            "id": identifier,
            "name": str(item.get("name") or "Controller")[:64],
            "percent": percent,
            "level": level,
            "charging": charging if isinstance(charging, bool) else None,
        }
    return result


class ControllerProvider:
    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._lock = threading.RLock()
        self._controllers = {}
        self._initialized = False
        self._active = None
        self._started_at = 0.0
        self._roster_changed_at = 0.0
        self._warned = {}

    def clear_transients(self):
        with self._lock:
            self._active = None

    def clear(self):
        with self._lock:
            self._controllers.clear()
            self._warned.clear()
            self._active = None
            self._initialized = False

    def _start(self, kind, controller, values, preview=False, variant=""):
        if values.get("mode") == "disabled":
            return False
        if not preview and not values.get("controller_alerts_enabled", False):
            return False
        selected = variant or values.get(f"controller_{kind}_variant", VARIANTS[kind][0])
        if selected not in VARIANTS[kind]:
            return False
        self._active = (kind, selected, controller, preview)
        self._started_at = self._clock()
        return True

    def update(self, raw, values, game_running=False):
        fresh = _normalise_controllers(raw)
        started_kind = None
        with self._lock:
            previous = self._controllers
            self._controllers = fresh
            if set(previous) != set(fresh):
                self._roster_changed_at = self._clock()
            for identifier in set(previous) - set(fresh):
                self._warned.pop(identifier, None)
                if self._active and self._active[2].get("id") == identifier and not self._active[3]:
                    self._active = None
            if not self._initialized:
                self._initialized = True
                return None
            policy = values.get("controller_alert_context", "both")
            allowed = policy == "both" or policy == ("game" if game_running else "home")
            if not allowed:
                return None
            threshold = values.get("controller_low_threshold", 20)
            for identifier, item in fresh.items():
                before = previous.get(identifier)
                percent = item["percent"]
                level = item["level"] if percent is None else None
                if percent is not None and percent >= threshold + 5:
                    self._warned.pop(identifier, None)
                elif level is not None and level >= 2:
                    self._warned.pop(identifier, None)
                was_low = before is not None and before["percent"] is not None and before["percent"] <= threshold
                was_low = was_low or (before is not None and before["percent"] is None and before["level"] == 1)
                low = ((percent is not None and percent <= threshold) or level == 1) and item["charging"] is not True
                if low and not was_low and identifier not in self._warned and values.get("controller_low_enabled", True):
                    self._warned[identifier] = True
                    if self._start("low", item, values):
                        started_kind = "low"
                elif before is None and started_kind != "low" and values.get("controller_connect_enabled", True):
                    if len(fresh) >= 2 and len(previous) == 1:
                        if self._start("duo", next(iter(fresh.values())), values):
                            started_kind = "duo"
                    else:
                        if self._start("connect", item, values):
                            started_kind = "connect"
                elif before is not None and started_kind != "low" and before["charging"] is False and item["charging"] is True and values.get("controller_charging_enabled", True):
                    if self._start("charging", item, values):
                        started_kind = "charging"
        return started_kind

    def preview(self, kind, values, variant=""):
        if kind not in VARIANTS:
            return False
        with self._lock:
            sample = {"id": "preview", "name": "Controller 1", "percent": 14 if kind == "low" else 38 if kind == "charging" else 74, "level": None, "charging": kind == "charging"}
            return self._start(kind, sample, values, preview=True, variant=variant)

    def cancel_for_settings(self, values, game_running=False):
        with self._lock:
            if self._active and not self._active[3]:
                kind = self._active[0]
                policy = values["controller_alert_context"]
                context_allowed = policy == "both" or policy == ("game" if game_running else "home")
                if (not values["controller_alerts_enabled"] or values["mode"] == "disabled"
                        or not context_allowed or not values.get(f"controller_{kind}_enabled", True)):
                    self._active = None

    def event_output(self):
        now = self._clock()
        with self._lock:
            if self._active is None:
                return ProviderOutput("controller", None, "no controller alert")
            kind, variant, item, preview = self._active
            elapsed = now - self._started_at
            if elapsed >= DURATIONS[kind]:
                self._active = None
                return ProviderOutput("controller", None, "controller alert ended")
            second = 25 if preview and kind == "duo" else None
            if kind == "duo" and not preview:
                others = [other for other in self._controllers.values() if other["id"] != item["id"]]
                second = _render_percent(others[0]) if others else None
            frame = controller_frame(kind, variant, elapsed, _render_percent(item), second,
                                     intro_age=elapsed if kind == "duo" else None)
            return ProviderOutput(f"controller:{kind}", frame, f"{variant} animation")

    def persistent_output(self, values, game_running=False):
        policy = values.get("controller_battery_display", "off")
        if policy == "off" or (policy == "home" and game_running):
            return ProviderOutput("controller-battery", None, "battery display disabled here")
        with self._lock:
            known = [item for item in self._controllers.values() if _render_percent(item) is not None]
            if not known:
                return ProviderOutput("controller-battery", None, "battery level unavailable")
            now = self._clock()
            if len(known) >= 2:
                variant = values.get("controller_duo_variant", "twin")
                frame = controller_frame("duo", variant, now, _render_percent(known[0]), _render_percent(known[1]),
                                         intro_age=now - self._roster_changed_at)
            else:
                variant = values.get("controller_persistent_variant", "clean")
                frame = controller_frame("persistent", variant, now, _render_percent(known[0]))
            return ProviderOutput("controller-battery", frame, "controller battery gauge")

    def status(self, values, game_running=False):
        with self._lock:
            current = list(self._controllers.values())
            active = self._active
        transient = self.event_output()
        persistent = self.persistent_output(values, game_running)
        display = transient if transient.frame is not None else persistent
        return {
            "controllers": current,
            "active": transient.frame is not None,
            "kind": active[0] if active and transient.frame is not None else "",
            "variant": active[1] if active and transient.frame is not None else "",
            "colors": [list(pixel) for pixel in display.frame] if display.frame else [],
            "persistent_available": persistent.frame is not None,
        }

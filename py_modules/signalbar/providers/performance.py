"""Local CPU/GPU metrics and compact 17-pixel meter layouts."""

from __future__ import annotations

import glob
import os
import time

from signalbar.models import LED_COUNT, PerformanceSample, ProviderOutput, normalize_frame

PALETTES = {
    "thermal": ((30, 180, 230), (245, 180, 45), (235, 45, 55)),
    "classic": ((35, 205, 95), (245, 205, 45), (235, 45, 55)),
    "icefire": ((45, 105, 245), (170, 75, 220), (245, 55, 95)),
}


def _lerp(left, right, amount):
    return int(round(left + (right - left) * amount))


def temperature_color(temp_c, cool_c=50.0, hot_c=90.0, palette="thermal"):
    cool, middle, hot = PALETTES.get(palette, PALETTES["thermal"])
    span = max(1.0, float(hot_c) - float(cool_c))
    heat = max(0.0, min(1.0, (float(temp_c) - float(cool_c)) / span))
    if heat <= 0.5:
        amount = heat * 2.0
        return tuple(_lerp(cool[index], middle[index], amount) for index in range(3))
    amount = (heat - 0.5) * 2.0
    return tuple(_lerp(middle[index], hot[index], amount) for index in range(3))


def _meter(load_percent, temp_c, count, cool_c, hot_c, palette):
    load = max(0.0, min(100.0, float(load_percent)))
    lit = max(0, min(count, int(round(count * load / 100.0))))
    color = temperature_color(temp_c, cool_c, hot_c, palette)
    return [color] * lit + [(0, 0, 0)] * (count - lit)


def performance_frame(load_percent, temp_c, cool_c=50.0, hot_c=90.0, palette="thermal"):
    return normalize_frame(_meter(load_percent, temp_c, LED_COUNT, cool_c, hot_c, palette))


def mixed_performance_frame(sample, cool_c=50.0, hot_c=90.0, palette="thermal", direction="mirrored"):
    """CPU left, black separator, GPU right with selectable direction."""
    cpu = _meter(sample.cpu_load or 0.0, sample.cpu_temp_c or cool_c, 8, cool_c, hot_c, palette)
    gpu = _meter(sample.gpu_load or 0.0, sample.gpu_temp_c or cool_c, 8, cool_c, hot_c, palette)
    if direction == "mirrored":
        gpu = list(reversed(gpu))
    return normalize_frame(cpu + [(0, 0, 0)] + gpu)


class LinuxSystemMetrics:
    def __init__(self, sys_root="/sys", proc_root="/proc"):
        self.sys_root = sys_root.rstrip("/")
        self.proc_root = proc_root.rstrip("/")
        self._previous_cpu = None

    @staticmethod
    def _read_number(path):
        try:
            with open(path, encoding="ascii") as handle:
                return float(handle.read().strip())
        except (OSError, ValueError):
            return None

    @staticmethod
    def _read_text(path):
        try:
            with open(path, encoding="ascii") as handle:
                return handle.read().strip()
        except OSError:
            return ""

    def _gpu_load(self):
        pattern = os.path.join(self.sys_root, "class/drm/card*/device/gpu_busy_percent")
        for path in sorted(glob.glob(pattern)):
            value = self._read_number(path)
            if value is not None:
                return max(0.0, min(100.0, value))
        return None

    def _gpu_temp(self):
        pattern = os.path.join(self.sys_root, "class/drm/card*/device/hwmon/hwmon*")
        for hwmon in sorted(glob.glob(pattern)):
            name = self._read_text(os.path.join(hwmon, "name")).lower()
            if name and "amd" not in name and "gpu" not in name:
                continue
            for path in sorted(glob.glob(os.path.join(hwmon, "temp*_input"))):
                value = self._read_number(path)
                if value is not None:
                    return value / 1000.0 if value > 500.0 else value
        return None

    def _cpu_load(self):
        try:
            first = self._read_text(os.path.join(self.proc_root, "stat")).splitlines()[0].split()
            if not first or first[0] != "cpu":
                return None
            values = [float(value) for value in first[1:]]
        except (IndexError, ValueError):
            return None
        total = sum(values)
        idle = (values[3] if len(values) > 3 else 0.0) + (values[4] if len(values) > 4 else 0.0)
        previous = self._previous_cpu
        self._previous_cpu = (total, idle)
        if previous is None:
            return None
        total_delta = total - previous[0]
        idle_delta = idle - previous[1]
        if total_delta <= 0:
            return None
        return max(0.0, min(100.0, 100.0 * (1.0 - idle_delta / total_delta)))

    def _cpu_temp(self):
        preferred = ("k10temp", "coretemp", "zenpower", "cpu_thermal", "acpitz")
        for hwmon in sorted(glob.glob(os.path.join(self.sys_root, "class/hwmon/hwmon*"))):
            name = self._read_text(os.path.join(hwmon, "name")).lower()
            if name and not any(token in name for token in preferred):
                continue
            candidates = []
            for path in sorted(glob.glob(os.path.join(hwmon, "temp*_input"))):
                label = self._read_text(path.replace("_input", "_label")).lower()
                priority = 0 if any(token in label for token in ("tctl", "tdie", "package")) else 1
                candidates.append((priority, path))
            for _, path in sorted(candidates):
                value = self._read_number(path)
                if value is not None:
                    return value / 1000.0 if value > 500.0 else value
        for path in sorted(glob.glob(os.path.join(self.sys_root, "class/thermal/thermal_zone*/temp"))):
            value = self._read_number(path)
            if value is not None:
                return value / 1000.0 if value > 500.0 else value
        return None

    def sample(self):
        return PerformanceSample(
            gpu_load=self._gpu_load(),
            gpu_temp_c=self._gpu_temp(),
            cpu_load=self._cpu_load(),
            cpu_temp_c=self._cpu_temp(),
            sampled_at=time.monotonic(),
        )


LinuxGpuMetrics = LinuxSystemMetrics


class PerformanceProvider:
    name = "performance"

    def __init__(self, metrics=None, interval_s=0.5, clock=time.monotonic):
        self.metrics = metrics or LinuxSystemMetrics()
        self.interval_s = max(0.5, float(interval_s))
        self._clock = clock
        self._last = PerformanceSample()
        self._next_sample_at = 0.0

    @property
    def sample(self):
        return self._last

    def output(
        self, metric="gpu", cool_c=50.0, hot_c=90.0, palette="thermal",
        direction="mirrored", enabled=True,
    ):
        now = self._clock()
        if enabled and now >= self._next_sample_at:
            self._last = self.metrics.sample()
            self._next_sample_at = now + self.interval_s
        if not enabled:
            return ProviderOutput(self.name, None, "performance disabled")
        if metric == "cpu":
            if not self._last.cpu_available:
                return ProviderOutput(self.name, None, "CPU metrics unavailable")
            frame = performance_frame(self._last.cpu_load, self._last.cpu_temp_c, cool_c, hot_c, palette)
            return ProviderOutput(self.name, frame, "CPU load and temperature")
        if metric == "mixed":
            if not (self._last.cpu_available or self._last.gpu_available):
                return ProviderOutput(self.name, None, "CPU/GPU metrics unavailable")
            frame = mixed_performance_frame(self._last, cool_c, hot_c, palette, direction)
            return ProviderOutput(self.name, frame, "CPU left, GPU right")
        if not self._last.gpu_available:
            return ProviderOutput(self.name, None, "GPU metrics unavailable")
        frame = performance_frame(self._last.gpu_load, self._last.gpu_temp_c, cool_c, hot_c, palette)
        return ProviderOutput(self.name, frame, "GPU load and temperature")

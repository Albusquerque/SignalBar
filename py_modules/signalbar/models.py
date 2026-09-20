"""Shared immutable models for the provider/arbiter/renderer pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

RGB = Tuple[int, int, int]
Frame = Tuple[RGB, ...]
LED_COUNT = 17


def normalize_frame(values) -> Frame:
    """Validate and clamp an arbitrary RGB sequence to exactly 17 pixels."""
    if not isinstance(values, (list, tuple)) or len(values) != LED_COUNT:
        raise ValueError(f"a frame must contain exactly {LED_COUNT} RGB pixels")
    out = []
    for pixel in values:
        if not isinstance(pixel, (list, tuple)) or len(pixel) != 3:
            raise ValueError("each pixel must contain exactly three channels")
        channels = []
        for channel in pixel:
            value = int(round(float(channel)))
            channels.append(max(0, min(255, value)))
        out.append(tuple(channels))
    return tuple(out)


@dataclass(frozen=True)
class GameState:
    appid: int = 0
    title: str = ""

    @property
    def running(self) -> bool:
        return self.appid > 0 or bool(self.title)


@dataclass(frozen=True)
class PerformanceSample:
    gpu_load: Optional[float] = None
    gpu_temp_c: Optional[float] = None
    cpu_load: Optional[float] = None
    cpu_temp_c: Optional[float] = None
    sampled_at: float = 0.0

    @property
    def gpu_available(self) -> bool:
        return self.gpu_load is not None and self.gpu_temp_c is not None

    @property
    def cpu_available(self) -> bool:
        return self.cpu_load is not None and self.cpu_temp_c is not None

    @property
    def available(self) -> bool:
        return self.gpu_available


@dataclass(frozen=True)
class ProviderOutput:
    provider: str
    frame: Optional[Frame]
    reason: str

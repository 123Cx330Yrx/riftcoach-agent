from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PollingPolicy:
    initial_delay_s: float = 0.1
    maximum_delay_s: float = 2.0
    multiplier: float = 2.0
    jitter_ratio: float = 0.2

    def __post_init__(self) -> None:
        values = {
            "initial_delay_s": self.initial_delay_s,
            "maximum_delay_s": self.maximum_delay_s,
            "multiplier": self.multiplier,
            "jitter_ratio": self.jitter_ratio,
        }
        for name, value in values.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be a finite number")
            if not math.isfinite(float(value)):
                raise ValueError(f"{name} must be finite")
        if self.initial_delay_s <= 0:
            raise ValueError("initial_delay_s must be greater than zero")
        if self.maximum_delay_s < self.initial_delay_s:
            raise ValueError(
                "maximum_delay_s must be greater than or equal to initial_delay_s"
            )
        if self.multiplier < 1:
            raise ValueError("multiplier must be greater than or equal to one")
        if not 0 <= self.jitter_ratio < 1:
            raise ValueError("jitter_ratio must be in the range [0, 1)")

    def delay_for_idle(self, *, idle_count: int, jitter_unit: float) -> float:
        if isinstance(idle_count, bool) or not isinstance(idle_count, int):
            raise TypeError("idle_count must be an integer")
        if idle_count < 1:
            raise ValueError("idle_count must be greater than zero")
        if isinstance(jitter_unit, bool) or not isinstance(jitter_unit, (int, float)):
            raise TypeError("jitter_unit must be a finite number")
        if not math.isfinite(float(jitter_unit)) or not 0 <= jitter_unit <= 1:
            raise ValueError("jitter_unit must be in the range [0, 1]")

        try:
            exponential = self.initial_delay_s * (
                self.multiplier ** (idle_count - 1)
            )
        except OverflowError:
            exponential = self.maximum_delay_s
        base = min(self.maximum_delay_s, exponential)
        lower = base * (1 - self.jitter_ratio)
        upper = min(
            self.maximum_delay_s,
            base * (1 + self.jitter_ratio),
        )
        return float(lower + ((upper - lower) * jitter_unit))


__all__ = ["PollingPolicy"]

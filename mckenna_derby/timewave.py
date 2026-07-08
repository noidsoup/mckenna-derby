"""Timewave Zero — Python port of Peter Meyer's public-domain algorithm.

The timewave is a fractal function built from a set of 384 numbers derived
from the King Wen sequence of I Ching hexagrams. Lower values = higher
"novelty" in McKenna's terminology; higher values = more "habit".

Ported from twz-point.c (Peter Meyer / John A. Phelps, public domain,
https://github.com/kl4yfd/timewave_z3r0).

Note: McKenna's wave is only defined *before* the zero date (conventionally
2012-12-21). For dates after the zero point we return the value at the
mirrored distance |days_to_zero| so modern race data can still be scored;
this extension is ours, not McKenna's, and is flagged via `mirrored=True`.
"""

from __future__ import annotations

import datetime as dt
import math
from importlib import resources

NUM_DATA_POINTS = 384
DEFAULT_WAVE_FACTOR = 64
CALC_PREC = 1_000_000
ZERO_DATE = dt.date(2012, 12, 21)

#: Available 384-number sets, in the same order as the original software.
NUMBER_SETS = ("kelley", "watkins", "sheliak", "huangti")


def _load_number_set(name: str) -> list[int]:
    if name not in NUMBER_SETS:
        raise ValueError(f"unknown number set {name!r}; choose from {NUMBER_SETS}")
    text = resources.files("mckenna_derby.wavesets").joinpath(f"{name}.txt").read_text()
    values = [int(tok) for tok in text.replace(",", " ").split()]
    if len(values) != NUM_DATA_POINTS:
        raise ValueError(f"{name}: expected {NUM_DATA_POINTS} values, got {len(values)}")
    return values


class Timewave:
    """Evaluate the timewave for a given 384-number set and wave factor."""

    def __init__(self, number_set: str = "kelley", wave_factor: int = DEFAULT_WAVE_FACTOR):
        if not (2 <= wave_factor <= 10_000):
            raise ValueError("wave_factor must be in [2, 10000]")
        self.number_set = number_set
        self.wave_factor = wave_factor
        self.w = _load_number_set(number_set)
        # Direct port of set_powers(); 64 powers is what the original used.
        self.powers = [float(wave_factor) ** j for j in range(64)]

    def _v(self, y: float) -> float:
        """Piecewise-linear interpolation through the 384 data points."""
        i = int(math.fmod(y, NUM_DATA_POINTS))
        j = (i + 1) % NUM_DATA_POINTS
        z = y - math.floor(y)
        if z == 0.0:
            return float(self.w[i])
        return (self.w[j] - self.w[i]) * z + self.w[i]

    def value_at_days_to_zero(self, x: float) -> float:
        """Timewave value `x` days before the zero point (Meyer's f(x))."""
        if x < 0:
            raise ValueError("x must be >= 0 (days before the zero point)")
        if x == 0:
            return 0.0
        total = 0.0
        i = 0
        while x >= self.powers[i]:
            total += self._v(x / self.powers[i]) * self.powers[i]
            i += 1
        i = 0
        last = 0.0
        while True:
            i += 1
            if i > CALC_PREC + 2:
                break
            last = total
            total += self._v(x * self.powers[i]) / self.powers[i]
            if total != 0.0 and total <= last:
                break
        return total / self.powers[3]

    def value_on(self, date: dt.date, zero_date: dt.date = ZERO_DATE) -> tuple[float, bool]:
        """Timewave value on a calendar date.

        Returns (value, mirrored) where mirrored=True indicates the date is
        after the zero point and the symmetric extension was used.
        """
        days = (zero_date - date).days
        mirrored = days < 0
        return self.value_at_days_to_zero(abs(days)), mirrored

    def series(self, start: dt.date, end: dt.date, step_days: int = 1):
        """Yield (date, value) pairs from start to end inclusive."""
        d = start
        while d <= end:
            yield d, self.value_on(d)[0]
            d += dt.timedelta(days=step_days)

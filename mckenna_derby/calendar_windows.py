"""Upcoming high-novelty (low-wave) calendar windows from Timewave Zero.

Calls the frozen ``timewave.Timewave`` API and the same causal expanding-
percentile day filter used by ``backtest.causal_select_mask``. Does **not**
rewrite wave math.

Resolution
==========
Peter Meyer's timewave is evaluated on **calendar dates** (one value per
day). There is no honest hourly / intra-day precision in this codebase —
``Timewave.value_on`` takes a ``date``, and ``series`` steps by whole days.
If someone asks "Friday 5–8pm", the honest answer is: we can say whether
**that Friday** is in the high-novelty zone, not which hours.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd

from .backtest import causal_select_mask, default_min_history, expanding_percentile_thresholds
from .timewave import DEFAULT_WAVE_FACTOR, Timewave

# Honest UI copy: do not claim hourly windows.
RESOLUTION_NOTE = (
    "The timewave here is **daily** (one value per calendar day). "
    "We cannot honestly mark hours like \"Friday 5–8\" — only whole days."
)

DEFAULT_HORIZON_DAYS = 60
DEFAULT_LOOKBACK_DAYS = 365


def upcoming_novelty_windows(
    *,
    start: dt.date | None = None,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    number_set: str = "kelley",
    threshold_pct: float = 20.0,
    wave_factor: int = DEFAULT_WAVE_FACTOR,
    min_history: int | None = None,
) -> pd.DataFrame:
    """List upcoming days with wave value and causal bet-zone flag.

    Parameters
    ----------
    start
        First day of the *upcoming* window (inclusive). Defaults to today.
    horizon_days
        How many days ahead to list (inclusive of ``start``).
    lookback_days
        Past days before ``start`` used to warm the expanding percentile
        (same causal rule as the backtest).
    number_set
        I Ching number table (prereg default: ``kelley``).
    threshold_pct
        Lowest X% of the wave = high-novelty / bet zone (prereg: 20).
    wave_factor
        Timewave fractal factor (default 64).
    min_history
        Warm-up length for the causal mask; defaults to
        :func:`backtest.default_min_history`.

    Returns
    -------
    DataFrame with columns:
        ``date``, ``wave_value``, ``threshold``, ``in_bet_zone``, ``mirrored``
    Only rows from ``start`` through ``start + horizon_days - 1`` are kept
    (history is used for the threshold, then dropped).
    """
    if horizon_days < 1:
        raise ValueError("horizon_days must be >= 1")
    if lookback_days < 0:
        raise ValueError("lookback_days must be >= 0")
    if not (0.0 <= float(threshold_pct) <= 100.0):
        raise ValueError("threshold_pct must be in [0, 100]")

    start = start or dt.date.today()
    hist_start = start - dt.timedelta(days=lookback_days)
    end = start + dt.timedelta(days=horizon_days - 1)

    tw = Timewave(number_set=number_set, wave_factor=wave_factor)
    rows: list[dict] = []
    d = hist_start
    while d <= end:
        value, mirrored = tw.value_on(d)
        rows.append(
            {
                "date": d,
                "wave_value": float(value),
                "mirrored": bool(mirrored),
            }
        )
        d += dt.timedelta(days=1)
    full = pd.DataFrame(rows)
    if full.empty:
        return pd.DataFrame(
            columns=["date", "wave_value", "threshold", "in_bet_zone", "mirrored"]
        )

    series = full.set_index("date")["wave_value"].sort_index()
    mh = default_min_history(len(series)) if min_history is None else int(min_history)
    mask = causal_select_mask(series, float(threshold_pct), min_history=mh, side="low")
    thresholds = expanding_percentile_thresholds(
        series.to_numpy(dtype=float), float(threshold_pct), mh
    )
    full = full.sort_values("date").reset_index(drop=True)
    full["threshold"] = thresholds
    full["in_bet_zone"] = mask.reindex(full["date"]).to_numpy(dtype=bool)

    upcoming = full[full["date"] >= start].copy()
    upcoming = upcoming.reset_index(drop=True)
    return upcoming[
        ["date", "wave_value", "threshold", "in_bet_zone", "mirrored"]
    ]


def bet_zone_days(windows: pd.DataFrame) -> list[dt.date]:
    """Return dates flagged ``in_bet_zone`` from an upcoming-windows frame."""
    if windows is None or windows.empty or "in_bet_zone" not in windows.columns:
        return []
    return [d for d, flag in zip(windows["date"], windows["in_bet_zone"]) if bool(flag)]


def format_window_rows(windows: pd.DataFrame) -> pd.DataFrame:
    """Human-facing table: date, wave, threshold, bet-zone label."""
    if windows is None or windows.empty:
        return pd.DataFrame(
            columns=["Date", "Wave value", "Cutoff", "Bet zone?"]
        )
    out = pd.DataFrame(
        {
            "Date": [d.isoformat() if hasattr(d, "isoformat") else str(d) for d in windows["date"]],
            "Wave value": [f"{v:.6f}" for v in windows["wave_value"]],
            "Cutoff": [
                "—" if pd.isna(t) else f"{float(t):.6f}" for t in windows["threshold"]
            ],
            "Bet zone?": [
                "Yes — high novelty (low wave)" if bool(z) else "No"
                for z in windows["in_bet_zone"]
            ],
        }
    )
    return out

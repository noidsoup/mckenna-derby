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
from typing import Iterable

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


def payout_settlement_summary(payout_sources: Iterable[str] | dict) -> dict:
    """Summarize actual vs modeled trifecta settlement for UI captions.

    Accepts either a sequence of ``payout_source`` labels or a
    ``value_counts()``-style dict.
    """
    if isinstance(payout_sources, dict):
        counts = {str(k): int(v) for k, v in payout_sources.items()}
    else:
        counts: dict[str, int] = {}
        for src in payout_sources:
            key = str(src)
            counts[key] = counts.get(key, 0) + 1

    n_actual = int(counts.get("actual", 0))
    n_modeled = int(counts.get("modeled", 0))
    n_total = n_actual + n_modeled + sum(
        v for k, v in counts.items() if k not in ("actual", "modeled")
    )

    if n_actual > 0 and n_modeled == 0 and n_total == n_actual:
        mode = "cash"
        label = "Cash dividends"
        detail = (
            f"All {n_actual:,} races settled with real `trifecta_payout` "
            "(cash dividends)."
        )
    elif n_actual > 0 and n_modeled > 0:
        mode = "mixed"
        label = "Mixed: cash + modeled"
        detail = (
            f"{n_actual:,} races with **cash dividends**; "
            f"{n_modeled:,} with **modeled payouts** (no real trifecta file for those)."
        )
    else:
        mode = "modeled"
        label = "Modeled payouts (no real trifecta file)"
        detail = (
            f"All {n_modeled or n_total:,} races use modeled parimutuel payouts "
            "(no real trifecta dividends attached)."
        )

    return {
        "mode": mode,
        "label": label,
        "detail": detail,
        "n_actual": n_actual,
        "n_modeled": n_modeled,
        "n_total": n_total,
        "counts": counts,
    }


HOW_TO_ADD_DIVIDENDS = """
**No cash trifecta dividends in this run.** Settlement is **modeled**
(expected return ≈ −track cut when there is no edge).

To attach real ordered 1-2-3 dividends when you have them:

1. Build a companion CSV like `mckenna_derby/datasets/exotic_dividends.example.csv`
   with `race_id` + `trifecta_payout` (per $1 stake).
2. Rebuild: `python scripts/build_bundled_data.py --exotics path/to/exotic_dividends.csv`
3. See `mckenna_derby/datasets/README.md` for the schema (and optional Renavon remap).

Until then, treat trifecta P&L as a timing/model exercise — not cash settlement.
""".strip()

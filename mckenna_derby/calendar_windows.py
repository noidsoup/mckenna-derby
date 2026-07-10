"""Upcoming high-novelty (low-wave) calendar windows from Timewave Zero.

Calls the frozen ``timewave.Timewave`` API and the same causal expanding-
percentile filter used by ``backtest.causal_select_mask``. Does **not**
rewrite wave math.

Resolution
==========
``Timewave.value_on`` is date-only, but the underlying Meyer function
``value_at_days_to_zero(x)`` accepts a **fractional** day count. This module
samples that API at hourly civil timestamps (default timezone
``America/Los_Angeles``) and collapses contiguous bet-zone hours into
display windows such as ``Fri Jul 11, 5:00–8:00 PM``.

The locked historical claim remains day-level (prereg / race dates). Hourly
windows are a calendar convenience for *upcoming* moments only.
"""

from __future__ import annotations

import datetime as dt
from typing import Iterable
from zoneinfo import ZoneInfo

import pandas as pd

from .backtest import causal_select_mask, default_min_history, expanding_percentile_thresholds
from .timewave import DEFAULT_WAVE_FACTOR, ZERO_DATE, Timewave

# Default display / sampling timezone for upcoming hour windows.
DEFAULT_TIMEZONE = "America/Los_Angeles"

RESOLUTION_NOTE = (
    "Upcoming windows are sampled **hourly** in "
    f"**{DEFAULT_TIMEZONE}** (Pacific), using fractional days into the "
    "classic Timewave function. Contiguous high-novelty hours are collapsed "
    "(e.g. Fri Jul 11, 5:00–8:00 PM). The locked backtest claim stays "
    "day-level; this is a calendar preview only."
)

DEFAULT_HORIZON_DAYS = 60
DEFAULT_LOOKBACK_DAYS = 365


def wave_at_datetime(
    tw: Timewave,
    when: dt.datetime,
    zero_date: dt.date = ZERO_DATE,
) -> tuple[float, bool]:
    """Evaluate Timewave at a civil datetime via fractional days.

    Thin wrapper around ``Timewave.value_at_days_to_zero`` — does not change
    the frozen core. Naive ``when`` is treated as a wall-clock civil time;
    aware ``when`` is converted to naive wall clock in its own timezone
    (same calendar arithmetic as ``value_on`` at midnight of that date).
    """
    if when.tzinfo is not None:
        when_naive = when.replace(tzinfo=None)
    else:
        when_naive = when
    zero_dt = dt.datetime.combine(zero_date, dt.time.min)
    delta_days = (zero_dt - when_naive).total_seconds() / 86400.0
    mirrored = delta_days < 0.0
    return tw.value_at_days_to_zero(abs(delta_days)), mirrored


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
    """List upcoming **days** with wave value and causal bet-zone flag.

    Day-level helper (one sample at local midnight / calendar date via
    ``Timewave.value_on``). Prefer :func:`upcoming_novelty_hours` +
    :func:`collapse_contiguous_windows` for the dashboard hour list.
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


def upcoming_novelty_hours(
    *,
    start: dt.date | dt.datetime | None = None,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    number_set: str = "kelley",
    threshold_pct: float = 20.0,
    wave_factor: int = DEFAULT_WAVE_FACTOR,
    min_history: int | None = None,
    timezone: str = DEFAULT_TIMEZONE,
) -> pd.DataFrame:
    """Scan upcoming hours for high-novelty (low-wave) bet-zone flags.

    Samples ``wave_at_datetime`` every hour in ``timezone``, warms the
    causal expanding-percentile cutoff with ``lookback_days`` of past hours,
    and returns only rows from ``start`` forward.

    Returns
    -------
    DataFrame columns:
        ``timestamp``, ``wave_value``, ``threshold``, ``in_bet_zone``,
        ``mirrored``, ``timezone``
    """
    if horizon_days < 1:
        raise ValueError("horizon_days must be >= 1")
    if lookback_days < 0:
        raise ValueError("lookback_days must be >= 0")
    if not (0.0 <= float(threshold_pct) <= 100.0):
        raise ValueError("threshold_pct must be in [0, 100]")

    tz = ZoneInfo(timezone)
    if start is None:
        start_local = dt.datetime.now(tz=tz).replace(minute=0, second=0, microsecond=0)
    elif isinstance(start, dt.datetime):
        if start.tzinfo is None:
            start_local = start.replace(tzinfo=tz, minute=0, second=0, microsecond=0)
        else:
            start_local = start.astimezone(tz).replace(minute=0, second=0, microsecond=0)
    else:
        start_local = dt.datetime.combine(start, dt.time.min, tzinfo=tz)

    hist_start = start_local - dt.timedelta(days=lookback_days)
    end_local = start_local + dt.timedelta(days=horizon_days) - dt.timedelta(hours=1)

    tw = Timewave(number_set=number_set, wave_factor=wave_factor)
    rows: list[dict] = []
    cursor = hist_start
    step = dt.timedelta(hours=1)
    while cursor <= end_local:
        value, mirrored = wave_at_datetime(tw, cursor)
        rows.append(
            {
                "timestamp": cursor,
                "wave_value": float(value),
                "mirrored": bool(mirrored),
                "timezone": timezone,
            }
        )
        cursor += step

    full = pd.DataFrame(rows)
    empty_cols = [
        "timestamp",
        "wave_value",
        "threshold",
        "in_bet_zone",
        "mirrored",
        "timezone",
    ]
    if full.empty:
        return pd.DataFrame(columns=empty_cols)

    series = full.set_index("timestamp")["wave_value"].sort_index()
    mh = default_min_history(len(series)) if min_history is None else int(min_history)
    mask = causal_select_mask(series, float(threshold_pct), min_history=mh, side="low")
    thresholds = expanding_percentile_thresholds(
        series.to_numpy(dtype=float), float(threshold_pct), mh
    )
    full = full.sort_values("timestamp").reset_index(drop=True)
    full["threshold"] = thresholds
    full["in_bet_zone"] = mask.reindex(full["timestamp"]).to_numpy(dtype=bool)

    upcoming = full[full["timestamp"] >= start_local].copy().reset_index(drop=True)
    return upcoming[empty_cols]


def format_hour_window_label(
    start: dt.datetime,
    end_exclusive: dt.datetime,
) -> str:
    """Human label for ``[start, end_exclusive)`` in local wall time.

    Examples
    --------
    - Fri Jul 11, 5:00–8:00 PM  (same calendar day)
    - Fri Jul 11, 10:00 PM – Sat Jul 12, 2:00 AM  (cross midnight)
    """
    if start.tzinfo is not None:
        start = start.replace(tzinfo=None)
    if end_exclusive.tzinfo is not None:
        end_exclusive = end_exclusive.replace(tzinfo=None)

    # %-d / %-I are POSIX; fall back for platforms that reject them.
    def _fmt_day(d: dt.datetime) -> str:
        try:
            return d.strftime("%a %b %-d")
        except ValueError:
            return d.strftime("%a %b %d").replace(" 0", " ")

    def _fmt_time(d: dt.datetime) -> str:
        try:
            return d.strftime("%-I:%M %p")
        except ValueError:
            return d.strftime("%I:%M %p").lstrip("0")

    last_included = end_exclusive - dt.timedelta(microseconds=1)
    same_day = start.date() == last_included.date()
    # end_exclusive is the first hour *after* the run (e.g. 5–8 PM → ends 8:00).
    if same_day:
        return f"{_fmt_day(start)}, {_fmt_time(start)}–{_fmt_time(end_exclusive)}"
    return (
        f"{_fmt_day(start)}, {_fmt_time(start)} – "
        f"{_fmt_day(end_exclusive)}, {_fmt_time(end_exclusive)}"
    )


def collapse_contiguous_windows(
    hours: pd.DataFrame,
    *,
    only_bet_zone: bool = True,
) -> pd.DataFrame:
    """Collapse contiguous hourly bet-zone rows into display windows.

    A run of hours ``h, h+1, …, h+k`` becomes one row with
    ``start=h``, ``end_exclusive=h+k+1``, and a friendly ``label``.
    """
    cols = [
        "start",
        "end_exclusive",
        "label",
        "n_hours",
        "wave_min",
        "wave_mean",
        "timezone",
    ]
    if hours is None or hours.empty:
        return pd.DataFrame(columns=cols)

    frame = hours.sort_values("timestamp").reset_index(drop=True)
    if only_bet_zone:
        if "in_bet_zone" not in frame.columns:
            return pd.DataFrame(columns=cols)
        frame = frame[frame["in_bet_zone"]].reset_index(drop=True)
    if frame.empty:
        return pd.DataFrame(columns=cols)

    windows: list[dict] = []
    run_start_idx = 0
    for i in range(1, len(frame) + 1):
        boundary = i == len(frame)
        if not boundary:
            prev = frame.loc[i - 1, "timestamp"]
            cur = frame.loc[i, "timestamp"]
            gap = cur - prev
            contiguous = gap == dt.timedelta(hours=1)
        else:
            contiguous = False
        if boundary or not contiguous:
            chunk = frame.iloc[run_start_idx:i]
            start = chunk.iloc[0]["timestamp"]
            last = chunk.iloc[-1]["timestamp"]
            end_exclusive = last + dt.timedelta(hours=1)
            tz_name = str(chunk.iloc[0].get("timezone", DEFAULT_TIMEZONE))
            windows.append(
                {
                    "start": start,
                    "end_exclusive": end_exclusive,
                    "label": format_hour_window_label(start, end_exclusive),
                    "n_hours": int(len(chunk)),
                    "wave_min": float(chunk["wave_value"].min()),
                    "wave_mean": float(chunk["wave_value"].mean()),
                    "timezone": tz_name,
                }
            )
            run_start_idx = i

    return pd.DataFrame(windows, columns=cols)


def bet_zone_days(windows: pd.DataFrame) -> list[dt.date]:
    """Return dates flagged ``in_bet_zone`` from a daily upcoming-windows frame."""
    if windows is None or windows.empty or "in_bet_zone" not in windows.columns:
        return []
    return [d for d, flag in zip(windows["date"], windows["in_bet_zone"]) if bool(flag)]


def format_window_rows(windows: pd.DataFrame) -> pd.DataFrame:
    """Human-facing table for daily or collapsed hourly windows."""
    if windows is None or windows.empty:
        return pd.DataFrame(columns=["Window", "Wave value", "Cutoff", "Bet zone?"])

    # Collapsed hourly windows
    if "label" in windows.columns and "start" in windows.columns:
        return pd.DataFrame(
            {
                "Window": list(windows["label"]),
                "Hours": [int(n) for n in windows["n_hours"]],
                "Wave (min)": [f"{v:.6f}" for v in windows["wave_min"]],
                "Wave (mean)": [f"{v:.6f}" for v in windows["wave_mean"]],
                "Timezone": list(windows["timezone"]),
            }
        )

    # Daily rows
    if "date" in windows.columns:
        return pd.DataFrame(
            {
                "Date": [
                    d.isoformat() if hasattr(d, "isoformat") else str(d)
                    for d in windows["date"]
                ],
                "Wave value": [f"{v:.6f}" for v in windows["wave_value"]],
                "Cutoff": [
                    "—" if pd.isna(t) else f"{float(t):.6f}"
                    for t in windows["threshold"]
                ],
                "Bet zone?": [
                    "Yes — high novelty (low wave)" if bool(z) else "No"
                    for z in windows["in_bet_zone"]
                ],
            }
        )

    # Raw hourly rows
    if "timestamp" in windows.columns:
        return pd.DataFrame(
            {
                "Hour": [
                    ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
                    for ts in windows["timestamp"]
                ],
                "Wave value": [f"{v:.6f}" for v in windows["wave_value"]],
                "Cutoff": [
                    "—" if pd.isna(t) else f"{float(t):.6f}"
                    for t in windows["threshold"]
                ],
                "Bet zone?": [
                    "Yes — high novelty (low wave)" if bool(z) else "No"
                    for z in windows["in_bet_zone"]
                ],
            }
        )

    return pd.DataFrame(columns=["Window", "Wave value", "Cutoff", "Bet zone?"])


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

"""Tests for upcoming high-novelty calendar windows (hourly + daily)."""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from mckenna_derby.calendar_windows import (
    DEFAULT_TIMEZONE,
    HOW_TO_ADD_DIVIDENDS,
    RESOLUTION_NOTE,
    bet_zone_days,
    collapse_contiguous_windows,
    format_hour_window_label,
    format_window_rows,
    payout_settlement_summary,
    upcoming_novelty_hours,
    upcoming_novelty_windows,
    wave_at_datetime,
)
from mckenna_derby.timewave import Timewave


def test_resolution_note_is_hourly():
    assert "hourly" in RESOLUTION_NOTE.lower()
    assert DEFAULT_TIMEZONE in RESOLUTION_NOTE
    assert "America/Los_Angeles" in RESOLUTION_NOTE


def test_wave_at_datetime_matches_value_on_at_midnight():
    tw = Timewave(number_set="kelley")
    day = dt.date(2010, 3, 15)
    expected, mirrored = tw.value_on(day)
    got, got_m = wave_at_datetime(tw, dt.datetime.combine(day, dt.time.min))
    assert got == pytest.approx(expected)
    assert bool(got_m) is bool(mirrored)


def test_wave_at_datetime_varies_within_day():
    tw = Timewave(number_set="kelley")
    day = dt.date(2024, 7, 12)
    v0, _ = wave_at_datetime(tw, dt.datetime.combine(day, dt.time(0, 0)))
    v17, _ = wave_at_datetime(tw, dt.datetime.combine(day, dt.time(17, 0)))
    assert v0 != pytest.approx(v17, abs=1e-12)


def test_upcoming_windows_shape_and_columns():
    start = dt.date(2024, 6, 1)
    df = upcoming_novelty_windows(
        start=start,
        horizon_days=14,
        lookback_days=60,
        number_set="kelley",
        threshold_pct=20.0,
        min_history=10,
    )
    assert list(df.columns) == [
        "date",
        "wave_value",
        "threshold",
        "in_bet_zone",
        "mirrored",
    ]
    assert len(df) == 14
    assert df["date"].iloc[0] == start
    assert df["date"].iloc[-1] == start + dt.timedelta(days=13)
    assert df["wave_value"].notna().all()
    assert df["in_bet_zone"].dtype == bool


def test_upcoming_windows_matches_timewave_api():
    start = dt.date(2010, 3, 15)
    tw = Timewave(number_set="kelley")
    df = upcoming_novelty_windows(
        start=start,
        horizon_days=5,
        lookback_days=40,
        number_set="kelley",
        threshold_pct=50.0,
        min_history=5,
    )
    for _, row in df.iterrows():
        expected, mirrored = tw.value_on(row["date"])
        assert row["wave_value"] == pytest.approx(expected)
        assert bool(row["mirrored"]) is bool(mirrored)


def test_bet_zone_uses_low_wave_causal_rule():
    """With enough history, a day at/below the expanding past percentile is selected."""
    start = dt.date(2005, 1, 1)
    df = upcoming_novelty_windows(
        start=start,
        horizon_days=30,
        lookback_days=90,
        number_set="kelley",
        threshold_pct=20.0,
        min_history=30,
    )
    zone = bet_zone_days(df)
    assert isinstance(zone, list)
    for _, row in df[df["in_bet_zone"]].iterrows():
        assert row["wave_value"] <= row["threshold"] + 1e-12
    for _, row in df[~df["in_bet_zone"]].iterrows():
        if pd.notna(row["threshold"]):
            assert row["wave_value"] > row["threshold"] - 1e-12


def test_upcoming_hours_shape_and_timezone():
    tz = ZoneInfo(DEFAULT_TIMEZONE)
    start = dt.datetime(2024, 6, 1, 0, 0, tzinfo=tz)
    df = upcoming_novelty_hours(
        start=start,
        horizon_days=2,
        lookback_days=5,
        number_set="kelley",
        threshold_pct=20.0,
        min_history=24,
        timezone=DEFAULT_TIMEZONE,
    )
    assert list(df.columns) == [
        "timestamp",
        "wave_value",
        "threshold",
        "in_bet_zone",
        "mirrored",
        "timezone",
    ]
    assert len(df) == 48  # 2 days × 24 hours
    assert df["timestamp"].iloc[0] == start
    assert (df["timezone"] == DEFAULT_TIMEZONE).all()
    assert df["wave_value"].notna().all()


def test_upcoming_hours_matches_wave_at_datetime():
    tz = ZoneInfo(DEFAULT_TIMEZONE)
    start = dt.datetime(2010, 3, 15, 0, 0, tzinfo=tz)
    tw = Timewave(number_set="kelley")
    df = upcoming_novelty_hours(
        start=start,
        horizon_days=1,
        lookback_days=2,
        number_set="kelley",
        threshold_pct=50.0,
        min_history=5,
        timezone=DEFAULT_TIMEZONE,
    )
    for _, row in df.iterrows():
        expected, mirrored = wave_at_datetime(tw, row["timestamp"])
        assert row["wave_value"] == pytest.approx(expected)
        assert bool(row["mirrored"]) is bool(mirrored)


def test_format_hour_window_label_same_day():
    start = dt.datetime(2026, 7, 11, 17, 0)  # Sat Jul 11, 5 PM
    end = dt.datetime(2026, 7, 11, 20, 0)  # exclusive → through 8 PM
    label = format_hour_window_label(start, end)
    assert "Jul 11" in label or "Jul 11" in label.replace("  ", " ")
    assert "5:00" in label
    assert "8:00" in label
    assert "PM" in label


def test_format_hour_window_label_cross_midnight():
    start = dt.datetime(2026, 7, 11, 22, 0)
    end = dt.datetime(2026, 7, 12, 2, 0)
    label = format_hour_window_label(start, end)
    assert "Jul 11" in label
    assert "Jul 12" in label


def test_collapse_contiguous_windows_merges_hours():
    tz_name = DEFAULT_TIMEZONE
    tz = ZoneInfo(tz_name)
    base = dt.datetime(2026, 7, 11, 17, 0, tzinfo=tz)  # 5 PM
    rows = []
    # 5, 6, 7 PM in zone; gap; 9 PM in zone
    for h in (0, 1, 2, 4):
        rows.append(
            {
                "timestamp": base + dt.timedelta(hours=h),
                "wave_value": 0.01 - 0.0001 * h,
                "threshold": 0.02,
                "in_bet_zone": True,
                "mirrored": True,
                "timezone": tz_name,
            }
        )
    # one out-of-zone hour between runs should not appear
    hours = pd.DataFrame(rows)
    collapsed = collapse_contiguous_windows(hours, only_bet_zone=True)
    assert len(collapsed) == 2
    assert int(collapsed.iloc[0]["n_hours"]) == 3
    assert int(collapsed.iloc[1]["n_hours"]) == 1
    assert collapsed.iloc[0]["start"] == base
    assert collapsed.iloc[0]["end_exclusive"] == base + dt.timedelta(hours=3)
    label0 = collapsed.iloc[0]["label"]
    assert "5:00" in label0 and "8:00" in label0


def test_collapse_skips_non_zone_hours():
    tz = ZoneInfo(DEFAULT_TIMEZONE)
    t0 = dt.datetime(2026, 7, 11, 12, 0, tzinfo=tz)
    hours = pd.DataFrame(
        [
            {
                "timestamp": t0,
                "wave_value": 0.05,
                "threshold": 0.02,
                "in_bet_zone": False,
                "mirrored": True,
                "timezone": DEFAULT_TIMEZONE,
            },
            {
                "timestamp": t0 + dt.timedelta(hours=1),
                "wave_value": 0.01,
                "threshold": 0.02,
                "in_bet_zone": True,
                "mirrored": True,
                "timezone": DEFAULT_TIMEZONE,
            },
        ]
    )
    collapsed = collapse_contiguous_windows(hours, only_bet_zone=True)
    assert len(collapsed) == 1
    assert collapsed.iloc[0]["start"] == t0 + dt.timedelta(hours=1)
    assert int(collapsed.iloc[0]["n_hours"]) == 1


def test_format_window_rows_daily_labels():
    raw = upcoming_novelty_windows(
        start=dt.date(2011, 1, 1),
        horizon_days=7,
        lookback_days=40,
        min_history=10,
    )
    pretty = format_window_rows(raw)
    assert list(pretty.columns) == ["Date", "Wave value", "Cutoff", "Bet zone?"]
    assert len(pretty) == 7
    assert pretty["Bet zone?"].isin(
        ["Yes — high novelty (low wave)", "No"]
    ).all()


def test_format_window_rows_collapsed():
    start = dt.datetime(2026, 7, 11, 17, 0, tzinfo=ZoneInfo(DEFAULT_TIMEZONE))
    hours = pd.DataFrame(
        [
            {
                "timestamp": start + dt.timedelta(hours=i),
                "wave_value": 0.01,
                "threshold": 0.02,
                "in_bet_zone": True,
                "mirrored": True,
                "timezone": DEFAULT_TIMEZONE,
            }
            for i in range(3)
        ]
    )
    collapsed = collapse_contiguous_windows(hours)
    pretty = format_window_rows(collapsed)
    assert "Window" in pretty.columns
    assert len(pretty) == 1


def test_payout_settlement_summary_modes():
    cash = payout_settlement_summary(["actual", "actual"])
    assert cash["mode"] == "cash"
    assert cash["label"] == "Cash dividends"
    assert cash["n_actual"] == 2

    modeled = payout_settlement_summary({"modeled": 10})
    assert modeled["mode"] == "modeled"
    assert "Modeled payouts" in modeled["label"]
    assert modeled["n_modeled"] == 10

    mixed = payout_settlement_summary({"actual": 3, "modeled": 7})
    assert mixed["mode"] == "mixed"
    assert "cash" in mixed["label"].lower()
    assert mixed["n_actual"] == 3 and mixed["n_modeled"] == 7


def test_how_to_add_dividends_points_at_example():
    assert "exotic_dividends.example.csv" in HOW_TO_ADD_DIVIDENDS
    assert "build_bundled_data.py --exotics" in HOW_TO_ADD_DIVIDENDS


def test_friday_5_to_8_label_example():
    """Document the display shape for a Fri 5–8 PM window."""
    # 2026-07-10 is a Friday
    start = dt.datetime(2026, 7, 10, 17, 0)
    end = dt.datetime(2026, 7, 10, 20, 0)
    label = format_hour_window_label(start, end)
    assert label == "Fri Jul 10, 5:00 PM–8:00 PM"

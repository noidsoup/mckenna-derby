"""Tests for upcoming high-novelty calendar windows + settlement labels."""

from __future__ import annotations

import datetime as dt

import pandas as pd
import pytest

from mckenna_derby.calendar_windows import (
    HOW_TO_ADD_DIVIDENDS,
    RESOLUTION_NOTE,
    bet_zone_days,
    format_window_rows,
    payout_settlement_summary,
    upcoming_novelty_windows,
)
from mckenna_derby.timewave import Timewave


def test_resolution_note_is_daily_honest():
    assert "daily" in RESOLUTION_NOTE.lower()
    assert "hour" in RESOLUTION_NOTE.lower()


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
    # Warm-up may leave early upcoming days out of zone; flags are boolean.
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
    # Build a short synthetic check via the public helper with a known start.
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
    # Every bet-zone day must have wave_value <= that day's threshold.
    for _, row in df[df["in_bet_zone"]].iterrows():
        assert row["wave_value"] <= row["threshold"] + 1e-12
    # Non-zone days with a finite threshold should sit above it.
    for _, row in df[~df["in_bet_zone"]].iterrows():
        if pd.notna(row["threshold"]):
            assert row["wave_value"] > row["threshold"] - 1e-12


def test_format_window_rows_labels():
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

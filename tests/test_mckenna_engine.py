import datetime as dt

import numpy as np
import pandas as pd
import pytest

from mckenna_derby import data
from mckenna_derby.mckenna_engine import (
    IChingSelector,
    RollingTimewave,
    selective_backtest,
)


# ---------------------------------------------------------------------------
# RollingTimewave
# ---------------------------------------------------------------------------

def make_daily(n_days: int, start: str = "2010-01-01", seed: int = 7) -> pd.Series:
    rng = np.random.default_rng(seed)
    idx = [dt.date.fromisoformat(start) + dt.timedelta(days=i) for i in range(n_days)]
    return pd.Series(rng.normal(size=n_days), index=idx)


def test_rolling_timewave_is_causal():
    """Truncating the future must not change past signal values."""
    daily = make_daily(200)
    rtw = RollingTimewave(wave_factor=64, levels=3)
    full = rtw.signal(daily)
    truncated = rtw.signal(daily.iloc[:150])
    common = truncated.index
    assert len(common) > 0
    pd.testing.assert_series_equal(full.loc[common], truncated, check_freq=False)


def test_rolling_timewave_known_values():
    """Hand-checked values on a tiny series with wave_factor=4."""
    idx = [dt.date(2010, 1, 1) + dt.timedelta(days=i) for i in range(10)]
    vals = [float(i) for i in range(10)]  # novelty(day i) = i
    daily = pd.Series(vals, index=idx)
    rtw = RollingTimewave(wave_factor=4, levels=2)
    sig = rtw.signal(daily)

    # Signal starts once lag wave_factor (4 days) exists: first day is index 4.
    assert sig.index[0] == dt.date(2010, 1, 5)
    # s(day i) = novelty(i-1)/1 + novelty(i-4)/4
    assert sig.loc[dt.date(2010, 1, 5)] == pytest.approx(3.0 + 0.0 / 4)
    assert sig.loc[dt.date(2010, 1, 10)] == pytest.approx(8.0 + 5.0 / 4)


def test_rolling_timewave_missing_days_fall_back_or_zero():
    # Day gap of more than max_gap_days: that level contributes 0.
    idx = [dt.date(2010, 1, 1), dt.date(2010, 1, 20), dt.date(2010, 1, 21)]
    daily = pd.Series([5.0, 2.0, 3.0], index=idx)
    rtw = RollingTimewave(wave_factor=4, levels=2, max_gap_days=7)
    sig = rtw.signal(daily)
    # 2010-01-21: lag-1 -> 2010-01-20 (value 2), lag-4 -> 2010-01-17, nearest
    # earlier is 2010-01-01 (16 days back, beyond tolerance) -> 0.
    assert sig.loc[dt.date(2010, 1, 21)] == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# IChingSelector
# ---------------------------------------------------------------------------

def test_hexagram_in_range():
    sel = IChingSelector(seed=3)
    for _ in range(200):
        h = sel.cast_hexagram()
        assert 1 <= h <= 64


def test_iching_deterministic_with_seed():
    a = IChingSelector(seed=42)
    b = IChingSelector(seed=42)
    assert [a.cast_hexagram() for _ in range(20)] == [
        b.cast_hexagram() for _ in range(20)
    ]
    combos = list(range(100))
    got_a = IChingSelector(seed=9).select_combinations(combos, 10)
    got_b = IChingSelector(seed=9).select_combinations(combos, 10)
    assert got_a == got_b


def test_select_combinations_returns_k_unique():
    combos = [(i, i + 1, i + 2) for i in range(50)]
    picked = IChingSelector(seed=1).select_combinations(combos, 12)
    assert len(picked) == 12
    assert len(set(picked)) == 12
    assert all(c in combos for c in picked)
    # k >= len returns everything
    assert IChingSelector(seed=1).select_combinations(combos, 99) == combos


def test_select_combinations_weighted():
    combos = list(range(5))
    weights = [0.0, 0.0, 1.0, 1.0, 1.0]
    picked = IChingSelector(seed=5).select_combinations(combos, 3, weights=weights)
    assert set(picked) == {2, 3, 4}


# ---------------------------------------------------------------------------
# selective_backtest
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def runners():
    return data.synthetic_races(
        dt.date(2010, 1, 1), dt.date(2010, 6, 30), races_per_day=6, seed=11
    )


def _row(summary: pd.DataFrame, strategy: str) -> pd.Series:
    return summary.set_index("strategy").loc[strategy]


def test_beta_one_selective_places_no_bets(runners):
    """Fair pool (beta=1): every combo has EV = -takeout, so no bets."""
    summary = selective_backtest(runners, beta=1.0, seed=1904)
    sel = _row(summary, "selective")
    assert sel["tickets"] == 0
    assert np.isnan(sel["roi_pct"])
    gated = _row(summary, "selective_gated")
    assert gated["tickets"] == 0


def test_beta_one_buy_all_roi_near_minus_takeout(runners):
    summary = selective_backtest(runners, beta=1.0, takeout=0.22, seed=1904)
    roi = _row(summary, "buy_all")["roi_pct"]
    # Expected exactly -22%; trifecta payouts are heavy-tailed so allow slack.
    assert -40.0 < roi < -5.0


def test_beta_favorites_overbet_gives_positive_modeled_roi(runners):
    """beta=1.15: longshot combos are underpriced -> +EV bets exist and the
    selective strategy shows positive MODELED roi (conditional on the
    assumed bias -- see module docstring)."""
    summary = selective_backtest(runners, beta=1.15, seed=1904)
    sel = _row(summary, "selective")
    assert sel["tickets"] > 0
    assert sel["roi_pct"] > 0
    gated = _row(summary, "selective_gated")
    assert gated["races"] < sel["races"]  # gate actually filters races


def test_random_control_matches_gated_ticket_counts(runners):
    summary = selective_backtest(runners, beta=1.15, seed=1904)
    gated = _row(summary, "selective_gated")
    control = _row(summary, "random_control")
    assert control["races"] == gated["races"]
    assert control["tickets"] == gated["tickets"]


def test_summary_shape(runners):
    summary = selective_backtest(runners, beta=1.15, seed=1904)
    assert list(summary["strategy"]) == [
        "buy_all", "selective_gated", "selective", "random_control",
    ]
    assert set(summary.columns) == {
        "strategy", "races", "tickets", "cost", "payout", "pnl", "roi_pct",
    }

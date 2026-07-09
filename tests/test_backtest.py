import datetime as dt

import numpy as np
import pandas as pd
import pytest

from mckenna_derby import backtest as bt


def make_scores(payout=None, n_days=2, start="2010-01-01"):
    start_d = dt.date.fromisoformat(start)
    dates = [start_d + dt.timedelta(days=i) for i in range(n_days)]
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(dates),
            "race_id": list(range(1, n_days + 1)),
            "n_runners": [6] * n_days,
            "trifecta_probability": [0.25] * n_days,
        }
    )
    if payout is not None:
        df["trifecta_payout"] = payout
    return df


def test_modeled_payout_pnl():
    pnl = bt.race_pnl(make_scores(), takeout=0.2, ticket=1.0)
    assert pnl["n_combos"].iloc[0] == 120
    assert pnl["cost"].iloc[0] == pytest.approx(120.0)
    assert pnl["payout"].iloc[0] == pytest.approx(3.2)   # 0.8 / 0.25
    assert pnl["pnl"].iloc[0] == pytest.approx(-116.8)
    assert set(pnl["payout_source"]) == {"modeled"}


def test_real_dividend_overrides_model_and_nan_falls_back():
    pnl = bt.race_pnl(make_scores(payout=[500.0, float("nan")]), takeout=0.2)
    assert pnl["payout"].iloc[0] == pytest.approx(500.0)
    assert pnl["payout_source"].iloc[0] == "actual"
    assert pnl["payout"].iloc[1] == pytest.approx(3.2)
    assert pnl["payout_source"].iloc[1] == "modeled"


def test_default_min_history():
    assert bt.default_min_history(2) == 1
    assert bt.default_min_history(60) == 30
    assert bt.default_min_history(40) == 20
    assert bt.default_min_history(0) == 0


def test_backtest_causal_skips_insufficient_history():
    """With only 2 days, default min_history=1: day 0 never selected;
    day 1 uses past-only threshold from day 0 alone."""
    tw = pd.Series({dt.date(2010, 1, 1): 0.001, dt.date(2010, 1, 2): 0.010})
    res = bt.backtest(make_scores(), tw, novelty_threshold_pct=50.0, takeout=0.2)
    # Day 0: no past history → not selected.
    # Day 1: past = [0.001]; 50th pct of that is 0.001; 0.010 > 0.001 → not selected.
    assert res["strategy"]["races"] == 0
    assert res["bet_every_race"]["races"] == 2
    assert res["per_race"]["selected"].tolist() == [False, False]
    assert res["min_history"] == 1


def test_backtest_causal_selects_low_wave_after_warmup():
    """After warm-up, a day at/below the expanding past percentile is selected.

    Build 4 days with min_history=2. Day index 2 has value below the past
    50th percentile and should be selected; a later high day should not.
    """
    dates = [dt.date(2010, 1, 1) + dt.timedelta(days=i) for i in range(4)]
    # values: 10, 20, 5, 30  — day 2 (value 5) is below past median of {10,20}=15
    tw = pd.Series([10.0, 20.0, 5.0, 30.0], index=dates)
    scores = make_scores(n_days=4)
    res = bt.backtest(
        scores, tw, novelty_threshold_pct=50.0, takeout=0.2, min_history=2
    )
    assert res["min_history"] == 2
    assert res["per_race"]["selected"].tolist() == [False, False, True, False]
    assert res["strategy"]["races"] == 1


def test_backtest_no_lookahead_truncation():
    """Truncating the future must not change past selection decisions.

    Pass a fixed min_history so length-dependent warm-up defaults cannot
    confound the causality check.
    """
    dates = [dt.date(2010, 1, 1) + dt.timedelta(days=i) for i in range(40)]
    rng = np.random.default_rng(0)
    tw = pd.Series(rng.normal(size=40), index=dates)
    scores = make_scores(n_days=40)
    mh = 10
    full = bt.backtest(
        scores, tw, novelty_threshold_pct=20.0, takeout=0.2, min_history=mh
    )
    trunc_tw = tw.iloc[:25]
    trunc_scores = scores.iloc[:25]
    trunc = bt.backtest(
        trunc_scores, trunc_tw,
        novelty_threshold_pct=20.0, takeout=0.2, min_history=mh,
    )
    full_sel = full["per_race"].iloc[:25]["selected"].tolist()
    trunc_sel = trunc["per_race"]["selected"].tolist()
    assert full_sel == trunc_sel


def test_threshold_sweep_shape():
    dates = [dt.date(2010, 1, 1) + dt.timedelta(days=i) for i in range(40)]
    rng = np.random.default_rng(1)
    tw = pd.Series(rng.normal(size=40), index=dates)
    sweep = bt.threshold_sweep(
        make_scores(n_days=40), tw, pcts=(50, 100), takeout=0.2, min_history=10
    )
    assert list(sweep["threshold_pct"]) == [50, 100]
    # Looser threshold should select at least as many races.
    assert sweep["races"].iloc[-1] >= sweep["races"].iloc[0]
    assert sweep["races"].iloc[-1] >= 1

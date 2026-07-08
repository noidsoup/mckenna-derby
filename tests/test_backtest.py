import datetime as dt

import pandas as pd
import pytest

from mckenna_derby import backtest as bt


def make_scores(payout=None):
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2010-01-01", "2010-01-02"]),
            "race_id": [1, 2],
            "n_runners": [6, 6],
            "trifecta_probability": [0.25, 0.25],
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


def test_backtest_selects_low_wave_days():
    tw = pd.Series({dt.date(2010, 1, 1): 0.001, dt.date(2010, 1, 2): 0.010})
    res = bt.backtest(make_scores(), tw, novelty_threshold_pct=50.0, takeout=0.2)
    assert res["strategy"]["races"] == 1
    assert res["bet_every_race"]["races"] == 2
    assert res["per_race"]["selected"].tolist() == [True, False]


def test_threshold_sweep_shape():
    tw = pd.Series({dt.date(2010, 1, 1): 0.001, dt.date(2010, 1, 2): 0.010})
    sweep = bt.threshold_sweep(make_scores(), tw, pcts=(50, 100), takeout=0.2)
    assert list(sweep["threshold_pct"]) == [50, 100]
    assert sweep["races"].iloc[-1] == 2

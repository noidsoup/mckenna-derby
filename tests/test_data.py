import datetime as dt
from pathlib import Path

import pandas as pd
import pytest

from mckenna_derby import backtest as bt
from mckenna_derby import data, novelty


def test_validate_drops_dead_heats_and_small_fields():
    df = pd.DataFrame(
        {
            "date": ["2010-01-01"] * 8,
            "race_id": [1, 1, 1, 2, 2, 2, 3, 3],
            "horse": list("abcdefgh"),
            "decimal_odds": [2.0] * 8,
            # race 1 clean; race 2 has a dead heat; race 3 has only 2 runners
            "finish_position": [1, 2, 3, 1, 2, 2, 1, 2],
        }
    )
    out = data.validate_runners(df)
    assert set(out["race_id"]) == {1}


def test_synthetic_data_passes_validation_unchanged():
    df = data.synthetic_races(
        dt.date(2010, 1, 1), dt.date(2010, 1, 3), races_per_day=2, seed=1
    )
    assert data.validate_runners(df).shape[0] == df.shape[0]


def test_load_bundled_hk():
    path = data.bundled_hk_path()
    assert path.is_file(), f"missing bundled dataset at {path}"
    out = data.load_bundled_hk()
    assert set(out.columns) >= data.REQUIRED_COLUMNS
    assert out["race_id"].nunique() >= 1000
    assert out["date"].min().year == 1997
    assert out["date"].max().year == 2005
    # Re-validation should be a no-op on the committed file.
    assert len(data.validate_runners(out)) == len(out)
    # Real win/place dividends are first-class on the bundled CSV.
    assert "win_payout" in out.columns and "place_payout" in out.columns
    n_races = out["race_id"].nunique()
    # Nearly every race has a published win dividend (a handful of dead-heat /
    # missing rows in the Kaggle dump are expected).
    assert out["win_payout"].notna().sum() >= int(0.99 * n_races)
    # Winners should carry a win_payout; non-winners should be NaN.
    winners = out[out["finish_position"] == 1]
    assert winners["win_payout"].notna().mean() > 0.99
    # Trifecta cash settlement is still unavailable in the Kaggle source.
    has_tri = "trifecta_payout" in out.columns and out["trifecta_payout"].notna().any()
    assert not has_tri


def test_load_bundled_uk():
    """Exploratory UK/Ireland slice — larger free source, not the locked claim."""
    path = data.bundled_uk_path()
    assert path.is_file(), f"missing bundled UK dataset at {path}"
    out = data.load_bundled_uk()
    assert set(out.columns) >= data.REQUIRED_COLUMNS
    assert out["race_id"].nunique() >= 10_000
    assert out["date"].min().year == 2008
    assert out["date"].max().year == 2012
    assert len(data.validate_runners(out)) == len(out)
    # No real dividends on this free slice (odds from implied probability only).
    assert "win_payout" not in out.columns or out["win_payout"].isna().all()
    assert out["decimal_odds"].min() > 1.0


def test_load_uk_racing_converts_implied_probability(tmp_path):
    """hwaitt decimalPrice is an implied win probability, not decimal odds."""
    (tmp_path / "races_2010.csv").write_text(
        "rid,date\n1,2010-06-01\n2,2010-06-02\n"
    )
    (tmp_path / "horses_2010.csv").write_text(
        "rid,horseName,decimalPrice,position\n"
        "1,A,0.5,1\n1,B,0.25,2\n1,C,0.125,3\n"
        "2,A,0.4,1\n2,B,0.3,2\n2,C,0.2,3\n"
    )
    out = data.load_uk_racing(tmp_path)
    assert set(out.columns) >= data.REQUIRED_COLUMNS
    assert out["race_id"].nunique() == 2
    # 0.5 implied prob → 2.0 decimal odds
    assert float(out.loc[(out["race_id"] == 1) & (out["horse"] == "A"), "decimal_odds"].iloc[0]) == 2.0
    assert float(out.loc[(out["race_id"] == 1) & (out["horse"] == "B"), "decimal_odds"].iloc[0]) == 4.0


def _write_mini_hk(tmp_path: Path) -> Path:
    """Minimal gdaley-shaped races/runs with win/place dividends."""
    (tmp_path / "races.csv").write_text(
        "race_id,date,"
        "place_combination1,place_combination2,place_combination3,place_combination4,"
        "place_dividend1,place_dividend2,place_dividend3,place_dividend4,"
        "win_combination1,win_dividend1,win_combination2,win_dividend2\n"
        "1,2010-06-01,1,2,3,,25.0,40.0,55.0,,1,120.0,,\n"
        "2,2010-06-02,2,1,3,,30.0,35.0,50.0,,2,80.0,,\n"
    )
    (tmp_path / "runs.csv").write_text(
        "race_id,horse_no,result,win_odds\n"
        "1,1,1,2.0\n1,2,2,4.0\n1,3,3,5.0\n1,4,4,10.0\n"
        "2,1,2,3.0\n2,2,1,4.0\n2,3,3,6.0\n2,4,4,8.0\n"
    )
    return tmp_path


def test_load_hk_racing_attaches_win_place_per_dollar(tmp_path):
    raw = _write_mini_hk(tmp_path)
    out = data.load_hk_racing(raw)
    assert "win_payout" in out.columns and "place_payout" in out.columns
    # Published 120.0 per $10 → 12.0 per $1 on the winner of race 1.
    w1 = out[(out["race_id"] == 1) & (out["finish_position"] == 1)].iloc[0]
    assert w1["win_payout"] == pytest.approx(12.0)
    assert w1["place_payout"] == pytest.approx(2.5)
    # Non-winner without a place dividend stays NaN for win.
    long = out[(out["race_id"] == 1) & (out["horse"] == 4)].iloc[0]
    assert pd.isna(long["win_payout"])
    assert pd.isna(long["place_payout"])


def test_merge_exotic_dividends_prefers_trifecta_and_aliases_tierce(tmp_path):
    runners = pd.DataFrame(
        {
            "date": pd.to_datetime(["2010-06-01"] * 3),
            "race_id": [1, 1, 1],
            "horse": [1, 2, 3],
            "decimal_odds": [2.0, 4.0, 5.0],
            "finish_position": [1, 2, 3],
        }
    )
    exotics = pd.DataFrame(
        {"race_id": [1], "tierce_payout": [456.0], "trio_payout": [12.0]}
    )
    merged = data.merge_exotic_dividends(runners, exotics)
    assert merged["trifecta_payout"].tolist() == [456.0, 456.0, 456.0]
    assert merged["trio_payout"].tolist() == [12.0, 12.0, 12.0]

    # load_exotic_dividends from CSV + rebuild path
    path = tmp_path / "exotics.csv"
    path.write_text("race_id,trifecta_payout\n1,789.0\n")
    loaded = data.load_exotic_dividends(path)
    merged2 = data.merge_exotic_dividends(runners, loaded)
    assert merged2["trifecta_payout"].iloc[0] == pytest.approx(789.0)


def test_remap_renavon_dividends_joins_on_date_venue_race_no():
    """Renavon long-format TIERCE/TRIO → Kaggle race_id companion rows."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "remap_renavon_dividends",
        Path(__file__).resolve().parents[1] / "scripts" / "remap_renavon_dividends.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)

    races = pd.DataFrame(
        {
            "race_id": [10, 11],
            "date": ["2001-01-03", "2001-01-03"],
            "venue": ["HV", "HV"],
            "race_no": [1, 2],
        }
    )
    renavon = pd.DataFrame(
        {
            "race_date": ["2001-01-03", "2001-01-03", "2001-01-03"],
            "venue_code": ["HV", "HV", "HV"],
            "race_number": [1, 1, 2],
            "pool_type": ["TIERCE", "TRIO", "TIERCE"],
            "return_per_dollar": [100.0, 20.0, 200.0],
            "dividend": [1000.0, 200.0, 2000.0],
        }
    )
    out = mod.remap_renavon_to_exotics(
        renavon, races, start="2001-01-01", end="2005-08-28"
    )
    assert set(out["race_id"]) == {10, 11}
    row10 = out.set_index("race_id").loc[10]
    assert row10["trifecta_payout"] == pytest.approx(100.0)
    assert row10["trio_payout"] == pytest.approx(20.0)
    assert out.set_index("race_id").loc[11]["trifecta_payout"] == pytest.approx(200.0)


def test_backtest_uses_merged_trifecta_payout_as_actual():
    """End-to-end: merged trifecta_payout → score_races → race_pnl actual."""
    runners = pd.DataFrame(
        {
            "date": pd.to_datetime(["2010-06-01"] * 3),
            "race_id": [1, 1, 1],
            "horse": [1, 2, 3],
            "decimal_odds": [2.0, 4.0, 4.0],
            "finish_position": [1, 2, 3],
            "trifecta_payout": [500.0, 500.0, 500.0],
        }
    )
    scores = novelty.score_races(runners)
    pnl = bt.race_pnl(scores, takeout=0.2)
    assert pnl["payout"].iloc[0] == pytest.approx(500.0)
    assert pnl["payout_source"].iloc[0] == "actual"

import datetime as dt

import pandas as pd

from mckenna_derby import data


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

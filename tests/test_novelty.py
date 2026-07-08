import pandas as pd
import pytest

from mckenna_derby import novelty


def make_race(odds, payout=None, race_id=1, date="2010-06-01"):
    df = pd.DataFrame(
        {
            "date": [date] * len(odds),
            "race_id": [race_id] * len(odds),
            "horse": [f"H{i}" for i in range(len(odds))],
            "decimal_odds": odds,
            "finish_position": list(range(1, len(odds) + 1)),
        }
    )
    if payout is not None:
        df["trifecta_payout"] = payout
    return df


def test_clean_three_horse_race():
    scores = novelty.score_races(make_race([2.0, 4.0, 4.0]))
    row = scores.iloc[0]
    assert row["win_novelty"] == pytest.approx(1.0)       # -log2(0.5)
    assert row["trifecta_novelty"] == pytest.approx(2.0)  # -log2(0.25)
    assert row["trifecta_probability"] == pytest.approx(0.25)
    assert bool(row["winner_was_favorite"]) is True
    assert row["n_runners"] == 3


def test_longshot_win_is_more_novel_than_favorite_win():
    fav_wins = novelty.score_races(make_race([1.5, 3.0, 8.0]))
    longshot_wins = novelty.score_races(make_race([8.0, 3.0, 1.5]))
    assert longshot_wins.iloc[0]["win_novelty"] > fav_wins.iloc[0]["win_novelty"]
    assert bool(longshot_wins.iloc[0]["winner_was_favorite"]) is False


def test_payout_passthrough():
    # RED until Task 8: score_races must carry an optional trifecta_payout
    # column (one value per race) through to the race-level output.
    scores = novelty.score_races(make_race([2.0, 4.0, 4.0], payout=123.4))
    assert scores.iloc[0]["trifecta_payout"] == pytest.approx(123.4)


def test_missing_columns_rejected():
    with pytest.raises(ValueError):
        novelty.score_races(pd.DataFrame({"date": ["2010-01-01"]}))


def test_daily_novelty_returns_one_value_per_day():
    df = pd.concat(
        [
            make_race([2.0, 4.0, 4.0], race_id=1, date="2010-06-01"),
            make_race([1.5, 3.0, 8.0], race_id=2, date="2010-06-01"),
            make_race([2.0, 4.0, 4.0], race_id=3, date="2010-06-02"),
        ]
    )
    daily = novelty.daily_novelty(novelty.score_races(df))
    assert len(daily) == 2

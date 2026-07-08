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

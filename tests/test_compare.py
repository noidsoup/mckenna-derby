import datetime as dt

import pandas as pd

from mckenna_derby import compare


def test_lead_lag_shape_and_bounds():
    dates = [dt.date(2010, 1, 1) + dt.timedelta(days=i) for i in range(40)]
    daily = pd.Series(range(40), index=pd.Index(dates), dtype=float)
    out = compare.lead_lag(daily, number_set="kelley", max_lag=3)
    assert list(out["lag_days"]) == [-3, -2, -1, 0, 1, 2, 3]
    assert out["spearman_r"].abs().max() <= 1.0

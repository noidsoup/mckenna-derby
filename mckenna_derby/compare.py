"""Compare the racing novelty series against McKenna's timewave.

McKenna's convention: LOW timewave value = HIGH novelty. So if his wave had
predictive power over racing chaos, daily race novelty would be NEGATIVELY
correlated with the timewave value.

Because both series are autocorrelated, a naive p-value would overstate
significance, so we also run a circular-shift permutation test: shift the
timewave by random offsets and see how often the shifted correlation beats
the real one. That preserves each series' internal structure.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
from scipy import stats

from .timewave import Timewave


def timewave_series_for(dates: pd.Index, number_set: str = "kelley") -> pd.Series:
    tw = Timewave(number_set)
    return pd.Series({d: tw.value_on(d)[0] for d in dates}, name=f"timewave_{number_set}")


def compare(daily_novelty: pd.Series, number_set: str = "kelley", n_permutations: int = 2000,
            seed: int = 0) -> dict:
    """Correlate daily race novelty with the timewave.

    Returns Pearson and Spearman correlations plus a circular-shift
    permutation p-value for the Spearman statistic.
    """
    tw = timewave_series_for(daily_novelty.index, number_set)
    x = daily_novelty.to_numpy()
    y = tw.to_numpy()
    mask = ~(np.isnan(x) | np.isnan(y))
    x, y = x[mask], y[mask]

    pearson_r, pearson_p = stats.pearsonr(x, y)
    spearman_r, spearman_p = stats.spearmanr(x, y)

    rng = np.random.default_rng(seed)
    n = len(x)
    null_rs = np.empty(n_permutations)
    for i in range(n_permutations):
        shift = rng.integers(1, n)
        null_rs[i] = stats.spearmanr(x, np.roll(y, shift)).statistic
    perm_p = float((np.abs(null_rs) >= abs(spearman_r)).mean())

    return {
        "number_set": number_set,
        "n_days": n,
        "pearson_r": float(pearson_r),
        "pearson_p": float(pearson_p),
        "spearman_r": float(spearman_r),
        "spearman_p": float(spearman_p),
        "permutation_p": perm_p,
        "timewave": tw,
        "interpretation": _interpret(spearman_r, perm_p),
    }


def _interpret(r: float, perm_p: float) -> str:
    if perm_p < 0.05:
        direction = (
            "high race novelty on LOW timewave days — the direction McKenna's "
            "theory predicts" if r < 0 else
            "high race novelty on HIGH timewave days — the OPPOSITE of what "
            "McKenna's theory predicts"
        )
        return f"Correlation survives the permutation test ({direction})."
    return (
        "No statistically meaningful relationship between race novelty and the "
        "timewave once autocorrelation is accounted for."
    )


def lead_lag(daily_novelty: pd.Series, number_set: str = "kelley",
             max_lag: int = 30) -> pd.DataFrame:
    """Spearman correlation of novelty(d) vs timewave(d + lag), per lag.

    A peak at a nonzero lag would mean one series leads the other.
    Exploratory only — never part of the pre-registered analysis.
    """
    tw = Timewave(number_set)
    cache: dict = {}

    def wave(d):
        if d not in cache:
            cache[d] = tw.value_on(d)[0]
        return cache[d]

    x = daily_novelty.to_numpy()
    rows = []
    for lag in range(-max_lag, max_lag + 1):
        y = np.array([wave(d + dt.timedelta(days=lag)) for d in daily_novelty.index])
        rows.append(
            {"lag_days": lag, "spearman_r": float(stats.spearmanr(x, y).statistic)}
        )
    return pd.DataFrame(rows)

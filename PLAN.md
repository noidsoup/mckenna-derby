# Plan: Phase 2 of McKenna Derby — freeze the core, add real-data support, run the pre-registered experiment

## Context

- **Repo / module:** `/Users/thedao/Projects/mckenna-derby` (Python package `mckenna_derby`, venv at `.venv`)
- **Why now:** The Phase 1 prototype is complete and verified (the Timewave Zero port matches the reference C implementation to 16 decimals; the pipeline runs end-to-end on synthetic data and correctly shows a null result). Phase 2 makes the experiment runnable on real data, honestly.
- **Spec / source:** user request + skeptic review. Findings folded in:
  - **The statistical core is FROZEN.** The logic in `timewave.py`, `novelty.py`, and `compare.py` must not change except exactly where this plan says so. Task 3–4 install golden tests that pin current behavior; they must pass unchanged after every subsequent task.
  - **Pre-registration.** Four number sets × thresholds × takeouts is a garden of forking paths. One primary analysis is declared in `prereg.json` BEFORE running on real data; all other combinations are labeled exploratory with Bonferroni correction.
  - **The weakest link is data, not code.** Modeled parimutuel payouts have an expected ROI of exactly −takeout by construction. Real historical trifecta dividends are the important upgrade; this plan adds schema and backtest support for them.
  - **The deliverable is a result, not a product.** The timewave is undefined after 2012-12-21, so the usable dataset is historical and finite. No dashboards, no services, no live feeds.

### Implementer ground rules (read before starting)

1. Work from `/Users/thedao/Projects/mckenna-derby`. Use `.venv/bin/python` and `.venv/bin/pytest` for every command (do NOT use system python).
2. Do the tasks in order. After EVERY task from Task 3 onward, run `.venv/bin/pytest -q`. Expected state: all tests pass, EXCEPT that `test_payout_passthrough` (added in Task 4) is deliberately red from Task 4 through Task 7 and turns green at Task 8 (TDD). Any other failure means you broke something — stop and fix before continuing.
3. Copy code blocks verbatim. Do not "improve", rename, reorder, or reformat anything.
4. Where a task says "replace the file", the code block is the COMPLETE new file contents.
5. If a verify command fails and the fix is not obvious from the error message, STOP and report the error. Never guess at changes to `timewave.py`, `novelty.py`, or `compare.py`.

## Goal

- [ ] The pipeline runs on real racing data with a pre-registered primary analysis, uses real trifecta dividends when provided (falling back to the modeled payout otherwise), and writes a markdown report — with the frozen statistical core protected by a passing test suite.

## Non-goals

- [ ] No web app, dashboard, API, database, or service.
- [ ] No live odds feeds or real-money betting integration.
- [ ] No changes to the timewave algorithm, the Harville model, or the permutation test beyond what the tasks below specify.
- [ ] No new ML models — the "AI" is the scoring + statistics pipeline.
- [ ] No scraping of dividend data (out of scope; user supplies a CSV if/when they obtain it).

## Assumptions

- [ ] Python 3.9 venv exists at `.venv` with numpy/pandas/scipy/matplotlib installed. If missing: `cd /Users/thedao/Projects/mckenna-derby && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
- [ ] The demo currently runs clean: `.venv/bin/python run_analysis.py` exits 0. Verify this FIRST; if it fails, stop and report.
- [ ] Kaggle credentials may not be available. Every task except Task 16 works offline.

## Checklist

### Task 1 — Add `pyproject.toml`

- **File(s):** `/Users/thedao/Projects/mckenna-derby/pyproject.toml` (new)
- **Change:** Package definition (including the wavesets data files) and pytest config, so tests can import the package.

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "mckenna-derby"
version = "0.2.0"
description = "Horse-racing novelty analysis vs Timewave Zero"
requires-python = ">=3.9"
dependencies = [
    "numpy>=1.24",
    "pandas>=2.0",
    "scipy>=1.10",
    "matplotlib>=3.7",
]

[tool.setuptools.packages.find]
include = ["mckenna_derby*"]

[tool.setuptools.package-data]
"mckenna_derby.wavesets" = ["*.txt"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- **Verify:** `cd /Users/thedao/Projects/mckenna-derby && .venv/bin/pip install -e . pytest && .venv/bin/python -c "import mckenna_derby; print(mckenna_derby.__version__)"`

### Task 2 — Create the tests directory

- **File(s):** `/Users/thedao/Projects/mckenna-derby/tests/__init__.py` (new, empty)
- **Change:** Create the directory and an empty `__init__.py` file.

```bash
mkdir -p /Users/thedao/Projects/mckenna-derby/tests && touch /Users/thedao/Projects/mckenna-derby/tests/__init__.py
```

- **Verify:** `ls /Users/thedao/Projects/mckenna-derby/tests/__init__.py`

### Task 3 — Golden tests for the timewave (freezes the core)

- **File(s):** `/Users/thedao/Projects/mckenna-derby/tests/test_timewave.py` (new)
- **Change:** Pin the Python port to the values already verified against Peter Meyer's reference C implementation. These constants are correct — if a test fails, the code changed, not the test.

```python
import datetime as dt

import pytest

from mckenna_derby.timewave import Timewave, ZERO_DATE

# (value at 1000 days before zero, value at 12345.678 days before zero),
# verified against the compiled twz-point.c reference implementation.
GOLDEN = {
    "kelley": (0.0035158793131510, 0.0412491142607616),
    "watkins": (0.0035394941057478, 0.0412491142878900),
    "sheliak": (0.0033364068894159, 0.0202409528079362),
    "huangti": (0.0006744748070126, 0.0059600465473974),
}


@pytest.mark.parametrize("name", sorted(GOLDEN))
def test_matches_reference_c_implementation(name):
    tw = Timewave(name)
    v1000, v12345 = GOLDEN[name]
    assert tw.value_at_days_to_zero(1000) == pytest.approx(v1000, abs=1e-12)
    assert tw.value_at_days_to_zero(12345.678) == pytest.approx(v12345, abs=1e-12)


def test_zero_point_is_zero():
    assert Timewave("kelley").value_at_days_to_zero(0) == 0.0


def test_mirrored_extension_after_zero_date():
    tw = Timewave("kelley")
    v_before, m_before = tw.value_on(ZERO_DATE - dt.timedelta(days=500))
    v_after, m_after = tw.value_on(ZERO_DATE + dt.timedelta(days=500))
    assert m_before is False
    assert m_after is True
    assert v_after == pytest.approx(v_before)


def test_invalid_number_set_rejected():
    with pytest.raises(ValueError):
        Timewave("nonsense")


def test_negative_days_rejected():
    with pytest.raises(ValueError):
        Timewave("kelley").value_at_days_to_zero(-1)
```

- **Verify:** `cd /Users/thedao/Projects/mckenna-derby && .venv/bin/pytest tests/test_timewave.py -v`

### Task 4 — Golden tests for novelty scoring

- **File(s):** `/Users/thedao/Projects/mckenna-derby/tests/test_novelty.py` (new)
- **Change:** Hand-computed cases. With odds (2.0, 4.0, 4.0) the implied probabilities are exactly (0.5, 0.25, 0.25); win surprisal is 1 bit and the Harville trifecta probability is 0.5 × (0.25/0.5) × (0.25/0.25) = 0.25, i.e. 2 bits. NOTE: `test_payout_passthrough` is EXPECTED TO FAIL until Task 8 (TDD red). All other tests must pass now.

```python
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
```

- **Verify:** `cd /Users/thedao/Projects/mckenna-derby && .venv/bin/pytest tests/test_novelty.py -v; echo "expect exactly 1 failure: test_payout_passthrough"`

### Task 5 — Add lead-lag analysis to `compare.py` (additive only)

- **File(s):** `/Users/thedao/Projects/mckenna-derby/mckenna_derby/compare.py`
- **Change:** Two edits. (a) Add `import datetime as dt` to the imports; (b) append the `lead_lag` function at the end of the file. Do not touch anything else in this file.

Edit (a) — the import block currently reads:

```python
import numpy as np
import pandas as pd
from scipy import stats
```

Replace it with:

```python
import datetime as dt

import numpy as np
import pandas as pd
from scipy import stats
```

Edit (b) — append at the very end of the file:

```python
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
```

- **Verify:** `cd /Users/thedao/Projects/mckenna-derby && .venv/bin/python -c "from mckenna_derby.compare import lead_lag; print('ok')"`

### Task 6 — Test for lead-lag

- **File(s):** `/Users/thedao/Projects/mckenna-derby/tests/test_compare.py` (new)
- **Change:** Shape and sanity checks (correlations bounded, correct lag range).

```python
import datetime as dt

import pandas as pd

from mckenna_derby import compare


def test_lead_lag_shape_and_bounds():
    dates = [dt.date(2010, 1, 1) + dt.timedelta(days=i) for i in range(40)]
    daily = pd.Series(range(40), index=pd.Index(dates), dtype=float)
    out = compare.lead_lag(daily, number_set="kelley", max_lag=3)
    assert list(out["lag_days"]) == [-3, -2, -1, 0, 1, 2, 3]
    assert out["spearman_r"].abs().max() <= 1.0
```

- **Verify:** `cd /Users/thedao/Projects/mckenna-derby && .venv/bin/pytest tests/test_compare.py -v`

### Task 7 — Data validation + generic CSV loader (replace `data.py`)

- **File(s):** `/Users/thedao/Projects/mckenna-derby/mckenna_derby/data.py` (full replacement)
- **Change:** Extract a shared `validate_runners` (drops dead-heats, sub-3-runner fields, bad odds), add `load_generic_csv` for arbitrary runner-level CSVs (with optional `trifecta_payout` column for real dividends), and route `load_hk_racing` through the validator. `synthetic_races` and `_sample_order` are unchanged. Replace the entire file with:

```python
"""Data loading: Kaggle datasets, generic CSVs, or a synthetic demo dataset.

All loaders return a runner-level dataframe with columns:
    date, race_id, horse, decimal_odds, finish_position
and optionally:
    trifecta_payout  -- actual dividend paid per $1 winning trifecta ticket,
                        one value repeated on every row of the race. When
                        present, the backtest uses it instead of the modeled
                        parimutuel payout.

Real data
---------
Good free Kaggle datasets with per-runner odds and finishing positions:

- ``gdaley/hkracing``     Hong Kong Jockey Club races (runs.csv has win_odds
                          and result columns; races span 1997-2005, safely
                          before the timewave zero date)
- ``hwaitt/horse-racing`` UK/Ireland races with decimal odds

Download with the Kaggle CLI (``pip install kaggle``, token in
``~/.kaggle/kaggle.json``)::

    kaggle datasets download -d gdaley/hkracing -p rawdata --unzip

Demo data
---------
``synthetic_races`` generates race cards where the finishing order is sampled
from odds-implied probabilities via the Harville model, so market calibration
holds by construction: it is a null-hypothesis fixture for the pipeline.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = {"date", "race_id", "horse", "decimal_odds", "finish_position"}


def validate_runners(df: pd.DataFrame) -> pd.DataFrame:
    """Clean a runner-level dataframe.

    Drops rows with missing odds/positions or odds <= 1, then drops entire
    races whose finish positions are not a clean 1..n ordering (dead heats,
    scratches) or that have fewer than 3 runners (no trifecta possible).
    """
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")
    df = df.dropna(subset=["decimal_odds", "finish_position"]).copy()
    df = df[df["decimal_odds"] > 1.0]
    df["finish_position"] = df["finish_position"].astype(int)
    df["date"] = pd.to_datetime(df["date"])

    def clean(positions: pd.Series) -> bool:
        return len(positions) >= 3 and sorted(positions) == list(
            range(1, len(positions) + 1)
        )

    ok = df.groupby("race_id")["finish_position"].apply(clean)
    return df[df["race_id"].isin(ok[ok].index)].reset_index(drop=True)


def load_generic_csv(path: str | Path, column_map: dict | None = None) -> pd.DataFrame:
    """Load any runner-level CSV. ``column_map`` renames source columns to the
    required schema, e.g. {"odds": "decimal_odds", "pos": "finish_position"}."""
    df = pd.read_csv(path)
    if column_map:
        df = df.rename(columns=column_map)
    return validate_runners(df)


def load_hk_racing(rawdata_dir: str | Path) -> pd.DataFrame:
    """Load the gdaley/hkracing Kaggle dataset (races.csv + runs.csv)."""
    rawdata_dir = Path(rawdata_dir)
    races = pd.read_csv(rawdata_dir / "races.csv", usecols=["race_id", "date"])
    runs = pd.read_csv(
        rawdata_dir / "runs.csv",
        usecols=["race_id", "horse_no", "result", "win_odds"],
    )
    df = runs.merge(races, on="race_id")
    df = df.rename(
        columns={
            "horse_no": "horse",
            "win_odds": "decimal_odds",
            "result": "finish_position",
        }
    )
    df = df.dropna(subset=["finish_position"])
    return validate_runners(df)


def synthetic_races(
    start: dt.date,
    end: dt.date,
    races_per_day: int = 8,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate a synthetic runner-level dataset with market-calibrated outcomes."""
    rng = np.random.default_rng(seed)
    rows = []
    race_counter = 0
    d = start
    while d <= end:
        for _ in range(races_per_day):
            race_counter += 1
            n = int(rng.integers(6, 13))
            # Log-normal "ability" spread produces a realistic favorite/longshot mix.
            strength = rng.lognormal(mean=0.0, sigma=1.0, size=n)
            p = strength / strength.sum()
            # Market odds = fair odds plus ~18% total overround.
            overround = 1.18
            decimal_odds = 1.0 / (p * overround / p.sum())
            # Sample the true finishing order from the same p (Harville).
            order = _sample_order(rng, p)
            for pos, horse_idx in enumerate(order, start=1):
                rows.append(
                    {
                        "date": d,
                        "race_id": race_counter,
                        "horse": f"H{horse_idx + 1}",
                        "decimal_odds": round(float(decimal_odds[horse_idx]), 2),
                        "finish_position": pos,
                    }
                )
        d += dt.timedelta(days=1)
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df


def _sample_order(rng: np.random.Generator, p: np.ndarray) -> list[int]:
    """Sample a full finishing order via sequential sampling without replacement."""
    remaining = list(range(len(p)))
    weights = p.copy()
    order = []
    while remaining:
        w = weights[remaining]
        w = w / w.sum()
        pick = rng.choice(len(remaining), p=w)
        order.append(remaining.pop(pick))
    return order
```

- **Verify:** `cd /Users/thedao/Projects/mckenna-derby && .venv/bin/python -c "from mckenna_derby.data import validate_runners, load_generic_csv, load_hk_racing, synthetic_races; print('ok')"`

### Task 8 — Tests for data validation, then payout passthrough in `novelty.py` (turns Task 4 green)

- **File(s):** `/Users/thedao/Projects/mckenna-derby/tests/test_data.py` (new) and `/Users/thedao/Projects/mckenna-derby/mckenna_derby/novelty.py` (one function edit)

First create the data test:

```python
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
```

Then in `/Users/thedao/Projects/mckenna-derby/mckenna_derby/novelty.py`, find the `return` statement at the end of `score_race` (it currently reads):

```python
    return {
        "date": g["date"].iloc[0],
        "race_id": g["race_id"].iloc[0],
        "n_runners": n,
        "winner_odds": float(g["decimal_odds"].iloc[0]),
        "winner_was_favorite": odds_rank_of_winner == 1,
        "win_novelty": -math.log2(p_win),
        "trifecta_novelty": -math.log2(p_tri),
        "trifecta_probability": p_tri,
    }
```

and replace it with:

```python
    result = {
        "date": g["date"].iloc[0],
        "race_id": g["race_id"].iloc[0],
        "n_runners": n,
        "winner_odds": float(g["decimal_odds"].iloc[0]),
        "winner_was_favorite": odds_rank_of_winner == 1,
        "win_novelty": -math.log2(p_win),
        "trifecta_novelty": -math.log2(p_tri),
        "trifecta_probability": p_tri,
    }
    if "trifecta_payout" in g.columns:
        result["trifecta_payout"] = float(g["trifecta_payout"].iloc[0])
    return result
```

No other change to `novelty.py` is permitted.

- **Verify:** `cd /Users/thedao/Projects/mckenna-derby && .venv/bin/pytest -q` (ALL tests green now, including `test_payout_passthrough`)

### Task 9 — Real dividends + threshold sweep (replace `backtest.py`)

- **File(s):** `/Users/thedao/Projects/mckenna-derby/mckenna_derby/backtest.py` (full replacement)
- **Change:** `race_pnl` uses the actual dividend when a `trifecta_payout` value is present (falling back to the model where it is NaN) and records the source; new `threshold_sweep` runs the backtest across a grid of thresholds for the exploratory report section. Replace the entire file with:

```python
"""Backtest the buy-every-trifecta-combination strategy.

For each race we compare:

    cost   = n * (n-1) * (n-2) * ticket_price        (every exact order)
    payout = the ONE winning ticket's payout

Payout comes from, in order of preference:
1. ``trifecta_payout`` (actual historical dividend per $1 ticket) when the
   dataset provides it — this is the only credible basis for conclusions;
2. otherwise a modeled parimutuel pool consistent with the market's own
   Harville probabilities:  payout = ticket * (1 - takeout) / P(order).

Under the model, the expected return of buying everything is exactly
-takeout per race; profit can only come from a timing signal that finds
races where the realized order is more chaotic than the pool priced in.

The strategy filter: only bet on days where the timewave says novelty is
high (LOW wave value), per the McKenna hypothesis.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_TAKEOUT = 0.22
TICKET_PRICE = 1.0
DEFAULT_SWEEP_PCTS = (5, 10, 15, 20, 30, 40, 50, 75, 100)


def race_pnl(race_scores: pd.DataFrame, takeout: float = DEFAULT_TAKEOUT,
             ticket: float = TICKET_PRICE) -> pd.DataFrame:
    """Per-race profit/loss of buying every trifecta combination."""
    s = race_scores.copy()
    n = s["n_runners"]
    s["n_combos"] = n * (n - 1) * (n - 2)
    s["cost"] = s["n_combos"] * ticket
    modeled = ticket * (1.0 - takeout) / s["trifecta_probability"]
    if "trifecta_payout" in s.columns:
        s["payout"] = s["trifecta_payout"].where(s["trifecta_payout"].notna(), modeled)
        s["payout_source"] = np.where(
            s["trifecta_payout"].notna(), "actual", "modeled"
        )
    else:
        s["payout"] = modeled
        s["payout_source"] = "modeled"
    s["pnl"] = s["payout"] - s["cost"]
    return s


def backtest(race_scores: pd.DataFrame, timewave: pd.Series,
             novelty_threshold_pct: float = 20.0,
             takeout: float = DEFAULT_TAKEOUT) -> dict:
    """Bet only on days in the lowest `novelty_threshold_pct`% of timewave
    values (low wave = high predicted novelty), vs. betting every day."""
    pnl = race_pnl(race_scores, takeout)
    pnl["day"] = pnl["date"].dt.date
    tw = timewave.copy()
    tw.index = pd.Index([d for d in tw.index])
    threshold = np.percentile(tw.to_numpy(), novelty_threshold_pct)
    high_novelty_days = set(tw[tw <= threshold].index)
    pnl["selected"] = pnl["day"].isin(high_novelty_days)

    def summarize(frame: pd.DataFrame) -> dict:
        if frame.empty:
            return {"races": 0, "total_cost": 0.0, "total_payout": 0.0,
                    "total_pnl": 0.0, "roi_pct": float("nan"),
                    "hit_profit_pct": float("nan")}
        return {
            "races": int(len(frame)),
            "total_cost": float(frame["cost"].sum()),
            "total_payout": float(frame["payout"].sum()),
            "total_pnl": float(frame["pnl"].sum()),
            "roi_pct": float(100 * frame["pnl"].sum() / frame["cost"].sum()),
            "hit_profit_pct": float(100 * (frame["pnl"] > 0).mean()),
        }

    return {
        "threshold_wave_value": float(threshold),
        "strategy": summarize(pnl[pnl["selected"]]),
        "bet_every_race": summarize(pnl),
        "per_race": pnl,
    }


def threshold_sweep(race_scores: pd.DataFrame, timewave: pd.Series,
                    pcts: tuple = DEFAULT_SWEEP_PCTS,
                    takeout: float = DEFAULT_TAKEOUT) -> pd.DataFrame:
    """ROI of the strategy across a grid of timewave thresholds.

    Exploratory only: sweeping thresholds and picking the best one is
    p-hacking. This exists to show the shape of the curve, not to tune.
    """
    rows = []
    for pct in pcts:
        res = backtest(race_scores, timewave,
                       novelty_threshold_pct=float(pct), takeout=takeout)
        s = res["strategy"]
        rows.append(
            {
                "threshold_pct": pct,
                "wave_threshold": res["threshold_wave_value"],
                "races": s["races"],
                "total_cost": s["total_cost"],
                "total_pnl": s["total_pnl"],
                "roi_pct": s["roi_pct"],
                "hit_profit_pct": s["hit_profit_pct"],
            }
        )
    return pd.DataFrame(rows)
```

- **Verify:** `cd /Users/thedao/Projects/mckenna-derby && .venv/bin/python -c "from mckenna_derby.backtest import race_pnl, backtest, threshold_sweep; print('ok')" && .venv/bin/pytest -q`

### Task 10 — Tests for the backtest

- **File(s):** `/Users/thedao/Projects/mckenna-derby/tests/test_backtest.py` (new)
- **Change:** Hand-computed P&L (6 runners = 120 combos; takeout 0.2 and P=0.25 gives a $3.20 payout), dividend override with NaN fallback, day selection, and sweep shape.

```python
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
```

- **Verify:** `cd /Users/thedao/Projects/mckenna-derby && .venv/bin/pytest tests/test_backtest.py -v && .venv/bin/pytest -q`

### Task 11 — Pre-registration file

- **File(s):** `/Users/thedao/Projects/mckenna-derby/prereg.json` (new)
- **Change:** Declare the single primary analysis before any real-data run. This file is committed and then never edited.

```json
{
  "declared_on": "2026-07-08",
  "primary_number_set": "kelley",
  "metric": "trifecta_novelty",
  "primary_threshold_pct": 20.0,
  "takeout": 0.22,
  "prediction": "McKenna's theory predicts Spearman r < 0 between daily race novelty and the timewave (permutation p < 0.05), and timewave-filtered ROI exceeding bet-every-race ROI.",
  "rule": "Do not edit this file after the first real-data run. All other number sets, thresholds, sweeps, and lags are exploratory and reported with Bonferroni correction."
}
```

- **Verify:** `cd /Users/thedao/Projects/mckenna-derby && .venv/bin/python -c "import json; d=json.load(open('prereg.json')); assert d['primary_number_set']=='kelley'; print('ok')"`

### Task 12 — Report writer

- **File(s):** `/Users/thedao/Projects/mckenna-derby/mckenna_derby/report.py` (new)
- **Change:** Writes `output/report.md` summarizing the pre-registered primary result, the exploratory sections, and the backtest, with an explicit payout-source caveat.

```python
"""Markdown report writer for a pipeline run."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PRIMARY_KEYS = [
    "number_set", "n_days", "pearson_r", "pearson_p",
    "spearman_r", "spearman_p", "permutation_p", "interpretation",
]


def _backtest_row(name: str, s: dict) -> str:
    return (
        f"| {name} | {s['races']:,} | ${s['total_cost']:,.0f} | "
        f"${s['total_pnl']:+,.0f} | {s['roi_pct']:+.2f}% | {s['hit_profit_pct']:.1f}% |"
    )


def write_report(path, source: str, prereg: dict, primary: dict,
                 exploratory: pd.DataFrame, backtest_res: dict,
                 sweep: "pd.DataFrame | None" = None,
                 lag: "pd.DataFrame | None" = None) -> None:
    lines = ["# McKenna Derby — run report", ""]
    lines += [
        f"- **Data source:** {source}",
        f"- **Pre-registration:** primary set `{prereg['primary_number_set']}`, "
        f"threshold {prereg['primary_threshold_pct']}%, takeout {prereg['takeout']}, "
        f"declared {prereg['declared_on']}",
        f"- **Prediction:** {prereg['prediction']}",
        "",
    ]

    lines += ["## Primary analysis (pre-registered)", ""]
    for k in PRIMARY_KEYS:
        lines.append(f"- **{k}:** {primary[k]}")
    lines.append("")

    lines += [
        "## Exploratory: all number sets (Bonferroni x4)", "",
        "```", exploratory.to_string(index=False), "```", "",
    ]

    lines += [
        "## Backtest (buy every trifecta combination)", "",
        "| strategy | races | cost | P&L | ROI | profitable races |",
        "|---|---|---|---|---|---|",
        _backtest_row("Timewave-filtered", backtest_res["strategy"]),
        _backtest_row("Bet every race", backtest_res["bet_every_race"]),
        "",
    ]
    src_counts = backtest_res["per_race"]["payout_source"].value_counts().to_dict()
    lines += [
        f"Payout sources: {src_counts}. Modeled payouts have an expected ROI of "
        "exactly -takeout by construction; conclusions about profitability "
        "require actual historical dividends.",
        "",
    ]

    if sweep is not None:
        lines += [
            "## Exploratory: threshold sweep (p-hacking hazard — shape only)", "",
            "```", sweep.to_string(index=False), "```", "",
        ]
    if lag is not None:
        best = lag.loc[lag["spearman_r"].abs().idxmax()]
        lines += [
            "## Exploratory: lead-lag", "",
            f"Strongest |r| at lag {int(best['lag_days'])} days "
            f"(r = {best['spearman_r']:+.4f}).",
            "", "```", lag.to_string(index=False), "```", "",
        ]

    lines += ["## Plot", "", "![novelty vs timewave](novelty_vs_timewave.png)", ""]
    Path(path).write_text("\n".join(lines))
```

- **Verify:** `cd /Users/thedao/Projects/mckenna-derby && .venv/bin/python -c "from mckenna_derby.report import write_report; print('ok')"`

### Task 13 — Wire it together (replace `run_analysis.py`)

- **File(s):** `/Users/thedao/Projects/mckenna-derby/run_analysis.py` (full replacement)
- **Change:** Reads `prereg.json` for the primary analysis; adds `--csv` (generic loader), `--sweep`, and `--max-lag`; runs the exploratory all-sets comparison with Bonferroni correction; writes the markdown report. The `plot` function is unchanged from Phase 1. Replace the entire file with:

```python
#!/usr/bin/env python3
"""End-to-end pipeline: data -> novelty -> timewave comparison -> backtest -> report.

Usage:
    python run_analysis.py                          # synthetic demo data
    python run_analysis.py --hk rawdata/            # gdaley/hkracing Kaggle data
    python run_analysis.py --csv my_races.csv       # generic runner-level CSV
    python run_analysis.py --sweep --max-lag 30     # extra exploratory sections
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from mckenna_derby import backtest as bt
from mckenna_derby import compare, data, novelty, report

ROOT = Path(__file__).parent
OUTPUT = ROOT / "output"
ALL_SETS = ["kelley", "watkins", "sheliak", "huangti"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hk", metavar="DIR", help="path to gdaley/hkracing Kaggle data")
    ap.add_argument("--csv", metavar="FILE", help="generic runner-level CSV")
    ap.add_argument("--prereg", default=str(ROOT / "prereg.json"))
    ap.add_argument("--start", default="2005-01-01", help="synthetic data start date")
    ap.add_argument("--end", default="2012-12-20", help="synthetic data end date")
    ap.add_argument("--sweep", action="store_true", help="exploratory threshold sweep")
    ap.add_argument("--max-lag", type=int, default=0,
                    help="exploratory lead-lag window in days (0 = off)")
    args = ap.parse_args()
    OUTPUT.mkdir(exist_ok=True)
    prereg = json.loads(Path(args.prereg).read_text())

    if args.hk:
        source = f"hkracing ({args.hk})"
        runners = data.load_hk_racing(args.hk)
    elif args.csv:
        source = f"csv ({args.csv})"
        runners = data.load_generic_csv(args.csv)
    else:
        source = "synthetic demo (market-calibrated: expect null result, ROI ~ -takeout)"
        runners = data.synthetic_races(
            dt.date.fromisoformat(args.start), dt.date.fromisoformat(args.end)
        )
    print(f"Data: {source}")
    print(f"  {runners['race_id'].nunique():,} races, {len(runners):,} runners, "
          f"{runners['date'].min().date()} to {runners['date'].max().date()}")

    print("Scoring race novelty ...")
    scores = novelty.score_races(runners)
    daily = novelty.daily_novelty(scores, metric=prereg["metric"])
    scores.to_csv(OUTPUT / "race_scores.csv", index=False)

    print(f"Primary analysis (pre-registered): {prereg['primary_number_set']} timewave ...")
    primary = compare.compare(daily, number_set=prereg["primary_number_set"])
    print(f"  Spearman r = {primary['spearman_r']:+.4f}, "
          f"permutation p = {primary['permutation_p']:.3f}")
    print(f"  -> {primary['interpretation']}")

    print("Exploratory: all number sets (Bonferroni x4) ...")
    exploratory_rows = []
    for ns in ALL_SETS:
        r = primary if ns == prereg["primary_number_set"] else compare.compare(
            daily, number_set=ns
        )
        exploratory_rows.append(
            {
                "number_set": ns,
                "spearman_r": round(r["spearman_r"], 4),
                "permutation_p": r["permutation_p"],
                "bonferroni_p": min(1.0, r["permutation_p"] * len(ALL_SETS)),
            }
        )
    exploratory = pd.DataFrame(exploratory_rows)

    print("Backtesting buy-all-trifecta-combos strategy ...")
    tw = primary["timewave"]
    res = bt.backtest(scores, tw,
                      novelty_threshold_pct=prereg["primary_threshold_pct"],
                      takeout=prereg["takeout"])
    for label, key in [("Timewave-filtered", "strategy"),
                       ("Bet every race", "bet_every_race")]:
        s = res[key]
        print(f"  {label}: {s['races']:,} races, cost ${s['total_cost']:,.0f}, "
              f"P&L ${s['total_pnl']:+,.0f}, ROI {s['roi_pct']:+.2f}%, "
              f"profitable races {s['hit_profit_pct']:.1f}%")

    sweep = (bt.threshold_sweep(scores, tw, takeout=prereg["takeout"])
             if args.sweep else None)
    lag = (compare.lead_lag(daily, prereg["primary_number_set"], max_lag=args.max_lag)
           if args.max_lag > 0 else None)

    plot(daily, tw, res["per_race"], prereg["primary_number_set"])
    report.write_report(OUTPUT / "report.md", source, prereg, primary,
                        exploratory, res, sweep, lag)
    print(f"\nOutputs written to {OUTPUT}/ "
          "(report.md, race_scores.csv, novelty_vs_timewave.png)")


def plot(daily: pd.Series, tw: pd.Series, per_race: pd.DataFrame, number_set: str) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=True)
    dates = pd.to_datetime(pd.Index(daily.index))

    ax = axes[0]
    ax.plot(dates, daily.to_numpy(), lw=0.4, color="tab:blue", alpha=0.5)
    ax.plot(dates, daily.rolling(30, min_periods=5).mean().to_numpy(),
            lw=1.5, color="tab:blue", label="30-day mean")
    ax.set_ylabel("Race novelty (z)")
    ax.set_title("Daily horse-racing novelty (odds-implied surprisal)")
    ax.legend(loc="upper right")

    ax = axes[1]
    ax.plot(dates, tw.to_numpy(), lw=1.0, color="tab:purple")
    ax.invert_yaxis()  # McKenna: low value = high novelty; flip so up = novel
    ax.set_ylabel("Timewave (inverted)")
    ax.set_title(f"McKenna Timewave Zero ({number_set} set) — up = higher predicted novelty")

    ax = axes[2]
    daily_pnl = per_race.groupby("day")["pnl"].sum()
    pnl_dates = pd.to_datetime(pd.Index(daily_pnl.index))
    ax.plot(pnl_dates, daily_pnl.cumsum().to_numpy(), lw=1.2, color="tab:red",
            label="Bet every race")
    sel = per_race[per_race["selected"]].groupby("day")["pnl"].sum()
    strat = sel.reindex(daily_pnl.index, fill_value=0.0).cumsum()
    ax.plot(pnl_dates, strat.to_numpy(), lw=1.2, color="tab:green",
            label="Timewave-filtered")
    ax.axhline(0, color="k", lw=0.5)
    ax.set_ylabel("Cumulative P&L ($)")
    ax.set_title("Buy-every-trifecta-combination backtest")
    ax.legend(loc="best")
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())

    fig.tight_layout()
    fig.savefig(OUTPUT / "novelty_vs_timewave.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    main()
```

- **Verify:** `cd /Users/thedao/Projects/mckenna-derby && .venv/bin/python run_analysis.py --start 2010-01-01 --end 2010-06-30 --sweep --max-lag 10 && cat output/report.md`

### Task 14 — Full demo run + regression check

- **File(s):** none (verification task)
- **Change:** Run the whole suite and the full-length demo. Expected demo behavior (synthetic data is the null fixture): permutation p well above 0.05, both ROIs near −22%.

- **Verify:**

```bash
cd /Users/thedao/Projects/mckenna-derby && .venv/bin/pytest -q && .venv/bin/python run_analysis.py --sweep --max-lag 30
```

Confirm in the console output: (1) "No statistically meaningful relationship" for the primary analysis, (2) both ROI numbers between −30% and −18%, (3) `output/report.md` exists with all sections including the sweep and lead-lag.

### Task 15 — Update the README usage section

- **File(s):** `/Users/thedao/Projects/mckenna-derby/README.md`
- **Change:** In the "Quick start" section, replace the line:

```bash
python run_analysis.py            # synthetic demo data (null hypothesis)
```

with:

```bash
pip install -e . pytest && pytest -q   # verify the frozen core first
python run_analysis.py                 # synthetic demo data (null hypothesis)
python run_analysis.py --sweep --max-lag 30   # with exploratory sections
```

And at the end of the "Using real data" section, append this paragraph:

```markdown
The primary analysis (number set, threshold, takeout) is fixed in
`prereg.json` and must not be edited after the first real-data run. To use
real trifecta dividends, add a `trifecta_payout` column (dividend per $1
winning ticket, repeated on each row of the race) to a CSV and load it with
`--csv`; the backtest will prefer actual dividends over the modeled payout.
```

- **Verify:** `grep -c "prereg.json" /Users/thedao/Projects/mckenna-derby/README.md` (prints 1 or more)

### Task 16 — The real-data run (requires Kaggle credentials)

- **File(s):** none (execution task). Requires `~/.kaggle/kaggle.json` (from kaggle.com → Account → Create New API Token). If credentials are unavailable, STOP here and report — do not fake this step.
- **Change:** Download the Hong Kong dataset and run the pre-registered analysis.

```bash
cd /Users/thedao/Projects/mckenna-derby
.venv/bin/pip install kaggle
.venv/bin/kaggle datasets download -d gdaley/hkracing -p rawdata --unzip
.venv/bin/python run_analysis.py --hk rawdata/ --sweep --max-lag 30
```

- **Verify:** `cat /Users/thedao/Projects/mckenna-derby/output/report.md` — the report's primary-analysis section is the experiment's answer. Copy it verbatim into your final summary to the user, whatever it says. Do not rerun with different settings to get a "better" result.

## Test plan

- [ ] `cd /Users/thedao/Projects/mckenna-derby && .venv/bin/pytest -q` — full suite (timewave golden values, novelty math, data validation, dividend override, backtest selection, sweep, lead-lag)
- [ ] `.venv/bin/python run_analysis.py --start 2010-01-01 --end 2010-06-30 --sweep --max-lag 10` — fast end-to-end smoke (~1 min)
- [ ] `.venv/bin/python run_analysis.py --sweep --max-lag 30` — full synthetic null run; primary permutation p > 0.05 and ROI ≈ −22% confirm the pipeline is honest
- [ ] `.venv/bin/python run_analysis.py --hk rawdata/ --sweep --max-lag 30` — the actual experiment (only with Kaggle data present)

## Rollout / notes

- [ ] No migrations, env vars, or feature flags. Pure local analysis.
- [ ] `prereg.json` is append-never: commit it before Task 16 and do not touch it afterward.
- [ ] Rollback: the repo is a git repo — commit after each passing task (`git add -A && git commit -m "Task N: <name>"`) so any task can be reverted with `git revert`.
- [ ] `rawdata/` and `output/` are gitignored; only code, tests, and `prereg.json` are committed.

## Open questions

- [ ] **Real trifecta dividends:** the HKJC publishes historical dividends but the Kaggle dataset does not include them. Does the user want to source these (manual export or a paid data vendor)? Until then, backtest conclusions are model-based and the report says so.
- [ ] **Replication dataset:** after the HK run, a second market (UK/US) would guard against a dataset-specific fluke. Which one, if any, is worth the user's time depends on the HK result.
- [ ] **Pool-dilution:** buying all combinations in a real (small) parimutuel pool dilutes your own payout. Modeling this needs pool-size data we don't have; noted as a known limitation in any conclusion.

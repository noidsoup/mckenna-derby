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

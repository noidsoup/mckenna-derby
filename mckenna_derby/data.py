"""Data loading: bundled HK/UK races, Kaggle downloads, CSVs, or synthetic demo.

All loaders return a runner-level dataframe with columns:
    date, race_id, horse, decimal_odds, finish_position
and optionally:
    win_payout       -- actual win dividend per $1 stake (winner row only)
    place_payout     -- actual place dividend per $1 stake (placed rows)
    trifecta_payout  -- actual dividend paid per $1 winning trifecta/tierce
                        ticket, one value repeated on every row of the race.
                        When present, the backtest uses it instead of the
                        modeled parimutuel payout.

Default data
------------
``load_bundled_hk`` reads the committed processed CSV under
``mckenna_derby/datasets/hk_runners.csv`` (Hong Kong races 1997–2005 from
Kaggle ``gdaley/hkracing``). This is the default for the dashboard and CLI.

The Kaggle dump includes **win/place** dividends (joined into the bundled
CSV) but **not** trifecta/trio/tierce. To attach real exotic settlement when
you obtain them::

    python scripts/build_bundled_data.py --exotics path/to/exotic_dividends.csv

See ``mckenna_derby/datasets/README.md`` and
``exotic_dividends.example.csv`` for the join schema.

Rebuild from a local Kaggle download::

    kaggle datasets download -d gdaley/hkracing -p rawdata --unzip
    python scripts/build_bundled_data.py

Additional free bundled source
------------------------------
``load_bundled_uk`` reads ``uk_runners.csv`` — a validated slice of Kaggle
``hwaitt/horse-racing`` (UK/Ireland-style international dump, 2008–2012).
Exploratory only; does **not** replace the locked HK primary claim.
Rebuild::

    kaggle datasets download -d hwaitt/horse-racing -p rawdata-uk --unzip
    python scripts/build_bundled_uk.py

Other sources
-------------
- ``load_hk_racing`` — raw ``races.csv`` + ``runs.csv`` under a directory
- ``hwaitt/horse-racing`` full dump via ``load_uk_racing`` (optional date filter)
- ``synthetic_races`` — market-calibrated null fixture (Harville-sampled)
"""

from __future__ import annotations

import datetime as dt
from importlib import resources
from pathlib import Path

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = {"date", "race_id", "horse", "decimal_odds", "finish_position"}

# HKJC published dividends in gdaley/hkracing are per $10 stake.
HKJC_DIVIDEND_UNIT = 10.0

# Optional companion CSV for exotic settlement (see datasets README).
EXOTIC_PAYOUT_COLUMNS = ("trifecta_payout", "tierce_payout", "trio_payout")


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


def bundled_hk_path() -> Path:
    """Filesystem path to the committed Hong Kong runners CSV."""
    # Prefer importlib.resources so installed wheels resolve correctly.
    try:
        root = resources.files("mckenna_derby.datasets")
        return Path(str(root.joinpath("hk_runners.csv")))
    except (TypeError, FileNotFoundError, ModuleNotFoundError):
        return Path(__file__).resolve().parent / "datasets" / "hk_runners.csv"


def load_bundled_hk() -> pd.DataFrame:
    """Load the packaged Hong Kong dataset (default real-data source)."""
    path = bundled_hk_path()
    if not path.is_file():
        raise FileNotFoundError(
            f"bundled HK data missing at {path}; "
            "run: python scripts/build_bundled_data.py"
        )
    return load_generic_csv(path)


def bundled_uk_path() -> Path:
    """Filesystem path to the committed UK/Ireland runners CSV (exploratory)."""
    try:
        root = resources.files("mckenna_derby.datasets")
        return Path(str(root.joinpath("uk_runners.csv")))
    except (TypeError, FileNotFoundError, ModuleNotFoundError):
        return Path(__file__).resolve().parent / "datasets" / "uk_runners.csv"


def load_bundled_uk() -> pd.DataFrame:
    """Load the packaged UK/Ireland slice (exploratory free source).

    Derived from Kaggle ``hwaitt/horse-racing`` (2008-01-01 → 2012-12-20).
    Odds come from implied win probabilities (``decimalPrice`` → ``1/p``).
    No real win/place/trifecta dividends are attached — backtest settlement
    stays modeled. Not the locked primary claim (see ``prereg.json`` / HK).
    """
    path = bundled_uk_path()
    if not path.is_file():
        raise FileNotFoundError(
            f"bundled UK data missing at {path}; "
            "run: python scripts/build_bundled_uk.py"
        )
    return load_generic_csv(path)


def _per_dollar(dividend: pd.Series, unit: float = HKJC_DIVIDEND_UNIT) -> pd.Series:
    """Convert published HKJC dividends (usually per $10) to per-$1 payouts."""
    return dividend.astype(float) / float(unit)


def _attach_win_place_dividends(
    runners: pd.DataFrame, races: pd.DataFrame
) -> pd.DataFrame:
    """Map race-level win/place dividend columns onto runner rows.

    ``races`` must include ``race_id`` plus the gdaley/hkracing combination
    and dividend columns. Output adds ``win_payout`` / ``place_payout``
    (per $1 stake); non-winning / non-placed runners get NaN.
    """
    out = runners.copy()
    out["win_payout"] = np.nan
    out["place_payout"] = np.nan

    race_cols = set(races.columns)
    if not {"race_id", "win_combination1", "win_dividend1"}.issubset(race_cols):
        return out

    win_parts = []
    for comb_col, div_col in (
        ("win_combination1", "win_dividend1"),
        ("win_combination2", "win_dividend2"),
    ):
        if comb_col not in race_cols or div_col not in race_cols:
            continue
        part = races[["race_id", comb_col, div_col]].dropna()
        if part.empty:
            continue
        part = part.rename(columns={comb_col: "horse", div_col: "win_payout"})
        part["horse"] = part["horse"].astype(int)
        part["win_payout"] = _per_dollar(part["win_payout"])
        win_parts.append(part[["race_id", "horse", "win_payout"]])
    if win_parts:
        win_map = pd.concat(win_parts, ignore_index=True).drop_duplicates(
            subset=["race_id", "horse"], keep="first"
        )
        out = out.drop(columns=["win_payout"]).merge(
            win_map, on=["race_id", "horse"], how="left"
        )

    place_parts = []
    for i in range(1, 5):
        comb_col, div_col = f"place_combination{i}", f"place_dividend{i}"
        if comb_col not in race_cols or div_col not in race_cols:
            continue
        part = races[["race_id", comb_col, div_col]].dropna()
        if part.empty:
            continue
        part = part.rename(columns={comb_col: "horse", div_col: "place_payout"})
        part["horse"] = part["horse"].astype(int)
        part["place_payout"] = _per_dollar(part["place_payout"])
        place_parts.append(part[["race_id", "horse", "place_payout"]])
    if place_parts:
        place_map = pd.concat(place_parts, ignore_index=True).drop_duplicates(
            subset=["race_id", "horse"], keep="first"
        )
        out = out.drop(columns=["place_payout"]).merge(
            place_map, on=["race_id", "horse"], how="left"
        )

    return out


def load_exotic_dividends(path: str | Path) -> pd.DataFrame:
    """Load a race-level exotic-dividend companion CSV.

    Required columns: ``race_id`` and at least one of
    ``trifecta_payout``, ``tierce_payout``, ``trio_payout``.

    All payout columns must already be **per $1 stake** (convert from the
    published unit before writing the companion file). ``tierce_payout`` is
    treated as an alias for ordered 1-2-3 settlement and is copied onto
    ``trifecta_payout`` when the latter is missing.
    """
    path = Path(path)
    df = pd.read_csv(path)
    if "race_id" not in df.columns:
        raise ValueError(f"{path}: missing race_id column")
    present = [c for c in EXOTIC_PAYOUT_COLUMNS if c in df.columns]
    if not present:
        raise ValueError(
            f"{path}: need one of {EXOTIC_PAYOUT_COLUMNS}; found {list(df.columns)}"
        )
    keep = ["race_id"] + present
    if "date" in df.columns:
        keep.append("date")
    out = df[keep].copy()
    out["race_id"] = out["race_id"].astype(out["race_id"].dtype)
    # One row per race_id (last wins if duplicates).
    out = out.drop_duplicates(subset=["race_id"], keep="last")
    if "trifecta_payout" not in out.columns and "tierce_payout" in out.columns:
        out["trifecta_payout"] = out["tierce_payout"]
    return out.reset_index(drop=True)


def merge_exotic_dividends(
    runners: pd.DataFrame, exotics: pd.DataFrame
) -> pd.DataFrame:
    """Left-join race-level exotic payouts onto every runner row of a race.

    Prefer ``trifecta_payout`` (ordered 1-2-3). ``trio_payout`` (any-order)
    is carried through for diagnostics but is **not** used by the trifecta
    backtest settlement path.
    """
    if exotics.empty:
        return runners
    cols = ["race_id"] + [
        c for c in ("trifecta_payout", "tierce_payout", "trio_payout") if c in exotics.columns
    ]
    pay = exotics[cols].drop_duplicates(subset=["race_id"], keep="last")
    if "trifecta_payout" not in pay.columns and "tierce_payout" in pay.columns:
        pay = pay.copy()
        pay["trifecta_payout"] = pay["tierce_payout"]
    out = runners.merge(pay, on="race_id", how="left", suffixes=("", "_exotic"))
    # If runners already had trifecta_payout, prefer non-null existing values.
    if "trifecta_payout_exotic" in out.columns:
        if "trifecta_payout" in runners.columns:
            out["trifecta_payout"] = out["trifecta_payout"].where(
                out["trifecta_payout"].notna(), out["trifecta_payout_exotic"]
            )
        else:
            out["trifecta_payout"] = out["trifecta_payout_exotic"]
        out = out.drop(columns=["trifecta_payout_exotic"])
    return out


def load_hk_racing(
    rawdata_dir: str | Path,
    *,
    exotics_path: str | Path | None = None,
    include_win_place: bool = True,
) -> pd.DataFrame:
    """Load the gdaley/hkracing Kaggle dataset (races.csv + runs.csv).

    When ``include_win_place`` is True (default), attaches real ``win_payout``
    and ``place_payout`` columns (per $1) from the race-level dividend fields.
    Optional ``exotics_path`` merges a companion exotic-dividends CSV (see
    ``load_exotic_dividends``).
    """
    rawdata_dir = Path(rawdata_dir)
    race_usecols = ["race_id", "date"]
    if include_win_place:
        race_usecols += [
            "place_combination1",
            "place_combination2",
            "place_combination3",
            "place_combination4",
            "place_dividend1",
            "place_dividend2",
            "place_dividend3",
            "place_dividend4",
            "win_combination1",
            "win_dividend1",
            "win_combination2",
            "win_dividend2",
        ]
    races = pd.read_csv(rawdata_dir / "races.csv", usecols=race_usecols)
    runs = pd.read_csv(
        rawdata_dir / "runs.csv",
        usecols=["race_id", "horse_no", "result", "win_odds"],
    )
    df = runs.merge(races[["race_id", "date"]], on="race_id")
    df = df.rename(
        columns={
            "horse_no": "horse",
            "win_odds": "decimal_odds",
            "result": "finish_position",
        }
    )
    df = df.dropna(subset=["finish_position"])
    df = validate_runners(df)
    if include_win_place:
        df = _attach_win_place_dividends(df, races)
    if exotics_path is not None:
        df = merge_exotic_dividends(df, load_exotic_dividends(exotics_path))
    return df


def load_uk_racing(
    rawdata_dir: str | Path,
    *,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    """Load the hwaitt/horse-racing Kaggle dataset (races_YYYY + horses_YYYY).

    ``decimalPrice`` in this dataset is an implied win probability in (0, 1];
    we convert to decimal odds as ``1 / decimalPrice``. Optional ``start`` /
    ``end`` (ISO dates) filter race dates — useful because the raw dump
    includes a few malformed future-dated rows.
    """
    rawdata_dir = Path(rawdata_dir)
    race_files = sorted(rawdata_dir.glob("races_*.csv"))
    horse_files = sorted(rawdata_dir.glob("horses_*.csv"))
    if not race_files or not horse_files:
        raise FileNotFoundError(
            f"expected races_*.csv and horses_*.csv under {rawdata_dir}"
        )
    races = pd.concat(
        (pd.read_csv(p, usecols=["rid", "date"]) for p in race_files),
        ignore_index=True,
    )
    horses = pd.concat(
        (
            pd.read_csv(p, usecols=["rid", "horseName", "decimalPrice", "position"])
            for p in horse_files
        ),
        ignore_index=True,
    )
    df = horses.merge(races, on="rid", how="inner")
    df = df.rename(
        columns={
            "rid": "race_id",
            "horseName": "horse",
            "position": "finish_position",
        }
    )
    df["date"] = pd.to_datetime(df["date"], format="mixed", errors="coerce")
    df = df.dropna(subset=["date", "decimalPrice", "finish_position"])
    if start is not None:
        df = df[df["date"] >= pd.Timestamp(start)]
    if end is not None:
        df = df[df["date"] <= pd.Timestamp(end)]
    # decimalPrice is implied probability; reject non-positive / >1 junk.
    df = df[(df["decimalPrice"] > 0.0) & (df["decimalPrice"] <= 1.0)]
    df["decimal_odds"] = 1.0 / df["decimalPrice"]
    df = df.drop(columns=["decimalPrice"])
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

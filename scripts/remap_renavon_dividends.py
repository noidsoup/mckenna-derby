#!/usr/bin/env python3
"""Remap a Renavon ``hkjc_dividends`` export onto Kaggle ``race_id`` values.

Renavon rows are long-format (one row per pool per race) with::

    race_date, venue_code, race_number, pool_type, dividend, return_per_dollar

Kaggle ``gdaley/hkracing`` uses integer ``race_id`` keyed by
``date + venue + race_no`` in ``rawdata/races.csv``.

This script filters TIERCE / TRIO, converts to **per $1** payouts, joins to
Kaggle race ids, and writes the companion CSV expected by::

    python scripts/build_bundled_data.py --exotics path/to/exotic_dividends.csv

Example (after you purchase / download the archive)::

    python scripts/remap_renavon_dividends.py \\
        --renavon path/to/hkjc_dividends.csv.gz \\
        --races rawdata/races.csv \\
        --out rawdata/exotic_dividends.csv \\
        --start 2001-01-01 --end 2005-08-28

Does **not** download or purchase anything. Renavon Full Archive starts
Jan 2001 — years 1997–2000 in the bundled CSV stay modeled.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RACES = ROOT / "rawdata" / "races.csv"
DEFAULT_OUT = ROOT / "rawdata" / "exotic_dividends.csv"


def _read_renavon(path: Path) -> pd.DataFrame:
    path = Path(path)
    if path.suffix == ".gz" or path.name.endswith(".csv.gz"):
        df = pd.read_csv(path, compression="gzip")
    else:
        df = pd.read_csv(path)
    required = {"race_date", "venue_code", "race_number", "pool_type"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path}: missing columns {sorted(missing)}")
    if "return_per_dollar" not in df.columns and "dividend" not in df.columns:
        raise ValueError(f"{path}: need return_per_dollar or dividend")
    return df


def remap_renavon_to_exotics(
    renavon: pd.DataFrame,
    races: pd.DataFrame,
    *,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    """Pivot TIERCE/TRIO onto one row per Kaggle ``race_id`` (per-$1)."""
    need = {"race_id", "date", "venue", "race_no"}
    if not need.issubset(races.columns):
        raise ValueError(f"races.csv needs {sorted(need)}")

    rv = renavon.copy()
    rv["race_date"] = pd.to_datetime(rv["race_date"], utc=True).dt.tz_localize(None)
    rv["date"] = rv["race_date"].dt.strftime("%Y-%m-%d")
    if start:
        rv = rv[rv["date"] >= start]
    if end:
        rv = rv[rv["date"] <= end]

    pools = rv[rv["pool_type"].isin(["TIERCE", "TRIO"])].copy()
    if pools.empty:
        return pd.DataFrame(
            columns=["race_id", "date", "trifecta_payout", "tierce_payout", "trio_payout"]
        )

    # Prefer return_per_dollar (already per $1). Else dividend is per $10.
    if "return_per_dollar" in pools.columns:
        pools["payout_per_dollar"] = pd.to_numeric(pools["return_per_dollar"], errors="coerce")
    else:
        pools["payout_per_dollar"] = pd.to_numeric(pools["dividend"], errors="coerce") / 10.0

    pools["venue"] = pools["venue_code"].astype(str).str.upper()
    pools["race_no"] = pd.to_numeric(pools["race_number"], errors="coerce").astype("Int64")

    wide = (
        pools.pivot_table(
            index=["date", "venue", "race_no"],
            columns="pool_type",
            values="payout_per_dollar",
            aggfunc="last",
        )
        .reset_index()
        .rename(columns={"TIERCE": "tierce_payout", "TRIO": "trio_payout"})
    )
    for col in ("tierce_payout", "trio_payout"):
        if col not in wide.columns:
            wide[col] = pd.NA

    key = races[["race_id", "date", "venue", "race_no"]].copy()
    key["date"] = pd.to_datetime(key["date"]).dt.strftime("%Y-%m-%d")
    key["venue"] = key["venue"].astype(str).str.upper()
    key["race_no"] = pd.to_numeric(key["race_no"], errors="coerce").astype("Int64")

    merged = key.merge(wide, on=["date", "venue", "race_no"], how="inner")
    merged["trifecta_payout"] = merged["tierce_payout"]
    out = merged[
        ["race_id", "date", "trifecta_payout", "tierce_payout", "trio_payout"]
    ].drop_duplicates(subset=["race_id"], keep="last")
    return out.reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--renavon",
        type=Path,
        required=True,
        help="Renavon hkjc_dividends CSV or .csv.gz",
    )
    ap.add_argument(
        "--races",
        type=Path,
        default=DEFAULT_RACES,
        help="Kaggle races.csv with race_id/date/venue/race_no",
    )
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--start", default="2001-01-01", help="inclusive YYYY-MM-DD")
    ap.add_argument("--end", default="2005-08-28", help="inclusive YYYY-MM-DD")
    args = ap.parse_args()

    if not args.races.exists():
        raise SystemExit(
            f"Missing {args.races}. Download gdaley/hkracing into rawdata/ first."
        )

    renavon = _read_renavon(args.renavon)
    races = pd.read_csv(args.races)
    out = remap_renavon_to_exotics(
        renavon, races, start=args.start, end=args.end
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)

    n_tri = int(out["trifecta_payout"].notna().sum())
    n_trio = int(out["trio_payout"].notna().sum()) if "trio_payout" in out.columns else 0
    print(
        f"Wrote {args.out}: {len(out):,} races matched "
        f"({n_tri:,} with tierce/trifecta, {n_trio:,} with trio) "
        f"in {args.start}…{args.end}"
    )
    if len(out) == 0:
        print(
            "  NOTE: zero matches. Free Renavon sample is recent-only (~6 months) "
            "and will not overlap 1997–2005. Need Full Archive (from Jan 2001)."
        )


if __name__ == "__main__":
    main()

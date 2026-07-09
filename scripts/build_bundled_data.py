#!/usr/bin/env python3
"""Rebuild the bundled Hong Kong runner CSV from a local Kaggle download.

Requires ``rawdata/races.csv`` and ``rawdata/runs.csv`` from::

    kaggle datasets download -d gdaley/hkracing -p rawdata --unzip

Writes ``mckenna_derby/datasets/hk_runners.csv`` (validated runner-level
schema with real win/place dividends when present in races.csv).

Optional exotic dividends (trifecta/tierce/trio) are **not** in the Kaggle
dump. When you obtain a companion CSV, pass ``--exotics``::

    python scripts/build_bundled_data.py \\
        --exotics mckenna_derby/datasets/exotic_dividends.csv

See ``mckenna_derby/datasets/README.md`` and
``exotic_dividends.example.csv`` for the join schema (race_id + per-$1
payouts).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from mckenna_derby import data

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW = ROOT / "rawdata"
DEFAULT_OUT = ROOT / "mckenna_derby" / "datasets" / "hk_runners.csv"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--rawdata",
        type=Path,
        default=DEFAULT_RAW,
        help="directory with races.csv + runs.csv (default: rawdata/)",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="output CSV path (default: mckenna_derby/datasets/hk_runners.csv)",
    )
    ap.add_argument(
        "--exotics",
        type=Path,
        default=None,
        help=(
            "optional companion CSV with race_id + trifecta_payout "
            "(and/or tierce_payout / trio_payout), already per $1 stake"
        ),
    )
    ap.add_argument(
        "--no-win-place",
        action="store_true",
        help="skip attaching win/place dividends from races.csv",
    )
    args = ap.parse_args()

    runners = data.load_hk_racing(
        args.rawdata,
        exotics_path=args.exotics,
        include_win_place=not args.no_win_place,
    )
    export = runners.copy()
    export["date"] = export["date"].dt.strftime("%Y-%m-%d")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    export.to_csv(args.out, index=False)

    n_races = export["race_id"].nunique()
    n_win = (
        int(export["win_payout"].notna().sum())
        if "win_payout" in export.columns
        else 0
    )
    n_place = (
        int(export["place_payout"].notna().sum())
        if "place_payout" in export.columns
        else 0
    )
    n_tri = (
        int(export.groupby("race_id")["trifecta_payout"].first().notna().sum())
        if "trifecta_payout" in export.columns
        else 0
    )
    print(
        f"Wrote {args.out} ({args.out.stat().st_size:,} bytes): "
        f"{n_races:,} races, {len(export):,} runners, "
        f"{export['date'].min()} to {export['date'].max()}"
    )
    print(
        f"  win_payout rows: {n_win:,} | place_payout rows: {n_place:,} | "
        f"trifecta_payout races: {n_tri:,}"
    )
    if n_tri == 0:
        print(
            "  NOTE: no trifecta/tierce dividends attached. "
            "Kaggle gdaley/hkracing has win/place only. "
            "Pass --exotics when you have a companion CSV."
        )


if __name__ == "__main__":
    main()

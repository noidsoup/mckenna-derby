#!/usr/bin/env python3
"""Rebuild the bundled UK/Ireland runner CSV from a local Kaggle download.

Requires yearly ``races_YYYY.csv`` + ``horses_YYYY.csv`` under a directory
(default ``rawdata-uk/``) from::

    kaggle datasets download -d hwaitt/horse-racing -p rawdata-uk --unzip

Writes ``mckenna_derby/datasets/uk_runners.csv`` — a validated slice covering
the usable Timewave historical window (default 2008-01-01 → 2012-12-20).

This is an **exploratory** free source. It does not replace the locked Hong
Kong primary claim in ``prereg.json``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from mckenna_derby import data

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW = ROOT / "rawdata-uk"
DEFAULT_OUT = ROOT / "mckenna_derby" / "datasets" / "uk_runners.csv"
# Prefer years that overlap the usable Timewave window (ends ~2012-12-21)
# and stay a commit-friendly size (~16 MB) while still larger than HK.
DEFAULT_START = "2008-01-01"
DEFAULT_END = "2012-12-20"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--rawdata",
        type=Path,
        default=DEFAULT_RAW,
        help="directory with races_*.csv + horses_*.csv (default: rawdata-uk/)",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="output CSV path (default: mckenna_derby/datasets/uk_runners.csv)",
    )
    ap.add_argument(
        "--start",
        default=DEFAULT_START,
        help=f"inclusive start date (default: {DEFAULT_START})",
    )
    ap.add_argument(
        "--end",
        default=DEFAULT_END,
        help=f"inclusive end date (default: {DEFAULT_END})",
    )
    args = ap.parse_args()

    runners = data.load_uk_racing(args.rawdata, start=args.start, end=args.end)
    export = runners.copy()
    export["date"] = export["date"].dt.strftime("%Y-%m-%d")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    export.to_csv(args.out, index=False)

    n_races = export["race_id"].nunique()
    print(
        f"Wrote {args.out} ({args.out.stat().st_size:,} bytes): "
        f"{n_races:,} races, {len(export):,} runners, "
        f"{export['date'].min()} to {export['date'].max()}"
    )
    print(
        "  NOTE: exploratory free source — odds from implied probability; "
        "no real win/place/trifecta dividends. HK remains the locked default."
    )


if __name__ == "__main__":
    main()

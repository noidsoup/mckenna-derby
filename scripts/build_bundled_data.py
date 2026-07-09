#!/usr/bin/env python3
"""Rebuild the bundled Hong Kong runner CSV from a local Kaggle download.

Requires ``rawdata/races.csv`` and ``rawdata/runs.csv`` from::

    kaggle datasets download -d gdaley/hkracing -p rawdata --unzip

Writes ``mckenna_derby/datasets/hk_runners.csv`` (validated runner-level schema).
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
    args = ap.parse_args()

    runners = data.load_hk_racing(args.rawdata)
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


if __name__ == "__main__":
    main()

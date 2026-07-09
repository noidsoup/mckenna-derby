#!/usr/bin/env python3
"""McKenna engine: four-strategy selective trifecta backtest.

Usage:
    python run_mckenna.py                      # synthetic demo data
    python run_mckenna.py --beta 1.15          # assume favorites overbet
    python run_mckenna.py --hk rawdata/        # gdaley/hkracing Kaggle data
    python run_mckenna.py --csv my_races.csv   # generic runner-level CSV

REMEMBER: --beta is an ASSUMPTION about pool bias, not a measurement.
beta=1.0 (default) is the fair-pool null case and should find no edge.
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from mckenna_derby import data
from mckenna_derby.mckenna_engine import selective_backtest

ROOT = Path(__file__).parent
OUTPUT = ROOT / "output"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hk", metavar="DIR", help="path to gdaley/hkracing Kaggle data")
    ap.add_argument("--csv", metavar="FILE", help="generic runner-level CSV")
    ap.add_argument("--start", default="2010-01-01", help="synthetic data start date")
    ap.add_argument("--end", default="2010-12-31", help="synthetic data end date")
    ap.add_argument("--beta", type=float, default=1.0,
                    help="assumed pool bias exponent (1.0 = fair pool, null case)")
    ap.add_argument("--k-max", type=int, default=50,
                    help="max tickets per race (I Ching selector caps the rest)")
    ap.add_argument("--gate-pct", type=float, default=20.0,
                    help="bet only days in the top X%% of the resonance signal")
    ap.add_argument("--takeout", type=float, default=0.22)
    ap.add_argument("--seed", type=int, default=1904)
    args = ap.parse_args()
    OUTPUT.mkdir(exist_ok=True)

    if args.hk:
        source = f"hkracing ({args.hk})"
        runners = data.load_hk_racing(args.hk)
    elif args.csv:
        source = f"csv ({args.csv})"
        runners = data.load_generic_csv(args.csv)
    else:
        source = "synthetic demo (market-calibrated)"
        runners = data.synthetic_races(
            dt.date.fromisoformat(args.start), dt.date.fromisoformat(args.end)
        )
    print(f"Data: {source}")
    print(f"  {runners['race_id'].nunique():,} races, {len(runners):,} runners, "
          f"{runners['date'].min().date()} to {runners['date'].max().date()}")
    print(f"Assumed pool bias beta = {args.beta} "
          f"({'fair pool -- expect no selective edge' if args.beta == 1.0 else 'MODELED bias, not measured'})")

    summary = selective_backtest(
        runners,
        beta=args.beta,
        gate_pct=args.gate_pct,
        k_max=args.k_max,
        takeout=args.takeout,
        seed=args.seed,
    )
    print()
    print(summary.to_string(index=False))
    out_path = OUTPUT / "mckenna_engine.csv"
    summary.to_csv(out_path, index=False)
    print(f"\nWritten to {out_path}")
    if args.beta != 1.0:
        print("NOTE: any positive ROI above is conditional on the assumed beta; "
              "estimate beta from real dividends before believing it.")


if __name__ == "__main__":
    main()

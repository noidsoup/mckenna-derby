#!/usr/bin/env python3
"""End-to-end pipeline: data -> novelty -> timewave comparison -> backtest -> report.

Usage:
    python run_analysis.py                          # bundled Hong Kong races (default)
    python run_analysis.py --synthetic              # market-calibrated null demo
    python run_analysis.py --hk rawdata/            # raw gdaley/hkracing Kaggle layout
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
    ap.add_argument(
        "--synthetic",
        action="store_true",
        help="use market-calibrated synthetic demo instead of bundled HK data",
    )
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

    n_sources = sum(bool(x) for x in (args.synthetic, args.hk, args.csv))
    if n_sources > 1:
        ap.error("use only one of --synthetic, --hk, or --csv")

    if args.hk:
        source = f"hkracing ({args.hk})"
        runners = data.load_hk_racing(args.hk)
    elif args.csv:
        source = f"csv ({args.csv})"
        runners = data.load_generic_csv(args.csv)
    elif args.synthetic:
        source = "synthetic demo (market-calibrated: expect null result, ROI ~ -takeout)"
        runners = data.synthetic_races(
            dt.date.fromisoformat(args.start), dt.date.fromisoformat(args.end)
        )
    else:
        source = "Hong Kong bundled (gdaley/hkracing 1997–2005)"
        runners = data.load_bundled_hk()
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

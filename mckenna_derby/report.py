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

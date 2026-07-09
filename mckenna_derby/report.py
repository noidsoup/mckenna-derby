"""Markdown report writer for a pipeline run."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# Lead with the honest inference statistic; naive p-values are secondary.
PRIMARY_KEYS = [
    "number_set", "n_days", "spearman_r", "permutation_p", "interpretation",
]
NAIVE_KEYS = [
    ("pearson_r", "pearson_r (naive)"),
    ("pearson_p", "pearson_p (naive / uncorrected)"),
    ("spearman_p", "spearman_p (naive / uncorrected)"),
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
    lines.append(
        "Primary inference uses the circular-shift **permutation p** "
        "(accounts for autocorrelation). Pearson/Spearman p-values below are "
        "naive / uncorrected and should not be treated as confirmatory."
    )
    lines.append("")
    for k in PRIMARY_KEYS:
        lines.append(f"- **{k}:** {primary[k]}")
    for key, label in NAIVE_KEYS:
        lines.append(f"- **{label}:** {primary[key]}")
    lines.append("")

    lines += [
        "## Exploratory: all number sets (Bonferroni x4)", "",
        "```", exploratory.to_string(index=False), "```", "",
    ]

    lines += [
        "## Backtest (buy every trifecta combination)", "",
        "Day selection uses a causal expanding-window timewave percentile "
        "(no full-sample look-ahead).",
        "",
        "| strategy | races | cost | P&L | ROI | profitable races |",
        "|---|---|---|---|---|---|",
    ]
    lines += [
        _backtest_row("Timewave-filtered", backtest_res["strategy"]),
        _backtest_row("Bet every race", backtest_res["bet_every_race"]),
        "",
    ]
    src_counts = backtest_res["per_race"]["payout_source"].value_counts().to_dict()
    lines += [
        f"Payout sources: {src_counts}. Modeled payouts have an expected ROI of "
        "exactly -takeout by construction; conclusions about profitability "
        "require actual historical dividends. ROI comparisons are exploratory "
        "and are not pre-registered success criteria.",
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

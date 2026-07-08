"""Backtest the buy-every-trifecta-combination strategy.

For each race we compare:

    cost   = n * (n-1) * (n-2) * ticket_price        (every exact order)
    payout = the ONE winning ticket's payout

Payout comes from, in order of preference:
1. ``trifecta_payout`` (actual historical dividend per $1 ticket) when the
   dataset provides it — this is the only credible basis for conclusions;
2. otherwise a modeled parimutuel pool consistent with the market's own
   Harville probabilities:  payout = ticket * (1 - takeout) / P(order).

Under the model, the expected return of buying everything is exactly
-takeout per race; profit can only come from a timing signal that finds
races where the realized order is more chaotic than the pool priced in.

The strategy filter: only bet on days where the timewave says novelty is
high (LOW wave value), per the McKenna hypothesis.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_TAKEOUT = 0.22
TICKET_PRICE = 1.0
DEFAULT_SWEEP_PCTS = (5, 10, 15, 20, 30, 40, 50, 75, 100)


def race_pnl(race_scores: pd.DataFrame, takeout: float = DEFAULT_TAKEOUT,
             ticket: float = TICKET_PRICE) -> pd.DataFrame:
    """Per-race profit/loss of buying every trifecta combination."""
    s = race_scores.copy()
    n = s["n_runners"]
    s["n_combos"] = n * (n - 1) * (n - 2)
    s["cost"] = s["n_combos"] * ticket
    modeled = ticket * (1.0 - takeout) / s["trifecta_probability"]
    if "trifecta_payout" in s.columns:
        s["payout"] = s["trifecta_payout"].where(s["trifecta_payout"].notna(), modeled)
        s["payout_source"] = np.where(
            s["trifecta_payout"].notna(), "actual", "modeled"
        )
    else:
        s["payout"] = modeled
        s["payout_source"] = "modeled"
    s["pnl"] = s["payout"] - s["cost"]
    return s


def backtest(race_scores: pd.DataFrame, timewave: pd.Series,
             novelty_threshold_pct: float = 20.0,
             takeout: float = DEFAULT_TAKEOUT) -> dict:
    """Bet only on days in the lowest `novelty_threshold_pct`% of timewave
    values (low wave = high predicted novelty), vs. betting every day."""
    pnl = race_pnl(race_scores, takeout)
    pnl["day"] = pnl["date"].dt.date
    tw = timewave.copy()
    tw.index = pd.Index([d for d in tw.index])
    threshold = np.percentile(tw.to_numpy(), novelty_threshold_pct)
    high_novelty_days = set(tw[tw <= threshold].index)
    pnl["selected"] = pnl["day"].isin(high_novelty_days)

    def summarize(frame: pd.DataFrame) -> dict:
        if frame.empty:
            return {"races": 0, "total_cost": 0.0, "total_payout": 0.0,
                    "total_pnl": 0.0, "roi_pct": float("nan"),
                    "hit_profit_pct": float("nan")}
        return {
            "races": int(len(frame)),
            "total_cost": float(frame["cost"].sum()),
            "total_payout": float(frame["payout"].sum()),
            "total_pnl": float(frame["pnl"].sum()),
            "roi_pct": float(100 * frame["pnl"].sum() / frame["cost"].sum()),
            "hit_profit_pct": float(100 * (frame["pnl"] > 0).mean()),
        }

    return {
        "threshold_wave_value": float(threshold),
        "strategy": summarize(pnl[pnl["selected"]]),
        "bet_every_race": summarize(pnl),
        "per_race": pnl,
    }


def threshold_sweep(race_scores: pd.DataFrame, timewave: pd.Series,
                    pcts: tuple = DEFAULT_SWEEP_PCTS,
                    takeout: float = DEFAULT_TAKEOUT) -> pd.DataFrame:
    """ROI of the strategy across a grid of timewave thresholds.

    Exploratory only: sweeping thresholds and picking the best one is
    p-hacking. This exists to show the shape of the curve, not to tune.
    """
    rows = []
    for pct in pcts:
        res = backtest(race_scores, timewave,
                       novelty_threshold_pct=float(pct), takeout=takeout)
        s = res["strategy"]
        rows.append(
            {
                "threshold_pct": pct,
                "wave_threshold": res["threshold_wave_value"],
                "races": s["races"],
                "total_cost": s["total_cost"],
                "total_pnl": s["total_pnl"],
                "roi_pct": s["roi_pct"],
                "hit_profit_pct": s["hit_profit_pct"],
            }
        )
    return pd.DataFrame(rows)

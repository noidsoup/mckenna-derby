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

Causal threshold (no look-ahead)
================================
Day selection uses an *expanding-window* percentile, not a full-sample cut.

For each day ``d`` (0-indexed in the sorted timewave series), the threshold
is the ``novelty_threshold_pct`` percentile of **past-only** values
``tw[:d]`` (exclusive of day ``d``). Day ``d`` is selected when::

    tw[d] <= percentile(tw[:d], novelty_threshold_pct)

This is the strict causal / bet-before-observing-today choice. Days with
fewer than ``min_history`` past observations are never selected.
``min_history`` defaults to ``min(30, len(series) // 2)`` (at least 1 when
the series is non-empty), so short demos still warm up but cannot peek at
the full sample.

Note: at the 100th percentile, a day is selected only if its wave value is
<= the max of the past — brand-new highs are excluded. That is intentional
under exclusive past-only semantics.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_TAKEOUT = 0.22
TICKET_PRICE = 1.0
DEFAULT_SWEEP_PCTS = (5, 10, 15, 20, 30, 40, 50, 75, 100)
DEFAULT_MIN_HISTORY_CAP = 30


def default_min_history(n: int) -> int:
    """Warm-up length: lesser of 30 and len/2 (at least 1 when n >= 1)."""
    if n <= 0:
        return 0
    return max(1, min(DEFAULT_MIN_HISTORY_CAP, n // 2))


def expanding_percentile_thresholds(
    values: np.ndarray,
    pct: float,
    min_history: int,
) -> np.ndarray:
    """Per-day expanding percentile of *past-only* values (exclusive of today).

    ``out[d]`` is ``nan`` when ``d < min_history`` (insufficient past history).
    Otherwise ``out[d] = np.percentile(values[:d], pct)``.
    """
    values = np.asarray(values, dtype=float)
    n = len(values)
    out = np.full(n, np.nan, dtype=float)
    if n == 0:
        return out
    # Exclusive past-only: need at least one prior observation to form a percentile.
    start = max(int(min_history), 1)
    for d in range(start, n):
        out[d] = float(np.percentile(values[:d], pct))
    return out


def causal_select_mask(
    series: pd.Series,
    pct: float,
    min_history: int | None = None,
    *,
    side: str = "low",
) -> pd.Series:
    """Boolean mask: days selected by a causal expanding-window percentile.

    Parameters
    ----------
    series
        Sorted (or will be sorted) value series indexed by day.
    pct
        Percentile in [0, 100]. For ``side="low"`` this is the upper bound
        percentile (select values at or below it). For ``side="high"`` pass
        the lower-bound percentile (e.g. ``100 - gate_pct``).
    min_history
        Required number of *past* observations before a day may be selected.
        Defaults to :func:`default_min_history`.
    side
        ``"low"`` → select ``value <= threshold`` (timewave novelty filter).
        ``"high"`` → select ``value >= threshold`` (resonance gate).
    """
    if side not in ("low", "high"):
        raise ValueError("side must be 'low' or 'high'")
    s = series.sort_index()
    vals = s.to_numpy(dtype=float)
    n = len(vals)
    mh = default_min_history(n) if min_history is None else int(min_history)
    thresholds = expanding_percentile_thresholds(vals, pct, mh)
    if side == "low":
        selected = vals <= thresholds
    else:
        selected = vals >= thresholds
    selected = selected & ~np.isnan(thresholds)
    return pd.Series(selected, index=s.index, dtype=bool)


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
             takeout: float = DEFAULT_TAKEOUT,
             min_history: int | None = None) -> dict:
    """Bet only on days in the lowest `novelty_threshold_pct`% of timewave
    values under a *causal* expanding-window rule (see module docstring),
    vs. betting every day.
    """
    pnl = race_pnl(race_scores, takeout)
    pnl["day"] = pnl["date"].dt.date
    tw = timewave.copy()
    tw.index = pd.Index([d for d in tw.index])
    tw = tw.sort_index()
    mh = default_min_history(len(tw)) if min_history is None else int(min_history)
    mask = causal_select_mask(
        tw, novelty_threshold_pct, min_history=mh, side="low"
    )
    high_novelty_days = set(mask.index[mask])
    thresholds = expanding_percentile_thresholds(
        tw.to_numpy(dtype=float), novelty_threshold_pct, mh
    )
    # Summary threshold: last finite expanding cut (not a full-sample peek).
    finite = thresholds[~np.isnan(thresholds)]
    summary_threshold = float(finite[-1]) if len(finite) else float("nan")
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
        "threshold_wave_value": summary_threshold,
        "min_history": mh,
        "strategy": summarize(pnl[pnl["selected"]]),
        "bet_every_race": summarize(pnl),
        "per_race": pnl,
    }


def threshold_sweep(race_scores: pd.DataFrame, timewave: pd.Series,
                    pcts: tuple = DEFAULT_SWEEP_PCTS,
                    takeout: float = DEFAULT_TAKEOUT,
                    min_history: int | None = None) -> pd.DataFrame:
    """ROI of the strategy across a grid of timewave thresholds.

    Exploratory only: sweeping thresholds and picking the best one is
    p-hacking. This exists to show the shape of the curve, not to tune.
    Uses the same causal expanding-window rule as :func:`backtest`.
    """
    rows = []
    for pct in pcts:
        res = backtest(
            race_scores, timewave,
            novelty_threshold_pct=float(pct),
            takeout=takeout,
            min_history=min_history,
        )
        s = res["strategy"]
        rows.append(
            {
                "threshold_pct": pct,
                "wave_threshold": res["threshold_wave_value"],
                "min_history": res["min_history"],
                "races": s["races"],
                "total_cost": s["total_cost"],
                "total_pnl": s["total_pnl"],
                "roi_pct": s["roi_pct"],
                "hit_profit_pct": s["hit_profit_pct"],
            }
        )
    return pd.DataFrame(rows)

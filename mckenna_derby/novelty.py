"""Race novelty scoring.

A race outcome's "novelty" is defined information-theoretically: the
surprisal (negative log probability) of what actually happened, under the
probabilities implied by the betting market's final odds.

- Favorite wins as expected  -> low surprisal -> low novelty
- 40-1 longshot wins         -> high surprisal -> high novelty

Two scores per race:
- win_novelty:      -log2 P(winner wins)
- trifecta_novelty: -log2 P(exact 1-2-3 order), via the Harville model
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = {"date", "race_id", "horse", "decimal_odds", "finish_position"}


def implied_probabilities(decimal_odds: np.ndarray) -> np.ndarray:
    """Market-implied win probabilities, normalized to remove the overround.

    decimal_odds are European-style (payout per 1 staked, including stake),
    so raw implied probability is 1/odds; bookmakers' margins make these sum
    to >1, so we renormalize.
    """
    raw = 1.0 / np.asarray(decimal_odds, dtype=float)
    return raw / raw.sum()


def harville_trifecta_probability(p: np.ndarray, first: int, second: int, third: int) -> float:
    """P(exact 1-2-3 order) under the Harville (sequential) model."""
    p1 = p[first]
    p2 = p[second] / (1.0 - p[first])
    p3 = p[third] / (1.0 - p[first] - p[second])
    return float(p1 * p2 * p3)


def score_race(group: pd.DataFrame) -> dict:
    """Compute novelty metrics for a single race (rows = runners)."""
    g = group.sort_values("finish_position")
    p = implied_probabilities(g["decimal_odds"].to_numpy())
    n = len(g)
    if n < 3:
        raise ValueError("race must have at least 3 runners")

    # After the sort, row 0/1/2 are the top three finishers.
    p_win = p[0]
    p_tri = harville_trifecta_probability(p, 0, 1, 2)

    # Rank of the winner in the odds ordering (1 = favorite won).
    odds_rank_of_winner = int((g["decimal_odds"].to_numpy() < g["decimal_odds"].iloc[0]).sum()) + 1

    result = {
        "date": g["date"].iloc[0],
        "race_id": g["race_id"].iloc[0],
        "n_runners": n,
        "winner_odds": float(g["decimal_odds"].iloc[0]),
        "winner_was_favorite": odds_rank_of_winner == 1,
        "win_novelty": -math.log2(p_win),
        "trifecta_novelty": -math.log2(p_tri),
        "trifecta_probability": p_tri,
    }
    if "trifecta_payout" in g.columns:
        result["trifecta_payout"] = float(g["trifecta_payout"].iloc[0])
    return result


def score_races(df: pd.DataFrame) -> pd.DataFrame:
    """Score every race in a runner-level dataframe.

    Expects columns: date, race_id, horse, decimal_odds, finish_position.
    Returns one row per race.
    """
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")
    rows = [score_race(g) for _, g in df.groupby("race_id", sort=False)]
    out = pd.DataFrame(rows)
    out["date"] = pd.to_datetime(out["date"])
    return out.sort_values("date").reset_index(drop=True)


def daily_novelty(race_scores: pd.DataFrame, metric: str = "trifecta_novelty") -> pd.Series:
    """Aggregate per-race novelty to a daily mean series.

    Note: raw trifecta surprisal grows with field size (more runners = more
    possible orders), so we z-score within each field-size bucket first to
    make days with different card compositions comparable.
    """
    s = race_scores.copy()
    z = s.groupby("n_runners")[metric].transform(
        lambda x: (x - x.mean()) / x.std(ddof=0) if x.std(ddof=0) > 0 else x * 0.0
    )
    s["novelty_z"] = z
    return s.groupby(s["date"].dt.date)["novelty_z"].mean()

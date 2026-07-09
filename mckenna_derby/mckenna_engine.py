"""McKenna-inspired selective trifecta betting engine.

Three components, in increasing order of economic seriousness:

1. ``RollingTimewave`` — a *fractal resonance* signal. Instead of anchoring
   McKenna's timewave to the fixed 2012-12-21 zero date, we apply his core
   fractal-self-similarity idea to racing's own novelty history: today's
   resonance is a weighted echo of past novelty at lags 1, 64, 64^2, ... days
   (the wave-factor-64 hierarchy from Timewave Zero), with weights decaying
   by 1/64 per level. Strictly causal: only past data is used.

2. ``IChingSelector`` — hexagram casting (the classical three-coin method)
   as the randomness source for choosing WHICH trifecta combinations to buy
   when a race offers more attractive combos than we are willing to fund.
   Deterministic given a seed, so backtests are reproducible.

3. ``selective_backtest`` — the economically serious part. Prices every
   trifecta permutation with Harville probabilities from the odds, models
   the pool's payout under a configurable favorite-longshot bias, buys only
   positive-expected-value combos, gates races by the resonance signal, and
   compares four strategies over the same data.

HONESTY WARNING — the ``beta`` parameter is an ASSUMPTION, not a finding
=========================================================================
The modeled payout for a combination is::

    payout = ticket * (1 - takeout) / pool_prob
    pool_prob = harville_prob**beta / sum(harville_prob**beta)

``beta`` describes how the betting pool distorts fair (Harville) odds:

- ``beta = 1.0`` (default): the pool prices combinations fairly. Every combo
  then has expected value exactly ``-takeout`` and the selective strategy
  finds NO positive-EV bets. This is the null case and it is what honest
  market-calibrated data looks like.
- ``beta > 1.0``: the pool overbets favorites, so longshot combinations are
  underpriced and become +EV. The engine will show positive *modeled* ROI.
- ``beta < 1.0``: the pool overbets longshots (the classic favorite-longshot
  bias direction), making favorite combos the value plays.

Any positive ROI produced with ``beta != 1`` is conditional on that bias
actually existing at that magnitude in the real pool. Real profitability
requires estimating beta from real dividend data (compare actual
``trifecta_payout`` dividends to Harville predictions), not assuming it.
This module is a framework for exploiting pool bias IF it exists — with
McKenna-flavored timing (resonance gate) and selection (I Ching) layered
on top.
"""

from __future__ import annotations

import itertools
from functools import lru_cache

import numpy as np
import pandas as pd

from .backtest import causal_select_mask, default_min_history
from .novelty import daily_novelty, implied_probabilities, score_races

DEFAULT_TAKEOUT = 0.22
TICKET_PRICE = 1.0
STRATEGIES = ("buy_all", "selective_gated", "selective", "random_control")


class RollingTimewave:
    """Fractal-resonance signal derived from the novelty series itself.

    For each day ``d``::

        s(d) = sum_{i=0..levels-1} novelty(d - wave_factor**i days) / wave_factor**i

    i.e. lags 1, 64, 4096, ... days with geometrically decaying weights —
    the wave-factor-64 fractal hierarchy of Timewave Zero, but resonating
    with racing's own history instead of a fixed zero date.

    Missing lag days fall back to the nearest earlier available day within
    ``max_gap_days``; if none exists, that level contributes 0. The signal is
    only emitted once at least ``wave_factor`` days of history exist, and it
    is strictly causal: the value on day ``d`` depends only on days < ``d``.
    """

    def __init__(self, wave_factor: int = 64, levels: int = 3,
                 max_gap_days: int = 7):
        if wave_factor < 2:
            raise ValueError("wave_factor must be >= 2")
        if levels < 1:
            raise ValueError("levels must be >= 1")
        self.wave_factor = wave_factor
        self.levels = levels
        self.max_gap_days = max_gap_days

    def signal(self, daily_novelty: pd.Series) -> pd.Series:
        """Compute the resonance signal for a daily novelty series.

        ``daily_novelty`` is indexed by date (as produced by
        ``novelty.daily_novelty``). Returns a series with the same kind of
        index, containing only the days where the signal is valid.
        """
        if daily_novelty.empty:
            return daily_novelty.iloc[0:0].astype(float)
        s = daily_novelty.copy()
        s.index = pd.to_datetime(pd.Index(s.index))
        s = s.sort_index()
        idx = s.index

        total = np.zeros(len(idx))
        for i in range(self.levels):
            lag = self.wave_factor ** i
            targets = idx - pd.Timedelta(days=lag)
            vals = s.reindex(
                targets, method="ffill",
                tolerance=pd.Timedelta(days=self.max_gap_days),
            )
            total += vals.fillna(0.0).to_numpy() / float(self.wave_factor ** i)

        valid = idx >= idx[0] + pd.Timedelta(days=self.wave_factor)
        out = pd.Series(total, index=[d.date() for d in idx], dtype=float)
        return out[np.asarray(valid)]


class IChingSelector:
    """I Ching hexagram casting as a reproducible ticket-selection oracle.

    ``cast_hexagram`` implements the classical three-coin method: six lines,
    each the sum of three coin tosses (heads=3, tails=2, so 6/7/8/9); odd
    sums are yang, even sums are yin. The six-bit line pattern is then mapped
    to a hexagram number 1..64 as ``1 + (binary value of lines) % 64``.

    NOTE: that mapping is a SIMPLIFICATION — the traditional King Wen
    sequence orders the 64 hexagrams non-numerically. The simplification
    preserves the essential property (a uniform 1..64 oracle from coin
    parity) without embedding the full King Wen lookup table.

    Given the same construction seed, every cast and selection is
    deterministic, so backtests are reproducible.
    """

    def __init__(self, seed: int | None = None):
        self._rng = np.random.default_rng(seed)

    def cast_hexagram(self) -> int:
        """Cast one hexagram via the three-coin method. Returns 1..64."""
        lines = []
        for _ in range(6):
            # Three coins, each worth 2 (tails/yin) or 3 (heads/yang).
            toss = int(self._rng.integers(2, 4, size=3).sum())  # 6..9
            lines.append(toss % 2)  # odd => yang (1), even => yin (0)
        value = sum(bit << pos for pos, bit in enumerate(lines))  # 0..63
        return 1 + value % 64

    def select_combinations(self, race_combos: list, k: int,
                            weights=None) -> list:
        """Choose ``k`` distinct combinations from ``race_combos``.

        A hexagram is cast and its number seeds the sampling RNG; sampling is
        without replacement, weighted by ``weights`` (e.g. fair_probability *
        payout_edge) when given, else uniform.
        """
        if k >= len(race_combos):
            return list(race_combos)
        hexagram = self.cast_hexagram()
        rng = np.random.default_rng(hexagram)
        p = None
        if weights is not None:
            w = np.asarray(weights, dtype=float)
            if len(w) != len(race_combos):
                raise ValueError("weights length must match race_combos")
            w = np.clip(w, 0.0, None)
            if w.sum() > 0:
                p = w / w.sum()
        chosen = rng.choice(len(race_combos), size=k, replace=False, p=p)
        return [race_combos[j] for j in chosen]


@lru_cache(maxsize=32)
def _trifecta_index_arrays(n: int):
    """Index arrays (first, second, third) for all n(n-1)(n-2) permutations.

    The first permutation is always (0, 1, 2), which — for runners sorted by
    finish position — is the winning combination.
    """
    perms = np.array(list(itertools.permutations(range(n), 3)), dtype=int)
    return perms[:, 0], perms[:, 1], perms[:, 2]


def _harville_all(p: np.ndarray) -> np.ndarray:
    """Harville probability of every exact trifecta order, vectorized."""
    i1, i2, i3 = _trifecta_index_arrays(len(p))
    return p[i1] * p[i2] / (1.0 - p[i1]) * p[i3] / (1.0 - p[i1] - p[i2])


def _compute_gated_days(
    daily: pd.Series,
    gate_pct: float,
    wave_factor: int,
    levels: int,
    min_history: int | None = None,
) -> set:
    """Days whose resonance is in the top ``gate_pct``% under a causal rule.

    Uses an expanding-window percentile of *past-only* resonance values
    (exclusive of today), matching :func:`mckenna_derby.backtest.causal_select_mask`.
    Days with fewer than ``min_history`` past resonance observations are
    never gated in. Default ``min_history`` is
    ``min(30, len(resonance) // 2)``.
    """
    resonance = RollingTimewave(wave_factor=wave_factor, levels=levels).signal(daily)
    if len(resonance) == 0:
        return set()
    mh = default_min_history(len(resonance)) if min_history is None else int(min_history)
    # High-resonance gate: lower bound = expanding (100 - gate_pct) percentile.
    mask = causal_select_mask(
        resonance, 100.0 - gate_pct, min_history=mh, side="high"
    )
    return set(mask.index[mask])


def _selective_picks(
    ev: np.ndarray, fair: np.ndarray, k_max: int, iching: "IChingSelector",
) -> np.ndarray:
    """Indices of the +EV combinations, capped at ``k_max`` by the I Ching selector."""
    qualifying = np.where(ev > 0.0)[0]
    if len(qualifying) > k_max:
        picked = iching.select_combinations(
            list(qualifying), k_max,
            weights=fair[qualifying] * ev[qualifying],
        )
        return np.asarray(picked, dtype=int)
    return qualifying


def _settlement_payout(
    g: pd.DataFrame, modeled_win_payout: float, ticket: float,
) -> float:
    """Winning-ticket payout for settlement: actual dividend when present.

    Selection / EV still uses the modeled pool; only the cash settled on a
    winning ticket prefers ``trifecta_payout`` (scaled to ``ticket`` size)
    when the race carries a non-null actual dividend.
    """
    if "trifecta_payout" in g.columns:
        actual = g["trifecta_payout"].iloc[0]
        if pd.notna(actual):
            # trifecta_payout is defined per $1 ticket (same as backtest.race_pnl).
            return float(actual) * float(ticket)
    return float(modeled_win_payout)


def _build_race_bets(
    g: pd.DataFrame,
    beta: float,
    takeout: float,
    ticket: float,
    ev_threshold: float,
    k_max: int,
    gated_days: set,
    iching: "IChingSelector",
    control_rng: np.random.Generator,
) -> dict:
    """Compute per-strategy (n_tickets, won, win_payout) tuples for one race.

    EV / combo selection uses the beta-distorted *modeled* pool. Settlement
    payout for a winning ticket uses actual ``trifecta_payout`` when present
    on the race rows, otherwise the modeled win payout.
    """
    g = g.sort_values("finish_position")
    p = implied_probabilities(g["decimal_odds"].to_numpy())
    fair = _harville_all(p)
    n_combos = len(fair)

    pool_w = fair ** beta
    pool = pool_w / pool_w.sum()
    modeled_payout = ticket * (1.0 - takeout) / pool
    ev = fair * modeled_payout - ticket

    # Runners sorted by finish position: winning exact order is always index 0.
    winner = 0
    modeled_win = float(modeled_payout[winner])
    win_payout = _settlement_payout(g, modeled_win, ticket)
    day = g["date"].iloc[0].date()

    qualifying = np.where(ev > ev_threshold)[0]
    if len(qualifying) > k_max:
        bought = _selective_picks(ev, fair, k_max, iching)
    else:
        bought = qualifying

    bet = {
        "buy_all": (n_combos, True),
        "selective": (len(bought), bool(np.isin(winner, bought))),
    }

    if day in gated_days and len(bought) > 0:
        bet["selective_gated"] = (len(bought), bool(np.isin(winner, bought)))
        rand = control_rng.choice(n_combos, size=len(bought), replace=False)
        bet["random_control"] = (len(rand), bool(np.isin(winner, rand)))

    return {s: (n, w, win_payout) for s, (n, w) in bet.items()}


def _summarize_totals(totals: dict) -> pd.DataFrame:
    """Flatten the per-strategy running totals into the summary DataFrame."""
    rows = []
    for s in STRATEGIES:
        t = totals[s]
        pnl = t["payout"] - t["cost"]
        rows.append(
            {
                "strategy": s,
                "races": t["races"],
                "tickets": t["tickets"],
                "cost": round(t["cost"], 2),
                "payout": round(t["payout"], 2),
                "pnl": round(pnl, 2),
                "roi_pct": round(100.0 * pnl / t["cost"], 2)
                if t["cost"] > 0 else float("nan"),
            }
        )
    return pd.DataFrame(rows)


def selective_backtest(
    runners: pd.DataFrame,
    beta: float = 1.0,
    ev_threshold: float = 0.0,
    gate_pct: float = 20.0,
    k_max: int = 50,
    takeout: float = DEFAULT_TAKEOUT,
    ticket: float = TICKET_PRICE,
    seed: int = 1904,
    wave_factor: int = 64,
    levels: int = 3,
    min_history: int | None = None,
) -> pd.DataFrame:
    """Compare four trifecta strategies over the same runner-level data.

    Strategies:

    - ``buy_all``:          every combination in every race (baseline;
                            expected ROI = -takeout when beta = 1).
    - ``selective``:        only combos with EV > ``ev_threshold`` under the
                            beta-distorted pool model, capped at ``k_max``
                            tickets per race by the I Ching selector.
    - ``selective_gated``:  ``selective``, but only on days whose fractal
                            resonance signal is in the top ``gate_pct``
                            percent under a *causal* expanding-window rule
                            (past-only; see ``_compute_gated_days``).
    - ``random_control``:   for every race ``selective_gated`` bets, the same
                            NUMBER of tickets chosen uniformly at random —
                            the control that separates pricing skill from
                            ticket-count luck.

    Selection vs settlement
    -----------------------
    Combo selection and EV use the beta-distorted *modeled* pool. When a
    race carries a non-null ``trifecta_payout`` column (actual dividend per
    $1 ticket), that actual dividend is used to settle the winning ticket's
    payout; otherwise settlement falls back to the modeled win payout.
    This matches ``backtest.race_pnl``.

    Returns a summary DataFrame with one row per strategy: races, tickets,
    cost, payout, pnl, roi_pct. See the module docstring for why any profit
    at beta != 1 is a *modeled* result conditional on an assumed pool bias.
    """
    scores = score_races(runners)
    daily = daily_novelty(scores)
    gated_days = _compute_gated_days(
        daily, gate_pct, wave_factor, levels, min_history=min_history,
    )
    iching = IChingSelector(seed=seed)
    control_rng = np.random.default_rng(seed + 1)

    totals = {
        s: {"races": 0, "tickets": 0, "cost": 0.0, "payout": 0.0}
        for s in STRATEGIES
    }

    def record(strategy: str, n_tickets: int, won: bool, win_payout: float) -> None:
        if n_tickets == 0:
            return
        t = totals[strategy]
        t["races"] += 1
        t["tickets"] += n_tickets
        t["cost"] += n_tickets * ticket
        if won:
            t["payout"] += win_payout

    df = runners.sort_values(["date", "race_id"])
    for _, g in df.groupby("race_id", sort=False):
        for strategy, (n_tickets, won, win_payout) in _build_race_bets(
            g, beta, takeout, ticket, ev_threshold, k_max,
            gated_days, iching, control_rng,
        ).items():
            record(strategy, n_tickets, won, win_payout)

    return _summarize_totals(totals)

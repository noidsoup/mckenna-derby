#!/usr/bin/env python3
"""Exploratory free win/place idea poke on bundled HK data.

LAB NOTEBOOK companion — every section is **exploratory**. Lock rules on
train (1997–2002); only **test** (2003–2005) ROI is a claim. No prereg
edits, no paid feeds, no cherry-pick-until-green as a finding.

Usage:
    .venv/bin/python scripts/exploratory_win_place_poke.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mckenna_derby import compare, data, novelty  # noqa: E402
from mckenna_derby.backtest import causal_select_mask  # noqa: E402

RAWDATA = ROOT / "rawdata"
OUT_DIR = ROOT / "output"
OUT_MD = OUT_DIR / "WIN_PLACE_POKE.md"
OUT_JSON = OUT_DIR / "win_place_poke.json"

TRAIN_END = pd.Timestamp("2002-12-31")
# Pre-declared odds caps (Bonferroni-aware menu — not a continuous search claim)
PREDECLARED_CAPS = (2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0)
# HKJC win pool takeout is historically ~17.5%; place similar order.
# We report empirical overround as the "takeout-ish" baseline, not a claim.
NOMINAL_WIN_TAKEOUT = 0.175
SEED = 1904
# Minimum train/test bets before a rule may be "locked" as a claim.
# Smaller cells are still reported (diagnostic) but cannot win the lock.
MIN_TRAIN_BETS = 100
MIN_TEST_BETS_DIAG = 50


def _section(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}", flush=True)


def _tbl(df: pd.DataFrame, float_fmt: str = "%.2f") -> str:
    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        return "_(empty)_"
    try:
        return df.to_markdown(index=False, floatfmt=float_fmt)
    except ImportError:
        cols = list(df.columns)
        lines = [
            "| " + " | ".join(cols) + " |",
            "| " + " | ".join("---" for _ in cols) + " |",
        ]
        for _, row in df.iterrows():
            cells = []
            for c in cols:
                v = row[c]
                if isinstance(v, float):
                    cells.append(float_fmt % v)
                else:
                    cells.append(str(v))
            lines.append("| " + " | ".join(cells) + " |")
        return "\n".join(lines)


def _roi(cost: float, payout: float, n: int, hits: int) -> dict:
    pnl = payout - cost
    return {
        "bets": int(n),
        "hits": int(hits),
        "hit_rate": float(hits / n) if n else float("nan"),
        "cost": float(cost),
        "payout": float(payout),
        "pnl": float(pnl),
        "roi_pct": float(100.0 * pnl / cost) if cost else float("nan"),
    }


def _roi_from_bets(bets: pd.DataFrame) -> dict:
    """bets columns: cost, payout, hit (0/1)."""
    if bets is None or bets.empty:
        return _roi(0.0, 0.0, 0, 0)
    return _roi(
        float(bets["cost"].sum()),
        float(bets["payout"].sum()),
        len(bets),
        int(bets["hit"].sum()),
    )


# ---------------------------------------------------------------------------
# Data prep
# ---------------------------------------------------------------------------


def enrich_runners(runners: pd.DataFrame) -> pd.DataFrame:
    """Attach horse_id + race_no from local rawdata when present (free)."""
    r = runners.copy()
    r["date"] = pd.to_datetime(r["date"])
    r["won"] = (r["finish_position"] == 1).astype(int)
    r["placed"] = r["place_payout"].notna().astype(int)
    r["field_size"] = r.groupby("race_id")["horse"].transform("size")
    r["odds_rank"] = r.groupby("race_id")["decimal_odds"].rank(method="min")
    r["is_favorite"] = r["odds_rank"] == 1
    r["is_second_fav"] = r["odds_rank"] == 2
    # Implied fair share after removing overround within race
    r["impl_raw"] = 1.0 / r["decimal_odds"]
    r["overround"] = r.groupby("race_id")["impl_raw"].transform("sum")
    r["impl_fair"] = r["impl_raw"] / r["overround"]

    runs_path = RAWDATA / "runs.csv"
    races_path = RAWDATA / "races.csv"
    if runs_path.is_file():
        runs = pd.read_csv(
            runs_path, usecols=["race_id", "horse_no", "horse_id"]
        )
        runs = runs.rename(columns={"horse_no": "horse"})
        before = len(r)
        r = r.merge(runs, on=["race_id", "horse"], how="left")
        matched = float(r["horse_id"].notna().mean())
        print(f"  enriched horse_id from rawdata/runs.csv "
              f"(match={matched:.1%}, rows={before})")
    else:
        r["horse_id"] = np.nan
        print("  no rawdata/runs.csv — horse follow will be skipped")

    if races_path.is_file():
        races = pd.read_csv(
            races_path, usecols=["race_id", "race_no", "venue"]
        )
        r = r.merge(races, on="race_id", how="left")
        print(f"  enriched race_no/venue from rawdata/races.csv "
              f"(race_no null={r['race_no'].isna().mean():.1%})")
    else:
        # Fallback: order by race_id within day (bundled IDs are sequential)
        r = r.sort_values(["date", "race_id"])
        r["race_no"] = r.groupby("date")["race_id"].rank(method="dense").astype(int)
        r["venue"] = "UNK"
        print("  no rawdata/races.csv — using race_id order within day as race_no")

    return r


def race_table(runners: pd.DataFrame) -> pd.DataFrame:
    """One row per race with favorite / 2nd-fav win+place settlement fields."""
    rows = []
    for rid, g in runners.groupby("race_id", sort=False):
        g = g.sort_values("decimal_odds")
        favs = g[g["is_favorite"]]
        if favs.empty:
            continue
        # Split stake across tied favorites
        n_fav = len(favs)
        stake = 1.0 / n_fav
        fav_odds = float(favs["decimal_odds"].iloc[0])
        win_pay = 0.0
        place_pay = 0.0
        fav_won = 0
        fav_placed = 0
        for _, row in favs.iterrows():
            if row["won"] == 1 and pd.notna(row["win_payout"]):
                win_pay += stake * float(row["win_payout"])
                fav_won = 1
            if pd.notna(row["place_payout"]):
                place_pay += stake * float(row["place_payout"])
                fav_placed = 1

        seconds = g[g["is_second_fav"]]
        sec_odds = float(seconds["decimal_odds"].iloc[0]) if len(seconds) else float("nan")
        sec_win = 0.0
        sec_place = 0.0
        sec_won = 0
        sec_placed = 0
        if len(seconds):
            n2 = len(seconds)
            s2 = 1.0 / n2
            for _, row in seconds.iterrows():
                if row["won"] == 1 and pd.notna(row["win_payout"]):
                    sec_win += s2 * float(row["win_payout"])
                    sec_won = 1
                if pd.notna(row["place_payout"]):
                    sec_place += s2 * float(row["place_payout"])
                    sec_placed = 1

        winner = g[g["won"] == 1]
        winner_odds = float(winner["decimal_odds"].iloc[0]) if len(winner) else float("nan")

        rows.append(
            {
                "race_id": rid,
                "date": g["date"].iloc[0],
                "race_no": g["race_no"].iloc[0] if "race_no" in g.columns else np.nan,
                "venue": g["venue"].iloc[0] if "venue" in g.columns else "UNK",
                "field_size": int(g["field_size"].iloc[0]),
                "overround": float(g["overround"].iloc[0]),
                "fav_odds": fav_odds,
                "fav_impl_fair": float(favs["impl_fair"].iloc[0]),
                "n_tied_favs": n_fav,
                "fav_win_payout": win_pay,  # already stake-weighted for $1 total
                "fav_place_payout": place_pay,
                "fav_won": fav_won,
                "fav_placed": fav_placed,
                "sec_odds": sec_odds,
                "sec_win_payout": sec_win,
                "sec_place_payout": sec_place,
                "sec_won": sec_won,
                "sec_placed": sec_placed,
                "winner_odds": winner_odds,
            }
        )
    out = pd.DataFrame(rows).sort_values(["date", "race_no", "race_id"]).reset_index(drop=True)
    out["day"] = out["date"].dt.date
    return out


def split_train_test(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    train = df[df["date"] <= TRAIN_END].copy()
    test = df[df["date"] > TRAIN_END].copy()
    return train, test


# ---------------------------------------------------------------------------
# Step 0 — Inventory + baselines
# ---------------------------------------------------------------------------


def step0(runners: pd.DataFrame, races: pd.DataFrame) -> dict:
    _section("STEP 0 — Inventory + takeout baseline")
    train, test = split_train_test(races)
    over = float(races["overround"].mean())
    takeout_proxy = over - 1.0
    out = {
        "n_runners": int(len(runners)),
        "n_races": int(races["race_id"].nunique()),
        "date_min": str(races["date"].min().date()),
        "date_max": str(races["date"].max().date()),
        "train_races": int(len(train)),
        "test_races": int(len(test)),
        "train_years": "1997-06 → 2002-12",
        "test_years": "2003-01 → 2005-08",
        "mean_overround": over,
        "takeout_proxy_pct": float(100.0 * takeout_proxy),
        "nominal_win_takeout_pct": float(100.0 * NOMINAL_WIN_TAKEOUT),
        "has_horse_id": bool(runners["horse_id"].notna().any()),
        "n_horse_ids": int(runners["horse_id"].nunique(dropna=True)),
        "has_race_no": bool(runners["race_no"].notna().any()),
        "label": "EXPLORATORY",
    }
    for k, v in out.items():
        print(f"  {k}: {v}")
    return out


def fav_win_bets(races: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "race_id": races["race_id"].values,
            "date": races["date"].values,
            "cost": 1.0,
            "payout": races["fav_win_payout"].values,
            "hit": races["fav_won"].values,
        }
    )


def fav_place_bets(races: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "race_id": races["race_id"].values,
            "date": races["date"].values,
            "cost": 1.0,
            "payout": races["fav_place_payout"].values,
            "hit": races["fav_placed"].values,
        }
    )


def step_baselines(races: pd.DataFrame) -> dict:
    _section("STEP B — Always-favorite + random baselines (full sample + split)")
    train, test = split_train_test(races)
    results = {}
    for name, df in (("full", races), ("train", train), ("test", test)):
        w = _roi_from_bets(fav_win_bets(df))
        p = _roi_from_bets(fav_place_bets(df))
        results[f"fav_win_{name}"] = w
        results[f"fav_place_{name}"] = p
        print(f"  fav WIN  {name}: ROI {w['roi_pct']:+.2f}%  n={w['bets']}  hit={w['hit_rate']:.3f}")
        print(f"  fav PLACE {name}: ROI {p['roi_pct']:+.2f}%  n={p['bets']}  hit={p['hit_rate']:.3f}")

    # Random runner win/place (seeded) — expect ~−takeout
    rng = np.random.default_rng(SEED)
    # Need runner-level; rebuild from races via merge later in main — here use
    # winner_odds proxy: pick random odds-rank within field is done in step_random
    results["note"] = (
        "Favorite baselines restated for context. Random baseline in step 9."
    )
    return results


# ---------------------------------------------------------------------------
# Step 1 — Fade longshots (odds cap)
# ---------------------------------------------------------------------------


def step1_fade_longshots(runners: pd.DataFrame, races: pd.DataFrame) -> dict:
    _section("STEP 1 — Fade longshots (never bet odds > X)")
    train_r, test_r = split_train_test(runners)
    train_race, test_race = split_train_test(races)

    def flat_cap_roi(df: pd.DataFrame, cap: float) -> dict:
        sub = df[df["decimal_odds"] <= cap]
        if sub.empty:
            return {**_roi(0, 0, 0, 0), "cap": cap}
        cost = float(len(sub))
        payout = float(
            (sub["won"] * sub["win_payout"].fillna(0.0)).sum()
        )
        s = _roi(cost, payout, len(sub), int(sub["won"].sum()))
        s["cap"] = cap
        return s

    def fav_cap_roi(race_df: pd.DataFrame, cap: float) -> dict:
        sub = race_df[race_df["fav_odds"] <= cap]
        if sub.empty:
            return {**_roi(0, 0, 0, 0), "cap": cap}
        bets = fav_win_bets(sub)
        s = _roi_from_bets(bets)
        s["cap"] = cap
        return s

    # A) Pre-declared caps — Bonferroni label (report ALL on test)
    pre_rows = []
    for cap in PREDECLARED_CAPS:
        tr = flat_cap_roi(train_r, cap)
        te = flat_cap_roi(test_r, cap)
        pre_rows.append(
            {
                "cap": cap,
                "train_roi_pct": tr["roi_pct"],
                "train_bets": tr["bets"],
                "test_roi_pct": te["roi_pct"],
                "test_bets": te["bets"],
                "test_hit_rate": te["hit_rate"],
                "family": "flat_all_runners_odds_le_X",
            }
        )
        print(f"  PREDECL flat ≤{cap}: train {tr['roi_pct']:+.2f}% → "
              f"TEST {te['roi_pct']:+.2f}% (n={te['bets']})")

    fav_pre = []
    for cap in PREDECLARED_CAPS:
        tr = fav_cap_roi(train_race, cap)
        te = fav_cap_roi(test_race, cap)
        fav_pre.append(
            {
                "cap": cap,
                "train_roi_pct": tr["roi_pct"],
                "train_bets": tr["bets"],
                "test_roi_pct": te["roi_pct"],
                "test_bets": te["bets"],
                "test_hit_rate": te["hit_rate"],
                "family": "favorite_if_odds_le_X",
            }
        )
        print(f"  PREDECL fav ≤{cap}: train {tr['roi_pct']:+.2f}% → "
              f"TEST {te['roi_pct']:+.2f}% (n={te['bets']})")

    # B) Lock best-by-train among predeclared (selection step — test is claim)
    flat_df = pd.DataFrame(pre_rows)
    fav_df = pd.DataFrame(fav_pre)
    best_flat = flat_df.loc[flat_df["train_roi_pct"].idxmax()]
    best_fav = fav_df.loc[fav_df["train_roi_pct"].idxmax()]
    claim = {
        "locked_flat_cap": float(best_flat["cap"]),
        "flat_train_roi_pct": float(best_flat["train_roi_pct"]),
        "flat_test_roi_pct": float(best_flat["test_roi_pct"]),
        "flat_test_bets": int(best_flat["test_bets"]),
        "locked_fav_cap": float(best_fav["cap"]),
        "fav_train_roi_pct": float(best_fav["train_roi_pct"]),
        "fav_test_roi_pct": float(best_fav["test_roi_pct"]),
        "fav_test_bets": int(best_fav["test_bets"]),
        "n_predeclared": len(PREDECLARED_CAPS),
        "bonferroni_note": (
            f"{len(PREDECLARED_CAPS)} pre-declared caps × 2 families = "
            f"{2 * len(PREDECLARED_CAPS)} looks; treat any single green test "
            "cell as weak unless it survives multiplicity + replication."
        ),
        "label": "EXPLORATORY — TEST ROI of train-locked cap is the claim",
    }
    print(f"\n  LOCKED flat cap={claim['locked_flat_cap']} → "
          f"TEST {claim['flat_test_roi_pct']:+.2f}%")
    print(f"  LOCKED fav  cap={claim['locked_fav_cap']} → "
          f"TEST {claim['fav_test_roi_pct']:+.2f}%")
    return {
        "predeclared_flat": pre_rows,
        "predeclared_fav": fav_pre,
        "claim": claim,
    }


# ---------------------------------------------------------------------------
# Step 2 — Overlay / underlay vs field
# ---------------------------------------------------------------------------


def step2_overlay(races: pd.DataFrame) -> dict:
    _section("STEP 2 — Favorite overlay/underlay vs field size")
    train, test = split_train_test(races)

    # Expected favorite fair share roughly ~ something of field; use
    # residual: fav_impl_fair vs median fair-fav for same field_size on TRAIN.
    train = train.copy()
    med = train.groupby("field_size")["fav_impl_fair"].median()
    train["fav_fair_med"] = train["field_size"].map(med)
    train["overlay"] = train["fav_impl_fair"] - train["fav_fair_med"]
    # Positive overlay = favorite has MORE fair-implied than typical for field
    # (shorter than peers) → "underlay" in betting slang sometimes flipped;
    # we define: high_overlay = shorter-than-typical; low_overlay = longer-than-typical

    # Pre-declare tertile rules on train overlays
    q33, q67 = train["overlay"].quantile([0.33, 0.67])

    def apply_med(df: pd.DataFrame) -> pd.DataFrame:
        d = df.copy()
        d["fav_fair_med"] = d["field_size"].map(med)
        d["overlay"] = d["fav_impl_fair"] - d["fav_fair_med"]
        return d

    test = apply_med(test)
    train = apply_med(train)

    rules = [
        ("always_fav", lambda d: d),
        ("short_for_field_top_tertile", lambda d: d[d["overlay"] >= q67]),
        ("typical_middle_tertile", lambda d: d[(d["overlay"] > q33) & (d["overlay"] < q67)]),
        ("long_for_field_bottom_tertile", lambda d: d[d["overlay"] <= q33]),
        # Absolute: fav odds high/low for field (raw odds, not residual)
        ("fav_odds_ge_4", lambda d: d[d["fav_odds"] >= 4.0]),
        ("fav_odds_le_2", lambda d: d[d["fav_odds"] <= 2.0]),
        ("large_field_ge_14", lambda d: d[d["field_size"] >= 14]),
        ("small_field_le_10", lambda d: d[d["field_size"] <= 10]),
    ]

    rows = []
    for name, fn in rules:
        tr = _roi_from_bets(fav_win_bets(fn(train)))
        te = _roi_from_bets(fav_win_bets(fn(test)))
        rows.append(
            {
                "rule": name,
                "train_roi_pct": tr["roi_pct"],
                "train_bets": tr["bets"],
                "test_roi_pct": te["roi_pct"],
                "test_bets": te["bets"],
                "test_hit_rate": te["hit_rate"],
            }
        )
        print(f"  {name}: train {tr['roi_pct']:+.2f}% → TEST {te['roi_pct']:+.2f}% "
              f"(n={te['bets']})")

    rdf = pd.DataFrame(rows)
    # Lock best train among overlay family (exclude always_fav as "lock target"
    # but still report it). Selection among non-baseline rules with enough bets.
    cand = rdf[
        (rdf["rule"] != "always_fav")
        & (rdf["train_bets"] >= MIN_TRAIN_BETS)
    ]
    if cand.empty:
        cand = rdf[rdf["rule"] != "always_fav"]
    best = cand.loc[cand["train_roi_pct"].idxmax()]
    claim = {
        "locked_rule": str(best["rule"]),
        "train_roi_pct": float(best["train_roi_pct"]),
        "test_roi_pct": float(best["test_roi_pct"]),
        "test_bets": int(best["test_bets"]),
        "train_q33_overlay": float(q33),
        "train_q67_overlay": float(q67),
        "min_train_bets": MIN_TRAIN_BETS,
        "label": "EXPLORATORY holdout claim",
    }
    print(f"\n  LOCKED {claim['locked_rule']} → TEST {claim['test_roi_pct']:+.2f}%")
    return {"rules": rows, "claim": claim}


# ---------------------------------------------------------------------------
# Step 3 — Consecutive favorite streaks
# ---------------------------------------------------------------------------


def step3_streaks(races: pd.DataFrame) -> dict:
    _section("STEP 3 — Favorite win streaks (same card / same day)")
    r = races.sort_values(["date", "race_no", "race_id"]).copy()
    # Prior favorite results on same day (before this race)
    r["prior_fav_wins_today"] = 0
    r["prior_races_today"] = 0
    chunks = []
    for _, day in r.groupby("day", sort=False):
        d = day.copy()
        # Expanding count of fav wins before current race
        prior_wins = d["fav_won"].cumsum().shift(1).fillna(0).astype(int)
        prior_n = pd.Series(np.arange(len(d)), index=d.index)
        d["prior_fav_wins_today"] = prior_wins.values
        d["prior_races_today"] = prior_n.values
        # Streak of consecutive fav wins ending at previous race
        streak = []
        s = 0
        for i, won in enumerate(d["fav_won"].values):
            streak.append(s)
            s = s + 1 if won == 1 else 0
        d["prior_fav_win_streak"] = streak
        chunks.append(d)
    r = pd.concat(chunks, ignore_index=True)

    train, test = split_train_test(r)

    rules = [
        ("always_fav", lambda d: d),
        ("after_0_prior_fav_wins", lambda d: d[d["prior_fav_wins_today"] == 0]),
        ("after_1plus_prior_fav_wins", lambda d: d[d["prior_fav_wins_today"] >= 1]),
        ("after_2plus_prior_fav_wins", lambda d: d[d["prior_fav_wins_today"] >= 2]),
        ("after_streak_ge_2", lambda d: d[d["prior_fav_win_streak"] >= 2]),
        ("after_streak_ge_3", lambda d: d[d["prior_fav_win_streak"] >= 3]),
        ("fade_after_streak_ge_2", lambda d: d[d["prior_fav_win_streak"] >= 2]),  # same filter; interpret as bet
        ("first_race_of_card", lambda d: d[d["prior_races_today"] == 0]),
        ("late_card_race_no_ge_7", lambda d: d[d["race_no"] >= 7]),
    ]
    # Also: FADE favorite after streak (bet 2nd fav instead)
    rows = []
    for name, fn in rules:
        if name.startswith("fade_"):
            # Bet second favorite when streak condition holds
            sub_tr = fn(train)
            sub_te = fn(test)

            def sec_bets(df: pd.DataFrame) -> pd.DataFrame:
                return pd.DataFrame(
                    {
                        "cost": 1.0,
                        "payout": df["sec_win_payout"].values,
                        "hit": df["sec_won"].values,
                    }
                )

            tr = _roi_from_bets(sec_bets(sub_tr))
            te = _roi_from_bets(sec_bets(sub_te))
            label = name + "_bet_2nd_fav"
        else:
            tr = _roi_from_bets(fav_win_bets(fn(train)))
            te = _roi_from_bets(fav_win_bets(fn(test)))
            label = name
        rows.append(
            {
                "rule": label,
                "train_roi_pct": tr["roi_pct"],
                "train_bets": tr["bets"],
                "test_roi_pct": te["roi_pct"],
                "test_bets": te["bets"],
                "test_hit_rate": te["hit_rate"],
            }
        )
        print(f"  {label}: train {tr['roi_pct']:+.2f}% → TEST {te['roi_pct']:+.2f}% "
              f"(n={te['bets']})")

    rdf = pd.DataFrame(rows)
    # Small-n streak cells (e.g. streak≥3) are diagnostic only — cannot lock.
    cand = rdf[
        (rdf["rule"] != "always_fav")
        & (rdf["train_bets"] >= MIN_TRAIN_BETS)
    ]
    thin = rdf[
        (rdf["rule"] != "always_fav")
        & (rdf["train_bets"] < MIN_TRAIN_BETS)
    ]
    if not thin.empty:
        print("\n  Thin cells (NOT eligible to lock — diagnostic only):")
        for _, row in thin.iterrows():
            print(
                f"    {row['rule']}: train_n={int(row['train_bets'])} "
                f"test ROI {row['test_roi_pct']:+.2f}% (n={int(row['test_bets'])})"
            )
    if cand.empty:
        cand = rdf[rdf["rule"] != "always_fav"]
    best = cand.loc[cand["train_roi_pct"].idxmax()]
    claim = {
        "locked_rule": str(best["rule"]),
        "train_roi_pct": float(best["train_roi_pct"]),
        "test_roi_pct": float(best["test_roi_pct"]),
        "test_bets": int(best["test_bets"]),
        "min_train_bets": MIN_TRAIN_BETS,
        "thin_cells_excluded_from_lock": thin["rule"].tolist() if len(thin) else [],
        "label": "EXPLORATORY holdout claim (min train bets enforced)",
    }
    print(f"\n  LOCKED {claim['locked_rule']} → TEST {claim['test_roi_pct']:+.2f}%")
    return {
        "rules": rows,
        "claim": claim,
        "thin_diagnostic": thin.to_dict(orient="records"),
    }


# ---------------------------------------------------------------------------
# Step 4 — Horse follow (last-start winner)
# ---------------------------------------------------------------------------


def step4_horse_follow(runners: pd.DataFrame) -> dict:
    _section("STEP 4 — Horse follow (won last start)")
    if runners["horse_id"].isna().all():
        print("  SKIPPED — no horse_id")
        return {"skipped": True, "reason": "no horse_id"}

    r = runners.dropna(subset=["horse_id"]).copy()
    r = r.sort_values(["horse_id", "date", "race_id"])
    r["prev_won"] = r.groupby("horse_id")["won"].shift(1)
    r["prev_odds"] = r.groupby("horse_id")["decimal_odds"].shift(1)
    r["starts_seen"] = r.groupby("horse_id").cumcount()

    train, test = split_train_test(r)

    def win_roi(df: pd.DataFrame) -> dict:
        if df.empty:
            return _roi(0, 0, 0, 0)
        cost = float(len(df))
        payout = float((df["won"] * df["win_payout"].fillna(0.0)).sum())
        return _roi(cost, payout, len(df), int(df["won"].sum()))

    def place_roi(df: pd.DataFrame) -> dict:
        if df.empty:
            return _roi(0, 0, 0, 0)
        cost = float(len(df))
        payout = float(df["place_payout"].fillna(0.0).sum())
        return _roi(cost, payout, len(df), int(df["placed"].sum()))

    rules: list[tuple[str, Callable]] = [
        ("won_last_start_win_bet", lambda d: d[d["prev_won"] == 1]),
        ("won_last_start_and_fav_now", lambda d: d[(d["prev_won"] == 1) & d["is_favorite"]]),
        ("won_last_start_odds_le_5", lambda d: d[(d["prev_won"] == 1) & (d["decimal_odds"] <= 5.0)]),
        ("won_last_as_longshot_now_fav", lambda d: d[
            (d["prev_won"] == 1) & (d["prev_odds"] > 10.0) & d["is_favorite"]
        ]),
        ("lost_last_start_win_bet", lambda d: d[d["prev_won"] == 0]),
        ("first_start_in_sample", lambda d: d[d["starts_seen"] == 0]),
    ]

    rows = []
    for name, fn in rules:
        tr = win_roi(fn(train))
        te = win_roi(fn(test))
        rows.append(
            {
                "rule": name,
                "market": "win",
                "train_roi_pct": tr["roi_pct"],
                "train_bets": tr["bets"],
                "test_roi_pct": te["roi_pct"],
                "test_bets": te["bets"],
                "test_hit_rate": te["hit_rate"],
            }
        )
        print(f"  WIN  {name}: train {tr['roi_pct']:+.2f}% → TEST {te['roi_pct']:+.2f}% "
              f"(n={te['bets']})")

    # Place variants for won-last
    for name, fn in [
        ("won_last_start_place_bet", lambda d: d[d["prev_won"] == 1]),
        ("won_last_and_fav_place", lambda d: d[(d["prev_won"] == 1) & d["is_favorite"]]),
    ]:
        tr = place_roi(fn(train))
        te = place_roi(fn(test))
        rows.append(
            {
                "rule": name,
                "market": "place",
                "train_roi_pct": tr["roi_pct"],
                "train_bets": tr["bets"],
                "test_roi_pct": te["roi_pct"],
                "test_bets": te["bets"],
                "test_hit_rate": te["hit_rate"],
            }
        )
        print(f"  PLACE {name}: train {tr['roi_pct']:+.2f}% → TEST {te['roi_pct']:+.2f}% "
              f"(n={te['bets']})")

    rdf = pd.DataFrame(rows)
    cand = rdf[rdf["train_bets"] >= MIN_TRAIN_BETS]
    thin = rdf[rdf["train_bets"] < MIN_TRAIN_BETS]
    if not thin.empty:
        print("\n  Thin cells (NOT eligible to lock):")
        for _, row in thin.iterrows():
            print(
                f"    {row['rule']}: train_n={int(row['train_bets'])} "
                f"test ROI {row['test_roi_pct']:+.2f}% (n={int(row['test_bets'])})"
            )
    if cand.empty:
        cand = rdf
    best = cand.loc[cand["train_roi_pct"].idxmax()]
    claim = {
        "locked_rule": str(best["rule"]),
        "market": str(best["market"]),
        "train_roi_pct": float(best["train_roi_pct"]),
        "test_roi_pct": float(best["test_roi_pct"]),
        "test_bets": int(best["test_bets"]),
        "min_train_bets": MIN_TRAIN_BETS,
        "thin_cells_excluded_from_lock": thin["rule"].tolist() if len(thin) else [],
        "label": "EXPLORATORY holdout claim (min train bets enforced)",
    }
    print(f"\n  LOCKED {claim['locked_rule']} → TEST {claim['test_roi_pct']:+.2f}%")
    return {
        "rules": rows,
        "claim": claim,
        "n_horses": int(r["horse_id"].nunique()),
        "thin_diagnostic": thin.to_dict(orient="records"),
    }


# ---------------------------------------------------------------------------
# Step 5 — Odds movement (unavailable)
# ---------------------------------------------------------------------------


def step5_odds_move() -> dict:
    _section("STEP 5 — Odds movement proxy")
    msg = (
        "Bundled + Kaggle dumps expose final win_odds / decimal_odds only. "
        "No morning line, no tote timeline, no scratched-runner reprice. "
        "Odds-movement ideas are UNAVAILABLE on free data — skipped."
    )
    print(f"  {msg}")
    return {"skipped": True, "reason": msg}


# ---------------------------------------------------------------------------
# Step 6 — Place vs win
# ---------------------------------------------------------------------------


def step6_place_vs_win(races: pd.DataFrame) -> dict:
    _section("STEP 6 — Place vs win (when is place less bad?)")
    train, test = split_train_test(races)

    def pack(name: str, win_fn, place_fn) -> dict:
        tw = _roi_from_bets(win_fn(train))
        te_w = _roi_from_bets(win_fn(test))
        tp = _roi_from_bets(place_fn(train))
        te_p = _roi_from_bets(place_fn(test))
        return {
            "rule": name,
            "train_win_roi_pct": tw["roi_pct"],
            "train_win_bets": tw["bets"],
            "test_win_roi_pct": te_w["roi_pct"],
            "test_win_bets": te_w["bets"],
            "train_place_roi_pct": tp["roi_pct"],
            "train_place_bets": tp["bets"],
            "test_place_roi_pct": te_p["roi_pct"],
            "test_place_bets": te_p["bets"],
            "test_place_minus_win_pp": (
                float(te_p["roi_pct"] - te_w["roi_pct"])
                if te_w["bets"] and te_p["bets"]
                else float("nan")
            ),
        }

    def sec_win(df):
        return pd.DataFrame(
            {"cost": 1.0, "payout": df["sec_win_payout"], "hit": df["sec_won"]}
        )

    def sec_place(df):
        return pd.DataFrame(
            {"cost": 1.0, "payout": df["sec_place_payout"], "hit": df["sec_placed"]}
        )

    rows = [
        pack("favorite", fav_win_bets, fav_place_bets),
        pack("second_favorite", sec_win, sec_place),
        pack(
            "favorite_odds_le_3",
            lambda d: fav_win_bets(d[d["fav_odds"] <= 3]),
            lambda d: fav_place_bets(d[d["fav_odds"] <= 3]),
        ),
        pack(
            "favorite_odds_gt_5",
            lambda d: fav_win_bets(d[d["fav_odds"] > 5]),
            lambda d: fav_place_bets(d[d["fav_odds"] > 5]),
        ),
        pack(
            "large_field_ge_14",
            lambda d: fav_win_bets(d[d["field_size"] >= 14]),
            lambda d: fav_place_bets(d[d["field_size"] >= 14]),
        ),
    ]
    for row in rows:
        print(
            f"  {row['rule']}: TEST win {row['test_win_roi_pct']:+.2f}% / "
            f"place {row['test_place_roi_pct']:+.2f}%  "
            f"(place−win {row['test_place_minus_win_pp']:+.2f} pp)"
        )

    place_menu = []
    for row in rows:
        place_menu.append(
            {
                "rule": row["rule"] + "_place",
                "train_roi_pct": row["train_place_roi_pct"],
                "train_bets": row["train_place_bets"],
                "test_roi_pct": row["test_place_roi_pct"],
                "test_bets": row["test_place_bets"],
            }
        )
    pdf = pd.DataFrame(place_menu)
    cand = pdf[
        (pdf["train_bets"] >= MIN_TRAIN_BETS)
        & (pdf["test_bets"] >= MIN_TEST_BETS_DIAG)
    ]
    if cand.empty:
        cand = pdf
    best = cand.loc[cand["train_roi_pct"].idxmax()]
    claim = {
        "locked_rule": str(best["rule"]),
        "train_roi_pct": float(best["train_roi_pct"]),
        "test_roi_pct": float(best["test_roi_pct"]),
        "test_bets": int(best["test_bets"]),
        "min_train_bets": MIN_TRAIN_BETS,
        "label": "EXPLORATORY — best train place rule → test claim",
    }
    print(f"\n  LOCKED {claim['locked_rule']} → TEST {claim['test_roi_pct']:+.2f}%")
    return {"comparisons": rows, "claim": claim}


# ---------------------------------------------------------------------------
# Step 7 — Bankroll path (least-bad rule, not an edge claim)
# ---------------------------------------------------------------------------


def step7_bankroll(races: pd.DataFrame, least_bad_rule: str, least_bad_fn) -> dict:
    _section("STEP 7 — Bankroll path of least-bad rule on TEST (illustrative)")
    _, test = split_train_test(races)
    bets = least_bad_fn(test)
    if bets.empty:
        print("  no bets")
        return {"skipped": True}

    bank0 = 1000.0
    # Fractional Kelly-ish: f* ≈ edge/odds; with negative edge use tiny flat
    # fraction just to show path — NOT recommending Kelly on a losing game.
    flat_frac = 0.01  # 1% of bank per bet (tiny)
    bank = bank0
    path = []
    ruin = False
    for i, row in bets.reset_index(drop=True).iterrows():
        stake = max(0.0, bank * flat_frac)
        if stake < 0.01:
            ruin = True
            break
        # Scale payout: bets are $1-unit; multiply by stake
        unit_payout = float(row["payout"])  # for $1
        unit_cost = float(row["cost"])
        pnl = stake * (unit_payout - unit_cost) / unit_cost if unit_cost else 0.0
        bank += pnl
        if i % max(1, len(bets) // 20) == 0 or i == len(bets) - 1:
            path.append({"bet_i": int(i), "bank": float(bank)})

    out = {
        "rule": least_bad_rule,
        "start_bank": bank0,
        "end_bank": float(bank),
        "n_bets": int(len(bets)),
        "flat_frac": flat_frac,
        "roi_pct": float(_roi_from_bets(bets)["roi_pct"]),
        "path_spar": path,
        "hit_ruin_floor": ruin,
        "note": (
            "Illustrative only. Negative-EV rules shrink bankroll; "
            "this is not a Kelly edge — fraction is arbitrary 1%."
        ),
        "label": "EXPLORATORY illustration",
    }
    print(f"  rule={least_bad_rule}  TEST ROI {out['roi_pct']:+.2f}%")
    print(f"  bank ${bank0:.0f} → ${bank:.0f} after {out['n_bets']} bets "
          f"@ {flat_frac:.0%} flat")
    return out


# ---------------------------------------------------------------------------
# Step 8 — McKenna wave-day filter on favorite WIN
# ---------------------------------------------------------------------------


def step8_mckenna(runners: pd.DataFrame, races: pd.DataFrame) -> dict:
    _section("STEP 8 — McKenna wave-day filter on favorite WIN bets")
    # Timewave is a calendar function — compute on full span, filter test days.
    scores = novelty.score_races(runners)
    daily = novelty.daily_novelty(scores, metric="trifecta_novelty")
    primary = compare.compare(daily, number_set="kelley")
    tw = primary["timewave"]

    # Causal low-wave days (novelty hypothesis) at locked 20% (prereg value —
    # used here only as a weak side filter on WIN, still exploratory)
    mask = causal_select_mask(tw, 20.0, side="low")
    wave_days = set(mask.index[mask].map(lambda x: x if hasattr(x, "year") else x))
    # Normalize to date
    wave_days = {pd.Timestamp(d).date() for d in mask.index[mask]}

    train, test = split_train_test(races)
    test = test.copy()
    test["wave_day"] = test["day"].isin(wave_days)
    train = train.copy()
    train["wave_day"] = train["day"].isin(wave_days)

    # Also try high-wave (opposite) and a few predeclared thresholds
    rows = []
    for pct in (10.0, 20.0, 30.0):
        m = causal_select_mask(tw, pct, side="low")
        days = {pd.Timestamp(d).date() for d in m.index[m]}
        for split_name, df in (("train", train), ("test", test)):
            pass
        tr_sub = train[train["day"].isin(days)]
        te_sub = test[test["day"].isin(days)]
        tr = _roi_from_bets(fav_win_bets(tr_sub))
        te = _roi_from_bets(fav_win_bets(te_sub))
        rows.append(
            {
                "rule": f"fav_win_on_low_wave_{pct:.0f}pct",
                "train_roi_pct": tr["roi_pct"],
                "train_bets": tr["bets"],
                "test_roi_pct": te["roi_pct"],
                "test_bets": te["bets"],
                "test_hit_rate": te["hit_rate"],
            }
        )
        print(f"  low-wave {pct:.0f}%: train {tr['roi_pct']:+.2f}% → "
              f"TEST {te['roi_pct']:+.2f}% (n={te['bets']})")

    # High-wave opposite (resonance side) — exploratory
    for pct in (80.0, 90.0):
        m = causal_select_mask(tw, pct, side="high")
        days = {pd.Timestamp(d).date() for d in m.index[m]}
        tr_sub = train[train["day"].isin(days)]
        te_sub = test[test["day"].isin(days)]
        tr = _roi_from_bets(fav_win_bets(tr_sub))
        te = _roi_from_bets(fav_win_bets(te_sub))
        rows.append(
            {
                "rule": f"fav_win_on_high_wave_ge_{pct:.0f}pct",
                "train_roi_pct": tr["roi_pct"],
                "train_bets": tr["bets"],
                "test_roi_pct": te["roi_pct"],
                "test_bets": te["bets"],
                "test_hit_rate": te["hit_rate"],
            }
        )
        print(f"  high-wave ≥{pct:.0f}%: train {tr['roi_pct']:+.2f}% → "
              f"TEST {te['roi_pct']:+.2f}% (n={te['bets']})")

    always_tr = _roi_from_bets(fav_win_bets(train))
    always_te = _roi_from_bets(fav_win_bets(test))
    rows.append(
        {
            "rule": "always_fav_win",
            "train_roi_pct": always_tr["roi_pct"],
            "train_bets": always_tr["bets"],
            "test_roi_pct": always_te["roi_pct"],
            "test_bets": always_te["bets"],
            "test_hit_rate": always_te["hit_rate"],
        }
    )
    print(f"  always fav: train {always_tr['roi_pct']:+.2f}% → "
          f"TEST {always_te['roi_pct']:+.2f}% (n={always_te['bets']})")

    rdf = pd.DataFrame(rows)
    # Lock best train among wave filters (not always) with enough bets
    cand = rdf[
        (rdf["rule"] != "always_fav_win")
        & (rdf["train_bets"] >= MIN_TRAIN_BETS)
    ]
    if cand.empty:
        cand = rdf[rdf["rule"] != "always_fav_win"]
    best = cand.loc[cand["train_roi_pct"].idxmax()]
    delta = float(best["test_roi_pct"] - always_te["roi_pct"])
    claim = {
        "locked_rule": str(best["rule"]),
        "train_roi_pct": float(best["train_roi_pct"]),
        "test_roi_pct": float(best["test_roi_pct"]),
        "test_bets": int(best["test_bets"]),
        "always_fav_test_roi_pct": float(always_te["roi_pct"]),
        "test_delta_vs_always_pp": delta,
        "helps_vs_always": delta > 0,
        "min_train_bets": MIN_TRAIN_BETS,
        "label": "EXPLORATORY — wave filter on WIN; delta vs always-fav on TEST",
    }
    print(f"\n  LOCKED {claim['locked_rule']} → TEST {claim['test_roi_pct']:+.2f}% "
          f"(Δ vs always {delta:+.2f} pp)")
    return {
        "rules": rows,
        "claim": claim,
        "primary_spearman_r": float(primary["spearman_r"]),
        "primary_permutation_p": float(primary["permutation_p"]),
    }


# ---------------------------------------------------------------------------
# Step 9 — Random baseline
# ---------------------------------------------------------------------------


def step9_random(runners: pd.DataFrame) -> dict:
    _section("STEP 9 — Random baseline (expect ~−takeout)")
    train, test = split_train_test(runners)
    rng = np.random.default_rng(SEED)

    def random_one_per_race(df: pd.DataFrame, market: str) -> dict:
        picks = []
        for rid, g in df.groupby("race_id"):
            idx = rng.integers(0, len(g))
            row = g.iloc[idx]
            if market == "win":
                pay = float(row["win_payout"]) if row["won"] == 1 and pd.notna(row["win_payout"]) else 0.0
                hit = int(row["won"] == 1)
            else:
                pay = float(row["place_payout"]) if pd.notna(row["place_payout"]) else 0.0
                hit = int(pd.notna(row["place_payout"]))
            picks.append({"cost": 1.0, "payout": pay, "hit": hit})
        return _roi_from_bets(pd.DataFrame(picks))

    out = {}
    for market in ("win", "place"):
        for name, df in (("train", train), ("test", test), ("full", runners)):
            s = random_one_per_race(df, market)
            key = f"random_{market}_{name}"
            out[key] = s
            print(f"  {key}: ROI {s['roi_pct']:+.2f}%  n={s['bets']}  hit={s['hit_rate']:.3f}")

    out["interpretation"] = (
        "Random one-runner-per-race should lose roughly the pool takeout / overround. "
        "If clever filters are not clearly better than random AND better than −takeout "
        "on TEST, they are not interesting."
    )
    return out


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def write_report(payload: dict) -> None:
    OUT_DIR.mkdir(exist_ok=True)
    lines: list[str] = []
    lines.append("# Win/place poke — exploratory lab notebook")
    lines.append("")
    lines.append("**Label:** All sections are **exploratory**. Not pre-registered.")
    lines.append(
        "**Discipline:** Lock rules on train (≤2002-12-31); **test ROI** (2003+) is the claim."
    )
    lines.append("**Data:** Free bundled `hk_runners.csv` + local `rawdata/` enrichments only.")
    lines.append("**Hard rules:** no prereg edits; no paid feeds; no fake edges.")
    lines.append("")
    lines.append("Generated by `scripts/exploratory_win_place_poke.py`.")
    lines.append("")

    inv = payload["step0"]
    lines.append("## Step 0 — Inventory")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    for k, v in inv.items():
        lines.append(f"| {k} | {v} |")
    lines.append("")
    lines.append(
        f"Mean win-market overround ≈ **{inv['mean_overround']:.3f}** "
        f"(takeout proxy **{inv['takeout_proxy_pct']:.1f}%**). "
        f"Nominal HK win takeout reference ~{inv['nominal_win_takeout_pct']:.1f}%."
    )
    lines.append("")

    b = payload["baselines"]
    lines.append("## Baselines — always favorite")
    lines.append("")
    lines.append("| Split | Win ROI | Place ROI | Win n | Place n |")
    lines.append("|---|---|---|---|---|")
    for split in ("full", "train", "test"):
        w, p = b[f"fav_win_{split}"], b[f"fav_place_{split}"]
        lines.append(
            f"| {split} | {w['roi_pct']:+.2f}% | {p['roi_pct']:+.2f}% | "
            f"{w['bets']} | {p['bets']} |"
        )
    lines.append("")
    lines.append(
        "**Suggestion:** Favorite win/place both lose ~15–20% on this sample — "
        "consistent with prior edge-hunt. Anything we keep must beat this *and* "
        "random on **test**, not just look less red on train."
    )
    lines.append("")

    s1 = payload["step1"]
    lines.append("## Step 1 — Fade longshots (odds ≤ X)")
    lines.append("")
    lines.append("### Pre-declared flat $1 every runner with odds ≤ X")
    lines.append("")
    lines.append(_tbl(pd.DataFrame(s1["predeclared_flat"])[
        ["cap", "train_roi_pct", "train_bets", "test_roi_pct", "test_bets", "test_hit_rate"]
    ]))
    lines.append("")
    lines.append("### Pre-declared favorite only if fav odds ≤ X")
    lines.append("")
    lines.append(_tbl(pd.DataFrame(s1["predeclared_fav"])[
        ["cap", "train_roi_pct", "train_bets", "test_roi_pct", "test_bets", "test_hit_rate"]
    ]))
    lines.append("")
    c = s1["claim"]
    lines.append(
        f"**Train-locked claim:** flat cap={c['locked_flat_cap']} → "
        f"test ROI **{c['flat_test_roi_pct']:+.2f}%** (n={c['flat_test_bets']}); "
        f"fav cap={c['locked_fav_cap']} → test ROI **{c['fav_test_roi_pct']:+.2f}%** "
        f"(n={c['fav_test_bets']})."
    )
    lines.append("")
    lines.append(c["bonferroni_note"])
    lines.append("")
    lines.append(
        "**Suggestion:** Shortest caps are least-bad on train (classic FLB) but "
        "still red on test. Fading longshots reduces damage; it does not create edge."
    )
    lines.append("")

    s2 = payload["step2"]
    lines.append("## Step 2 — Overlay / underlay vs field")
    lines.append("")
    lines.append(_tbl(pd.DataFrame(s2["rules"])))
    lines.append("")
    c2 = s2["claim"]
    lines.append(
        f"**Claim:** `{c2['locked_rule']}` → test ROI **{c2['test_roi_pct']:+.2f}%** "
        f"(n={c2['test_bets']})."
    )
    lines.append("")
    lines.append(
        "**Suggestion:** Field-relative favorite pricing is a cute idea; if test "
        "does not beat always-favorite by a clear margin, drop it."
    )
    lines.append("")

    s3 = payload["step3"]
    lines.append("## Step 3 — Favorite streaks on the card")
    lines.append("")
    lines.append(_tbl(pd.DataFrame(s3["rules"])))
    lines.append("")
    c3 = s3["claim"]
    lines.append(
        f"**Claim:** `{c3['locked_rule']}` → test ROI **{c3['test_roi_pct']:+.2f}%** "
        f"(n={c3['test_bets']})."
    )
    lines.append("")
    lines.append(
        "**Suggestion:** Streak / card-position filters are multiple-comparison bait. "
        "Only keep if test clearly beats always-fav *and* survives a second holdout."
    )
    lines.append("")

    s4 = payload["step4"]
    lines.append("## Step 4 — Horse follow (won last start)")
    lines.append("")
    if s4.get("skipped"):
        lines.append(f"_Skipped: {s4.get('reason')}_")
    else:
        lines.append(_tbl(pd.DataFrame(s4["rules"])))
        lines.append("")
        c4 = s4["claim"]
        lines.append(
            f"**Claim:** `{c4['locked_rule']}` ({c4['market']}) → "
            f"test ROI **{c4['test_roi_pct']:+.2f}%** (n={c4['test_bets']})."
        )
        lines.append("")
        lines.append(
            "**Suggestion:** Last-out winners are public information; market usually "
            "prices them. A green train that dies on test = bounce, not edge."
        )
    lines.append("")

    s5 = payload["step5"]
    lines.append("## Step 5 — Odds movement")
    lines.append("")
    lines.append(f"_Skipped:_ {s5.get('reason', 'n/a')}")
    lines.append("")

    s6 = payload["step6"]
    lines.append("## Step 6 — Place vs win")
    lines.append("")
    lines.append(_tbl(pd.DataFrame(s6["comparisons"])))
    lines.append("")
    c6 = s6["claim"]
    lines.append(
        f"**Claim (best train place rule):** `{c6['locked_rule']}` → "
        f"test ROI **{c6['test_roi_pct']:+.2f}%** (n={c6['test_bets']})."
    )
    lines.append("")
    lines.append(
        "**Suggestion:** If place is only a few points less bad than win, that is "
        "takeout structure — not a strategy. Prefer the market with better test ROI "
        "only if the gap is large and stable."
    )
    lines.append("")

    s7 = payload["step7"]
    lines.append("## Step 7 — Bankroll path (illustrative)")
    lines.append("")
    if s7.get("skipped"):
        lines.append("_Skipped — no bets._")
    else:
        lines.append(
            f"Least-bad rule on test context: **`{s7['rule']}`** "
            f"(test ROI {s7['roi_pct']:+.2f}%)."
        )
        lines.append("")
        lines.append(
            f"Flat {s7['flat_frac']:.0%} of bank: "
            f"${s7['start_bank']:.0f} → **${s7['end_bank']:.0f}** "
            f"over {s7['n_bets']} bets."
        )
        lines.append("")
        lines.append(s7["note"])
        lines.append("")
        lines.append(_tbl(pd.DataFrame(s7["path_spar"])))
    lines.append("")

    s8 = payload["step8"]
    lines.append("## Step 8 — McKenna wave-day filter on favorite WIN")
    lines.append("")
    lines.append(
        f"Primary novelty↔timewave (restatement): Spearman r="
        f"{s8['primary_spearman_r']:+.4f}, perm p={s8['primary_permutation_p']:.3f}."
    )
    lines.append("")
    lines.append(_tbl(pd.DataFrame(s8["rules"])))
    lines.append("")
    c8 = s8["claim"]
    lines.append(
        f"**Claim:** `{c8['locked_rule']}` → test ROI **{c8['test_roi_pct']:+.2f}%** "
        f"(always-fav test {c8['always_fav_test_roi_pct']:+.2f}%, "
        f"Δ **{c8['test_delta_vs_always_pp']:+.2f} pp**). "
        f"{'Helps a little on test.' if c8['helps_vs_always'] else 'Does not help vs always-fav on test.'}"
    )
    lines.append("")
    lines.append(
        "**Suggestion:** Wave timing was designed for exotic novelty, not favorite "
        "win bets. If Δ is small/noisy, stop using McKenna as a win-side filter."
    )
    lines.append("")

    s9 = payload["step9"]
    lines.append("## Step 9 — Random baseline")
    lines.append("")
    lines.append("| Key | ROI | Bets | Hit |")
    lines.append("|---|---|---|---|")
    for k, v in s9.items():
        if not isinstance(v, dict) or "roi_pct" not in v:
            continue
        lines.append(
            f"| {k} | {v['roi_pct']:+.2f}% | {v['bets']} | {v['hit_rate']:.3f} |"
        )
    lines.append("")
    lines.append(s9["interpretation"])
    lines.append("")

    lines.append("## Overall verdict")
    lines.append("")
    lines.append(payload["verdict_md"])
    lines.append("")

    lines.append("## Plain English")
    lines.append("")
    lines.append(payload["plain_english"])
    lines.append("")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    print(f"\nWrote {OUT_MD}")
    print(f"Wrote {OUT_JSON}")


def build_verdict(payload: dict) -> tuple[str, str]:
    """Return (verdict_md, plain_english)."""
    takeout = payload["step0"]["takeout_proxy_pct"]
    claims = []
    for key, label in [
        ("step1", "fade_longshot"),
        ("step2", "overlay"),
        ("step3", "streak"),
        ("step4", "horse_follow"),
        ("step6", "place"),
        ("step8", "mckenna_win"),
    ]:
        s = payload.get(key, {})
        if s.get("skipped"):
            continue
        c = s.get("claim", {})
        if not c:
            continue
        # Normalize test roi field names
        if "test_roi_pct" in c:
            roi = c["test_roi_pct"]
            rule = c.get("locked_rule", c.get("locked_fav_cap", "?"))
            n = c.get("test_bets", c.get("fav_test_bets", "?"))
        elif "fav_test_roi_pct" in c:
            roi = c["fav_test_roi_pct"]
            rule = f"fav_cap_{c['locked_fav_cap']}"
            n = c["fav_test_bets"]
            claims.append((label + "_fav", rule, roi, n))
            roi2 = c["flat_test_roi_pct"]
            claims.append((label + "_flat", f"flat_cap_{c['locked_flat_cap']}", roi2, c["flat_test_bets"]))
            continue
        else:
            continue
        claims.append((label, str(rule), float(roi), n))

    # Also add always-fav test as reference row
    af = payload["baselines"]["fav_win_test"]["roi_pct"]
    ap = payload["baselines"]["fav_place_test"]["roi_pct"]
    rnd = payload["step9"].get("random_win_test", {}).get("roi_pct", float("nan"))
    claims.append(
        (
            "baseline",
            "always_fav_win",
            float(af),
            payload["baselines"]["fav_win_test"]["bets"],
        )
    )

    # Best (least bad) test claim among locked rules with adequate n
    eligible = [t for t in claims if isinstance(t[3], (int, float)) and t[3] >= MIN_TEST_BETS_DIAG]
    if not eligible:
        eligible = claims
    if eligible:
        best = max(eligible, key=lambda t: t[2])
    else:
        best = ("none", "none", float("nan"), 0)

    # Flag: any non-locked diagnostic that looked green on test (thin n)
    thin_notes = []
    for key in ("step3", "step4"):
        thin = payload.get(key, {}).get("thin_diagnostic") or []
        for row in thin:
            if row.get("test_roi_pct", -999) > 0:
                thin_notes.append(
                    f"`{row['rule']}` test {row['test_roi_pct']:+.1f}% "
                    f"(n={int(row['test_bets'])}, train_n={int(row['train_bets'])}) "
                    "— NOT a claim (too thin to lock)."
                )

    beat_takeout = best[2] > -0.5 * takeout  # "meaningfully" better than -takeout
    # stricter: positive or within a few pp of 0
    meaningful = best[2] > -5.0  # still losing but maybe interesting
    green = best[2] > 0

    parts = []
    parts.append(
        f"**No free win/place edge found** on holdout. "
        f"Always-favorite test win ROI **{af:+.2f}%**, place **{ap:+.2f}%**; "
        f"random win test **{rnd:+.2f}%**; overround proxy **−{takeout:.1f}%**."
    )
    parts.append("")
    parts.append("### Locked-rule test ROIs (claims only)")
    parts.append("")
    parts.append("| Family | Locked rule | Test ROI | Test bets |")
    parts.append("|---|---|---|---|")
    for fam, rule, roi, n in sorted(claims, key=lambda t: -t[2]):
        parts.append(f"| {fam} | `{rule}` | {roi:+.2f}% | {n} |")
    parts.append("")
    parts.append(
        f"**Least-bad locked rule on test (n≥{MIN_TEST_BETS_DIAG}):** `{best[1]}` ({best[0]}) at "
        f"**{best[2]:+.2f}%** (n={best[3]})."
    )
    if thin_notes:
        parts.append("")
        parts.append("**Thin green cells (noise, not claims):**")
        for note in thin_notes:
            parts.append(f"- {note}")
    if green:
        parts.append(
            "Positive on test — treat as a **weak lead only** (train selection + "
            "one holdout look + multiplicity). Needs a fresh window before any claim."
        )
    elif best[0] != "baseline" and best[2] > af + 1.0:
        parts.append(
            f"Best locked rule beats always-favorite by "
            f"**{best[2] - af:+.2f} pp** on test, but remains deeply negative "
            f"({best[2]:+.2f}%). That is damage-control noise under multiplicity — "
            "**not** interesting enough to keep as a strategy."
        )
    elif best[2] >= af - 0.5 and best[0] != "baseline":
        parts.append(
            "Locked filters are roughly tied with always-favorite on test. "
            "Train-locking often *worsens* holdout on other families (classic overfit)."
        )
    elif beat_takeout or meaningful:
        parts.append(
            "Still negative; modestly less bad than raw takeout "
            "is **not** an edge — at best a damage-control curiosity."
        )
    else:
        parts.append(
            "Does not beat −takeout in any interesting way. "
            "**Stop** searching free win/place filters on this sample."
        )
    parts.append("")
    # Honest note: long-for-field looked good on test but lost on train (not locked)
    s2_rules = payload.get("step2", {}).get("rules") or []
    lucky = [
        r for r in s2_rules
        if r["rule"] != "always_fav"
        and r["test_roi_pct"] > af
        and r["train_roi_pct"] < payload["baselines"]["fav_win_train"]["roi_pct"]
    ]
    if lucky:
        parts.append(
            "**Lookahead warning:** some filters look better than always-fav on *test* "
            "but were worse on *train* (would never have been locked). Example: "
            + ", ".join(
                f"`{r['rule']}` test {r['test_roi_pct']:+.1f}% / train {r['train_roi_pct']:+.1f}%"
                for r in lucky[:3]
            )
            + ". Do not promote these."
        )
        parts.append("")
    parts.append(
        "McKenna as a win-side day filter: see Step 8 Δ vs always-fav. "
        "Odds movement: unavailable. Paid exotic dividends remain the unblock for "
        "the *project* thesis — but user said no spend; **free win/place poke should stop**."
    )

    # Plain English
    pe = []
    pe.append(
        f"We tried a bunch of free betting filters on Hong Kong races "
        f"(1997–2002 to pick rules, 2003–2005 to grade them). "
        f"Betting the favorite every time still loses about **{abs(af):.0f}%** on the test years. "
        f"Picking a horse at random loses about **{abs(rnd):.0f}%** — in the takeout ballpark "
        f"(random is noisier and often worse)."
    )
    pe.append("")
    pe.append(
        f"Among rules we were allowed to lock (enough train bets), the least-bad on test was "
        f"**{best[1]}** at **{best[2]:+.1f}%**. "
        + (
            "Still not something to bet — and several 'clever' filters did *worse* than plain favorites."
            if best[2] < 0
            else "Green on one holdout with selection bias — not enough to call an edge."
        )
    )
    pe.append("")
    if thin_notes:
        pe.append(
            "One tiny streak cell went green on test with only a few dozen bets — "
            "that is noise, not a system. We excluded it from locking on purpose."
        )
        pe.append("")
    pe.append(
        "McKenna's calendar wave as a 'only bet favorites on special days' filter "
        + (
            "helped a little vs always-favorite on test — still a loser; footnote at best."
            if payload["step8"]["claim"].get("helps_vs_always")
            else "did not help vs always-favorite on test — drop it for win bets."
        )
    )
    pe.append("")
    pe.append(
        "Bottom line: **no real free win/place edge**. Best honest loser is still "
        "roughly 'bet favorites / short odds' and you still bleed. "
        "**Stop** poking free win/place on this dump unless new free columns appear."
    )
    return "\n".join(parts), "\n".join(pe)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.parse_args()

    _section("LOAD")
    runners = enrich_runners(data.load_bundled_hk())
    races = race_table(runners)
    print(f"  race table: {len(races)} races")

    payload: dict = {}
    payload["step0"] = step0(runners, races)
    payload["baselines"] = step_baselines(races)
    payload["step1"] = step1_fade_longshots(runners, races)
    payload["step2"] = step2_overlay(races)
    payload["step3"] = step3_streaks(races)
    payload["step4"] = step4_horse_follow(runners)
    payload["step5"] = step5_odds_move()
    payload["step6"] = step6_place_vs_win(races)
    payload["step8"] = step8_mckenna(runners, races)
    payload["step9"] = step9_random(runners)

    # Pick least-bad among locked claims for bankroll illustration.
    def streak_2plus(df: pd.DataFrame) -> pd.DataFrame:
        r = df.sort_values(["date", "race_no", "race_id"]).copy()
        chunks = []
        for _, day in r.groupby(r["date"].dt.date, sort=False):
            d = day.copy()
            prior_wins = d["fav_won"].cumsum().shift(1).fillna(0).astype(int)
            d["prior_fav_wins_today"] = prior_wins.values
            chunks.append(d)
        r = pd.concat(chunks, ignore_index=True)
        return fav_win_bets(r[r["prior_fav_wins_today"] >= 2])

    candidates = []
    af_test = payload["baselines"]["fav_win_test"]
    candidates.append(("always_fav_win", af_test["roi_pct"], fav_win_bets))

    c1 = payload["step1"]["claim"]
    cap = c1["locked_fav_cap"]

    def fav_cap_fn(df, c=cap):
        return fav_win_bets(df[df["fav_odds"] <= c])

    candidates.append(
        (f"fav_odds_le_{cap}", c1["fav_test_roi_pct"], fav_cap_fn)
    )

    c3 = payload["step3"]["claim"]
    if c3["locked_rule"] == "after_2plus_prior_fav_wins":
        candidates.append(
            (c3["locked_rule"], c3["test_roi_pct"], streak_2plus)
        )
    else:
        candidates.append((c3["locked_rule"], c3["test_roi_pct"], None))

    for key in ("step2", "step6", "step8"):
        c = payload[key]["claim"]
        candidates.append((c["locked_rule"], c["test_roi_pct"], None))

    callable_cands = [(n, r, f) for n, r, f in candidates if f is not None]
    best_name, best_roi, best_fn = max(callable_cands, key=lambda t: t[1])
    all_rois = [(n, r) for n, r, _ in candidates]
    overall_best = max(all_rois, key=lambda t: t[1])
    print(f"\n  Least-bad among callables: {best_name} ({best_roi:+.2f}%)")
    print(f"  Least-bad among all locked labels: {overall_best[0]} ({overall_best[1]:+.2f}%)")

    payload["step7"] = step7_bankroll(races, best_name, best_fn)
    payload["least_bad"] = {
        "callable_rule": best_name,
        "callable_test_roi_pct": best_roi,
        "overall_best_label": overall_best[0],
        "overall_best_test_roi_pct": overall_best[1],
    }

    verdict, plain = build_verdict(payload)
    payload["verdict_md"] = verdict
    payload["plain_english"] = plain
    write_report(payload)

    _section("VERDICT")
    print(verdict)
    print("\n--- Plain English ---\n")
    print(plain)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

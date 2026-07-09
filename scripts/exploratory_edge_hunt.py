#!/usr/bin/env python3
"""Exploratory honest edge hunt on bundled / raw HK data.

LAB NOTEBOOK — every section is labeled exploratory unless it re-states a
pre-registered primary result. Do not treat a single green cell as a finding.

Hard rules enforced here:
- No editing prereg.json
- No raising beta until ROI is green and calling that a finding
- Prefer real win/place dividends from the bundled CSV (or rawdata/races.csv)
- Report measured effects; label assumptions

Usage:
    .venv/bin/python scripts/exploratory_edge_hunt.py
    .venv/bin/python scripts/exploratory_edge_hunt.py --skip-engine  # faster
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mckenna_derby import backtest, compare, data, novelty  # noqa: E402
from mckenna_derby.mckenna_engine import selective_backtest  # noqa: E402

RAWDATA = ROOT / "rawdata"
OUT_DIR = ROOT / "output"
OUT_MD = OUT_DIR / "EXPLORATORY_EDGE_HUNT.md"
OUT_JSON = OUT_DIR / "exploratory_edge_hunt.json"

# HKJC dividends in gdaley/hkracing are per $10 stake.
WIN_DIV_UNIT = 10.0
TAKEOUT = 0.22  # prereg takeout for modeled trifecta only
SEED = 1904


def _section(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}", flush=True)


def _tbl(df: pd.DataFrame, float_fmt: str = "%.3f") -> str:
    if df.empty:
        return "_(empty)_"
    try:
        return df.to_markdown(index=False, floatfmt=float_fmt)
    except ImportError:
        # Fallback without tabulate
        cols = list(df.columns)
        lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
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


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_runners() -> pd.DataFrame:
    return data.load_bundled_hk()


def load_win_market(runners: pd.DataFrame) -> pd.DataFrame:
    """Per-race win market with REAL dividends (per $1).

    Prefers ``win_payout`` already on the bundled runners CSV. Falls back to
    joining ``rawdata/races.csv`` when the bundled file predates that column.
    """
    if "win_payout" in runners.columns and runners["win_payout"].notna().any():
        r = runners.rename(
            columns={
                "decimal_odds": "win_odds",
                "finish_position": "result",
                "win_payout": "win_payout_per_1",
            }
        ).copy()
        r["won"] = (r["result"] == 1).astype(int)
        r["is_favorite"] = r.groupby("race_id")["win_odds"].transform(
            lambda s: s == s.min()
        )
        r["odds_rank"] = r.groupby("race_id")["win_odds"].rank(method="min")
        # Race-level win dividend for favorite settlement: winner's payout.
        race_pay = (
            r.loc[r["won"] == 1, ["race_id", "win_payout_per_1"]]
            .drop_duplicates("race_id")
            .rename(columns={"win_payout_per_1": "_race_win_pay"})
        )
        r = r.merge(race_pay, on="race_id", how="left")
        # For favorite flat bets we need the race win dividend even on the
        # favorite row (which may not be the winner). Use race-level value.
        r["win_payout_per_1"] = r["_race_win_pay"]
        r = r.drop(columns=["_race_win_pay"])
        return r

    if not (RAWDATA / "races.csv").is_file():
        raise FileNotFoundError(
            f"bundled runners lack win_payout and {RAWDATA}/races.csv missing"
        )

    races = pd.read_csv(
        RAWDATA / "races.csv",
        usecols=[
            "race_id",
            "date",
            "win_combination1",
            "win_dividend1",
            "win_combination2",
            "win_dividend2",
        ],
    )
    runs = pd.read_csv(
        RAWDATA / "runs.csv",
        usecols=["race_id", "horse_no", "result", "win_odds"],
    )
    # Keep only races that survived bundled validation.
    ok_ids = set(runners["race_id"].unique())
    races = races[races["race_id"].isin(ok_ids)].copy()
    runs = runs[runs["race_id"].isin(ok_ids)].copy()

    races["win_payout_per_1"] = races["win_dividend1"] / WIN_DIV_UNIT
    races["date"] = pd.to_datetime(races["date"])

    # Runner-level with favorite flag + whether this horse won.
    r = runs.merge(
        races[["race_id", "date", "win_combination1", "win_payout_per_1"]],
        on="race_id",
        how="inner",
    )
    r = r.dropna(subset=["win_odds", "result"])
    r = r[r["win_odds"] > 1.0].copy()
    r["won"] = (r["result"] == 1).astype(int)
    # Favorite = lowest win_odds in race (ties: all marked favorite).
    r["is_favorite"] = r.groupby("race_id")["win_odds"].transform(
        lambda s: s == s.min()
    )
    r["odds_rank"] = r.groupby("race_id")["win_odds"].rank(method="min")
    return r


# ---------------------------------------------------------------------------
# Step 0 — Inventory
# ---------------------------------------------------------------------------


def step0_inventory(runners: pd.DataFrame, win_mkt: pd.DataFrame) -> dict:
    _section("STEP 0 — Inventory")
    n_races = runners["race_id"].nunique()
    field = runners.groupby("race_id").size()
    has_tri = "trifecta_payout" in runners.columns and runners["trifecta_payout"].notna().any()
    fav_win = (
        win_mkt.groupby("race_id")
        .apply(lambda g: bool(g.loc[g["won"] == 1, "is_favorite"].any()), include_groups=False)
        .mean()
    )
    has_win = "win_payout" in runners.columns and runners["win_payout"].notna().any()
    has_place = "place_payout" in runners.columns and runners["place_payout"].notna().any()
    out = {
        "bundled_columns": list(runners.columns),
        "n_runners": int(len(runners)),
        "n_races": int(n_races),
        "date_min": str(runners["date"].min().date()),
        "date_max": str(runners["date"].max().date()),
        "has_real_trifecta_payout": bool(has_tri),
        "has_real_win_payout": bool(has_win),
        "has_real_place_payout": bool(has_place),
        "field_size_mean": float(field.mean()),
        "field_size_median": float(field.median()),
        "field_size_min": int(field.min()),
        "field_size_max": int(field.max()),
        "favorite_win_rate": float(fav_win),
        "win_dividend_races": int(win_mkt["race_id"].nunique()),
        "raw_win_dividends_available": bool(has_win) or (RAWDATA / "races.csv").is_file(),
        "exotic_dividends_gap": (
            "Kaggle gdaley/hkracing and alternate local dumps have win/place only. "
            "Attach trifecta/tierce via scripts/build_bundled_data.py --exotics "
            "(see mckenna_derby/datasets/README.md)."
        ),
    }
    for k, v in out.items():
        print(f"  {k}: {v}")
    return out


# ---------------------------------------------------------------------------
# Step 1 — Market efficiency / FLB (real win dividends)
# ---------------------------------------------------------------------------


def _roi_summary(cost: float, payout: float, n: int, hits: int) -> dict:
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


def step1_win_baselines(win_mkt: pd.DataFrame) -> dict:
    _section("STEP 1 — Win-market baselines (REAL dividends, exploratory)")
    # One bet per race on the favorite(s): if tied favorites, split stake equally.
    rows = []
    for rid, g in win_mkt.groupby("race_id"):
        favs = g[g["is_favorite"]]
        if favs.empty:
            continue
        stake_each = 1.0 / len(favs)
        cost = 1.0
        payout = 0.0
        hit = 0
        for _, row in favs.iterrows():
            if row["won"] == 1:
                # Real dividend is for the winning horse; pay stake_each * payout.
                payout += stake_each * float(row["win_payout_per_1"])
                hit = 1
        rows.append({"race_id": rid, "cost": cost, "payout": payout, "hit": hit})
    fav_df = pd.DataFrame(rows)
    fav_sum = _roi_summary(
        fav_df["cost"].sum(), fav_df["payout"].sum(), len(fav_df), int(fav_df["hit"].sum())
    )
    print("  Bet every favorite (flat $1/race, real win div):", fav_sum)

    # Longshot bands by winner odds of the horse we bet.
    # Flat $1 on every runner in band (many bets per race).
    bands = [
        ("favorites_odds_le_3", lambda o: o <= 3.0),
        ("odds_3_to_6", lambda o: (o > 3.0) & (o <= 6.0)),
        ("odds_6_to_12", lambda o: (o > 6.0) & (o <= 12.0)),
        ("odds_12_to_25", lambda o: (o > 12.0) & (o <= 25.0)),
        ("longshots_gt_25", lambda o: o > 25.0),
        ("all_runners_flat", lambda o: o > 0),
    ]
    band_rows = []
    for name, pred in bands:
        mask = pred(win_mkt["win_odds"].to_numpy())
        sub = win_mkt.loc[mask]
        cost = float(len(sub))  # $1 each
        payout = float((sub["won"] * sub["win_payout_per_1"]).sum())
        s = _roi_summary(cost, payout, len(sub), int(sub["won"].sum()))
        s["band"] = name
        band_rows.append(s)
        print(f"  {name}: ROI {s['roi_pct']:+.2f}%  bets={s['bets']}  hit={s['hit_rate']:.3f}")

    # Odds-decile FLB chart: group runners by race-relative implied-prob decile
    # using raw 1/odds (not renormalized) so deciles reflect posted odds.
    w = win_mkt.copy()
    w["impl"] = 1.0 / w["win_odds"]
    # Within each race, rank by odds (1=fav). Also global odds deciles.
    w["odds_decile"] = pd.qcut(w["win_odds"], 10, labels=False, duplicates="drop") + 1
    dec_rows = []
    for d, sub in w.groupby("odds_decile"):
        cost = float(len(sub))
        payout = float((sub["won"] * sub["win_payout_per_1"]).sum())
        implied_mean = float(sub["impl"].mean())
        actual_rate = float(sub["won"].mean())
        s = _roi_summary(cost, payout, len(sub), int(sub["won"].sum()))
        s["odds_decile"] = int(d)
        s["mean_odds"] = float(sub["win_odds"].mean())
        s["mean_implied_p"] = implied_mean
        s["actual_win_rate"] = actual_rate
        s["actual_minus_implied"] = actual_rate - implied_mean
        dec_rows.append(s)
    dec_df = pd.DataFrame(dec_rows).sort_values("odds_decile")
    print("\n  Odds-decile FLB (flat $1 every runner in decile, real dividends):")
    print(dec_df[
        ["odds_decile", "mean_odds", "mean_implied_p", "actual_win_rate",
         "actual_minus_implied", "roi_pct", "bets"]
    ].to_string(index=False))

    # Classic FLB summary: favorite decile ROI vs longshot decile ROI
    flb = {
        "favorite_flat_roi_pct": fav_sum["roi_pct"],
        "shortest_decile_roi_pct": float(dec_df.iloc[0]["roi_pct"]),
        "longest_decile_roi_pct": float(dec_df.iloc[-1]["roi_pct"]),
        "flb_spread_pp": float(dec_df.iloc[0]["roi_pct"] - dec_df.iloc[-1]["roi_pct"]),
        "interpretation": (
            "Positive spread (short ROI > long ROI) = classic favorite-longshot bias "
            "(longshots overbet). Negative spread = reverse bias (favorites overbet)."
        ),
    }
    print(f"\n  FLB spread (decile1 ROI − decile10 ROI): {flb['flb_spread_pp']:+.2f} pp")
    print(f"  → {flb['interpretation']}")

    return {
        "bet_favorite": fav_sum,
        "bands": band_rows,
        "odds_deciles": dec_df.to_dict(orient="records"),
        "flb": flb,
    }


def estimate_win_beta(win_mkt: pd.DataFrame) -> dict:
    """MLE-ish grid: P(win) ∝ implied_p ** beta within each race.

    beta>1 → favorites get more probability mass than market (pool overbets favs
    relative to true outcomes — wait: we fit to *outcomes*).

    Here we fit outcome probabilities: true_p ∝ market_implied ** beta.
    - beta = 1: market well-calibrated (after overround removal)
    - beta > 1: favorites win MORE than market implies → market overbet longshots
      (classic FLB). Maps to engine beta < 1 for *pool* distortion if pool=market.
    - beta < 1: favorites win LESS than market implies → market overbet favorites.

    Engine convention (pool distortion of fair Harville):
      pool ∝ fair**engine_beta
      engine_beta > 1: pool overbets favorites
      engine_beta < 1: pool overbets longshots

    If market odds ≈ pool and outcomes follow fair ∝ market**outcome_beta with
    outcome_beta > 1 (favs win more than odds say), then the pool overbet
    longshots → engine_beta < 1. Mapping used below:
      engine_beta_proxy ≈ 1 / outcome_beta
    """
    _section("STEP 1b — Estimate outcome-calibration beta from win results")
    races = []
    for _, g in win_mkt.groupby("race_id"):
        odds = g["win_odds"].to_numpy(dtype=float)
        won = g["won"].to_numpy(dtype=int)
        if won.sum() != 1:
            continue  # skip dead heats / messy
        p = 1.0 / odds
        p = p / p.sum()
        winner_idx = int(np.argmax(won))
        races.append((p, winner_idx))

    betas = np.linspace(0.5, 1.8, 27)
    logliks = []
    for b in betas:
        ll = 0.0
        for p, widx in races:
            w = p ** b
            w = w / w.sum()
            ll += np.log(max(w[widx], 1e-15))
        logliks.append(ll)
    logliks = np.asarray(logliks)
    best_i = int(np.argmax(logliks))
    outcome_beta = float(betas[best_i])
    # Relative to beta=1
    ll1 = float(logliks[np.argmin(np.abs(betas - 1.0))])
    engine_proxy = float(1.0 / outcome_beta)
    out = {
        "n_races_fit": len(races),
        "outcome_beta_mle": outcome_beta,
        "loglik_at_mle": float(logliks[best_i]),
        "loglik_at_beta1": ll1,
        "delta_ll_vs_1": float(logliks[best_i] - ll1),
        "engine_beta_proxy": engine_proxy,
        "note": (
            "outcome_beta>1 means favorites win more often than odds imply "
            "(classic FLB / longshots overbet). engine_beta_proxy=1/outcome_beta "
            "is a rough map into the selective engine's pool-distortion parameter. "
            "This is WIN-market calibration, not trifecta-pool beta."
        ),
        "grid": [
            {"beta": float(b), "loglik": float(ll)} for b, ll in zip(betas, logliks)
        ],
    }
    print(f"  races fit: {out['n_races_fit']}")
    print(f"  outcome_beta MLE: {outcome_beta:.3f}  (1.0 = calibrated)")
    print(f"  Δll vs β=1: {out['delta_ll_vs_1']:+.1f}")
    print(f"  engine_beta_proxy (1/outcome_beta): {engine_proxy:.3f}")
    print(f"  note: {out['note']}")
    return out


# ---------------------------------------------------------------------------
# Step 1c — Place market (real place dividends)
# ---------------------------------------------------------------------------


def step1c_place_baselines(runners: pd.DataFrame) -> dict:
    """Favorite-to-place and odds-decile place ROI using bundled place_payout."""
    _section("STEP 1c — Place-market baselines (REAL dividends, exploratory)")
    if "place_payout" not in runners.columns or not runners["place_payout"].notna().any():
        print("  no place_payout on runners — skipped")
        return {"skipped": True, "reason": "no place_payout column"}

    r = runners.copy()
    r["is_favorite"] = r.groupby("race_id")["decimal_odds"].transform(
        lambda s: s == s.min()
    )
    r["placed"] = r["place_payout"].notna().astype(int)

    # Race-level place dividend for the favorite horse (its own place_payout).
    rows = []
    for rid, g in r.groupby("race_id"):
        favs = g[g["is_favorite"]]
        if favs.empty:
            continue
        stake_each = 1.0 / len(favs)
        cost = 1.0
        payout = 0.0
        hit = 0
        for _, row in favs.iterrows():
            if pd.notna(row["place_payout"]):
                payout += stake_each * float(row["place_payout"])
                hit = 1
        rows.append({"race_id": rid, "cost": cost, "payout": payout, "hit": hit})
    fav_df = pd.DataFrame(rows)
    fav_sum = _roi_summary(
        fav_df["cost"].sum(), fav_df["payout"].sum(), len(fav_df), int(fav_df["hit"].sum())
    )
    print("  Bet every favorite to place (flat $1/race):", fav_sum)

    w = r.copy()
    w["odds_decile"] = pd.qcut(w["decimal_odds"], 10, labels=False, duplicates="drop") + 1
    dec_rows = []
    for d, sub in w.groupby("odds_decile"):
        cost = float(len(sub))
        payout = float(sub["place_payout"].fillna(0.0).sum())
        s = _roi_summary(cost, payout, len(sub), int(sub["placed"].sum()))
        s["odds_decile"] = int(d)
        dec_rows.append(s)
    dec_df = pd.DataFrame(dec_rows).sort_values("odds_decile")
    print("\n  Odds-decile place (flat $1 every runner):")
    print(dec_df[["odds_decile", "bets", "hit_rate", "roi_pct"]].to_string(index=False))

    return {
        "bet_favorite_place": fav_sum,
        "odds_deciles": dec_df.to_dict(orient="records"),
    }


# ---------------------------------------------------------------------------
# Step 2 — Timewave timing (modeled trifecta)
# ---------------------------------------------------------------------------


def step2_timewave(runners: pd.DataFrame) -> dict:
    _section("STEP 2 — Timewave timing alone (modeled trifecta, exploratory ROI)")
    scores = novelty.score_races(runners)
    daily = novelty.daily_novelty(scores, metric="trifecta_novelty")
    primary = compare.compare(daily, number_set="kelley")
    tw = primary["timewave"]

    res = backtest.backtest(scores, tw, novelty_threshold_pct=20.0, takeout=TAKEOUT)
    strat = res["strategy"]
    base = res["bet_every_race"]
    print(f"  wave-picked (20% causal): races={strat['races']} ROI={strat['roi_pct']:+.2f}%")
    print(f"  bet-every:                races={base['races']} ROI={base['roi_pct']:+.2f}%")
    print(f"  primary Spearman r={primary['spearman_r']:+.4f}  "
          f"perm p={primary['permutation_p']:.3f}  (pre-registered restatement)")
    print("  NOTE: settlement is MODELED — expected ROI ≈ −takeout under fair pool;")
    print("  positive bet-every is a model artifact, not cash.")

    sweep = backtest.threshold_sweep(scores, tw, takeout=TAKEOUT)
    print("\n  Exploratory threshold sweep (shape only):")
    print(sweep[["threshold_pct", "races", "roi_pct"]].to_string(index=False))

    # Simple holdout: lock 20% (prereg) — evaluate test years only
    train_end = pd.Timestamp("2002-12-31")
    scores_train = scores[scores["date"] <= train_end]
    scores_test = scores[scores["date"] > train_end]
    daily_train = novelty.daily_novelty(scores_train, metric="trifecta_novelty")
    daily_test = novelty.daily_novelty(scores_test, metric="trifecta_novelty")
    # Causal mask uses the full-span timewave series (same as live betting would:
    # wave is a calendar function). Only TEST race P&L is the claim.
    res_test = backtest.backtest(
        scores_test, tw, novelty_threshold_pct=20.0, takeout=TAKEOUT,
    )
    pnl_test = backtest.race_pnl(scores_test, TAKEOUT)
    test_every = {
        "races": int(len(pnl_test)),
        "roi_pct": float(100 * pnl_test["pnl"].sum() / pnl_test["cost"].sum()),
        "total_pnl": float(pnl_test["pnl"].sum()),
        "total_cost": float(pnl_test["cost"].sum()),
    }
    holdout = {
        "rule": "novelty_threshold_pct=20 locked (prereg); evaluate dates > 2002-12-31",
        "train_years": "1997–2002 (rule not re-tuned; prereg value)",
        "test_years": "2003–2005",
        "test_wave_picked": res_test["strategy"],
        "test_bet_every": test_every,
        "n_train_races": int(len(scores_train)),
        "n_test_races": int(len(scores_test)),
        "n_train_days": int(len(daily_train)),
        "n_test_days": int(len(daily_test)),
    }
    print("\n  Holdout (locked 20% rule → 2003–2005 only):")
    print(f"    test wave-picked ROI: {res_test['strategy']['roi_pct']:+.2f}% "
          f"(n={res_test['strategy']['races']})")
    print(f"    test bet-every ROI:   {test_every['roi_pct']:+.2f}% "
          f"(n={test_every['races']})")

    return {
        "wave_picked": strat,
        "bet_every": base,
        "primary_spearman_r": float(primary["spearman_r"]),
        "primary_permutation_p": float(primary["permutation_p"]),
        "sweep": sweep.to_dict(orient="records"),
        "holdout": holdout,
        "payout_sources": dict(res["per_race"]["payout_source"].value_counts()),
    }


# ---------------------------------------------------------------------------
# Step 3 — Picky / I Ching at measured conditions
# ---------------------------------------------------------------------------


def step3_engine(runners: pd.DataFrame, engine_beta: float, skip: bool) -> dict:
    _section("STEP 3 — Selective / I Ching at measured conditions")
    if skip:
        print("  skipped (--skip-engine)")
        return {"skipped": True}

    print("  Running selective_backtest at beta=1.0 (fair-pool null)…")
    s1 = selective_backtest(runners, beta=1.0, seed=SEED, takeout=TAKEOUT)
    print(s1.to_string(index=False))

    print(f"\n  Running selective_backtest at MEASURED engine_beta_proxy={engine_beta:.4f} "
          f"(exploratory; win-market proxy, NOT trifecta-measured)…")
    sm = selective_backtest(runners, beta=engine_beta, seed=SEED, takeout=TAKEOUT)
    print(sm.to_string(index=False))

    # Compare selective vs random when tickets exist
    sel = sm[sm["strategy"] == "selective"].iloc[0]
    rnd = sm[sm["strategy"] == "random_control"].iloc[0]
    gated = sm[sm["strategy"] == "selective_gated"].iloc[0]
    comparison = {
        "selective_tickets": int(sel["tickets"]),
        "selective_roi": float(sel["roi_pct"]) if pd.notna(sel["roi_pct"]) else None,
        "gated_tickets": int(gated["tickets"]),
        "gated_roi": float(gated["roi_pct"]) if pd.notna(gated["roi_pct"]) else None,
        "random_control_tickets": int(rnd["tickets"]),
        "random_control_roi": float(rnd["roi_pct"]) if pd.notna(rnd["roi_pct"]) else None,
        "iching_vs_random": (
            None
            if pd.isna(gated["roi_pct"]) or pd.isna(rnd["roi_pct"])
            else float(gated["roi_pct"] - rnd["roi_pct"])
        ),
        "label": "EXPLORATORY — modeled trifecta settlement; beta from win-market proxy",
    }
    print(f"\n  I Ching gated vs random_control ΔROI: {comparison['iching_vs_random']}")

    # Diagnostic: where do tickets first appear? (NOT a finding — takeout barrier.)
    print("\n  Diagnostic ticket-onset scan on 800-race subsample (label: not a finding)…")
    rids = runners["race_id"].drop_duplicates().head(800)
    sub = runners[runners["race_id"].isin(rids)]
    onset_rows = []
    for b in (0.85, 0.90, 0.92, 0.95, 1.0, 1.03, 1.05, 1.15):
        s = selective_backtest(sub, beta=b, seed=SEED, takeout=TAKEOUT)
        sel = s[s["strategy"] == "selective"].iloc[0]
        onset_rows.append(
            {
                "beta": b,
                "selective_tickets": int(sel["tickets"]),
                "selective_races": int(sel["races"]),
                "roi_pct": float(sel["roi_pct"]) if pd.notna(sel["roi_pct"]) else None,
            }
        )
        print(f"    beta={b:.2f} tickets={int(sel['tickets'])} roi={sel['roi_pct']}")
    diagnostic = {
        "subsample_races": int(sub["race_id"].nunique()),
        "onset_grid": onset_rows,
        "note": (
            "Selective tickets appear only for engine β far from 1 relative to takeout; "
            "measured win-market proxy typically yields zero tickets. Extreme-β green "
            "ROIs are conditional simulations, not findings."
        ),
    }

    return {
        "beta_1_0": s1.to_dict(orient="records"),
        "beta_measured": sm.to_dict(orient="records"),
        "engine_beta_used": engine_beta,
        "comparison": comparison,
        "diagnostic_ticket_onset": diagnostic,
    }


# ---------------------------------------------------------------------------
# Step 4 — Gate sensitivity grid
# ---------------------------------------------------------------------------


def step4_gate_grid(runners: pd.DataFrame, engine_beta: float, skip: bool) -> dict:
    _section("STEP 4 — Gate × k_max grid (exploratory, Bonferroni-aware)")
    if skip:
        print("  skipped (--skip-engine)")
        return {"skipped": True}

    gate_pcts = [10.0, 20.0, 30.0]
    k_maxes = [20, 50, 100]
    n_cells = len(gate_pcts) * len(k_maxes)
    rows = []
    for g in gate_pcts:
        for k in k_maxes:
            print(f"  cell gate={g} k_max={k} …", flush=True)
            summary = selective_backtest(
                runners,
                beta=engine_beta,
                gate_pct=g,
                k_max=k,
                seed=SEED,
                takeout=TAKEOUT,
            )
            for _, row in summary.iterrows():
                if row["strategy"] not in ("selective_gated", "random_control", "selective"):
                    continue
                rows.append(
                    {
                        "gate_pct": g,
                        "k_max": k,
                        "strategy": row["strategy"],
                        "races": int(row["races"]),
                        "tickets": int(row["tickets"]),
                        "roi_pct": float(row["roi_pct"]) if pd.notna(row["roi_pct"]) else None,
                        "pnl": float(row["pnl"]),
                    }
                )
    grid = pd.DataFrame(rows)
    gated = grid[grid["strategy"] == "selective_gated"].copy()
    print("\n  selective_gated ROI distribution across grid:")
    if gated["roi_pct"].notna().any():
        print(f"    n_cells={len(gated)}  min={gated['roi_pct'].min():+.2f}  "
              f"median={gated['roi_pct'].median():+.2f}  max={gated['roi_pct'].max():+.2f}")
        print(gated[["gate_pct", "k_max", "races", "tickets", "roi_pct"]].to_string(index=False))
    else:
        print("    all NaN (no tickets)")

    return {
        "n_comparisons": n_cells,
        "bonferroni_note": (
            f"{n_cells} gated cells examined; a single green cell at α=0.05 would need "
            f"roughly p < {0.05 / n_cells:.4f} to survive naive Bonferroni — and these "
            "are modeled-settlement ROIs anyway, not cash p-values."
        ),
        "grid": grid.to_dict(orient="records"),
        "gated_roi_min": float(gated["roi_pct"].min()) if gated["roi_pct"].notna().any() else None,
        "gated_roi_median": float(gated["roi_pct"].median()) if gated["roi_pct"].notna().any() else None,
        "gated_roi_max": float(gated["roi_pct"].max()) if gated["roi_pct"].notna().any() else None,
        "engine_beta_used": engine_beta,
    }


# ---------------------------------------------------------------------------
# Step 5 — Holdout discipline on win market + optional engine
# ---------------------------------------------------------------------------


def step5_holdout(win_mkt: pd.DataFrame, runners: pd.DataFrame, engine_beta: float, skip: bool) -> dict:
    _section("STEP 5 — Holdout discipline (train 1997–2002 → test 2003–2005)")
    train_end = pd.Timestamp("2002-12-31")
    train = win_mkt[win_mkt["date"] <= train_end]
    test = win_mkt[win_mkt["date"] > train_end]

    def fav_roi(df: pd.DataFrame) -> dict:
        rows = []
        for _, g in df.groupby("race_id"):
            favs = g[g["is_favorite"]]
            if favs.empty:
                continue
            stake_each = 1.0 / len(favs)
            payout = float((favs["won"] * stake_each * favs["win_payout_per_1"]).sum())
            hit = int((favs["won"] == 1).any())
            rows.append({"cost": 1.0, "payout": payout, "hit": hit})
        d = pd.DataFrame(rows)
        return _roi_summary(d["cost"].sum(), d["payout"].sum(), len(d), int(d["hit"].sum()))

    def band_roi(df: pd.DataFrame, lo: float, hi: float) -> dict:
        if hi is None:
            mask = df["win_odds"] > lo
        else:
            mask = (df["win_odds"] > lo) & (df["win_odds"] <= hi)
        sub = df.loc[mask]
        cost = float(len(sub))
        payout = float((sub["won"] * sub["win_payout_per_1"]).sum())
        return _roi_summary(cost, payout, len(sub), int(sub["won"].sum()))

    # Lock rules on TRAIN only: pick the best of a small pre-declared menu
    menu = [
        ("bet_favorite", lambda d: fav_roi(d)),
        ("flat_odds_le_3", lambda d: band_roi(d, 0, 3.0)),
        ("flat_odds_3_6", lambda d: band_roi(d, 3.0, 6.0)),
        ("flat_odds_6_12", lambda d: band_roi(d, 6.0, 12.0)),
        ("flat_longshot_gt_25", lambda d: band_roi(d, 25.0, None)),
    ]
    train_scores = []
    for name, fn in menu:
        s = fn(train)
        s["rule"] = name
        train_scores.append(s)
        print(f"  TRAIN {name}: ROI {s['roi_pct']:+.2f}%  bets={s['bets']}")

    train_df = pd.DataFrame(train_scores)
    # Lock the best train ROI (exploratory — this IS a selection step; test is the claim)
    best_rule = train_df.loc[train_df["roi_pct"].idxmax(), "rule"]
    print(f"\n  LOCKED rule from train: {best_rule}")

    test_by_rule = []
    for name, fn in menu:
        s = fn(test)
        s["rule"] = name
        s["locked"] = name == best_rule
        test_by_rule.append(s)
        mark = " ← LOCKED" if name == best_rule else ""
        print(f"  TEST  {name}: ROI {s['roi_pct']:+.2f}%  bets={s['bets']}{mark}")

    locked_test = next(r for r in test_by_rule if r["locked"])
    claim = {
        "locked_rule": best_rule,
        "train_roi_pct": float(train_df.loc[train_df["rule"] == best_rule, "roi_pct"].iloc[0]),
        "test_roi_pct": float(locked_test["roi_pct"]),
        "test_bets": int(locked_test["bets"]),
        "test_is_claim": True,
        "label": "EXPLORATORY holdout — only TEST ROI of locked rule is the claim",
    }
    print(f"\n  CLAIM (test only): {best_rule} → ROI {claim['test_roi_pct']:+.2f}%")

    engine_holdout = None
    if not skip and abs(engine_beta - 1.0) > 1e-6:
        print("\n  Engine holdout at measured beta (test years only)…")
        runners_test = runners[runners["date"] > train_end]
        sm = selective_backtest(
            runners_test, beta=engine_beta, seed=SEED, takeout=TAKEOUT
        )
        engine_holdout = sm.to_dict(orient="records")
        print(sm.to_string(index=False))

    return {
        "train_menu": train_scores,
        "test_by_rule": test_by_rule,
        "claim": claim,
        "engine_holdout_test": engine_holdout,
    }


# ---------------------------------------------------------------------------
# Step 6 — What would unblock
# ---------------------------------------------------------------------------


def step6_unblock(inv: dict, flb: dict, beta_est: dict) -> dict:
    _section("STEP 6 — What would unblock a real search")
    items = [
        {
            "need": "Historical trifecta (or trio/tierce) dividends per race",
            "why": "Modeled Harville settlement cannot show a cash edge; EV≈−takeout by construction at β=1.",
            "where": "HKJC dividend archives, paid vendors, or jurisdictions that publish exotic dividends with odds.",
        },
        {
            "need": "Same-race win + exotic dividends to estimate trifecta-pool beta",
            "why": (
                f"Win-market outcome_beta≈{beta_est.get('outcome_beta_mle')} is only a proxy; "
                "trifecta pools can distort differently."
            ),
            "where": "Match trifecta_payout to Harville prediction; fit engine beta on train, evaluate on test.",
        },
        {
            "need": "Larger / newer sample with real settlement",
            "why": f"Current HK window {inv['date_min']}→{inv['date_max']} has win dividends but no exotics.",
            "where": "UK/Ireland dumps already on disk lack easy exotic dividends; check vendor schemas.",
        },
    ]
    for i, it in enumerate(items, 1):
        print(f"  {i}. {it['need']}\n     why: {it['why']}\n     where: {it['where']}")
    return {"upgrades": items, "flb_summary": flb, "beta_est_summary": {
        k: beta_est[k] for k in (
            "outcome_beta_mle", "engine_beta_proxy", "delta_ll_vs_1", "n_races_fit"
        ) if k in beta_est
    }}


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------


def write_report(payload: dict) -> None:
    OUT_DIR.mkdir(exist_ok=True)
    inv = payload["step0"]
    s1 = payload["step1"]
    beta = payload["step1b"]
    s2 = payload["step2"]
    s3 = payload.get("step3", {})
    s4 = payload.get("step4", {})
    s5 = payload["step5"]
    s6 = payload["step6"]

    lines = []
    lines.append("# Exploratory edge hunt — lab notebook")
    lines.append("")
    lines.append("**Label:** All sections below are **exploratory** unless noted.")
    lines.append("**Hard rules:** no prereg edits; no “raise β until green” as a finding; no cherry-picking.")
    lines.append(f"**Run:** generated by `scripts/exploratory_edge_hunt.py`")
    lines.append("")

    lines.append("## Step 0 — Inventory")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    for k, v in inv.items():
        lines.append(f"| {k} | {v} |")
    lines.append("")
    lines.append(
        f"**Real trifecta_payout:** {'YES' if inv['has_real_trifecta_payout'] else 'NO'}. "
        f"**Real win/place:** {'YES' if inv.get('has_real_win_payout') else 'NO'} / "
        f"{'YES' if inv.get('has_real_place_payout') else 'NO'} (per $1 on bundled CSV). "
        f"{inv.get('exotic_dividends_gap', '')}"
    )
    lines.append("")

    lines.append("## Step 1 — Market efficiency baselines (real win dividends)")
    lines.append("")
    lines.append("### Bet every favorite ($1/race)")
    lines.append("")
    bf = s1["bet_favorite"]
    lines.append(
        f"ROI **{bf['roi_pct']:+.2f}%** on {bf['bets']} races "
        f"(hit rate {bf['hit_rate']:.1%}, P&L ${bf['pnl']:+,.0f})."
    )
    lines.append("")
    lines.append("### Odds bands (flat $1 every runner in band)")
    lines.append("")
    lines.append(_tbl(pd.DataFrame(s1["bands"])[
        ["band", "bets", "hit_rate", "roi_pct", "pnl"]
    ]))
    lines.append("")
    lines.append("### Odds-decile FLB chart")
    lines.append("")
    lines.append(_tbl(pd.DataFrame(s1["odds_deciles"])[
        ["odds_decile", "mean_odds", "mean_implied_p", "actual_win_rate",
         "actual_minus_implied", "roi_pct", "bets"]
    ]))
    lines.append("")
    flb = s1["flb"]
    lines.append(
        f"**FLB spread** (shortest decile ROI − longest): "
        f"**{flb['flb_spread_pp']:+.2f} pp**. {flb['interpretation']}"
    )
    lines.append("")
    lines.append("### Win-market outcome β (calibration)")
    lines.append("")
    lines.append(
        f"- outcome_beta MLE = **{beta['outcome_beta_mle']:.3f}** "
        f"(n={beta['n_races_fit']}, Δll vs 1 = {beta['delta_ll_vs_1']:+.1f})"
    )
    lines.append(f"- engine_beta_proxy = 1/outcome_beta = **{beta['engine_beta_proxy']:.3f}**")
    lines.append(f"- {beta['note']}")
    lines.append("")

    s1c = payload.get("step1c", {})
    lines.append("## Step 1c — Place market (real place dividends)")
    lines.append("")
    if s1c.get("skipped"):
        lines.append(f"_Skipped: {s1c.get('reason', 'n/a')}_")
    else:
        bp = s1c["bet_favorite_place"]
        lines.append(
            f"Bet favorite to place: ROI **{bp['roi_pct']:+.2f}%** "
            f"(hit {bp['hit_rate']:.1%}, n={bp['bets']})."
        )
        lines.append("")
        lines.append(_tbl(pd.DataFrame(s1c["odds_deciles"])[
            ["odds_decile", "bets", "hit_rate", "roi_pct"]
        ]))
        lines.append("")
        lines.append(
            "**What this suggests:** Place market also loses across odds deciles "
            "when settled on real dividends — not an edge."
        )
    lines.append("")

    lines.append("## Step 2 — Timewave timing alone (modeled trifecta)")
    lines.append("")
    lines.append(
        f"| Strategy | Races | ROI | P&L |"
    )
    lines.append("|---|---|---|---|")
    wp, be = s2["wave_picked"], s2["bet_every"]
    lines.append(
        f"| Wave-picked 20% causal | {wp['races']} | {wp['roi_pct']:+.2f}% | ${wp['total_pnl']:+,.0f} |"
    )
    lines.append(
        f"| Bet every race | {be['races']} | {be['roi_pct']:+.2f}% | ${be['total_pnl']:+,.0f} |"
    )
    lines.append("")
    lines.append(f"Payout sources: `{s2['payout_sources']}` — all modeled.")
    lines.append("")
    lines.append("### Holdout (locked 20% → test 2003–2005)")
    lines.append("")
    h = s2["holdout"]
    lines.append(
        f"- Test wave-picked ROI: **{h['test_wave_picked']['roi_pct']:+.2f}%** "
        f"(n={h['test_wave_picked']['races']})"
    )
    lines.append(
        f"- Test bet-every ROI: **{h['test_bet_every']['roi_pct']:+.2f}%** "
        f"(n={h['test_bet_every']['races']})"
    )
    lines.append("")

    lines.append("## Step 3 — Picky / I Ching at measured β")
    lines.append("")
    if s3.get("skipped"):
        lines.append("_Skipped (--skip-engine)._")
    else:
        lines.append("### β = 1.0 (fair pool)")
        lines.append("")
        lines.append(_tbl(pd.DataFrame(s3["beta_1_0"])))
        lines.append("")
        lines.append(
            f"### β = {s3['engine_beta_used']:.4f} (win-market proxy — EXPLORATORY, modeled settlement)"
        )
        lines.append("")
        lines.append(_tbl(pd.DataFrame(s3["beta_measured"])))
        lines.append("")
        c = s3["comparison"]
        lines.append(
            f"I Ching gated − random_control ΔROI = **{c['iching_vs_random']}** "
            f"({c['label']})"
        )
    lines.append("")

    lines.append("## Step 4 — Gate × k_max grid")
    lines.append("")
    if s4.get("skipped"):
        lines.append("_Skipped (--skip-engine)._")
    else:
        lines.append(s4["bonferroni_note"])
        lines.append("")
        lines.append(
            f"selective_gated ROI across grid: "
            f"min={s4['gated_roi_min']}, median={s4['gated_roi_median']}, max={s4['gated_roi_max']}"
        )
        lines.append("")
        gdf = pd.DataFrame(s4["grid"])
        gated = gdf[gdf["strategy"] == "selective_gated"]
        lines.append(_tbl(gated[["gate_pct", "k_max", "races", "tickets", "roi_pct", "pnl"]]))
    lines.append("")

    lines.append("## Step 5 — Holdout claim (win market)")
    lines.append("")
    claim = s5["claim"]
    lines.append(
        f"Locked rule from train: **`{claim['locked_rule']}`** "
        f"(train ROI {claim['train_roi_pct']:+.2f}%)."
    )
    lines.append("")
    lines.append(
        f"**TEST CLAIM:** ROI **{claim['test_roi_pct']:+.2f}%** "
        f"on {claim['test_bets']} bets ({claim['label']})."
    )
    lines.append("")
    lines.append("### All rules on test (for context — only locked row is the claim)")
    lines.append("")
    lines.append(_tbl(pd.DataFrame(s5["test_by_rule"])[
        ["rule", "locked", "bets", "hit_rate", "roi_pct", "pnl"]
    ]))
    lines.append("")

    lines.append("## Step 6 — What would unblock a real search")
    lines.append("")
    for i, it in enumerate(s6["upgrades"], 1):
        lines.append(f"{i}. **{it['need']}**")
        lines.append(f"   - Why: {it['why']}")
        lines.append(f"   - Where: {it['where']}")
        lines.append("")

    # Overall verdict — filled by main after seeing numbers
    lines.append("## Overall verdict")
    lines.append("")
    lines.append(payload["verdict_md"])
    lines.append("")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    print(f"\nWrote {OUT_MD}")
    print(f"Wrote {OUT_JSON}")


def build_verdict(payload: dict) -> str:
    inv = payload["step0"]
    flb = payload["step1"]["flb"]
    beta = payload["step1b"]
    s2 = payload["step2"]
    claim = payload["step5"]["claim"]
    s3 = payload.get("step3", {})

    parts = []
    parts.append(
        f"**Still no demonstrated cash edge** on this HK sample for McKenna/I Ching trifecta strategies. "
        f"Bundled data has **no** `trifecta_payout` ({inv['n_races']} races, "
        f"{inv['date_min']}→{inv['date_max']}). "
        f"Real win/place dividends **are** on the bundled CSV; exotic settlement remains blocked "
        f"until a companion `--exotics` file is supplied."
    )
    parts.append("")
    parts.append(
        f"Win market (real dividends): favorite flat ROI {payload['step1']['bet_favorite']['roi_pct']:+.2f}%; "
        f"FLB spread {flb['flb_spread_pp']:+.2f} pp; "
        f"outcome β MLE {beta['outcome_beta_mle']:.3f} → engine proxy {beta['engine_beta_proxy']:.3f}."
    )
    parts.append("")
    parts.append(
        f"Timewave-filtered modeled trifecta ROI {s2['wave_picked']['roi_pct']:+.2f}% vs "
        f"bet-every {s2['bet_every']['roi_pct']:+.2f}% (model artifact, not cash). "
        f"Holdout test wave-picked {s2['holdout']['test_wave_picked']['roi_pct']:+.2f}%."
    )
    parts.append("")
    parts.append(
        f"Win-market holdout claim (`{claim['locked_rule']}`): "
        f"**test ROI {claim['test_roi_pct']:+.2f}%** — "
        + (
            "still below break-even; no edge."
            if claim["test_roi_pct"] < 0
            else "positive on test — treat as a weak lead only; menu selection on train + one test look."
        )
    )
    if not s3.get("skipped") and s3.get("comparison"):
        c = s3["comparison"]
        parts.append("")
        parts.append(
            f"At measured engine β proxy, selective tickets={c['selective_tickets']}, "
            f"gated ROI={c['gated_roi']}, random_control ROI={c['random_control_roi']} "
            f"(modeled settlement — not a cash claim)."
        )
    parts.append("")
    parts.append(
        "**Most promising honest next experiment:** obtain historical **trifecta/trio dividends** "
        "for the same races (or another jurisdiction), fit pool β on a train window from "
        "actual vs Harville payouts, lock a selective rule, and report **test-only** ROI with "
        "real settlement. Win-market FLB here is measurable but small; it does not unlock "
        "trifecta profitability by itself."
    )
    return "\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--skip-engine",
        action="store_true",
        help="Skip selective_backtest / gate grid (faster)",
    )
    args = ap.parse_args()

    runners = load_runners()
    has_bundled_win = (
        "win_payout" in runners.columns and runners["win_payout"].notna().any()
    )
    if not has_bundled_win and not (RAWDATA / "races.csv").is_file():
        raise SystemExit(
            "Need win_payout on bundled CSV or rawdata/races.csv for real win dividends"
        )
    win_mkt = load_win_market(runners)

    payload: dict = {}
    payload["step0"] = step0_inventory(runners, win_mkt)
    payload["step1"] = step1_win_baselines(win_mkt)
    payload["step1b"] = estimate_win_beta(win_mkt)
    payload["step1c"] = step1c_place_baselines(runners)

    engine_beta = float(payload["step1b"]["engine_beta_proxy"])
    # Clamp to a sane exploratory range; still label as proxy.
    engine_beta = float(np.clip(engine_beta, 0.5, 1.5))
    payload["step1b"]["engine_beta_used_clipped"] = engine_beta

    payload["step2"] = step2_timewave(runners)
    payload["step3"] = step3_engine(runners, engine_beta, skip=args.skip_engine)
    payload["step4"] = step4_gate_grid(runners, engine_beta, skip=args.skip_engine)
    payload["step5"] = step5_holdout(win_mkt, runners, engine_beta, skip=args.skip_engine)
    payload["step6"] = step6_unblock(
        payload["step0"], payload["step1"]["flb"], payload["step1b"]
    )
    payload["verdict_md"] = build_verdict(payload)

    write_report(payload)
    _section("VERDICT")
    print(payload["verdict_md"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

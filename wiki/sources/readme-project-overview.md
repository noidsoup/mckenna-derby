---
title: README — project overview
type: source
summary: "Digest of README.md: hypothesis, pipeline stages, McKenna Engine, honest expectations."
status: active
created: 2026-07-30
updated: 2026-07-30
last_verified: 2026-07-30
sources: []
tags: [readme, hypothesis, pipeline]
aliases: [readme]
---
# README — project overview

McKenna Derby tests whether horse-racing **chaos** (outcome surprisal under betting-market odds) aligns with Terence McKenna's **Timewave Zero**, and whether a timewave-filtered **buy-all-trifecta-combinations** strategy can beat random timing. The deliverable is an honest statistical result, not a betting product.

## Key points

- **Novelty scoring** (`novelty.py`): surprisal `-log2 P(actual outcome)` via Harville trifecta probabilities; z-normalized by field size; daily average series.
- **Timewave Zero** (`timewave.py`): Peter Meyer algorithm port; four I Ching number sets; zero date 2012-12-21; post-zero dates use mirrored extension (flagged).
- **Comparison** (`compare.py`): Pearson/Spearman + circular-shift permutation test; McKenna predicts **negative** correlation (low wave = high novelty).
- **Backtest** (`backtest.py`): buy all `n·(n−1)·(n−2)` trifecta permutations; modeled parimutuel takeout (default 22%); ROI ≈ −takeout without an edge.
- **McKenna Engine** (`mckenna_engine.py`): fractal resonance gate, I Ching ticket selector, selective +EV betting with configurable pool-bias `beta`.
- **Honest null:** synthetic demo is market-calibrated — expect no timewave signal and ROI ≈ −takeout.

## Detailed notes

### Pipeline outputs

CLI `run_analysis.py` writes to `output/`: `race_scores.csv`, `report.md`, `novelty_vs_timewave.png` (novelty, inverted timewave, cumulative P&L).

### Real data

Hong Kong Kaggle dataset (`gdaley/hkracing`) via `--hk rawdata/`. Prefer real `trifecta_payout` column on CSV rows over modeled payouts.

### Dashboard

`streamlit run dashboard.py` — synthetic, HK, or uploaded CSV; defaults from `prereg.json`; optional threshold sweep and McKenna Engine section.

### Beta assumption (McKenna Engine)

`beta = 1.0` → fair pool → selective strategy places **zero** bets. `beta > 1` models favorites-overbet bias; positive ROI is conditional on that bias existing. Estimate beta from real dividends before trusting modeled ROI.

## Entities mentioned

- [[mckenna-derby-package]]
- [[prereg-json]]
- [[streamlit-dashboard]]

## Concepts discussed

- [[novelty-surprisal-scoring]]
- [[timewave-zero-comparison]]
- [[frozen-statistical-core]]
- [[mckenna-engine-selective-betting]]

## Related

- [[run-analysis-pipeline]]
- [[documentation-in-repo]]
- [[SCHEMA]]

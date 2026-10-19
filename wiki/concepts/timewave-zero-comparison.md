---
title: Timewave Zero comparison
type: concept
summary: Spearman/Pearson plus a circular-shift permutation test against the timewave; permutation_p is the one that counts.
status: active
created: 2026-07-30
updated: 2026-10-19
last_verified: 2026-10-19
sources: ["[[readme-project-overview]]"]
tags: [timewave, mckenna, correlation, permutation]
aliases: [timewave comparison, timewave zero]
---
# Timewave Zero comparison

## Definition

**Timewave Zero** is Terence McKenna's I Ching–derived novelty wave. This project ports Peter Meyer's public-domain algorithm (`mckenna_derby/timewave.py`) with four canonical 384-number sets (Kelley, Watkins, Sheliak, Huang Ti). Zero date: **2012-12-21**. Dates after zero use a **mirrored extension** (clearly flagged — the wave is undefined past the zero point in McKenna's theory).

## Application here

`mckenna_derby/compare.py` (**frozen**) computes Pearson and Spearman correlations between daily novelty and the timewave, plus a **circular-shift permutation test** that respects autocorrelation in both series.

McKenna's convention: **low wave = high novelty**, so the theory predicts a **negative** correlation.

Primary hypothesis (from [[prereg-json]]): Spearman r < 0 with permutation p < 0.05. ROI comparisons are exploratory only ([[0005-roi-is-exploratory]]).

Use `permutation_p` for inference. `pearson_p` and `spearman_p` are naive — they ignore autocorrelation — and are kept for transparency only (`compare.py` docstring, commit `2ef1b0e`).

On real Hong Kong data the primary test was null (r ≈ 0.008, permutation p = 0.936); UK exploratory was null too ([[real-data-results-2026-07-09]]).

## Tradeoffs

- Two slow-moving wiggly lines can spuriously correlate — permutation test keeps results honest.
- Exploratory comparisons (all number sets, lead-lag sweeps) need Bonferroni labels.
- Usable historical window for strict interpretation ends at the zero date.

## Related

- [[novelty-surprisal-scoring]]
- [[frozen-statistical-core]]
- [[prereg-json]]
- [[0002-preregistered-primary-analysis]]
- [[real-data-results-2026-07-09]]

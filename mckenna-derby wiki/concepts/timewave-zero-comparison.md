---
title: Timewave Zero comparison
type: concept
created: 2026-07-30
updated: 2026-07-30
tags: [timewave, mckenna, correlation, permutation]
aliases: [timewave comparison, timewave zero]
sources: ["[[readme-project-overview]]"]
status: active
---

# Timewave Zero comparison

## Definition

**Timewave Zero** is Terence McKenna's I Ching–derived novelty wave. This project ports Peter Meyer's public-domain algorithm (`mckenna_derby/timewave.py`) with four canonical 384-number sets (Kelley, Watkins, Sheliak, Huang Ti). Zero date: **2012-12-21**. Dates after zero use a **mirrored extension** (clearly flagged — the wave is undefined past the zero point in McKenna's theory).

## Application here

`mckenna_derby/compare.py` (**frozen**) computes Pearson and Spearman correlations between daily novelty and the timewave, plus a **circular-shift permutation test** that respects autocorrelation in both series.

McKenna's convention: **low wave = high novelty**, so the theory predicts a **negative** correlation.

Primary hypothesis (from [[prereg-json]]): Spearman r < 0 with permutation p < 0.05, and timewave-filtered ROI exceeds bet-every-race ROI.

## Tradeoffs

- Two slow-moving wiggly lines can spuriously correlate — permutation test keeps results honest.
- Exploratory comparisons (all number sets, lead-lag sweeps) need Bonferroni labels.
- Usable historical window for strict interpretation ends at the zero date.

## Related

- [[novelty-surprisal-scoring]]
- [[frozen-statistical-core]]
- [[prereg-json]]
- [[0002-preregistered-primary-analysis]]

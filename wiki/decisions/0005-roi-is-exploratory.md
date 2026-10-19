---
title: ROI comparisons are exploratory, not a pre-registered criterion
type: decision
summary: On 2026-07-09, before the first real-data run, the ROI clause was taken out of prereg.json's prediction; only the correlation test counts.
status: active
created: 2026-10-19
updated: 2026-10-19
last_verified: 2026-10-19
sources: ["commit 2ef1b0e", "commit 9086d8c", prereg.json, mckenna_derby/compare.py]
tags: [preregistration, methodology, roi]
---

# ROI comparisons are exploratory, not a pre-registered criterion

## Status

**Active** since 2026-07-09 09:29 (commit `2ef1b0e`). The first real-data run was committed at 09:30 (`9086d8c`).

## Context

The 2026-07-08 `prereg.json` predicted both a negative correlation **and** "timewave-filtered ROI exceeding bet-every-race ROI". An accuracy audit found that the ROI side rests on modeled parimutuel payouts (expected ROI = −takeout by construction) and had look-ahead bias in the day selection.

## Decision

- The prediction is only: Spearman r < 0 with circular-shift permutation p < 0.05.
- ROI comparisons (timewave-filtered vs bet-every-race) are exploratory and not success criteria.
- Inference uses `permutation_p`; naive Pearson/Spearman p-values are reported for transparency only (`compare.py` docstring, same commit).
- Day selection became a causal expanding-window percentile (no full-sample look-ahead).

## Why this is not parameter fishing

The edit landed before any real data was run, and `prereg.json` has not changed since (`git log -- prereg.json`). It narrowed the claim; it did not tune parameters.

## Consequences

- Never present a positive ROI from a run as support for the hypothesis.
- Wiki pages that still said ROI was part of the prediction were corrected on 2026-10-19.

## Related

- [[0002-preregistered-primary-analysis]]
- [[prereg-json]]
- [[real-data-results-2026-07-09]]

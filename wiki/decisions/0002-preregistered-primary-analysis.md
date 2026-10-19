---
title: Pre-registered primary analysis
type: decision
summary: Primary parameters locked in prereg.json before the first real-data run; everything else is exploratory with Bonferroni.
status: active
created: 2026-07-30
updated: 2026-10-19
last_verified: 2026-10-19
sources: []
tags: [preregistration, statistics, methodology]
aliases: [0002, prereg decision]
---
# Pre-registered primary analysis

## Status

Accepted (2026-07-08)

## Context

The project tests a speculative hypothesis (timewave ↔ racing novelty). Without pre-registration, parameter fishing on real data would invalidate inference.

## Decision

Lock primary analysis parameters in **`prereg.json`** at repo root. **Do not edit after the first real-data run.** All other number sets, thresholds, sweeps, and lags are exploratory and reported with Bonferroni correction.

Primary: Kelley number set, 20% threshold, 22% takeout, trifecta novelty metric. Success criterion: Spearman r < 0 with circular-shift permutation p < 0.05 — ROI is not part of it ([[0005-roi-is-exploratory]]).

## Outcome

The first real-data run (2026-07-09, commit `9086d8c`) left `prereg.json` unchanged and reported the primary result verbatim: not supported ([[real-data-results-2026-07-09]]). `git log -- prereg.json` shows only two commits, both before that run.

## Consequences

- Agents must read [[prereg-json]] before real-data work and report primary results verbatim.
- Dashboard and CLI default to prereg values for the primary path.
- Exploratory overrides are allowed but must be labeled.

## Related

- [[prereg-json]]
- [[timewave-zero-comparison]]
- [[run-analysis-pipeline]]
- [[readme-project-overview]]

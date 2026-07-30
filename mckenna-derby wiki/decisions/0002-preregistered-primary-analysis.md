---
title: Pre-registered primary analysis
type: decision
created: 2026-07-30
updated: 2026-07-30
tags: [preregistration, statistics, methodology]
aliases: [0002, prereg decision]
sources: []
status: accepted
---

# Pre-registered primary analysis

## Status

Accepted (2026-07-08)

## Context

The project tests a speculative hypothesis (timewave ↔ racing novelty). Without pre-registration, parameter fishing on real data would invalidate inference.

## Decision

Lock primary analysis parameters in **`prereg.json`** at repo root. **Do not edit after the first real-data run.** All other number sets, thresholds, sweeps, and lags are exploratory and reported with Bonferroni correction.

Primary: Kelley number set, 20% threshold, 22% takeout, trifecta novelty metric.

## Consequences

- Agents must read [[prereg-json]] before real-data work and report primary results verbatim.
- Dashboard and CLI default to prereg values for the primary path.
- Exploratory overrides are allowed but must be labeled.

## Related

- [[prereg-json]]
- [[timewave-zero-comparison]]
- [[run-analysis-pipeline]]
- [[readme-project-overview]]

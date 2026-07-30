---
title: prereg.json — pre-registered primary analysis
type: entity
created: 2026-07-30
updated: 2026-07-30
tags: [preregistration, config, statistics]
aliases: [prereg, primary analysis]
sources: ["[[readme-project-overview]]"]
status: active
---

# prereg.json — pre-registered primary analysis

## What it is

JSON file at repo root declaring the **primary** statistical analysis parameters and hypothesis. Declared 2026-07-08. Must not be edited after the first real-data run.

## How it's used in the project

- `run_analysis.py` and `dashboard.py` read defaults from this file for the primary result.
- Exploratory runs (other number sets, threshold sweeps, lead-lag) must be labeled exploratory and use Bonferroni correction where noted.
- Agents must check `prereg.json` before any real-data analysis and must not tune parameters to improve p-values.

## Key details

| Field | Value |
|-------|-------|
| `primary_number_set` | `kelley` |
| `metric` | `trifecta_novelty` |
| `primary_threshold_pct` | `20.0` |
| `takeout` | `0.22` |
| `prediction` | Spearman r < 0 between daily novelty and timewave (permutation p < 0.05); timewave-filtered ROI exceeds bet-every-race ROI |

## Related

- [[0002-preregistered-primary-analysis]]
- [[timewave-zero-comparison]]
- [[run-analysis-pipeline]]
- [[mckenna-derby-package]]

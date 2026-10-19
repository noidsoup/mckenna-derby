---
title: prereg.json — pre-registered primary analysis
type: entity
summary: "prereg.json: the locked primary analysis (Kelley, 20%, 22% takeout, Spearman r < 0); ROI is not a success criterion."
status: active
created: 2026-07-30
updated: 2026-10-19
last_verified: 2026-10-19
sources: ["[[readme-project-overview]]"]
tags: [preregistration, config, statistics]
aliases: [prereg, primary analysis]
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
| `prediction` | Spearman r < 0 between daily novelty and timewave, with circular-shift permutation p < 0.05. ROI comparisons (timewave-filtered vs bet-every-race) are **exploratory only**, not success criteria |
| `declared_on` | `2026-07-08` |

The ROI clause was moved out of the prediction on 2026-07-09 (commit `2ef1b0e`), one commit **before** the first real-data run (`9086d8c`), so the lock rule was not broken. Older copies of this page said ROI was part of the prediction — it is not. See [[0005-roi-is-exploratory]].

## Result

The first and only pre-registered run (2026-07-09, Kaggle `gdaley/hkracing`, 682 race days) gave Spearman r ≈ 0.008, permutation p = 0.936: **not supported** ([[real-data-results-2026-07-09]]).

## Related

- [[0002-preregistered-primary-analysis]]
- [[timewave-zero-comparison]]
- [[run-analysis-pipeline]]
- [[mckenna-derby-package]]

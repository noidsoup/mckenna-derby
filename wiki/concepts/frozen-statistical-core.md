---
title: Frozen statistical core
type: concept
summary: "timewave.py, novelty.py and compare.py are pinned by golden tests and change only with Nicholas's approval."
status: active
created: 2026-07-30
updated: 2026-10-19
last_verified: 2026-10-19
sources: ["[[readme-project-overview]]"]
tags: [testing, golden-tests, frozen]
aliases: [frozen core, golden tests]
---
# Frozen statistical core

## Definition

Three modules form the **frozen statistical core** — the reproducible heart of the analysis. They must not change without explicit user approval and corresponding **golden test** updates in `tests/`.

## Application here

| Module | Responsibility |
|--------|----------------|
| `mckenna_derby/timewave.py` | Timewave Zero algorithm |
| `mckenna_derby/novelty.py` | Surprisal scoring |
| `mckenna_derby/compare.py` | Correlation + permutation |

`pytest -q` freezes expected outputs. Run after every change touching these files; `bash .verify.sh` runs it through the repo venv (77 tests passed on 2026-10-10, commit `453c884`).

The freeze is not absolute history: `compare.py` gained a docstring note in the 2026-07-09 accuracy fix (commit `2ef1b0e`, "use `permutation_p`; naive p-values ignore autocorrelation"). Behavior did not change. The same commit fixed look-ahead bias in the non-frozen backtest (causal expanding-window thresholds).

Non-frozen modules (`backtest.py`, `mckenna_engine.py`, `data.py`, `report.py`, `calendar_windows.py`, dashboard) can evolve more freely but should still pass tests.

## Tradeoffs

- Freezing prevents silent statistical drift but slows intentional algorithm changes.
- Golden tests encode the null-hypothesis pipeline — synthetic data should show no signal and ROI ≈ −takeout.

## Related

- [[novelty-surprisal-scoring]]
- [[timewave-zero-comparison]]
- [[mckenna-derby-package]]
- [[run-analysis-pipeline]]

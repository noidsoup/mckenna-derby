---
title: Frozen statistical core
type: concept
created: 2026-07-30
updated: 2026-07-30
tags: [testing, golden-tests, frozen]
aliases: [frozen core, golden tests]
sources: ["[[readme-project-overview]]"]
status: active
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

`pytest -q` freezes expected outputs. Run after every change touching these files.

Non-frozen modules (`backtest.py`, `mckenna_engine.py`, `data.py`, `report.py`, dashboard) can evolve more freely but should still pass tests.

## Tradeoffs

- Freezing prevents silent statistical drift but slows intentional algorithm changes.
- Golden tests encode the null-hypothesis pipeline — synthetic data should show no signal and ROI ≈ −takeout.

## Related

- [[novelty-surprisal-scoring]]
- [[timewave-zero-comparison]]
- [[mckenna-derby-package]]
- [[run-analysis-pipeline]]

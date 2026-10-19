---
title: 0003 — Ship the UK/Ireland exploratory slice alongside the locked HK default
type: decision
summary: Bundle a 2008-2012 UK/Ireland slice as exploratory only; Hong Kong stays the locked default.
status: active
created: 2026-09-12
updated: 2026-09-12
last_verified: 2026-09-12
tags: [decision, datasets, uk, exploratory]
aliases: [uk slice, free datasets]
---
# 0003 — Ship the UK/Ireland exploratory slice alongside the locked HK default

## Context

The repo had a single default dataset: bundled Hong Kong races in `mckenna_derby/datasets/hk_runners.csv`. The 2026-07-09 session ("Free datasets hunt + UK/Ireland wire-in", `AI_SESSION_MEMORY.md`) inventoried local free dumps and web-reviewed free Kaggle/GitHub candidates (skipping paid Renavon/Equibase) and settled on bundling an exploratory UK/Ireland slice from `hwaitt/horse-racing`.

## Decision

- Bundle **`uk_runners.csv`** (~34,449 races, 2008–2012, ~16 MB) rather than the full 1990–2020 raw (~725 MB, gitignored).
- Wire it in via **`load_bundled_uk()`** (`mckenna_derby`), **`scripts/build_bundled_uk.py`**, a dashboard **Advanced radio**, and CLI flag **`--uk`**.
- Label it **exploratory only** — it is *not* the locked primary claim. **Do not edit `prereg.json`** for it.
- HK remains the locked default.

## Consequences

- UK labeled exploratory; the primary `prereg.json` claim is untouched (HK).
- Exploratory smoke test: favorite ROI ≈ −3.4%; primary compare null (p≈0.49) — **not** a McKenna edge.
- Optional: rebuild a wider UK window locally via `scripts/build_bundled_uk.py --start …`.

## Related

- [[mckenna-derby-package]]
- [[0002-preregistered-primary-analysis]]
- [[ai-session-memory-2026-07-09]]

---
title: Index
type: overview
summary: Start here. Must-know facts, then one line per page.
status: active
created: 2026-07-30
updated: 2026-10-19
last_verified: 2026-10-19
sources: []
tags: [meta]
---

# mckenna-derby wiki

## Must know

- `prereg.json` is locked; the pre-registered real-data test was null (p = 0.936) ([[real-data-results-2026-07-09]]).
- Only the correlation test is pre-registered; ROI is exploratory and modeled, never an edge ([[0005-roi-is-exploratory]]).
- `timewave.py`, `novelty.py`, `compare.py` are frozen by golden tests ([[frozen-statistical-core]]).
- HK is the locked default; UK is exploratory only ([[bundled-datasets]]).
- Public repo; gate is `bash .verify.sh` (pytest in `.venv`) ([[overview]]).

## Overview

- [[overview]] — what this is, who it's for, where it runs
- [[gotchas]] — known traps; check after a repeated failure

## Entities

- [[mckenna-derby-package]] — the `mckenna_derby` package, CLIs, which modules are frozen
- [[prereg-json]] — the locked primary analysis and its result
- [[bundled-datasets]] — `hk_runners.csv` and `uk_runners.csv`; why trifecta settlement is modeled
- [[streamlit-dashboard]] — `dashboard.py`: data sources, copy, calendar windows, password gate
- [[lancedb-project-knowledge-search]] — local semantic search over docs and the wiki

## Concepts

- [[novelty-surprisal-scoring]] — Harville surprisal, z-normalized, daily series
- [[timewave-zero-comparison]] — correlation + circular-shift permutation test
- [[frozen-statistical-core]] — golden-test freeze and its one docstring exception
- [[mckenna-engine-selective-betting]] — resonance gate, I Ching selector, beta assumption

## Decisions

- [[0001-local-simplemem-backend]] — SimpleMem local JSON committed in `docs/simplemem/`
- [[0002-preregistered-primary-analysis]] — primary params locked before real data
- [[0003-uk-exploratory-slice]] — bundle UK 2008–2012 as exploratory only
- [[0004-driver-js-then-removed]] — guided tour added then removed (2026-07-09)
- [[0005-roi-is-exploratory]] — ROI clause removed from the prediction before the real run
- [[0006-drop-crewai]] — unused CrewAI subproject removed with audit fixes (PR #1)

## Guides

- [[run-analysis-pipeline]] — install, test, CLI runs, engine, dashboard
- [[documentation-in-repo]] — which repo file holds what

## Sources

- [[real-data-results-2026-07-09]] — digest of `output/REAL_DATA_RESULTS.md`
- [[readme-project-overview]] — digest of `README.md`
- [[ai-session-memory-2026-07-09]] — digest of the 2026-07-09 session entries
- [[simplemem-archive]] — archived SimpleMem mirror (to 2026-07-09)
- [[simplemem-in-wiki]] — archived note on the old mirror

## Meta

- [[SCHEMA]] — how to write here · [[log]] — change history

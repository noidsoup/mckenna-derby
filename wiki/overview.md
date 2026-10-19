---
title: Overview
type: overview
summary: What mckenna-derby is (an honest-null research project), who it's for, where it runs.
status: active
created: 2026-10-19
updated: 2026-10-19
last_verified: 2026-10-19
sources: [README.md, AGENTS.md, PLAN.md, DEPLOY_STREAMLIT.md, output/REAL_DATA_RESULTS.md, .claude/launch.json]
tags: [overview]
---

# mckenna-derby

A Python research project that tests whether horse-racing "novelty" (how surprising results were versus the betting odds) lines up with Terence McKenna's Timewave Zero, and whether timing bets by the wave beats betting every race (`README.md`). The deliverable is an honest statistical answer, not a betting product (`PLAN.md`, Context).

## What and why

- **Pipeline:** race odds + finishes → daily novelty ([[novelty-surprisal-scoring]]) → correlation and permutation test against the timewave ([[timewave-zero-comparison]]) → buy-every-trifecta backtest; plus an optional selective "McKenna Engine" ([[mckenna-engine-selective-betting]]).
- **Rigor:** the statistical core is frozen by golden tests ([[frozen-statistical-core]]); the primary test is pre-registered in `prereg.json` ([[0002-preregistered-primary-analysis]], [[0005-roi-is-exploratory]]).
- **Answer so far:** the pre-registered test on real Hong Kong data was null (permutation p = 0.936), and the UK exploratory check was null too ([[real-data-results-2026-07-09]]).
- **Status:** dormant since 2026-07-09 apart from agent-setup and wiki commits (git log). Real trifecta dividends are the main missing input ([[bundled-datasets]]).

## People and roles

| Role | Who | Source |
|---|---|---|
| Owner, researcher | Nicholas (`noidsoup`) | repo owner |
| Audience | Nicholas and a friend he shares the dashboard with | `DEPLOY_STREAMLIT.md` |

## Where it runs

| Environment | URL / host | Deploys from |
|---|---|---|
| Local CLI + tests | `.venv` (Python 3.9); `bash .verify.sh` runs `pytest -q` | working tree |
| Local dashboard | `http://localhost:8501` (`.claude/launch.json`, `scripts/start-dashboard.sh`) | working tree |
| Streamlit Community Cloud | app URL not recorded; optional password in Streamlit secrets *(live status unverified)* | `main`, `dashboard.py`, `runtime.txt` |
| GitHub | <https://github.com/noidsoup/mckenna-derby> — **public** as of 2026-10-19 | — |

## Key links

- Commands and session rules: `AGENTS.md`, `AI_RUNBOOK.md`
- Free-data survey: `docs/FREE_DATASETS.md`; dataset schema: `mckenna_derby/datasets/README.md`
- Original Phase 2 plan (frozen core, prereg, no dashboard — later relaxed): `PLAN.md`
- Memory: SimpleMem local store `docs/simplemem/memories.json` ([[0001-local-simplemem-backend]])

## Related

- [[gotchas]]
- [[run-analysis-pipeline]]
- [[streamlit-dashboard]]

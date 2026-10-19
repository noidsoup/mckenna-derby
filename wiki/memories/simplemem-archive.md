---
title: SimpleMem archive
type: source
summary: Archived mirror of SimpleMem entries up to 2026-07-09.
status: archived
created: 2026-07-30
updated: 2026-10-19
last_verified: 2026-10-19
tags: [simplemem, archive, session-memory]
aliases: [simplemem memories]
---
# SimpleMem archive

> **Archived 2026-10-19.** Frozen copy; the live store is `docs/simplemem/memories.json`.

> Compiled from **`docs/simplemem/memories.json`** (committed store). Do not edit by hand — refresh from the JSON store when memories change.
>
> Refreshed 2026-09-12 to include the 2026-07-09 entries (CrewAI removal, real-data run, free-datasets hunt, mobile scroll fix).

## Entries

### 2026-07-08 — Set up project for AI

**Branch:** `main`
**Source:** `ai_session_memory` (session 1)

**Completed:**
- Bootstrapped SimpleMem (local-only, namespace `mckenna-derby`, committed store at `docs/simplemem/`)
- Added `AGENTS.md`, `AI_RUNBOOK.md`, `.cursor/context7-libraries.md`, `.cursor/rules/simplemem.mdc`
- Installed repo skills: `python-testing-patterns`, `python-project-structure` under `.agents/skills/`
- Added CrewAI planner subproject in `crewai/` (requires Python 3.10+ and `OPENAI_API_KEY`)
- Updated `.gitignore` for `.env` and `uncommitted/`; added `requests` and `python-dotenv` deps

**Project state:** Phase 2 complete — frozen statistical core with golden tests, pre-registered analysis in `prereg.json`, CLI pipeline (`run_analysis.py`), Streamlit dashboard (`dashboard.py`), dashboard start script on port 8501.

**Key decisions:**
- SimpleMem uses **local backend** so memories travel with the repo without cloud tokens
- CrewAI kept separate from main venv (3.9) because CrewAI requires Python 3.10+

### 2026-07-09 — Removed CrewAI subproject

**Branch:** `main`
**Source:** `ai_session_memory`

**Completed:**
- Removed the unused `crewai/` planner subproject (9 files, ~28K, separate Python 3.10+ venv, `OPENAI_API_KEY` requirement)
- Patched `AGENTS.md` to drop the CrewAI section and the Python 3.10+ tech-stack note
- Patched `AI_RUNBOOK.md` to drop CrewAI from the tech stack, project structure, add-feature workflow, commands reference, and the standalone "CrewAI planner" section
- Verified all 32 pytest tests still pass on the main package (CrewAI was isolated — no impact on `mckenna_derby/`)

**Key decisions:**
- Subproject was documented and configured but never wired into the analysis pipeline; keeping it added a dependency on a non-default Python version and an external API key for zero benefit
- Replaced `plan-and-implement` workflow entry in `AI_RUNBOOK.md` to point at the global `plan-and-implement` skill directly (writes `.cursor/plans/PLAN.md`), since that was the actual planning path in use

**Next steps:**
- Run Hong Kong real-data experiment when Kaggle credentials are available (`python run_analysis.py --hk rawdata/`)
- Source historical trifecta dividends for credible backtest conclusions

### 2026-07-09 — Real-data run

**Branch:** `main`
**Source:** `real-data-run`

2026-07-09 real-data run: downloaded gdaley/hkracing (6157 races, 1997-2005) plus UK and secondary HK dumps. Primary pre-registered Kelley analysis: Spearman r=+0.0080, permutation p=0.936 — null. Timewave-filtered ROI −5.87% vs bet-every +1.95% (all modeled payouts). McKenna engine beta=1.0 places zero selective tickets; beta=1.15 is modeled-only. Results in `output/REAL_DATA_RESULTS.md`. Auth used KAGGLE_API_TOKEN via kagglehub (Python 3.9 cannot use kaggle CLI 1.8+).

### 2026-07-09 — Free exploratory UK/Ireland slice wired in

**Branch:** `main`
**Source:** `free-datasets-hunt`

Wired free exploratory UK/Ireland race dataset (hwaitt/horse-racing 2008-2012, ~34,449 races) as `uk_runners.csv` with `load_bundled_uk`, dashboard Advanced option, and CLI `--uk`. HK bundled remains locked default; `prereg.json` unchanged. Paid Renavon/Equibase skipped. Inventory in `docs/FREE_DATASETS.md`. Exploratory smoke: favorite ROI ~−3%, timewave compare null. See [[0003-uk-exploratory-slice]].

### 2026-07-09 — Mobile scroll fix

**Branch:** `main`
**Source:** `mobile-scroll-fix`

Fixed critical mobile UX: empty-state Run Analysis was below the fold (~1100px) after a tall intro; CSS `overflow-x:hidden` + `max-width:100vw` on `html/body/stAppViewContainer` risked locking vertical scroll. Moved Run under the title on the empty state, shortened the intro, split `EMPTY_STATE_DETAILS` below, set `stMain overflow-y:auto` + `touch-action:pan-y`, and used `overflow-x:clip` on `html/body` without `100vw`. Verified in Playwright at 390x844 and 320x568 (button in view and clickable).

## Related

- [[simplemem-in-wiki]]
- [[0001-local-simplemem-backend]]
- [[documentation-in-repo]]
- [[ai-session-memory-2026-07-09]]
- [[0003-uk-exploratory-slice]]

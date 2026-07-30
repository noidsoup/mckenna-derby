---
title: SimpleMem archive
type: guide
created: 2026-07-30
updated: 2026-07-30
tags: [simplemem, archive, session-memory]
aliases: [simplemem memories]
status: active
---

# SimpleMem archive

> Compiled from **`docs/simplemem/memories.json`**. Do not edit by hand — refresh from the JSON store when memories change.

## Entries

### 2026-07-08 — Set up project for AI

**Branch:** `main`

**Completed:**
- Bootstrapped SimpleMem (local-only, namespace `mckenna-derby`, committed store at `docs/simplemem/`)
- Added `AGENTS.md`, `AI_RUNBOOK.md`, `.cursor/context7-libraries.md`, `.cursor/rules/simplemem.mdc`
- Installed repo skills: `python-testing-patterns`, `python-project-structure` under `.agents/skills/`
- Updated `.gitignore` for `.env` and `uncommitted/`; added `requests` and `python-dotenv` deps

**Project state:** Phase 2 complete — frozen statistical core with golden tests, pre-registered analysis in `prereg.json`, CLI pipeline (`run_analysis.py`), Streamlit dashboard (`dashboard.py`), dashboard start script on port 8501.

**Key decisions:**
- SimpleMem uses **local backend** so memories travel with the repo without cloud tokens

**Next steps:**
- Run Hong Kong real-data experiment when Kaggle credentials are available (`python run_analysis.py --hk rawdata/`)
- Source historical trifecta dividends for credible backtest conclusions

## Related

- [[simplemem-in-wiki]]
- [[0001-local-simplemem-backend]]
- [[documentation-in-repo]]

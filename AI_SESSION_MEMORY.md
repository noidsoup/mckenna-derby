# AI Session Memory — McKenna Derby

Append-only log for AI assistants. Summarize completed work, decisions, and next steps. No secrets or PII.

---

## 2026-07-08 — Set up project for AI

**Branch:** `main`

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

**Next steps:**
- Copy `crewai/.env.example` → `crewai/.env` and set `OPENAI_API_KEY` to run the planner
- Run Hong Kong real-data experiment when Kaggle credentials are available (`python run_analysis.py --hk rawdata/`)
- Source historical trifecta dividends for credible backtest conclusions

---

## 2026-07-09 — Removed CrewAI subproject

**Branch:** `main`

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

---

## 2026-07-09 — Plain-English dashboard copy

**Branch:** `cursor/dashboard-plain-english-copy-1590`

**Completed:**
- Added an **About** landing section in `dashboard.py` explaining what the app does, the Timewave/novelty idea, principles (pre-registration, honest nulls, transparent math), and a jargon glossary
- Added plain-English captions on every results tab and sidebar control help text
- First visit shows About + a 30-second try-it guide; after a run, About is the first tab
- Regression test `test_dashboard_has_plain_english_about_copy`; full suite 44 passed

**Key decisions:**
- Copy lives as constants in `dashboard.py` (ABOUT_MARKDOWN, TAB_INTROS, SIDEBAR_HELP) so the Streamlit app is self-explanatory without requiring README reading
- Kept technical metrics intact; layered captions rather than renaming stats

**Next steps:**
- Optional: surface the same About blurb in README hero if desired

---

## 2026-07-09 — First-visit guided tour mode

**Branch:** `cursor/dashboard-tour-mode-1590`

**Completed:**
- Added `mckenna_derby/tour.py`: Driver.js popover tour injected into the parent Streamlit page
- Auto-starts on first visit (localStorage `mckenna_derby_tour_v1`); sidebar **Replay guided tour** to restart
- Anchored steps to header, About panel, data source, run params, engine params, and Run Analysis
- Keyed Streamlit containers/widgets for `.st-key-*` anchors; bumped `streamlit>=1.40`
- Tests: `tests/test_tour.py` + dashboard wiring assertion; 49 passed

**Key decisions:**
- Self-contained Driver.js via CDN instead of `streamlit-tour` (needs Python 3.10+ / Streamlit 1.51+)
- Missing anchors fall back to floating info steps so the tour still completes

**Next steps:**
- Manual click-through of tour on Streamlit Community Cloud (CDN + sidebar layout)

---

## 2026-07-09 — Exotic dividends upgrade (partial)

**Branch:** `main` (uncommitted working tree)

**Completed:**
- Inventoried all local raw dumps + re-confirmed Kaggle `gdaley/hkracing` has only `races.csv`/`runs.csv` with **win/place** dividends — **no** trifecta/tierce/trio
- Rebuilt bundled `hk_runners.csv` with real `win_payout` / `place_payout` (per $1)
- Loader + rebuild plumbing for companion exotic CSV (`--exotics`); schema in `mckenna_derby/datasets/README.md`
- Tests for win/place attach, exotic merge, backtest actual settlement; 59 pytest passed
- Re-ran exploratory edge hunt; wrote `output/EXOTIC_DIVIDENDS_UPGRADE.md` + refreshed `output/EXPLORATORY_EDGE_HUNT.md`

**Key decisions / honesty:**
- Upgrade status = **partial / blocked** on exotic source data — do not claim trifecta cash settlement
- Real win favorite ROI ≈ −15%; place ≈ −16%; modeled trifecta unchanged; no edge claimed

**Next steps:**
- Obtain race-matched trifecta/tierce dividends (paid archive or remapped IDs), then `build_bundled_data.py --exotics …` and re-run edge hunt for actual `payout_source`

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

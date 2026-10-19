# AGENTS.md — McKenna Derby

Primary always-on context for AI assistants. Read **AI_RUNBOOK.md** for operational detail.

**Project wiki:** read `wiki/index.md` before non-trivial work; open pages it points to only when relevant.
After a repeated failure, check `wiki/gotchas.md`. Writing to the wiki: follow `wiki/SCHEMA.md`.

Claude Code loads this file through `.claude/CLAUDE.md`. Always-on rules are in `.claude/rules/` (the wiki rule loads only for files in `wiki/`), and the repo skills are linked from `.claude/skills/`.

## Start of session

1. Read **AI_RUNBOOK.md** and **AI_SESSION_MEMORY.md**
2. Query SimpleMem: `python3 simplemem_cli.py query --question "<task topic>"`
3. Check **prereg.json** before any real-data analysis — do not change it after the first real-data run
4. Use Context7 with IDs from `.cursor/context7-libraries.md`

## Tech stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.9+ (main venv) |
| Package | `mckenna_derby` (setuptools, `pyproject.toml`) |
| Data | pandas, NumPy |
| Stats | SciPy (`stats`, permutation tests) |
| CLI plots | Matplotlib |
| Dashboard | Streamlit + Plotly |
| Tests | pytest (golden tests freeze the statistical core) |
| Memory | SimpleMem (local JSON at `docs/simplemem/`) |

## Critical patterns

- **Frozen core:** Do not change `mckenna_derby/timewave.py`, `mckenna_derby/novelty.py`, or `mckenna_derby/compare.py` without explicit user approval and golden test updates
- **Pre-registration:** Primary analysis params live in `prereg.json`; exploratory runs need Bonferroni labels
- **Honest nulls:** Synthetic data (`--synthetic`) is market-calibrated — expect no timewave signal and ROI ≈ −takeout
- **Default data:** Bundled Hong Kong races in `mckenna_derby/datasets/hk_runners.csv` (no Kaggle/upload required)
- **Exploratory free:** Bundled UK/Ireland slice in `mckenna_derby/datasets/uk_runners.csv` (`--uk` / Advanced options); not the locked claim — see `docs/FREE_DATASETS.md`
- **Payouts:** Bundled CSV includes real `win_payout` / `place_payout` (per $1). Prefer real `trifecta_payout` over modeled parimutuel when present — Kaggle `gdaley/hkracing` has **no** trifecta/tierce; merge via `scripts/build_bundled_data.py --exotics` (see `mckenna_derby/datasets/README.md`)
- **Timewave after 2012-12-21:** Mirrored extension is flagged; usable historical window ends at zero date

## Repo skills (`.agents/skills/`, linked from `.claude/skills/`)

| Skill | When to use |
|-------|-------------|
| `python-testing-patterns` | Adding or changing tests, fixtures, parametrization |
| `python-project-structure` | Package layout, imports, new modules |

## SimpleMem

- Namespace: `mckenna-derby`
- Backend: **local only** (`SIMPLEMEM_BACKEND=local`, store at `docs/simplemem/memories.json`)
- CLI: `python3 simplemem_cli.py add|query|import-ai-session|sync`
- **Commit** `docs/simplemem/memories.json` when memories change

## Context7

Prefer library IDs in `.cursor/context7-libraries.md`. Use for Streamlit, SciPy stats, pandas, pytest APIs.

## Commands

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e . pytest
bash .verify.sh                        # the gate: pytest -q via .venv/bin/pytest
pytest -q
python run_analysis.py                 # bundled HK (default)
python run_analysis.py --uk            # UK/Ireland exploratory free slice
python run_analysis.py --synthetic     # null demo
python run_analysis.py --sweep --max-lag 30
streamlit run dashboard.py
./scripts/start-dashboard.sh
```

## Session memory & handoff

- **AI_SESSION_MEMORY.md** — dated session log (append on significant work)
- **"Mark where you are"** — update `AI_SESSION_MEMORY.md` and `AI_RUNBOOK.md`; do not commit unless asked (Hermes close-out handles ceremony)

## Relevant rules

- `.claude/rules/pre-task-retrieval.md` — SimpleMem, then LanceDB, then vault recall before non-trivial work
- `.claude/rules/verify-before-done.md` — run `bash .verify.sh` and paste the real result
- `.claude/rules/simplemem.md` — memory namespace and security
- `.claude/rules/llm-wiki.md` — read `wiki/SCHEMA.md` before wiki work (path-scoped)

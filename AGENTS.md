# AGENTS.md — McKenna Derby

Primary always-on context for AI assistants. Read **AI_RUNBOOK.md** for operational detail.

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

- **Frozen core:** Do not change `timewave.py`, `novelty.py`, or `compare.py` without explicit user approval and golden test updates
- **Pre-registration:** Primary analysis params live in `prereg.json`; exploratory runs need Bonferroni labels
- **Honest nulls:** Synthetic data (`--synthetic`) is market-calibrated — expect no timewave signal and ROI ≈ −takeout
- **Default data:** Bundled Hong Kong races in `mckenna_derby/datasets/hk_runners.csv` (no Kaggle/upload required)
- **Payouts:** Prefer real `trifecta_payout` dividends over modeled parimutuel when available
- **Timewave after 2012-12-21:** Mirrored extension is flagged; usable historical window ends at zero date

## Repo skills (`.agents/skills/`)

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
pytest -q
python run_analysis.py                 # bundled HK (default)
python run_analysis.py --synthetic     # null demo
python run_analysis.py --sweep --max-lag 30
streamlit run dashboard.py
./scripts/start-dashboard.sh
```

## Session memory & handoff

- **AI_SESSION_MEMORY.md** — dated session log (append on significant work)
- **"Mark where you are"** — update `AI_SESSION_MEMORY.md` and `AI_RUNBOOK.md`; do not commit unless asked (Hermes close-out handles ceremony)

## Relevant rules

- `.cursor/rules/simplemem.mdc` — memory namespace and security

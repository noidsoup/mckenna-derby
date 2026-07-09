# AI Runbook — McKenna Derby

Read this first when working on this codebase. **AGENTS.md** has the short session-start checklist.

## What this project is

McKenna Derby tests whether horse-racing **novelty** (surprisal of outcomes under market odds) correlates with Terence McKenna's **Timewave Zero**, and whether a timewave-filtered **buy-all-trifecta-combinations** strategy beats random timing. The deliverable is an honest statistical result, not a betting product.

## Tech stack

| Piece | Technology |
|-------|------------|
| Core analysis | Python 3.9+, `mckenna_derby` package |
| Data | pandas, NumPy |
| Statistics | SciPy (Pearson/Spearman, permutation test) |
| CLI visualization | Matplotlib → `output/novelty_vs_timewave.png` |
| Dashboard | Streamlit + Plotly (`dashboard.py`) |
| Tests | pytest golden tests (freeze `timewave`, `novelty`, `compare`) |
| Pre-registration | `prereg.json` |
| AI memory | SimpleMem local JSON |

## Project structure

```
mckenna-derby/
├── mckenna_derby/          # Core package
│   ├── timewave.py         # Timewave Zero port (FROZEN)
│   ├── novelty.py          # Surprisal scoring (FROZEN)
│   ├── compare.py          # Correlation + permutation (FROZEN)
│   ├── backtest.py         # Trifecta P&L strategy
│   ├── data.py             # Loaders + synthetic null data
│   ├── report.py           # Markdown report writer
│   └── wavesets/           # I Ching number sets (txt)
├── run_analysis.py         # CLI pipeline
├── dashboard.py            # Streamlit UI
├── prereg.json             # Primary analysis (do not edit after real-data run)
├── tests/                  # Golden + integration tests
├── output/                 # Generated reports (gitignored)
├── rawdata/                # Kaggle downloads (gitignored)
├── docs/simplemem/         # Committed SimpleMem store
├── AGENTS.md               # Agent session start
└── AI_SESSION_MEMORY.md    # Session handoff log
```

## Key workflows

### Run the analysis pipeline

```bash
source .venv/bin/activate
pip install -e . pytest
pytest -q
python run_analysis.py                              # synthetic null demo
python run_analysis.py --sweep --max-lag 30           # exploratory sections
python run_analysis.py --hk rawdata/                  # Hong Kong Kaggle data
python run_analysis.py --csv path/to/runners.csv      # generic CSV
```

Outputs: `output/report.md`, `output/race_scores.csv`, `output/novelty_vs_timewave.png`

### Run the dashboard

```bash
streamlit run dashboard.py
# or
./scripts/start-dashboard.sh   # binds 8501/8502, logs to /tmp/mckenna-derby-streamlit.log
```

### Add a feature (AI-assisted)

1. For non-trivial work: use the global `plan-and-implement` skill (writes to `.cursor/plans/PLAN.md`)
2. Implement task-by-task; run `pytest -q` after each change to frozen modules
3. Append **AI_SESSION_MEMORY.md**; optionally `python3 simplemem_cli.py add --text "..."`

### Real-data experiment

1. Ensure `prereg.json` is committed and unchanged
2. `kaggle datasets download -d gdaley/hkracing -p rawdata --unzip`
3. `python run_analysis.py --hk rawdata/ --sweep --max-lag 30`
4. Report primary result verbatim — do not tune parameters to improve p-values

## Conventions

- Use `.venv/bin/python` and `.venv/bin/pytest` (not system Python)
- **Frozen core:** `timewave.py`, `novelty.py`, `compare.py` — only change with explicit approval + golden test updates
- Exploratory analyses (all number sets, threshold sweep, lead-lag) must be labeled exploratory; apply Bonferroni where noted
- Modeled trifecta payouts imply ROI ≈ −takeout; real dividends need `trifecta_payout` column on CSV rows

## Commands reference

| Task | Command |
|------|---------|
| Install | `pip install -r requirements.txt && pip install -e . pytest` |
| Test | `pytest -q` |
| Analysis | `python run_analysis.py` |
| Dashboard | `streamlit run dashboard.py` |
| SimpleMem add | `python3 simplemem_cli.py add --text "..."` |
| SimpleMem query | `python3 simplemem_cli.py query --question "..."` |
| Import session log | `python3 simplemem_cli.py import-ai-session --path AI_SESSION_MEMORY.md` |

## SimpleMem

- Config: `.env` (`SIMPLEMEM_ENABLED=true`, `SIMPLEMEM_BACKEND=local`, `SIMPLEMEM_NAMESPACE=mckenna-derby`)
- Store: `docs/simplemem/memories.json` — **commit when updated**
- Never store secrets, API keys, or PII

## Where to look

| Question | Location |
|----------|----------|
| Session start | `AGENTS.md` |
| Library docs | `.cursor/context7-libraries.md` + Context7 MCP |
| What we did last | `AI_SESSION_MEMORY.md` |
| Primary analysis params | `prereg.json` |
| Phase 2 implementation plan | `PLAN.md` (historical) |
| User-facing overview | `README.md` |

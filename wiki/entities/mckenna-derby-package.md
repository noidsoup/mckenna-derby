---
title: McKenna Derby package (this repository)
type: entity
summary: The mckenna_derby Python package, its CLIs and which modules are frozen.
status: active
created: 2026-07-30
updated: 2026-10-19
last_verified: 2026-10-19
sources: ["[[readme-project-overview]]"]
tags: [mckenna-derby, python, package]
aliases: [mckenna-derby, this repo]
---
# McKenna Derby package (this repository)

## What it is

The **mckenna-derby** repository: a Python 3.9+ research package (`mckenna_derby`) that scores racing novelty, compares it to Timewave Zero, and backtests trifecta strategies. GitHub: `noidsoup/mckenna-derby` (public as of 2026-10-19).

## How it's used in the project

| Path | Role |
|------|------|
| `mckenna_derby/timewave.py` | Timewave Zero port (**frozen**) |
| `mckenna_derby/novelty.py` | Surprisal scoring (**frozen**) |
| `mckenna_derby/compare.py` | Correlation + permutation (**frozen**) |
| `mckenna_derby/backtest.py` | Buy-all trifecta P&L |
| `mckenna_derby/mckenna_engine.py` | Selective betting engine |
| `mckenna_derby/data.py` | Loaders (bundled HK/UK, Kaggle HK, UK raw) + synthetic null data |
| `mckenna_derby/calendar_windows.py` | Upcoming high-novelty day/hour windows for the dashboard (added 2026-07-09, commit `95f0c3f`) |
| `mckenna_derby/assets/` | Local clipart used by the dashboard |
| `mckenna_derby/datasets/` | Bundled `hk_runners.csv`, `uk_runners.csv` and their README ([[bundled-datasets]]) |
| `run_analysis.py` | CLI pipeline |
| `run_mckenna.py` | McKenna Engine CLI |
| `dashboard.py` | Streamlit UI |
| `tests/` | pytest golden tests |
| `prereg.json` | Primary analysis lock |

## Key details

- Install: `pip install -e . pytest`
- Verify: `pytest -q` then `python run_analysis.py`
- Outputs: `output/` (gitignored)
- Raw data: `rawdata/` (gitignored; Kaggle HK racing)
- AI context: `AGENTS.md`, `AI_RUNBOOK.md`, `AI_SESSION_MEMORY.md`

## Related

- [[frozen-statistical-core]]
- [[prereg-json]]
- [[streamlit-dashboard]]
- [[run-analysis-pipeline]]
- [[documentation-in-repo]]
- [[SCHEMA]]

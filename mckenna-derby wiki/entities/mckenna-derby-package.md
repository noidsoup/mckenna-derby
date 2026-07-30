---
title: McKenna Derby package (this repository)
type: entity
created: 2026-07-30
updated: 2026-07-30
tags: [mckenna-derby, python, package]
aliases: [mckenna-derby, this repo]
sources: ["[[readme-project-overview]]"]
status: active
---

# McKenna Derby package (this repository)

## What it is

The **mckenna-derby** repository: a Python 3.9+ research package (`mckenna_derby`) that scores racing novelty, compares it to Timewave Zero, and backtests trifecta strategies. GitHub: `noidsoup/mckenna-derby`.

## How it's used in the project

| Path | Role |
|------|------|
| `mckenna_derby/timewave.py` | Timewave Zero port (**frozen**) |
| `mckenna_derby/novelty.py` | Surprisal scoring (**frozen**) |
| `mckenna_derby/compare.py` | Correlation + permutation (**frozen**) |
| `mckenna_derby/backtest.py` | Buy-all trifecta P&L |
| `mckenna_derby/mckenna_engine.py` | Selective betting engine |
| `mckenna_derby/data.py` | Loaders + synthetic null data |
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

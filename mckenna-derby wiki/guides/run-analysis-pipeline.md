---
title: Run the analysis pipeline
type: guide
created: 2026-07-30
updated: 2026-07-30
tags: [runbook, cli, pytest, dashboard]
status: active
---

# Run the analysis pipeline

## Prerequisites

- Python 3.9+
- Virtualenv at `.venv` (use `.venv/bin/python` and `.venv/bin/pytest`, not system Python)

## Steps

### 1. Install and verify frozen core

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e . pytest
pytest -q
```

### 2. Synthetic null demo

```bash
python run_analysis.py
python run_analysis.py --sweep --max-lag 30   # exploratory sections
```

Outputs: `output/report.md`, `output/race_scores.csv`, `output/novelty_vs_timewave.png`

### 3. Real Hong Kong data

1. Confirm [[prereg-json]] is committed and unchanged.
2. Kaggle token at `~/.kaggle/kaggle.json`.
3. Download and run:

```bash
kaggle datasets download -d gdaley/hkracing -p rawdata --unzip
python run_analysis.py --hk rawdata/ --sweep --max-lag 30
```

Report primary result verbatim — do not tune parameters to improve p-values.

### 4. McKenna Engine

```bash
python run_mckenna.py --beta 1.0            # fair pool: expect zero selective bets
python run_mckenna.py --beta 1.15           # assumed favorites-overbet bias
```

### 5. Dashboard

```bash
streamlit run dashboard.py
# or
./scripts/start-dashboard.sh
```

### 6. SimpleMem (optional)

```bash
python3 simplemem_cli.py query --question "<task topic>"
python3 simplemem_cli.py add --text "..."
python3 simplemem_cli.py import-ai-session --path AI_SESSION_MEMORY.md
```

## Troubleshooting

- **Golden test failures** after editing `timewave.py`, `novelty.py`, or `compare.py` — only change with explicit approval; update golden fixtures.
- **ROI always ≈ −takeout on synthetic data** — expected; validates pipeline, not hypothesis.
- **No timewave signal on synthetic** — expected honest null.

## Related

- [[frozen-statistical-core]]
- [[prereg-json]]
- [[streamlit-dashboard]]
- [[mckenna-engine-selective-betting]]
- [[mckenna-derby-package]]

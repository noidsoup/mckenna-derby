---
title: Streamlit dashboard
type: entity
created: 2026-07-30
updated: 2026-07-30
tags: [streamlit, plotly, ui]
aliases: [dashboard, dashboard.py]
sources: ["[[readme-project-overview]]"]
status: active
---

# Streamlit dashboard

## What it is

Interactive web UI at `dashboard.py` built with **Streamlit** and **Plotly**. Lets users run analysis without the CLI.

## How it's used in the project

```bash
streamlit run dashboard.py
# or
./scripts/start-dashboard.sh   # binds 8501/8502, logs to /tmp/mckenna-derby-streamlit.log
```

Data sources: synthetic demo, Hong Kong `rawdata/` (if downloaded), or uploaded CSV. Defaults from [[prereg-json]]; overrides for number set, threshold, and takeout are exploratory.

Charts: daily novelty with rolling mean, inverted timewave, cumulative P&L, correlation stats, all four number sets, optional threshold sweep. Includes **McKenna Engine** section (beta, gate percentile, ticket cap).

## Key details

- Deploy: see `DEPLOY_STREAMLIT.md` at repo root for Streamlit Community Cloud (private GitHub repo + optional shared password).
- Context7 library IDs: `.cursor/context7-libraries.md` for Streamlit APIs.

## Related

- [[mckenna-derby-package]]
- [[mckenna-engine-selective-betting]]
- [[run-analysis-pipeline]]
- [[readme-project-overview]]

---
title: Streamlit dashboard
type: entity
created: 2026-07-30
updated: 2026-09-12
tags: [streamlit, plotly, ui]
aliases: [dashboard, dashboard.py]
sources: ["[[readme-project-overview]]", "[[ai-session-memory-2026-07-09]]"]
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

Data sources: synthetic demo, bundled Hong Kong (`mckenna_derby/datasets/hk_runners.csv`, default), uploaded CSV, or the bundled UK/Ireland exploratory slice (`uk_runners.csv`, via the Advanced radio or CLI `--uk`). Defaults from [[prereg-json]]; overrides for number set, threshold, and takeout are exploratory.

Charts: daily novelty with rolling mean, inverted timewave, cumulative P&L, correlation stats, all four number sets, optional threshold sweep. Includes **McKenna Engine** section (beta, gate percentile, ticket cap).

## Plain-English copy (2026-07-09)

- **About** landing section (`ABOUT_MARKDOWN` constant): explains the app, the Timewave/novelty idea, principles (pre-registration, honest nulls, transparent math), and a jargon glossary. First visit shows About + a 30-second try-it guide; after a run, About is the first tab.
- Plain-English captions on every results tab (`TAB_INTROS`) + sidebar control help (`SIDEBAR_HELP`). Technical metrics kept intact; layered captions rather than renamed stats.
- Regression test `test_dashboard_has_plain_english_about_copy` guards the copy.

## First-visit guided tour (added then removed 2026-07-09)

- Initially added `mckenna_derby/tour.py` (Driver.js popover tour, auto-start on first visit via localStorage `mckenna_derby_tour_v1`, sidebar **Replay guided tour**; `streamlit>=1.40`; `tests/test_tour.py`).
- **Removed the same day** on `cursor/remove-dashboard-tour-f875`: deleted `tour.py` + tests, removed the auto-start/replay hooks, renamed Streamlit keys from tour anchors to semantic names. A regression assertion now guarantees the guided-tour wiring stays absent; plain-English copy retained. See [[0004-driver-js-then-removed]].

## Mobile UX (2026-07-09)

- Empty-state Run button moved under the title (was below the fold at ~1100px); intro shortened, `EMPTY_STATE_DETAILS` split below; `stMain overflow-y:auto` + `touch-action:pan-y`; `overflow-x:clip` on `html/body` (no `100vw`). Verified in Playwright at 390x844 and 320x568.

## Key details

- Deploy: see `DEPLOY_STREAMLIT.md` at repo root for Streamlit Community Cloud (private GitHub repo + optional shared password).
- Context7 library IDs: `.cursor/context7-libraries.md` for Streamlit APIs.
- UK slice: exploratory only, HK remains the locked default — see [[0003-uk-exploratory-slice]].

## Related

- [[mckenna-derby-package]]
- [[mckenna-engine-selective-betting]]
- [[run-analysis-pipeline]]
- [[readme-project-overview]]
- [[ai-session-memory-2026-07-09]]
- [[0003-uk-exploratory-slice]]
- [[0004-driver-js-then-removed]]

---
title: AI session memory — 2026-07-09
type: source
created: 2026-09-12
updated: 2026-09-12
tags: [session-memory, source, 2026-07-09]
sources: ["AI_SESSION_MEMORY.md"]
status: active
---

# AI session memory — 2026-07-09

Summarizes the 2026-07-09 entries in **`AI_SESSION_MEMORY.md`** (five sessions), the most recent work not yet reflected in the vault. No git commits land in the 24-hour gardener window; these entries capture dashboard UX, dataset, and settlement work on 2026-07-09.

## Plain-English dashboard copy (branch `cursor/dashboard-plain-english-copy-1590`)
- **About** landing section in `dashboard.py` explaining the app, the Timewave/novelty idea, principles (pre-registration, honest nulls, transparent math), and a jargon glossary.
- Plain-English captions on every results tab + sidebar control help.
- First visit shows About + a 30-second try-it guide; after a run, About is the first tab.
- Regression test `test_dashboard_has_plain_english_about_copy`; full suite **44 passed**.
- Decisions: copy lives as constants in `dashboard.py` (`ABOUT_MARKDOWN`, `TAB_INTROS`, `SIDEBAR_HELP`); layered captions rather than renaming stats.

## First-visit guided tour mode (branch `cursor/dashboard-tour-mode-1590`)
- Added `mckenna_derby/tour.py` (Driver.js popover tour); auto-starts on first visit (localStorage `mckenna_derby_tour_v1`), sidebar **Replay guided tour**.
- Anchored steps to header, About, data source, run params, engine params, Run Analysis; keyed Streamlit widgets for `.st-key-*` anchors; bumped `streamlit>=1.40`.
- Tests: `tests/test_tour.py` + wiring assertion; **49 passed**.
- Key decision: self-contained Driver.js via CDN (not `streamlit-tour`, which needs Python 3.10+ / Streamlit 1.51+); missing anchors fall back to floating info steps. See [[0004-driver-js-then-removed]].

## Exotic dividends upgrade — partial / blocked (branch `main`, uncommitted)
- Inventoried local raw dumps; re-confirmed Kaggle `gdaley/hkracing` has only `races.csv`/`runs.csv` with **win/place** dividends — **no** trifecta/tierce/trio.
- Rebuilt bundled `hk_runners.csv` with real `win_payout`/`place_payout` (per $1); loader + rebuild plumbing for a companion exotic CSV (`--exotics`); schema in `mckenna_derby/datasets/README.md`.
- Tests for win/place attach, exotic merge, backtest actual settlement; **59 pytest passed**.
- Honesty: status = **partial / blocked** on exotic source data — do not claim trifecta cash settlement. Real win-favorite ROI ≈ −15%, place ≈ −16%; modeled trifecta unchanged; no edge claimed.
- Written `output/EXOTIC_DIVIDENDS_UPGRADE.md` + refreshed `output/EXPLORATORY_EDGE_HUNT.md`.

## Free datasets hunt + UK/Ireland wire-in (branch `main`)
- Inventoried local free dumps; web-reviewed free Kaggle/GitHub candidates (skipped paid Renavon/Equibase).
- Bundled exploratory `uk_runners.csv` (~34,449 races, 2008–2012) from `hwaitt/horse-racing`; wired `load_bundled_uk()`, `scripts/build_bundled_uk.py`, dashboard Advanced radio, CLI `--uk`.
- Docs: `docs/FREE_DATASETS.md` (+ `output/FREE_DATASETS.md`), datasets README, AGENTS/RUNBOOK/README/DEPLOY.
- Tests for UK loader + dashboard option; **63 pytest passed**.
- Exploratory smoke: favorite ROI ≈ −3.4%; primary compare null (p≈0.49) — **not** a McKenna edge. Decision: ship the 2008–2012 slice (~16 MB) rather than the full raw (~725 MB, gitignored); do not edit `prereg.json`; UK exploratory only. See [[0003-uk-exploratory-slice]].

## Removed dashboard tour mode (branch `cursor/remove-dashboard-tour-f875`)
- Removed `mckenna_derby/tour.py` + tests; removed auto-start/replay hooks; renamed Streamlit keys from tour anchors to semantic names.
- Updated dashboard regression tests to assert guided-tour wiring stays absent; `pytest -q` passes (**59 tests**).
- Decision: kept the plain-English intro/sidebar copy and the main-page Run Analysis flow; removed the tour-specific Driver.js/localStorage behavior entirely rather than hiding the replay button. See [[0004-driver-js-then-removed]].

## Related

- [[streamlit-dashboard]]
- [[0003-uk-exploratory-slice]]
- [[0004-driver-js-then-removed]]
- [[simplemem-archive]]
- [[run-analysis-pipeline]]

---
title: Gotchas
type: overview
summary: Known traps. Check here after a repeated failure.
status: active
created: 2026-10-19
updated: 2026-10-19
last_verified: 2026-10-19
sources: [AGENTS.md, prereg.json, output/REAL_DATA_RESULTS.md, "PR #1", "commit 2ef1b0e", "commit 453c884"]
tags: [gotchas]
---

# Gotchas

One line each: the trap, then the fix or the page with details.

- **Never edit `prereg.json`.** The first real-data run happened on 2026-07-09; any change now is parameter fishing. → [[0002-preregistered-primary-analysis]]
- **ROI is not part of the prediction** (removed before the real-data run). Old notes that say otherwise are wrong. → [[0005-roi-is-exploratory]]
- **A positive ROI is not an edge.** Settlement is modeled (no real trifecta dividends), so expected ROI is −takeout; the +1.95% bet-every-race figure was a model artifact. → [[real-data-results-2026-07-09]], [[bundled-datasets]]
- **Use `permutation_p`, not `spearman_p`.** The naive p-values ignore autocorrelation. → [[timewave-zero-comparison]]
- **Don't touch `timewave.py`, `novelty.py`, `compare.py`** without Nicholas's OK and golden-test updates. → [[frozen-statistical-core]]
- **Look-ahead bias:** day selection must use the causal expanding-window percentile (fixed in `2ef1b0e`); don't reintroduce full-sample percentiles. → [[0005-roi-is-exploratory]]
- **UK data is exploratory only**; never report it as the primary claim. → [[0003-uk-exploratory-slice]]
- **Dates after 2012-12-21** use a mirrored timewave extension (flagged); the usable window ends at the zero date. → [[timewave-zero-comparison]]
- **Use `.venv/bin/python` / `bash .verify.sh`, not system Python** (Python 3.9 venv). Kaggle CLI ≥ 1.8 needs 3.11+, so real downloads used `kagglehub`. → [[real-data-results-2026-07-09]]
- **Dashboard copy is under test.** Changing the About text, hippie lines or tour wiring can fail `pytest` (regression asserts the tour stays gone). → [[streamlit-dashboard]], [[0004-driver-js-then-removed]]
- **`AGENTS.md`, `AI_RUNBOOK.md` and `.gitignore` use CRLF / mixed line endings** — keep them when editing (commit `453c884`).
- **The repo is public** but `DEPLOY_STREAMLIT.md` assumes private; the app password protects only the app. → [[streamlit-dashboard]]
- **Commit `docs/simplemem/memories.json`** when SimpleMem changes; it is the memory store. → [[0001-local-simplemem-backend]]
- **No CrewAI.** It was removed in PR #1. → [[0006-drop-crewai]]

## Related

- [[overview]]
- [[index]]

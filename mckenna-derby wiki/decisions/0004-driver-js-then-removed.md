---
title: 0004 — Use Driver.js for the first-visit guided tour, then remove the tour
type: decision
created: 2026-09-12
updated: 2026-09-12
tags: [decision, dashboard, tour, driver-js, ux]
aliases: [guided tour, driver js]
status: accepted
---

# 0004 — Use Driver.js for the first-visit guided tour, then remove the tour

## Context

Two related 2026-07-09 sessions (`AI_SESSION_MEMORY.md`) addressed dashboard onboarding.

**First-visit guided tour mode** (branch `cursor/dashboard-tour-mode-1590`) added `mckenna_derby/tour.py`: a Driver.js popover tour injected into the parent Streamlit page, auto-starting on first visit (localStorage `mckenna_derby_tour_v1`) with a sidebar **Replay guided tour** to restart. Steps anchored to the header, About panel, data source, run params, engine params, and Run Analysis. Streamlit containers/widgets were keyed for `.st-key-*` anchors, and `streamlit>=1.40` was bumped. Tests: `tests/test_tour.py` + a dashboard wiring assertion; 49 passed.

**Removed dashboard tour mode** (branch `cursor/remove-dashboard-tour-f875`) then deleted `mckenna_derby/tour.py` and its tests, removed the auto-start/replay hooks, and renamed the Streamlit keys from tour anchors to semantic names.

## Decision

- **Use self-contained Driver.js via CDN** rather than `streamlit-tour` (the package needed Python 3.10+ / Streamlit 1.51+, incompatible with the project's Python 3.9 main venv).
- **Missing anchors fell back** to floating info steps so the tour still completed.
- **Later, remove the tour entirely** (rather than hiding the replay button): delete `tour.py` + tests, drop the Driver.js/localStorage behavior, and rename Streamlit keys to semantic names.
- **Retain** the plain-English intro/sidebar copy and the main-page Run Analysis flow.

## Consequences

- The guided tour ships then is fully removed on 2026-07-09; `pytest -q` passes (59 tests) with the tour absent and a regression assertion that its wiring stays absent.
- Onboarding now rests on the plain-English About copy only.

## Related

- [[streamlit-dashboard]]
- [[ai-session-memory-2026-07-09]]

---
title: Log
type: overview
summary: Append-only history of wiki changes. Newest last.
status: active
created: 2026-07-30
updated: 2026-10-19
last_verified: 2026-10-19
sources: []
tags: [meta]
---

# Log

Format: `## [YYYY-MM-DD] ingest|session|lint|query|seed|upgrade | one line`. Keep ≤150 entries; move older ones to `log/YYYY.md`. Entries before 2026-10-19 were newest-first; reordered oldest-first, text unchanged.

## [2026-07-30] create | Wiki bootstrapped

Initial vault **`mckenna-derby wiki/`** created (SCHEMA, index, log, Obsidian settings, folder layout). Compiled 15 content pages from `README.md`, `AGENTS.md`, `AI_RUNBOOK.md`, `AI_SESSION_MEMORY.md`, and `docs/simplemem/memories.json`. Added `WIKI.md` pointer and `.cursor/rules/llm-wiki.mdc`. **Did not delete** any `docs/` files.


## [2026-07-30] migrate | Ingested repo root docs

- **Source:** [[readme-project-overview]] from `README.md`
- **Entities:** [[mckenna-derby-package]], [[prereg-json]], [[streamlit-dashboard]], [[lancedb-project-knowledge-search]]
- **Concepts:** [[novelty-surprisal-scoring]], [[timewave-zero-comparison]], [[frozen-statistical-core]], [[mckenna-engine-selective-betting]]
- **Decisions:** [[0001-local-simplemem-backend]], [[0002-preregistered-primary-analysis]]
- **Guides:** [[documentation-in-repo]], [[run-analysis-pipeline]]
- **Memories:** [[simplemem-in-wiki]], [[simplemem-archive]] from `docs/simplemem/memories.json`

## [2026-09-12] update | Gardener refresh after 2026-07-09 session entries

No git commits in the 24-hour window; `AI_SESSION_MEMORY.md` gained five 2026-07-09/10 entries not previously in the vault. Synced from session memory + working-tree `AI_RUNBOOK.md`:

- **Guides:** [[run-analysis-pipeline]] now documents the default bundled HK dataset, the bundled `uk_runners.csv` exploratory slice (`--uk` / Advanced radio), and the plain-English About copy + first-visit tour (added 2026-07-09, **removed again** same day on `cursor/remove-dashboard-tour-f875`; plain-English copy retained).
- **Entities:** [[streamlit-dashboard]] updated with the plain-English About section/captions, first-visit guided tour (Driver.js, removed 2026-07-09), and UK/Ireland data source.
- **Decisions:** new [[0003-uk-exploratory-slice]] and [[0004-driver-js-then-removed]] recorded.
- **Sources:** new [[ai-session-memory-2026-07-09]] summarizing the 2026-07-09 session log (exotic dividends partial, UK wire-in, mobile scroll fix, tour add+remove); refreshed [[simplemem-archive]] with the 2026-07-09 committed entries (real-data run, free-datasets hunt, mobile scroll fix, CrewAI removal).
- `docs/simplemem/memories.json` working tree drops two stale 2026-07-08/09 session entries (CrewAI-era); not committed — left for the session owner.


## [2026-10-19] upgrade | Wiki moved to wiki/ and brought to the standard

Renamed `mckenna-derby wiki/` → `wiki/` (kept `.obsidian/`). Standard SCHEMA and index; new [[overview]], [[gotchas]], [[real-data-results-2026-07-09]], [[bundled-datasets]], [[0005-roi-is-exploratory]], [[0006-drop-crewai]]. Fixed a wrong claim in [[prereg-json]], [[timewave-zero-comparison]] and [[0002-preregistered-primary-analysis]]: ROI is not part of the pre-registered prediction (removed in `2ef1b0e`). Added the later 2026-07-09 dashboard history to [[streamlit-dashboard]]. Archived `memories/`. Updated AGENTS.md, WIKI.md and `.claude/rules/llm-wiki.md`.

---
title: Wiki Log
type: log
created: 2026-07-30
updated: 2026-07-30
---

# Wiki Log

> Chronological record of wiki operations. Append-only.
>
> Format: `## [YYYY-MM-DD] verb | Subject`
>
> Verbs: `ingest`, `query`, `lint`, `update`, `create`, `migrate`, `session`

## [2026-07-30] create | Wiki bootstrapped

Initial vault **`mckenna-derby wiki/`** created (SCHEMA, index, log, Obsidian settings, folder layout). Compiled 15 content pages from `README.md`, `AGENTS.md`, `AI_RUNBOOK.md`, `AI_SESSION_MEMORY.md`, and `docs/simplemem/memories.json`. Added `WIKI.md` pointer and `.cursor/rules/llm-wiki.mdc`. **Did not delete** any `docs/` files.

## [2026-07-30] migrate | Ingested repo root docs

- **Source:** [[readme-project-overview]] from `README.md`
- **Entities:** [[mckenna-derby-package]], [[prereg-json]], [[streamlit-dashboard]], [[lancedb-project-knowledge-search]]
- **Concepts:** [[novelty-surprisal-scoring]], [[timewave-zero-comparison]], [[frozen-statistical-core]], [[mckenna-engine-selective-betting]]
- **Decisions:** [[0001-local-simplemem-backend]], [[0002-preregistered-primary-analysis]]
- **Guides:** [[documentation-in-repo]], [[run-analysis-pipeline]]
- **Memories:** [[simplemem-in-wiki]], [[simplemem-archive]] from `docs/simplemem/memories.json`

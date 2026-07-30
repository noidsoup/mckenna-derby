---
title: LanceDB project-knowledge search
type: entity
created: 2026-07-30
updated: 2026-07-30
tags: [lancedb, retrieval, semantic-search]
aliases: [lancedb, project-knowledge]
sources: []
status: active
---

# LanceDB project-knowledge search

## What it is

Local offline semantic search over repo markdown, rules, and agent docs using **LanceDB** + sentence-transformers. Sidecar tooling installed via AI-first bootstrap.

## How it's used in the project

| Script | Purpose |
|--------|---------|
| `scripts/index_project_knowledge_lancedb.py` | Build/update index |
| `scripts/search_project_knowledge_lancedb.py` | Query index |
| `scripts/project_knowledge_lancedb_common.py` | Shared helpers |

Index output: `uncommitted/lancedb_project_knowledge/` (gitignored). Deps: `requirements-lancedb.txt`.

Agents: search before grep on non-trivial tasks (see `.cursor/rules/project-knowledge-lancedb.mdc` and `.cursor/rules/pre-task-retrieval.mdc`). Re-index after doc edits.

## Key details

```bash
python3 -u scripts/search_project_knowledge_lancedb.py "<question>" --top-k 8
python3 -u scripts/index_project_knowledge_lancedb.py --apply --files <changed paths>
```

Retrieval order in `AGENTS.md`: SimpleMem → LanceDB → vault recall → Honcho.

## Related

- [[documentation-in-repo]]
- [[simplemem-in-wiki]]
- [[SCHEMA]]

---
title: Session memories in the wiki (SimpleMem)
type: guide
created: 2026-07-30
updated: 2026-10-10
tags: [simplemem, memories, wiki]
status: active
---

# Session memories in the wiki (SimpleMem)

## What lives where

| Location | Role |
|----------|------|
| **`docs/simplemem/memories.json`** | **SimpleMem** local store — what **`simplemem_cli.py`** reads/writes when **`SIMPLEMEM_BACKEND=local`**. Commit when the CLI updates it. |
| **`mckenna-derby wiki/memories/simplemem-archive.md`** | **Human-readable mirror** for Obsidian graph, wikilinks, and agents that live in the vault. |

Config (`.env`): `SIMPLEMEM_ENABLED=true`, `SIMPLEMEM_NAMESPACE=mckenna-derby`, `SIMPLEMEM_LOCAL_DIR=docs/simplemem`.

## Refresh the archive after JSON changes

Re-export entries into [[simplemem-archive]] when `docs/simplemem/memories.json` changes (manual or script). Commit both files together.

## Privacy

Same rules as SimpleMem: no secrets, tokens, or passwords. See `.claude/rules/simplemem.md`.

## Related

- [[simplemem-archive]]
- [[0001-local-simplemem-backend]]
- [[documentation-in-repo]]
- [[SCHEMA]]

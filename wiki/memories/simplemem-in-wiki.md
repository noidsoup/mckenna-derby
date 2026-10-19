---
title: Session memories in the wiki (SimpleMem)
type: source
summary: "Archived: how docs/simplemem/memories.json related to the old wiki mirror."
status: archived
created: 2026-07-30
updated: 2026-10-19
last_verified: 2026-10-19
tags: [simplemem, memories, wiki]
---
# Session memories in the wiki (SimpleMem)

> **Archived 2026-10-19.** The wiki standard keeps session history in `AI_SESSION_MEMORY.md` and SimpleMem in `docs/simplemem/`; this mirror is no longer refreshed.

## What lives where

| Location | Role |
|----------|------|
| **`docs/simplemem/memories.json`** | **SimpleMem** local store — what **`simplemem_cli.py`** reads/writes when **`SIMPLEMEM_BACKEND=local`**. Commit when the CLI updates it. |
| **`wiki/memories/simplemem-archive.md`** (was `mckenna-derby wiki/…`) | **Human-readable mirror** for Obsidian graph, wikilinks, and agents that live in the vault. |

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

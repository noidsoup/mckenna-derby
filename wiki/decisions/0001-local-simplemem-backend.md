---
title: Local SimpleMem backend
type: decision
summary: SimpleMem uses a local JSON store in docs/simplemem/ that is committed with the repo.
status: active
created: 2026-07-30
updated: 2026-10-10
last_verified: 2026-10-10
sources: []
tags: [simplemem, memory, ai]
aliases: [0001, simplemem local]
---
# Local SimpleMem backend

## Status

Accepted (2026-07-08)

## Context

AI assistants need durable session memory without cloud tokens or external dependencies. The project was bootstrapped for AI-first development with SimpleMem integration.

## Decision

Use SimpleMem with **`SIMPLEMEM_BACKEND=local`** only. Store committed JSON at **`docs/simplemem/memories.json`**. Namespace: **`mckenna-derby`**. Commit the store when memories change.

## Consequences

- Memories travel with the repo; no cloud API keys required.
- Wiki mirror at [[simplemem-archive]] for Obsidian graph and human reading.
- Same privacy rules: no secrets, API keys, or PII (see `.claude/rules/simplemem.md`).

## Related

- [[simplemem-in-wiki]]
- [[simplemem-archive]]
- [[documentation-in-repo]]
- [[0002-preregistered-primary-analysis]]

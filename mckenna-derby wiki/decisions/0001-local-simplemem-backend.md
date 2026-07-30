---
title: Local SimpleMem backend
type: decision
created: 2026-07-30
updated: 2026-07-30
tags: [simplemem, memory, ai]
aliases: [0001, simplemem local]
sources: []
status: accepted
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
- Same privacy rules: no secrets, API keys, or PII (see `.cursor/rules/simplemem.mdc`).

## Related

- [[simplemem-in-wiki]]
- [[simplemem-archive]]
- [[documentation-in-repo]]
- [[0002-preregistered-primary-analysis]]

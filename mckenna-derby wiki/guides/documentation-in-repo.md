---
title: Documentation in the repo vs this wiki
type: guide
created: 2026-07-30
updated: 2026-07-30
tags: [documentation, onboarding]
status: active
---

# Documentation in the repo vs this wiki

This vault (**`mckenna-derby wiki/`**) holds **compiled, linked knowledge** for humans and LLMs (entities, concepts, ADRs, runbooks). It does not replace every markdown file at the repo root.

## Canonical repo docs (live outside the vault)

| Location | Role |
|----------|------|
| `AGENTS.md` | Always-on agent index: stack, frozen core, SimpleMem, commands. |
| `AI_RUNBOOK.md` | Commands, project structure, real-data workflow, troubleshooting. |
| `README.md` | Human overview, hypothesis, quick start, honest expectations. |
| `AI_SESSION_MEMORY.md` | Dated session handoff log (append on significant work). |
| `MEMORY.md` | Rolling two-section summary (current + previous session). |
| `docs/simplemem/memories.json` | **SimpleMem** local store. **Wiki mirror:** [[simplemem-archive]]. |
| `docs/` | SimpleMem store and any future docs — **not deleted** when wiki is built. |

## When to add to the wiki

- Cross-cutting **decisions** → `decisions/`
- **How-tos** that outgrow a single README section → `guides/`
- **Systems and modules** (package, dashboard, LanceDB) → `entities/` and `concepts/`

## Related

- [[SCHEMA]]
- [[mckenna-derby-package]]
- [[simplemem-in-wiki]]
- [[index]]

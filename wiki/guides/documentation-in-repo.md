---
title: Documentation in the repo vs this wiki
type: guide
summary: Which repo file holds what (AGENTS, runbook, README, session memory, SimpleMem) versus this wiki.
status: active
created: 2026-07-30
updated: 2026-10-19
last_verified: 2026-10-19
tags: [documentation, onboarding]
---
# Documentation in the repo vs this wiki

This wiki (**`wiki/`**, called `mckenna-derby wiki/` until 2026-10-19) holds **compiled, linked knowledge** for humans and LLMs (entities, concepts, ADRs, runbooks). It does not replace every markdown file at the repo root.

## Canonical repo docs (live outside the vault)

| Location | Role |
|----------|------|
| `AGENTS.md` | Always-on agent index: stack, frozen core, SimpleMem, commands. |
| `AI_RUNBOOK.md` | Commands, project structure, real-data workflow, troubleshooting. |
| `README.md` | Human overview, hypothesis, quick start, honest expectations. |
| `AI_SESSION_MEMORY.md` | Dated session handoff log (append on significant work). |
| `MEMORY.md` | Rolling two-section summary (current + previous session). |
| `docs/simplemem/memories.json` | **SimpleMem** local store. The wiki mirror [[simplemem-archive]] is archived (frozen at 2026-07-09). |
| `docs/FREE_DATASETS.md` | Free dataset survey behind [[bundled-datasets]]. |
| `DEPLOY_STREAMLIT.md` | Streamlit Community Cloud deploy steps. |
| `output/REAL_DATA_RESULTS.md` | The one committed output: the real-data run ([[real-data-results-2026-07-09]]). |
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

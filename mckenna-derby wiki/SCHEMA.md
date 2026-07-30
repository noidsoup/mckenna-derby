# Wiki Schema

> This file tells the LLM how to maintain this wiki. Read it at the start of every session that touches wiki pages.

## Project

- **Name**: McKenna Derby
- **Domain**: Python research project testing whether horse-racing novelty (surprisal under market odds) correlates with Terence McKenna's Timewave Zero, and whether timewave-filtered trifecta backtests beat random timing. Stack: `mckenna_derby` package, pandas/SciPy, pytest golden tests, Streamlit dashboard, SimpleMem local memory.

## Directory structure

The vault folder at the project root is **`mckenna-derby wiki/`** (repository folder basename `mckenna-derby`, a space, then `wiki`) — not bare `wiki/`.

```
mckenna-derby wiki/
├── SCHEMA.md          ← you are here (LLM instructions)
├── index.md           ← content catalog, organized by type
├── log.md             ← chronological operations log
├── sources/           ← summaries of ingested documents
├── entities/          ← concrete things (tools, services, APIs, tables, configs)
├── concepts/          ← patterns, principles, architectural ideas
├── decisions/         ← architecture decision records (ADRs)
├── guides/            ← how-tos, runbooks, procedures
├── memories/          ← SimpleMem mirror + how-to
└── assets/            ← images, diagrams, attachments
```

## Page conventions

### Filenames

- **Kebab-case**, lowercase: `novelty-surprisal-scoring.md`, `prereg-json.md`
- Singular nouns for entities: `streamlit-dashboard.md` not `streamlit-dashboards.md`
- Verb-noun for guides: `run-analysis-pipeline.md`
- Decisions use numbered prefix: `0001-local-simplemem-backend.md`

### Frontmatter

Every page MUST have YAML frontmatter:

```yaml
---
title: Human-Readable Page Title
type: source | entity | concept | decision | guide
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [relevant, tags]
aliases: [alternate-name, abbreviation]
sources: ["[[source-page]]"]
status: active | draft | superseded | archived
---
```

### Links

Use Obsidian-style wikilinks exclusively:

- `[[page-name]]` for standard links
- `[[page-name|display text]]` for aliased links
- `[[page-name#section]]` for section links
- Never use markdown-style `[text](url)` for internal wiki links (reserve for external URLs)

### Page structure

Every page follows this skeleton:

```markdown
---
(frontmatter)
---

# Title

One-paragraph summary of what this page covers.

## Content sections
(varies by page type)

## Related
- [[linked-page-1]]
- [[linked-page-2]]
```

## Page types

### Source (`sources/`)

Summary of an ingested document. Key points, detailed notes, entities and concepts mentioned.

### Entity (`entities/`)

A concrete thing: module, config, CLI, data source, tool.

### Concept (`concepts/`)

A pattern, principle, or statistical idea (novelty scoring, frozen core, beta assumption).

### Decision (`decisions/`)

ADR. Filename: `NNNN-short-title.md`.

### Guide (`guides/`)

How-to or runbook.

## Operations

### Obsidian (human viewer)

Open the folder **`mckenna-derby wiki/`** as a vault (Obsidian → Open folder as vault). Graph view and backlinks work with wikilinks.

### Ingest

When the user provides a new source: create `sources/…`, update entities/concepts/decisions/guides, refresh `index.md`, append `log.md`.

### Ingest existing docs

Migrate from repo **`docs/`** in batches; synthesize; do **not** delete original `docs/` without human sign-off.

### Query

Read `index.md`, then relevant pages; answer with `[[wikilinks]]`; offer to file synthesis as new pages.

## Style rules

- Clear, direct prose. Prefer concrete paths, commands, and module names.
- Use McKenna Derby terminology consistently (novelty, timewave, takeout, prereg, frozen core).
- Update `updated` in frontmatter when editing a page.

## Relationship to other project files

- **`docs/`**: SimpleMem store at `docs/simplemem/memories.json`; not deleted when wiki is built.
- **`memories/simplemem-archive.md`**: Human-readable mirror of SimpleMem entries.
- **AI_SESSION_MEMORY.md**: Session breadcrumbs; wiki is compiled long-form knowledge.
- **AI_RUNBOOK.md**: Operations; mirrored in `guides/`.
- **AGENTS.md**: Agent index at repo root; complements this SCHEMA.
- **SimpleMem**: Short recall; wiki is structured narrative.

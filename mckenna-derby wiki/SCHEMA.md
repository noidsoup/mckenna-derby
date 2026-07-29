# Wiki Schema

> This file tells the LLM how to maintain this wiki. Read it at the start of every session that touches wiki pages.

## Project

- **Name**: <PROJECT NAME>
- **Domain**: <one or two sentences: what this project is, its stack, where it runs>

## Directory structure

The vault folder at the project root is **`<repo-folder-name> wiki/`** (repository folder basename + space + `wiki`) — not bare `wiki/`.

```
<repo> wiki/
├── SCHEMA.md          ← you are here (LLM instructions)
├── index.md           ← content catalog, organized by type
├── log.md             ← chronological operations log
├── sources/           ← summaries of ingested documents
├── entities/          ← concrete things (tools, services, APIs, tables, configs)
├── concepts/          ← patterns, principles, architectural ideas
├── decisions/         ← architecture decision records (ADRs)
├── guides/            ← how-tos, runbooks, procedures
├── memories/          ← session-memory mirrors / archives
└── assets/            ← images, diagrams, attachments
```

## Page conventions

### Filenames

- **Kebab-case**, lowercase: `api-rate-limiting.md`, `postgres-connection-pool.md`
- Singular nouns for entities: `redis-cache.md` not `redis-caches.md`
- Verb-noun for guides: `deploy-to-production.md`, `rotate-api-keys.md`
- Decisions use numbered prefix: `0001-use-postgres-over-mysql.md`

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

Summary of an ingested document, article, file, or conversation.

- **Key points** (bulleted takeaways)
- **Detailed notes**
- **Entities mentioned** — `[[wikilinks]]`
- **Concepts discussed** — `[[wikilinks]]`

### Entity (`entities/`)

A concrete thing: tool, service, API, library, database, config.

- **What it is** / **How it's used in this project** / **Key details** / **Related**

### Concept (`concepts/`)

A pattern, principle, or architectural idea.

- **Definition** / **Application here** / **Tradeoffs** / **Related**

### Decision (`decisions/`)

ADR. Filename: `NNNN-short-title.md`.

- **Status** / **Context** / **Decision** / **Consequences** / **Related**

### Guide (`guides/`)

How-to or runbook.

- **Prerequisites** / **Steps** / **Troubleshooting** / **Related**

## Operations

### Obsidian (human viewer)

Open the folder **`<repo> wiki/`** as a vault (Obsidian → Open folder as vault). Graph view and backlinks work with wikilinks.

### Ingest

When the user provides a new source: create `sources/…`, update entities/concepts/decisions/guides, refresh `index.md`, append `log.md`.

### Ingest existing docs

Migrate from repo **`docs/`** in batches; synthesize; do **not** delete original `docs/` without human sign-off.

### Query

Read `index.md`, then relevant pages; answer with `[[wikilinks]]`; offer to file synthesis as new pages.

### Lint

Orphans, dead links, index drift, stale frontmatter, thin pages — report as checklist; fix with user approval.

## Style rules

- Clear, direct prose. Prefer concrete paths, commands, and versions.
- Use project terminology consistently.
- Update `updated` in frontmatter when editing a page.

## Relationship to other project files

- **`docs/`**: Raw documentation; ingest into `sources/` + derived pages. Binaries stay in `docs/`.
- **AI_SESSION_MEMORY.md**: Session breadcrumbs; wiki is compiled long-form knowledge.
- **AI_RUNBOOK.md** (if present): Operations; may become `guides/` pages.
- **AGENTS.md**: Agent index at repo root; complements this SCHEMA.

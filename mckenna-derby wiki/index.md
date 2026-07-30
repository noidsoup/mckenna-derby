---
title: Wiki Index
type: index
created: 2026-07-30
updated: 2026-07-30
---

# McKenna Derby Wiki

> Content catalog. The LLM reads this first when answering queries. Conventions: [[SCHEMA]].

## Session memories (SimpleMem)

| Page | Purpose |
|------|---------|
| [[simplemem-in-wiki]] | Where **`docs/simplemem/memories.json`** and the wiki archive relate. |
| [[simplemem-archive]] | Full text of committed SimpleMem entries (Obsidian-friendly). |

## Sources

| Page | Summary | Date |
|------|---------|------|
| [[readme-project-overview]] | Hypothesis, pipeline stages, McKenna Engine, honest expectations | 2026-07-30 |

## Entities

| Page | What it is |
|------|------------|
| [[mckenna-derby-package]] | This repo: Python package, CLI, tests, frozen core modules. |
| [[prereg-json]] | Pre-registered primary analysis parameters (immutable after first real-data run). |
| [[streamlit-dashboard]] | Interactive Streamlit + Plotly UI (`dashboard.py`). |
| [[lancedb-project-knowledge-search]] | Local offline semantic search over repo docs and rules. |

## Concepts

| Page | Summary |
|------|---------|
| [[novelty-surprisal-scoring]] | Daily race surprisal under Harville odds; z-normalized by field size. |
| [[timewave-zero-comparison]] | Pearson/Spearman + circular-shift permutation test vs McKenna wave. |
| [[frozen-statistical-core]] | `timewave.py`, `novelty.py`, `compare.py` — golden-test frozen. |
| [[mckenna-engine-selective-betting]] | Resonance gate, I Ching selector, beta pool-bias assumption. |

## Decisions

| # | Decision | Status |
|---|----------|--------|
| [[0001-local-simplemem-backend]] | SimpleMem local JSON in `docs/simplemem/` travels with repo | Accepted |
| [[0002-preregistered-primary-analysis]] | Primary params locked in `prereg.json` after first real-data run | Accepted |

## Guides

| Page | Purpose |
|------|---------|
| [[documentation-in-repo]] | AGENTS, runbook, `docs/` vs vault; ingest note. |
| [[run-analysis-pipeline]] | Install, pytest, CLI analysis, dashboard, real HK data. |

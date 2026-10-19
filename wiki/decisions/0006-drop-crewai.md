---
title: Drop the unused CrewAI subproject
type: decision
summary: PR #1 deleted crewai/ (never wired in, needed Python 3.10+ and an OpenAI key) and fixed audit bugs in novelty z-scores and the dashboard gate.
status: active
created: 2026-10-19
updated: 2026-10-19
last_verified: 2026-10-19
sources: ["PR #1", "commit d9acaa8"]
tags: [cleanup, crewai, audit]
---

# Drop the unused CrewAI subproject

## Status

**Active.** Merged 2026-07-09 as PR #1 (`fix/audit-recommendations-and-remove-crewai`).

## Context

A `crewai/` subproject needed its own Python 3.10+ venv and `OPENAI_API_KEY` but was never wired into the analysis pipeline. The main package targets Python 3.9 and Streamlit Community Cloud.

## Decision

- `git rm -r crewai/` and remove every CrewAI reference from AGENTS.md, AI_RUNBOOK.md and Context7 notes. Planning goes through the global plan-and-implement skill instead.
- Same PR, audit fixes: single-race `n_runners` buckets now give a NaN z-score instead of 0 (it was silently leaking into the daily mean); the dashboard's resonance gate used a hard-coded 80th percentile instead of `threshold_pct`. Both have regression tests.

## Consequences

- Do not reintroduce CrewAI (also a standing rule in Nicholas's global instructions).
- Some SimpleMem entries from the CrewAI era were later dropped from the working-tree store (wiki log, 2026-09-12).

## Related

- [[frozen-statistical-core]]
- [[streamlit-dashboard]]

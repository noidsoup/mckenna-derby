---
title: Novelty surprisal scoring
type: concept
summary: Daily race surprisal (-log2 P) under Harville trifecta odds, z-normalized by field size.
status: active
created: 2026-07-30
updated: 2026-07-30
last_verified: 2026-07-30
sources: ["[[readme-project-overview]]"]
tags: [novelty, surprisal, harville, statistics]
aliases: [novelty scoring, surprisal]
---
# Novelty surprisal scoring

## Definition

**Novelty** measures how surprising a race outcome was relative to the betting market's implied probabilities. Each race gets a surprisal score: `-log2 P(actual outcome)` using odds-implied probabilities via the **Harville model** for the exact 1-2-3 trifecta order. A winning favorite scores low; a longshot trifecta scores high.

## Application here

Implemented in `mckenna_derby/novelty.py` (**frozen** — see [[frozen-statistical-core]]). Scores are z-normalized by field size and averaged into a **daily series** used for correlation against the timewave and for backtest gating.

## Tradeoffs

- Harville assumes independence structure from win odds; real pools deviate (favorite-longshot bias).
- Synthetic demo data is market-calibrated by construction — novelty carries no timewave signal there (honest null).
- For credible backtests, prefer real `trifecta_payout` dividends over modeled parimutuel payouts.

## Related

- [[timewave-zero-comparison]]
- [[frozen-statistical-core]]
- [[mckenna-derby-package]]
- [[readme-project-overview]]

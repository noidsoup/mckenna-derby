---
title: McKenna Engine selective betting
type: concept
summary: Resonance gate, I Ching ticket selector and the beta pool-bias assumption behind any positive ROI.
status: active
created: 2026-07-30
updated: 2026-07-30
last_verified: 2026-07-30
sources: ["[[readme-project-overview]]"]
tags: [mckenna-engine, backtest, beta, iching]
aliases: [mckenna engine, selective betting, beta assumption]
---
# McKenna Engine selective betting

## Definition

`mckenna_derby/mckenna_engine.py` layers a **selective betting engine** on the novelty pipeline: buy only positive-EV trifecta combos, optionally gated by a McKenna-flavored timing signal, with reproducible ticket selection.

## Application here

Three components:

1. **Fractal resonance** (`RollingTimewave`) — weighted echo of past novelty at lags 1, 64, 64² days (wave-factor-64 hierarchy). Strictly causal; tested for lookahead.
2. **I Ching ticket selector** (`IChingSelector`) — three-coin hexagram casting seeds RNG when more combos qualify than the per-race ticket cap.
3. **Selective backtest** (`selective_backtest`) — Harville pricing, pool payout model `ticket · (1 − takeout) / pool_prob` where `pool_prob ∝ harville_prob^beta`.

CLI: `python run_mckenna.py --beta 1.0` (fair pool → zero selective bets).

## Tradeoffs — the beta assumption

| `beta` | Meaning |
|--------|---------|
| `1.0` | Fair pool — every combo EV = −takeout; selective strategy places **zero bets** |
| `> 1` | Favorites overbet — longshots underpriced → modeled +EV |
| `< 1` | Reverse bias |

Any positive ROI at `beta ≠ 1` is **conditional** on that pool bias existing at that magnitude. Estimate beta from real trifecta dividends first. On synthetic data the resonance gate carries no real information.

## Related

- [[novelty-surprisal-scoring]]
- [[streamlit-dashboard]]
- [[mckenna-derby-package]]
- [[readme-project-overview]]

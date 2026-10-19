---
title: Bundled datasets
type: entity
summary: hk_runners.csv (locked default, real win/place, no trifecta) and uk_runners.csv (exploratory, no dividends) ship in the package.
status: active
created: 2026-10-19
updated: 2026-10-19
last_verified: 2026-10-19
sources: [mckenna_derby/datasets/README.md, docs/FREE_DATASETS.md, AI_SESSION_MEMORY.md]
tags: [data, datasets, dividends]
---

# Bundled datasets

Two processed CSVs ship inside the package so the CLI, tests and the Streamlit Cloud app work without a Kaggle token (`mckenna_derby/datasets/README.md`).

| File | Source | Races / dates | Dividends | Role |
|---|---|---|---|---|
| `hk_runners.csv` (~2 MB) | Kaggle `gdaley/hkracing` | ~6,157 races, 1997-06-02 → 2005-08-28 | Real `win_payout` / `place_payout` per $1; **no trifecta** | Default; the locked primary claim |
| `uk_runners.csv` (~16 MB) | Kaggle `hwaitt/horse-racing` | ~34,449 races, 2008-01-01 → 2012-12-19 | None; odds from `decimalPrice` (1/p) | Exploratory only ([[0003-uk-exploratory-slice]]) |

## Facts that matter

- **No free source has ordered exotic dividends** for the same races. The HK dump has only win/place (published per $10, converted to per $1); the other local dumps lack them too. So trifecta settlement is **modeled** everywhere, and cash trifecta claims are blocked (`AI_SESSION_MEMORY.md`, 2026-07-09 "Exotic dividends upgrade (partial)").
- A companion exotic CSV can be merged with `scripts/build_bundled_data.py --exotics` (schema: `exotic_dividends.example.csv`). Real `trifecta_payout` is preferred over the model when present.
- Raw downloads (`rawdata/`, `rawdata-*`) are gitignored; the full UK raw is ~725 MB.
- UK favorite flat win ROI: −2.4% in `docs/FREE_DATASETS.md`, −3.4% in the session log — a market-ish null either way, not a strategy.
- Redistribution is subject to Kaggle terms and each dataset page.

## Related

- [[real-data-results-2026-07-09]]
- [[run-analysis-pipeline]]
- [[mckenna-derby-package]]

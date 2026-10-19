---
title: Real-data results (2026-07-09)
type: source
summary: The one pre-registered run on real Hong Kong data was null (r ≈ 0.008, permutation p = 0.936); UK exploratory null too.
status: active
created: 2026-10-19
updated: 2026-10-19
last_verified: 2026-10-19
sources: [output/REAL_DATA_RESULTS.md, "commit 9086d8c", prereg.json]
tags: [results, real-data, null]
---

# Real-data results (2026-07-09)

Digest of `output/REAL_DATA_RESULTS.md` (commit `9086d8c`) — the only file under the gitignored `output/` that is committed. It is the project's headline answer.

## Key points

- **Primary (pre-registered):** Kaggle `gdaley/hkracing`, 6,157 races, 682 race days, 1997-06-02 → 2005-08-28 (all before the 2012-12-21 zero date). Kelley set: Spearman r ≈ 0.008, **permutation p = 0.936**. The prediction (r < 0, p < 0.05) is **not supported**.
- `prereg.json` was unchanged by the run.
- **All four number sets** (Bonferroni ×4): none survives; Sheliak's r = −0.025 has permutation p = 0.684.
- **Backtest** (modeled settlement only — the HK dump has no trifecta dividends): timewave-filtered 20% ROI −5.87% vs bet-every-race +1.95%. The +1.95% is a modeled-pool artifact, not cash.
- **UK exploratory** (`hwaitt/horse-racing`, 102,593 races, 1997–2012): r ≈ +0.005, permutation p = 0.796 — same null.
- Threshold sweep and lead-lag (strongest |r| = 0.012 at lag −24 days) are labeled exploratory / p-hacking hazards.

## Notes

- Downloads used `kagglehub`, because Python 3.9 cannot install Kaggle CLI ≥ 1.8. Token names only: `KAGGLE_TOKEN` / `KAGGLE_API_TOKEN` in `.env` (gitignored).
- `pytest` was 42 passed at the time; causal expanding-window thresholds had landed in `2ef1b0e` the minute before.

## Related

- [[prereg-json]]
- [[0002-preregistered-primary-analysis]]
- [[timewave-zero-comparison]]
- [[bundled-datasets]]

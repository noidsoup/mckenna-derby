# McKenna Derby — Real Data Results

**Run date:** 2026-07-09  
**Branch:** `main` (accuracy fixes already landed: causal expanding-window thresholds, actual-dividend settlement)  
**Pre-registration:** `prereg.json` (declared 2026-07-08) — **unchanged** after this run  
**Primary dataset:** `gdaley/hkracing` via Kaggle (`rawdata/`)

Auth note: `.env` provided a modern `KGAT_` API token (`KAGGLE_TOKEN`). Python 3.9 cannot install Kaggle CLI ≥1.8 (needs 3.11+), so downloads used `kagglehub` with `KAGGLE_API_TOKEN` / `~/.kaggle/access_token` (mode 600). No secrets are recorded here.

---

## Datasets downloaded

| Dataset | Local dir | Size on disk | Notes |
|---|---|---|---|
| **gdaley/hkracing** (primary) | `rawdata/` | 11.5 MB (2 files) | `races.csv` + `runs.csv`; win odds + finish positions |
| **hwaitt/horse-racing** | `rawdata-uk/` | 759.7 MB (63 files) | UK/Ireland; `decimalPrice` = implied win probability |
| **lantanacamara/hong-kong-horse-racing** | `rawdata-hk-2014-17/` | 8.8 MB | HK 2014–17; odds + finish; schema differs from gdaley |
| **jeffreymuller/hong-kong-horse-races-from-2013-to-2020** | `rawdata-hk-2013-20/` | 8.2 MB | HK 2013–20; odds + place; post–zero-date heavy |
| **bogdandoicin/horse-racing-results-2017-20** | `rawdata-results-2017-20/` | 3.3 MB | Semicolon CSV; odds + place; not wired to loader |

Skipped as too large / low priority for this pass: `deltaromeo/horse-racing-results-ukireland-2015-2025` (~1.1 GB compressed).

### Primary analysis sample (after validation)

| Field | Value |
|---|---|
| Source | `hkracing (rawdata/)` |
| Races | **6,157** |
| Runners | **77,024** |
| Date range | **1997-06-02 → 2005-08-28** |
| Days with races (novelty series) | **682** |
| Trifecta payouts | **None** — all settlement is **modeled** parimutuel |

All primary dates are before the Timewave Zero date (2012-12-21), so **no post-2012 mirrored extension** applies to this sample.

### Exploratory UK sample (not pre-registered)

Loaded with new `data.load_uk_racing`, filtered to the usable historical window:

| Field | Value |
|---|---|
| Source | `hwaitt/horse-racing` (`rawdata-uk/`) |
| Races | **102,593** |
| Runners | **1,032,364** |
| Date range | **1997-01-01 → 2012-12-19** |
| Days | **3,928** |
| Kelley Spearman r | **+0.0046** |
| Permutation p | **0.796** |
| Interpretation | Same null as HK — no meaningful novelty↔timewave link |

---

## Primary pre-registered analysis (VERBATIM)

From `output/report.md` / `run_analysis.py --hk rawdata/ --sweep --max-lag 30`:

- **number_set:** kelley  
- **n_days:** 682  
- **spearman_r:** 0.008041994839619846  
- **permutation_p:** 0.936  
- **interpretation:** No statistically meaningful relationship between race novelty and the timewave once autocorrelation is accounted for.  
- **pearson_r (naive):** 0.002648693991853142  
- **pearson_p (naive / uncorrected):** 0.9449544197454215  
- **spearman_p (naive / uncorrected):** 0.8339518787460684  

**Verdict:** Pre-registered prediction (Spearman r < 0 with permutation p < 0.05) is **not supported**. Result is a clear null.

---

## Exploratory: all number sets (Bonferroni ×4)

```
number_set  spearman_r  permutation_p  bonferroni_p
    kelley      0.0080         0.9360           1.0
   watkins      0.0001         1.0000           1.0
   sheliak     -0.0253         0.6840           1.0
   huangti      0.0341         0.7115           1.0
```

No set survives Bonferroni correction. Sheliak’s negative r is still consistent with noise (permutation p = 0.684).

---

## Backtest ROIs (buy every trifecta combination)

Day selection uses a **causal expanding-window** timewave percentile (no full-sample look-ahead). Accuracy-fix work is on `main` (`2ef1b0e`); `pytest` = **42 passed**.

| strategy | races | cost | P&L | ROI | profitable races |
|---|---|---|---|---|---|
| Timewave-filtered (20%) | 1,823 | $2,882,730 | $-169,151 | **-5.87%** | 18.8% |
| Bet every race | 6,157 | $9,740,148 | $+189,487 | **+1.95%** | 19.4% |

Payout sources: `{'modeled': 6157}`.

Timewave filtering **underperforms** betting every race on this sample. The +1.95% “bet every race” ROI under a modeled pool with takeout 0.22 is **not** a real edge — modeled payouts are Harville-consistent and expected ROI is −takeout by construction when the market is fair; the positive figure here is a finite-sample / model artifact, not cash.

### Exploratory threshold sweep (shape only — p-hacking hazard)

```
 threshold_pct  races   roi_pct
             5    519   -8.60
            10    998   -6.91
            15   1431   -9.24
            20   1823   -5.87
            30   2021   -5.46
            40   2206   -6.51
            50   2517   -0.85
            75   3156   -5.09
           100   5655   -0.51
```

### Exploratory lead-lag

Strongest |r| at lag −24 days (r = +0.0119) — still tiny and not confirmatory.

---

## McKenna engine

Command: `run_mckenna.py --hk rawdata/ --beta …`  
Same 6,157-race HK sample. Selection uses modeled EV; settlement would prefer actual `trifecta_payout` when present (none here).

### beta = 1.0 (fair-pool null)

| strategy | races | tickets | cost | payout | pnl | roi_pct |
|---|---|---|---|---|---|---|
| buy_all | 6157 | 9740148 | 9740148.0 | 9929635.06 | 189487.06 | 1.95 |
| selective_gated | 0 | 0 | 0.0 | 0.00 | 0.00 | NaN |
| selective | 0 | 0 | 0.0 | 0.00 | 0.00 | NaN |
| random_control | 0 | 0 | 0.0 | 0.00 | 0.00 | NaN |

As designed: with β = 1.0, no combo has positive modeled EV, so selective strategies place **zero** tickets.

### beta = 1.15 (assumed favorites-overbet bias — MODELED, not measured)

| strategy | races | tickets | cost | payout | pnl | roi_pct |
|---|---|---|---|---|---|---|
| buy_all | 6157 | 9740148 | 9740148.0 | 16701229.40 | 6961081.40 | 71.47 |
| selective_gated | 1102 | 55100 | 55100.0 | 82137.51 | 27037.51 | 49.07 |
| selective | 6156 | 307550 | 307550.0 | 438276.20 | 130726.20 | 42.51 |
| random_control | 1102 | 55100 | 55100.0 | 45083.21 | −10016.79 | −18.18 |

**Do not treat β = 1.15 ROIs as real money.** They are conditional on an assumed pool distortion. `selective_gated` beats `random_control` under that assumption, but without measured β from actual trifecta dividends this is a simulation, not evidence of an edge.

---

## Caveats

1. **Modeled vs actual trifecta payouts.** HK `gdaley/hkracing` has win/place odds only — no historical trifecta dividends. All P&L uses modeled parimutuel settlement. Credible economic conclusions need real dividends.
2. **Look-ahead.** Causal expanding-window selection is implemented and covered by tests (42/42 pass). Full-sample percentile look-ahead is **not** present in this run.
3. **Post-2012 mirroring.** Primary HK window ends 2005-08-28 — no mirrored timewave extension. UK exploratory run was capped at 2012-12-19 for the same reason. Secondary HK dumps that extend past the zero date were downloaded but not used for primary inference.
4. **Secondary schemas.** UK loader added (`load_uk_racing`). Other HK dumps (2013–20, 2014–17) are compatible in spirit (odds + finish) but use different column names and were not merged into the pre-registered path.
5. **Pre-registration.** Parameters were not retuned after seeing results.

---

## Commands used

```bash
# Auth via kagglehub + KAGGLE_API_TOKEN from .env (not legacy kaggle.json)
.venv/bin/python -c "… kagglehub.dataset_download('gdaley/hkracing') …"
.venv/bin/pytest -q   # 42 passed
.venv/bin/python run_analysis.py --hk rawdata/ --sweep --max-lag 30
.venv/bin/python run_mckenna.py --hk rawdata/ --beta 1.0
.venv/bin/python run_mckenna.py --hk rawdata/ --beta 1.15
./scripts/start-dashboard.sh
```

## Artifacts

- This file: `output/REAL_DATA_RESULTS.md`
- Pipeline report: `output/report.md`
- Plot: `output/novelty_vs_timewave.png`
- Race scores: `output/race_scores.csv`
- Engine table: `output/mckenna_engine.csv` (last write = β=1.15)

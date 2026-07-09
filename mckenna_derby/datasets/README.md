# Bundled race datasets

## `hk_runners.csv`

Processed Hong Kong Jockey Club races derived from the Kaggle dataset
[`gdaley/hkracing`](https://www.kaggle.com/datasets/gdaley/hkracing).

| Field | Value |
|-------|--------|
| Races | ~6,157 (after validation) |
| Date range | 1997-06-02 → 2005-08-28 |
| Required columns | `date`, `race_id`, `horse`, `decimal_odds`, `finish_position` |
| Real win/place | `win_payout`, `place_payout` (per $1 stake; NaN on non-paying rows) |
| Real trifecta | **Not available** in this Kaggle dump (column absent unless you merge a companion file) |

This file is the **default** data source for the dashboard and CLI so users do
not need a Kaggle token or CSV upload. Redistribution is subject to
[Kaggle Terms](https://www.kaggle.com/terms) and the dataset page.

### What the Kaggle dump actually contains

`rawdata/races.csv` has **win** and **place** combination + dividend columns
(published per $10; the build script converts to per $1). It does **not**
include trifecta, tierce, trio, quinella, or forecast dividends.

Alternate local dumps checked (`rawdata-hk-2013-20`, `rawdata-hk-2014-17`,
`rawdata-uk`, `rawdata-results-2017-20`) likewise lack ordered exotic
dividends usable for trifecta cash settlement on the same races.

### Rebuild from raw Kaggle download

```bash
kaggle datasets download -d gdaley/hkracing -p rawdata --unzip
python scripts/build_bundled_data.py
```

Raw `rawdata/` stays gitignored; only this processed CSV is committed.

### Attaching real exotic (trifecta/tierce) dividends when you get them

1. Obtain a race-level CSV with published ordered 1-2-3 dividends for the
   **same** `race_id` values as `gdaley/hkracing` (or remap IDs first).
2. Convert dividends to **per $1 stake** (HKJC often publishes per $10 —
   divide by 10).
3. Save as e.g. `rawdata/exotic_dividends.csv` with columns:

   | column | meaning |
   |--------|---------|
   | `race_id` | join key (required) |
   | `trifecta_payout` | ordered 1-2-3 dividend per $1 (preferred) |
   | `tierce_payout` | HK ordered 1-2-3 alias; copied to `trifecta_payout` if that column is missing |
   | `trio_payout` | any-order 1-2-3 (diagnostic only; not used by trifecta settlement) |

   See `exotic_dividends.example.csv` for a stub header.

4. Rebuild:

   ```bash
   python scripts/build_bundled_data.py --exotics rawdata/exotic_dividends.csv
   ```

5. Confirm: `trifecta_payout` is non-null on races; backtest
   `payout_source` counts should show `actual` for those races.

Commercial archives (e.g. paid HKJC dividend dumps) and HKJC result pages
publish Tierce/Trio; this repo does **not** scrape them. Until a companion
file is supplied, trifecta P&L remains **modeled** (expected ROI ≈ −takeout).

### Renavon Full Archive → companion CSV (recommended paid path)

Renavon [`hkjc_dividends`](https://renavon.com/data/hkjc/hkjc_dividends) Full
Archive (US$99, from **Jan 2001**) is the cleanest joinable source for the
**2001–2005** overlap with this bundle. It does **not** cover 1997–2000.

Exact remap steps (date + venue + race_no → Kaggle `race_id`):

See **`scripts/import_renavon_dividends.md`** and run:

```bash
python scripts/remap_renavon_dividends.py \
  --renavon rawdata/hkjc_dividends.csv.gz \
  --races rawdata/races.csv \
  --out rawdata/exotic_dividends.csv \
  --start 2001-01-01 --end 2005-08-28
python scripts/build_bundled_data.py --exotics rawdata/exotic_dividends.csv
```

Prefer Renavon `return_per_dollar` (already per $1). Free Renavon sample is
recent-only and will not match this date window.

# Import Renavon HKJC dividends into McKenna Derby

**Goal:** attach real Tierce (ordered 1-2-3) / Trio dividends for the
**2001-01-01 → 2005-08-28** overlap with the bundled Kaggle window.

**Does not cover 1997–2000.** Renavon Full Archive starts January 2001.
Those earlier races stay on modeled trifecta payouts.

## What to buy

| Product | URL | Price (public) | Years |
|---------|-----|----------------|-------|
| Renavon `hkjc_dividends` Full Archive | https://renavon.com/data/hkjc/hkjc_dividends | **US$99** one-time (gzipped CSV) | Jan 2001 – present |

Pass (US$49/mo, last 24 months) does **not** reach 2001–2005.
Free sample is last ~6 months only — useful for schema checks, not for the claim.

## Remap keys

| Renavon field | Kaggle `rawdata/races.csv` |
|---------------|----------------------------|
| `race_date` (date part) | `date` (`YYYY-MM-DD`) |
| `venue_code` (`ST` / `HV`) | `venue` |
| `race_number` | `race_no` |
| → join | `race_id` (integer) |

Renavon’s own `race_id` (`ST_YYYYMMDD_R01`) is **not** the Kaggle id.
Always join through date + venue + race number.

## Stake units

- Renavon `dividend` = payout on a **$10** stake (HKD).
- Renavon `return_per_dollar` = already **per $1** (prefer this).
- McKenna companion CSV and backtest expect **per $1**.
- Older HKJC HTML sometimes shows Tierce as `/$5.0` — Renavon’s
  `return_per_dollar` already normalizes; do not double-divide.

## Steps

1. Purchase Full Archive; download gzipped CSV (keep it under `rawdata/`,
   which is gitignored).

2. Remap to companion schema:

   ```bash
   python scripts/remap_renavon_dividends.py \
     --renavon rawdata/hkjc_dividends.csv.gz \
     --races rawdata/races.csv \
     --out rawdata/exotic_dividends.csv \
     --start 2001-01-01 --end 2005-08-28
   ```

3. Rebuild the bundled runners CSV:

   ```bash
   python scripts/build_bundled_data.py --exotics rawdata/exotic_dividends.csv
   ```

4. Spot-check ~10 races against [HKJC Local Results](https://racing.hkjc.com/racing/information/English/racing/LocalResults.aspx)
   (same date / course / race). Official pages are the validation source;
   this repo does **not** bulk-scrape them.

5. Re-run analysis / edge hunt. Label **1997–2000** as still modeled.
   Do not edit `prereg.json` after the first real-data run.

## Output schema (`exotic_dividends.csv`)

| column | meaning |
|--------|---------|
| `race_id` | Kaggle integer id (required) |
| `date` | optional, for humans |
| `trifecta_payout` | ordered 1-2-3 per $1 (from TIERCE) |
| `tierce_payout` | same as trifecta (alias) |
| `trio_payout` | any-order 1-2-3 (diagnostic only) |

See also `mckenna_derby/datasets/exotic_dividends.example.csv` and
`mckenna_derby/datasets/README.md`.

# Free race datasets hunt (2026-07-09)

Honest inventory of **free** horse-racing sources with at least race date,
win odds (or convertible implied probability), and finish position.
No paid feeds (Renavon Full Archive, Equibase purchases, etc.).

**Locked primary claim:** still Hong Kong bundled (`hk_runners.csv` /
`prereg.json`). Nothing here replaces that.

---

## What was wired

| Source | File | Size | How to select |
|--------|------|------|----------------|
| UK/Ireland exploratory | `mckenna_derby/datasets/uk_runners.csv` | ~34,449 races, 2008-01-01 → 2012-12-19 (~16 MB) | Dashboard → **Advanced options** → **UK/Ireland (free, exploratory)**; CLI: `python run_analysis.py --uk` |

- Loader: `load_bundled_uk()` / rebuild: `python scripts/build_bundled_uk.py`
- Upstream: Kaggle [`hwaitt/horse-racing`](https://www.kaggle.com/datasets/hwaitt/horse-racing) (local copy already in `rawdata-uk/`)
- Odds: `decimalPrice` implied win probability → decimal odds `1/p`
- Dividends: none (modeled trifecta settlement only)
- License: subject to [Kaggle Terms](https://www.kaggle.com/terms) + dataset page (uploader terms; treat as free-for-research with attribution)

### Exploratory smoke (not a McKenna edge claim)

On the bundled UK slice:

- Load OK: 34,449 races / 345,596 runners
- Favorite flat win ROI ≈ **−2.4%** (stake $1 on shortest-priced runner each race) — market-ish null, not a strategy tip
- Label: **exploratory**; do not treat as the locked HK primary result

---

## Local free data already on disk

| Path | Origin (best guess) | Rows / races | Years | date + odds + finish? | Notes |
|------|---------------------|--------------|-------|------------------------|-------|
| `rawdata/` | Kaggle `gdaley/hkracing` | 6,349 races / 79,447 runs | 1997–2005 | Yes | Already the HK default; has win/place dividends; **no** trifecta |
| `mckenna_derby/datasets/hk_runners.csv` | processed from above | ~6,157 races | 1997–2005 | Yes | **Default / locked** |
| `rawdata-uk/` | Kaggle `hwaitt/horse-racing` | ~years 1990–2020 yearly files (~725 MB raw) | 1990–2020 | Yes (via `decimalPrice`) | **Chosen** for bundled exploratory slice |
| `rawdata-hk-2013-20/` | HK scrape / Kaggle-style | 6,361 races / 80,320 perfs | 2013–2020 | Yes (`date`, `win_odds`, `place`) | Overlaps Timewave post-2012 mirror zone; not bundled (post zero-date) |
| `rawdata-hk-2014-17/` | Kaggle `lantanacamara/hong-kong-horse-racing` | 2,367 races / 30,189 horse rows | 2014–2017 | Yes | Smaller than UK; post-2012 |
| `rawdata-results-2017-20/` | multi-country results CSV (`;`-sep) | ~27k rows (messy encoding) | ~2018 | Partial (`Dato`, `Odds`, `Final place`) | Dirty parse; AU/NZ heavy; skipped |

All `rawdata*` paths are **gitignored**; only processed `datasets/*.csv` ship.

---

## Web / open candidates reviewed

| Candidate | Free? | date + odds + finish | Size | License note | Decision |
|-----------|-------|----------------------|------|--------------|----------|
| Kaggle `hwaitt/horse-racing` | Yes (Kaggle account) | Yes | Very large (1990–2020) | Kaggle + uploader terms | **Wired** (2008–2012 slice) |
| Kaggle `gdaley/hkracing` | Yes | Yes | ~6k races | Kaggle + uploader terms | Already default HK |
| Kaggle `lantanacamara/hong-kong-horse-racing` | Yes | Yes | ~1.5–2.4k races | Kaggle | Local as `rawdata-hk-2014-17`; skipped (smaller, post-2012) |
| GitHub `eprochasson/horserace_data` | Yes (scraped public sites) | Yes + some dividends | HK/SG seasons | No warranty; scrape provenance | Skipped (overlap with local HK 2013–20; license/provenance murkier) |
| Renavon HKJC dividends | **Paid** Full Archive | Dividends | 2001+ | Commercial | **Skipped** (out of scope for this free hunt) |
| Equibase / paid US charts | Paid | Varies | Large | Commercial | **Skipped** |

---

## What was skipped (and why)

- **Paid** Renavon / Equibase — user constraint: free only
- **Full** `rawdata-uk` 1990–2020 — too large to commit; loader still supports `load_uk_racing(rawdata-uk, start=…, end=…)` locally
- **HK 2013–20 / 2014–17** — free and loadable, but after Timewave zero date (mirrored extension flagged); smaller than UK slice
- **`rawdata-results-2017-20`** — encoding/parse issues; not clean enough to ship without a dedicated cleaner
- **Claiming McKenna edge** on UK — not done; smoke is a favorite-ROI null check only

---

## Rebuild / select cheat sheet

```bash
# Rebuild UK exploratory CSV from local Kaggle dump
python scripts/build_bundled_uk.py

# CLI exploratory run (does not change prereg.json)
python run_analysis.py --uk

# Dashboard: Advanced options → UK/Ireland (free, exploratory)
streamlit run dashboard.py
```

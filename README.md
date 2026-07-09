# McKenna Derby

Does horse-racing chaos line up with Terence McKenna's Timewave Zero?

This project builds a daily **novelty series** from historical horse-racing
results (surprisal of the actual outcome under the betting market's implied
probabilities), compares it statistically to McKenna's I Ching–derived
timewave, and backtests a **buy-every-trifecta-combination** strategy that
only fires on days the timewave predicts high novelty.

## How it works

1. **Novelty scoring** (`mckenna_derby/novelty.py`) — each race gets a
   surprisal score: `-log2 P(actual outcome)` using odds-implied
   probabilities (Harville model for the exact 1-2-3 order). A winning
   favorite scores low; a longshot trifecta scores high. Scores are
   z-normalized by field size and averaged into a daily series.
2. **Timewave Zero** (`mckenna_derby/timewave.py`) — a faithful Python port
   of Peter Meyer's public-domain algorithm, with all four canonical
   384-number sets (Kelley, Watkins, Sheliak, Huang Ti). Zero date
   2012-12-21; later dates use a mirrored extension (clearly flagged, since
   McKenna's wave is undefined after the zero point).
3. **Comparison** (`mckenna_derby/compare.py`) — Pearson/Spearman
   correlations plus a circular-shift permutation test that respects the
   autocorrelation in both series. McKenna's convention is low wave = high
   novelty, so his theory predicts a *negative* correlation.
4. **Backtest** (`mckenna_derby/backtest.py`) — buying all
   `n·(n−1)·(n−2)` trifecta permutations guarantees holding the winning
   ticket; the payout is modeled as a parimutuel pool with a configurable
   takeout (default 22%). Expected ROI without a timing edge is exactly
   −takeout, so the strategy only wins if the timewave filter genuinely
   finds days where outcomes are more chaotic than the pool priced in.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e . pytest && pytest -q   # verify the frozen core first
python run_analysis.py                 # bundled Hong Kong races (default)
python run_analysis.py --sweep --max-lag 30   # with exploratory sections
python run_analysis.py --synthetic     # market-calibrated null demo
```

Outputs land in `output/`: `race_scores.csv`, `report.md`, and `novelty_vs_timewave.png`
(three panels: daily novelty, the inverted timewave, cumulative backtest P&L).

Real Hong Kong races (1997–2005, ~6,157 races) ship in
`mckenna_derby/datasets/hk_runners.csv` — no Kaggle download or CSV upload
required.

## Dashboard

Interactive web UI (Streamlit):

```bash
pip install -e .
streamlit run dashboard.py
```

The dashboard defaults to the **bundled Hong Kong** dataset. Open **Advanced**
in the sidebar for a larger free **UK/Ireland** exploratory slice, a synthetic
null demo, or a custom CSV upload. Analysis defaults come from `prereg.json`;
you can override number set, threshold, and takeout for exploratory runs.
UK/Ireland is **not** the locked primary claim.

### Share on Streamlit Community Cloud

Deploy from the GitHub repo with an optional shared password for friends.
See **[DEPLOY_STREAMLIT.md](DEPLOY_STREAMLIT.md)** for step-by-step setup at
[share.streamlit.io](https://share.streamlit.io/). Bundled HK data works on
Cloud (no local `rawdata/` needed).

## Data sources

**Default:** packaged `load_bundled_hk()` — processed from Kaggle
[`gdaley/hkracing`](https://www.kaggle.com/datasets/gdaley/hkracing).

**Exploratory free:** packaged `load_bundled_uk()` — slice of Kaggle
[`hwaitt/horse-racing`](https://www.kaggle.com/datasets/hwaitt/horse-racing)
(~34k races, 2008–2012). CLI: `--uk`. See `docs/FREE_DATASETS.md`.

CLI flags: `--synthetic`, `--uk`, `--hk DIR` (raw Kaggle layout), `--csv FILE`,
`--sweep`, `--max-lag N`, `--start` / `--end` (synthetic range only). Primary
analysis params (number set, threshold, takeout, metric) come from
`prereg.json` — the CLI does not override them.

To **rebuild** the bundled CSV from a fresh Kaggle download:

```bash
kaggle datasets download -d gdaley/hkracing -p rawdata --unzip
python scripts/build_bundled_data.py
```

The bundled CSV includes real **win/place** dividends (`win_payout` /
`place_payout`, per $1). Kaggle `gdaley/hkracing` does **not** include
trifecta/tierce dividends. When you obtain them, merge with:

```bash
python scripts/build_bundled_data.py --exotics path/to/exotic_dividends.csv
```

(see `mckenna_derby/datasets/README.md`). Or add a `trifecta_payout` column
(dividend per $1 winning ticket, repeated on each row of the race) to a CSV
and load it with `--csv`; the backtest prefers actual dividends over the
modeled payout.

The primary analysis (number set, threshold, takeout) is fixed in
`prereg.json` and must not be edited after the first real-data run.

## McKenna Engine

`mckenna_derby/mckenna_engine.py` layers a selective betting engine on top of
the novelty pipeline, with three components:

1. **Fractal resonance signal** (`RollingTimewave`) — McKenna's fractal
   self-similarity idea applied to racing's own history instead of a fixed
   2012 zero date. Each day's resonance is a weighted echo of past novelty at
   lags 1, 64, and 64² days (the wave-factor-64 hierarchy from Timewave
   Zero), with weights decaying by 1/64 per level. Strictly causal — only
   past data — and tested for it.
2. **I Ching ticket selector** (`IChingSelector`) — hexagram casting via the
   classical three-coin method (six lines of three coins each; parity gives
   yin/yang) decides *which* trifecta combinations to buy when more combos
   qualify than the per-race ticket cap. The hexagram number seeds the
   sampling RNG, so everything is reproducible. (The hexagram-number mapping
   is a simplification of the King Wen sequence.)
3. **Selective backtest** (`selective_backtest`) — prices every trifecta
   permutation with Harville probabilities from the odds, models pool
   payouts as `ticket · (1 − takeout) / pool_prob` where
   `pool_prob ∝ harville_prob^beta`, buys only positive-EV combos, gates
   races by the resonance signal, and compares four strategies: buy-all,
   selective+gated, selective ungated, and a random-ticket control with the
   same ticket counts.

```bash
python run_mckenna.py --beta 1.0            # fair pool: expect zero selective bets
python run_mckenna.py --beta 1.15           # assumed favorites-overbet bias
# options: --beta --k-max --gate-pct --takeout --seed --hk DIR --csv FILE
```

The dashboard has a matching **McKenna Engine** section with sidebar
controls for beta, gate percentile, and ticket cap.

### The beta assumption (read this before believing any ROI)

`beta` describes how the pool distorts fair (Harville) prices:
`beta = 1.0` means the pool is fair — every combination then has expected
value exactly −takeout, and the selective strategy correctly places **zero
bets**. `beta > 1` means favorites are overbet, so longshot combinations are
underpriced and become +EV; `beta < 1` is the reverse. Any positive ROI at
`beta ≠ 1` is a *modeled* result conditional on that bias existing at that
magnitude in the real pool. The honest interpretation: **beta = 1 → no
edge**. The engine is a framework for exploiting pool bias *if it exists* —
estimate beta from real trifecta dividends first — with McKenna-flavored
timing (resonance gate) and selection (I Ching) layered on top. On synthetic
data the resonance gate carries no real information (the data is
market-calibrated), so gated-vs-ungated ROI differences there are noise.

## Honest expectations

- The synthetic demo is calibrated to the market by construction, so it
  should (and does) show **no** timewave correlation and roughly −takeout
  ROI — it validates the pipeline, not the hypothesis.
- Even with real data, buying every combination loses the takeout on
  average. Profit requires the timewave to genuinely predict *when* pools
  misprice chaos. The permutation test is there to keep us honest about
  whether any observed correlation is real or an artifact of two slow-moving
  wiggly lines.
- The payout model is an approximation; real trifecta pools deviate from
  Harville (favorite-longshot bias, pool-specific behavior). For a serious
  test, source historical trifecta payouts and replace `race_pnl`.

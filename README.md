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
python run_analysis.py                 # synthetic demo data (null hypothesis)
python run_analysis.py --sweep --max-lag 30   # with exploratory sections
```

Outputs land in `output/`: `race_scores.csv`, `report.md`, and `novelty_vs_timewave.png`
(three panels: daily novelty, the inverted timewave, cumulative backtest P&L).

## Dashboard

Interactive web UI (Streamlit):

```bash
pip install -e .
streamlit run dashboard.py
```

The dashboard lets you run analysis without the CLI: choose synthetic demo data,
Hong Kong data from `rawdata/` (if downloaded), or upload a CSV. Defaults come
from `prereg.json`; you can override number set, threshold, and takeout for
exploratory runs. Charts include daily novelty with rolling mean, inverted
timewave, cumulative P&L, correlation stats, all four number sets, and an
optional threshold sweep.

### Share on Streamlit Community Cloud

Deploy from the private GitHub repo with an optional shared password for friends.
See **[DEPLOY_STREAMLIT.md](DEPLOY_STREAMLIT.md)** for step-by-step setup at
[share.streamlit.io](https://share.streamlit.io/).

## Using real data

Get a Kaggle API token (`~/.kaggle/kaggle.json`), then:

```bash
kaggle datasets download -d gdaley/hkracing -p rawdata --unzip
python run_analysis.py --hk rawdata/
```

Other options: `--number-set {kelley,watkins,sheliak,huangti}`,
`--takeout 0.25`, `--threshold-pct 10` (bet only the most-novel N% of days).

The primary analysis (number set, threshold, takeout) is fixed in
`prereg.json` and must not be edited after the first real-data run. To use
real trifecta dividends, add a `trifecta_payout` column (dividend per $1
winning ticket, repeated on each row of the race) to a CSV and load it with
`--csv`; the backtest will prefer actual dividends over the modeled payout.

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

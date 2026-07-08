#!/usr/bin/env python3
"""Local web dashboard for McKenna Derby analysis.

Launch:
    streamlit run dashboard.py
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from mckenna_derby import backtest as bt
from mckenna_derby import compare, data, novelty

ROOT = Path(__file__).parent
PREREG_PATH = ROOT / "prereg.json"
HK_DIR = ROOT / "rawdata"
ALL_SETS = ["kelley", "watkins", "sheliak", "huangti"]


def _configured_password() -> str | None:
    try:
        value = st.secrets["dashboard"]["password"]
    except (KeyError, TypeError, FileNotFoundError):
        return None
    if not value:
        return None
    return str(value)


def require_auth() -> None:
    """Optional shared password (set in Streamlit secrets on Community Cloud)."""
    password = _configured_password()
    if password is None:
        return
    if st.session_state.get("authenticated"):
        return

    st.title("McKenna Derby")
    st.caption("Enter the shared password to open the dashboard.")
    entered = st.text_input("Password", type="password", key="auth_password")
    if st.button("Log in", type="primary"):
        if entered == password:
            st.session_state["authenticated"] = True
            st.rerun()
        st.error("Wrong password.")
    st.stop()


@st.cache_data
def load_prereg() -> dict:
    return json.loads(PREREG_PATH.read_text())


def run_pipeline(
    runners: pd.DataFrame,
    number_set: str,
    threshold_pct: float,
    takeout: float,
    metric: str,
    do_sweep: bool,
    max_lag: int,
) -> dict:
    scores = novelty.score_races(runners)
    daily = novelty.daily_novelty(scores, metric=metric)
    primary = compare.compare(daily, number_set=number_set)

    exploratory_rows = []
    for ns in ALL_SETS:
        r = primary if ns == number_set else compare.compare(daily, number_set=ns)
        exploratory_rows.append(
            {
                "number_set": ns,
                "spearman_r": round(r["spearman_r"], 4),
                "permutation_p": r["permutation_p"],
                "bonferroni_p": min(1.0, r["permutation_p"] * len(ALL_SETS)),
            }
        )
    exploratory = pd.DataFrame(exploratory_rows)

    tw = primary["timewave"]
    res = bt.backtest(
        scores, tw, novelty_threshold_pct=threshold_pct, takeout=takeout
    )
    sweep = (
        bt.threshold_sweep(scores, tw, takeout=takeout) if do_sweep else None
    )
    lag = (
        compare.lead_lag(daily, number_set, max_lag=max_lag)
        if max_lag > 0
        else None
    )
    return {
        "scores": scores,
        "daily": daily,
        "primary": primary,
        "exploratory": exploratory,
        "timewave": tw,
        "backtest": res,
        "sweep": sweep,
        "lag": lag,
    }


def plot_novelty_timewave_pnl(daily: pd.Series, tw: pd.Series,
                              per_race: pd.DataFrame, number_set: str) -> go.Figure:
    dates = pd.to_datetime(pd.Index(daily.index))
    rolling = daily.rolling(30, min_periods=5).mean()

    daily_pnl = per_race.groupby("day")["pnl"].sum()
    pnl_dates = pd.to_datetime(pd.Index(daily_pnl.index))
    cum_all = daily_pnl.cumsum()
    sel = per_race[per_race["selected"]].groupby("day")["pnl"].sum()
    cum_strat = sel.reindex(daily_pnl.index, fill_value=0.0).cumsum()

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06,
        subplot_titles=(
            "Daily horse-racing novelty (odds-implied surprisal)",
            f"McKenna Timewave Zero ({number_set}) — up = higher predicted novelty",
            "Buy-every-trifecta-combination backtest",
        ),
    )
    fig.add_trace(
        go.Scatter(x=dates, y=daily, mode="lines", name="Daily novelty",
                   line=dict(color="rgba(31,119,180,0.4)", width=1)),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=dates, y=rolling, mode="lines", name="30-day mean",
                   line=dict(color="rgb(31,119,180)", width=2)),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=dates, y=tw, mode="lines", name="Timewave (inverted)",
                   line=dict(color="rgb(148,103,189)", width=2)),
        row=2, col=1,
    )
    fig.add_trace(
        go.Scatter(x=pnl_dates, y=cum_all, mode="lines", name="Bet every race",
                   line=dict(color="rgb(214,39,40)", width=2)),
        row=3, col=1,
    )
    fig.add_trace(
        go.Scatter(x=pnl_dates, y=cum_strat, mode="lines", name="Timewave-filtered",
                   line=dict(color="rgb(44,160,44)", width=2)),
        row=3, col=1,
    )
    fig.update_yaxes(title_text="Race novelty (z)", row=1, col=1)
    fig.update_yaxes(title_text="Timewave (inverted)", row=2, col=1)
    fig.update_yaxes(title_text="Cumulative P&L ($)", row=3, col=1)
    fig.update_layout(height=900, showlegend=True, hovermode="x unified")
    return fig


def plot_sweep(sweep: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sweep["threshold_pct"], y=sweep["roi_pct"], mode="lines+markers",
        name="ROI %", line=dict(color="rgb(214,39,40)"),
    ))
    fig.update_layout(
        title="Threshold sweep (exploratory — shape only)",
        xaxis_title="Threshold percentile (low wave = bet)",
        yaxis_title="ROI %",
        height=400,
    )
    return fig


def main() -> None:
    st.set_page_config(page_title="McKenna Derby", layout="wide")
    require_auth()
    st.title("McKenna Derby Dashboard")
    st.caption(
        "Horse-racing novelty vs Terence McKenna's Timewave Zero — "
        "interactive analysis"
    )

    prereg = load_prereg()

    with st.sidebar:
        st.header("Data source")
        hk_available = HK_DIR.exists() and (HK_DIR / "races.csv").exists()
        source_options = ["Synthetic demo"]
        if hk_available:
            source_options.append("Hong Kong (rawdata/)")
        source_options.append("Upload CSV")
        source = st.radio("Source", source_options, index=0)

        uploaded = None
        if source == "Upload CSV":
            uploaded = st.file_uploader("Runner-level CSV", type=["csv"])

        st.header("Parameters")
        st.caption(f"Pre-registered defaults from prereg.json (declared {prereg['declared_on']})")
        number_set = st.selectbox(
            "Number set (primary)",
            ALL_SETS,
            index=ALL_SETS.index(prereg["primary_number_set"]),
        )
        threshold_pct = st.slider(
            "Timewave threshold % (low wave = bet)",
            5.0, 100.0, float(prereg["primary_threshold_pct"]), 5.0,
        )
        takeout = st.slider("Takeout", 0.10, 0.35, float(prereg["takeout"]), 0.01)
        metric = st.selectbox("Novelty metric", ["trifecta_novelty", "win_novelty"],
                              index=0 if prereg["metric"] == "trifecta_novelty" else 1)

        if source == "Synthetic demo":
            col1, col2 = st.columns(2)
            with col1:
                start = st.date_input("Start", dt.date(2010, 1, 1))
            with col2:
                end = st.date_input("End", dt.date(2010, 6, 30))
        else:
            start = end = None

        do_sweep = st.checkbox("Threshold sweep (exploratory)", value=True)
        max_lag = st.number_input("Lead-lag window (days, 0=off)", 0, 60, 10)

        run = st.button("Run analysis", type="primary")

    if not run:
        st.info("Configure options in the sidebar and click **Run analysis**.")
        if source == "Synthetic demo":
            st.markdown(
                "**Quick start:** defaults run ~6 months of synthetic data "
                "(market-calibrated null fixture)."
            )
        elif source == "Hong Kong (rawdata/)":
            st.markdown("HK Kaggle data detected in `rawdata/`.")
        return

    try:
        if source == "Synthetic demo":
            runners = data.synthetic_races(start, end)
            source_label = f"synthetic demo ({start} to {end})"
        elif source == "Hong Kong (rawdata/)":
            runners = data.load_hk_racing(HK_DIR)
            source_label = f"hkracing ({HK_DIR})"
        else:
            if uploaded is None:
                st.error("Please upload a CSV file.")
                return
            runners = data.load_generic_csv(uploaded)
            source_label = f"uploaded CSV ({uploaded.name})"
    except Exception as exc:
        st.error(f"Failed to load data: {exc}")
        return

    n_races = runners["race_id"].nunique()
    st.success(
        f"Loaded **{source_label}**: {n_races:,} races, {len(runners):,} runners, "
        f"{runners['date'].min().date()} to {runners['date'].max().date()}"
    )

    with st.spinner("Running pipeline ..."):
        result = run_pipeline(
            runners, number_set, threshold_pct, takeout, metric,
            do_sweep, int(max_lag),
        )

    primary = result["primary"]
    res = result["backtest"]

    st.subheader("Primary correlation (pre-registered analysis)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Spearman r", f"{primary['spearman_r']:+.4f}")
    c2.metric("Permutation p", f"{primary['permutation_p']:.4f}")
    c3.metric("Pearson r", f"{primary['pearson_r']:+.4f}")
    c4.metric("Days", f"{primary['n_days']:,}")
    st.write(primary["interpretation"])

    st.subheader("Time series & backtest")
    fig = plot_novelty_timewave_pnl(
        result["daily"], result["timewave"], res["per_race"], number_set
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Backtest summary")
    bt_cols = st.columns(2)
    for col, (label, key) in zip(bt_cols, [
        ("Timewave-filtered", "strategy"),
        ("Bet every race", "bet_every_race"),
    ]):
        s = res[key]
        with col:
            st.markdown(f"**{label}**")
            st.write(
                f"Races: {s['races']:,} | Cost: ${s['total_cost']:,.0f} | "
                f"P&L: ${s['total_pnl']:+,.0f} | ROI: {s['roi_pct']:+.2f}% | "
                f"Profitable races: {s['hit_profit_pct']:.1f}%"
            )
    src_counts = res["per_race"]["payout_source"].value_counts().to_dict()
    st.caption(
        f"Payout sources: {src_counts}. Modeled payouts have expected ROI ≈ -takeout."
    )

    st.subheader("Exploratory: all number sets (Bonferroni ×4)")
    st.dataframe(result["exploratory"], use_container_width=True, hide_index=True)

    if result["sweep"] is not None:
        st.subheader("Exploratory: threshold sweep")
        st.plotly_chart(plot_sweep(result["sweep"]), use_container_width=True)
        with st.expander("Sweep table"):
            st.dataframe(result["sweep"], use_container_width=True, hide_index=True)

    if result["lag"] is not None:
        lag = result["lag"]
        best = lag.loc[lag["spearman_r"].abs().idxmax()]
        st.subheader("Exploratory: lead-lag")
        st.write(
            f"Strongest |r| at lag **{int(best['lag_days'])}** days "
            f"(r = {best['spearman_r']:+.4f})"
        )
        with st.expander("Lead-lag table"):
            st.dataframe(lag, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()

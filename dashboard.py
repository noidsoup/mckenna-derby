#!/usr/bin/env python3
"""Local web dashboard for McKenna Derby analysis.

Launch:
    streamlit run dashboard.py
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from mckenna_derby import backtest as bt
from mckenna_derby import compare, data, novelty
from mckenna_derby.mckenna_engine import (
    IChingSelector,
    RollingTimewave,
    selective_backtest,
)

ROOT = Path(__file__).parent
PREREG_PATH = ROOT / "prereg.json"
HK_DIR = ROOT / "rawdata"
ALL_SETS = ["kelley", "watkins", "sheliak", "huangti"]
BETA_FRAMES = [1.0, 1.05, 1.10, 1.15, 1.20]
MAX_ANIM_FRAMES = 80


# ---------------------------------------------------------------------------
# Auth & config
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Animation helpers
# ---------------------------------------------------------------------------


def _subsample_indices(n: int, max_frames: int = MAX_ANIM_FRAMES) -> np.ndarray:
    if n <= 1:
        return np.array([0], dtype=int)
    cap = min(max_frames, n)
    return np.unique(np.linspace(0, n - 1, cap, dtype=int))


def _play_slider_menus(
    frame_labels: list[str],
    frame_duration: int = 80,
) -> tuple[list, dict]:
    """Build Plotly play/pause buttons + frame slider (no invalid slider props)."""
    steps = [
        {
            "args": [
                [label],
                {
                    "frame": {"duration": frame_duration, "redraw": True},
                    "mode": "immediate",
                    "transition": {"duration": 0},
                },
            ],
            "label": label,
            "method": "animate",
        }
        for label in frame_labels
    ]
    updatemenus = [
        {
            "type": "buttons",
            "showactive": False,
            "x": 0.05,
            "y": 1.12,
            "buttons": [
                {
                    "label": "Play",
                    "method": "animate",
                    "args": [
                        None,
                        {
                            "frame": {"duration": frame_duration, "redraw": True},
                            "fromcurrent": True,
                            "transition": {"duration": 0},
                        },
                    ],
                },
                {
                    "label": "Pause",
                    "method": "animate",
                    "args": [
                        [None],
                        {
                            "frame": {"duration": 0, "redraw": False},
                            "mode": "immediate",
                            "transition": {"duration": 0},
                        },
                    ],
                },
            ],
        }
    ]
    # layout.slider has no `xaxis` property — axis titles belong on the figure axes.
    sliders = [
        {
            "active": max(len(frame_labels) - 1, 0),
            "currentvalue": {"prefix": "Frame: "},
            "pad": {"t": 50},
            "steps": steps,
            "x": 0.1,
            "len": 0.85,
        }
    ]
    return updatemenus, sliders


def animate_novelty_timewave(
    daily: pd.Series, tw: pd.Series, max_frames: int = MAX_ANIM_FRAMES
) -> go.Figure:
    dates = pd.to_datetime(pd.Index(daily.index))
    # daily_novelty is already field-size z-scored; plot as-is (no second z-score).
    tw_inv = -tw
    idx = _subsample_indices(len(dates), max_frames)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(x=[], y=[], name="Daily novelty", line=dict(color="rgb(31,119,180)")),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=[], y=[], name="Timewave (inverted)",
            line=dict(color="rgb(148,103,189)", dash="dot"),
        ),
        secondary_y=True,
    )

    frames = []
    labels = []
    for i, end in enumerate(idx):
        sl = slice(0, int(end) + 1)
        label = str(dates[end].date())
        labels.append(label)
        frames.append(
            go.Frame(
                name=label,
                data=[
                    go.Scatter(x=dates[sl], y=daily.iloc[sl]),
                    go.Scatter(x=dates[sl], y=tw_inv.iloc[sl]),
                ],
                traces=[0, 1],
            )
        )

    fig.frames = frames
    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(title_text="Daily novelty", secondary_y=False)
    fig.update_yaxes(title_text="Timewave (inverted)", secondary_y=True)
    menus, sliders = _play_slider_menus(labels)
    fig.update_layout(
        title="Animated novelty + timewave timeline",
        height=480,
        hovermode="x unified",
        updatemenus=menus,
        sliders=sliders,
    )
    if labels:
        fig.update(data=list(frames[-1].data))
    return fig


def animate_cumulative_pnl(
    per_race: pd.DataFrame,
    mckenna_daily: pd.Series | None = None,
    max_frames: int = MAX_ANIM_FRAMES,
) -> go.Figure:
    pr = per_race.sort_values("date").reset_index(drop=True)
    idx = _subsample_indices(len(pr), max_frames)

    cum_all = pr["pnl"].cumsum()
    sel_mask = pr["selected"]
    cum_strat = pr["pnl"].where(sel_mask, 0.0).cumsum()

    mckenna_cum = None
    if mckenna_daily is not None and len(mckenna_daily) > 0:
        mckenna_cum = mckenna_daily.cumsum()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[], y=[], name="Bet every race", line=dict(color="rgb(214,39,40)")))
    fig.add_trace(
        go.Scatter(x=[], y=[], name="Timewave-filtered", line=dict(color="rgb(44,160,44)"))
    )
    if mckenna_cum is not None:
        fig.add_trace(
            go.Scatter(
                x=[], y=[], name="McKenna selective (gated)",
                line=dict(color="rgb(255,127,14)"),
            )
        )

    frames = []
    labels = []
    for end in idx:
        sl = slice(0, int(end) + 1)
        sub = pr.iloc[sl]
        label = str(sub["date"].iloc[-1].date())
        labels.append(label)
        frame_data = [
            go.Scatter(x=sub["date"], y=cum_all.iloc[sl]),
            go.Scatter(x=sub["date"], y=cum_strat.iloc[sl]),
        ]
        if mckenna_cum is not None:
            days = sub["day"]
            mc = mckenna_daily.reindex(days, fill_value=0.0).cumsum()
            frame_data.append(go.Scatter(x=sub["date"], y=mc.to_numpy()))
        frames.append(go.Frame(name=label, data=frame_data, traces=list(range(len(frame_data)))))

    fig.frames = frames
    menus, sliders = _play_slider_menus(labels)
    fig.update_layout(
        title="Animated cumulative P&L (race-by-race)",
        xaxis_title="Date",
        yaxis_title="Cumulative P&L ($)",
        height=480,
        hovermode="x unified",
        updatemenus=menus,
        sliders=sliders,
    )
    if frames:
        fig.update(data=list(frames[-1].data))
    return fig


def animate_resonance(
    resonance: pd.Series,
    gated_days: set,
    max_frames: int = MAX_ANIM_FRAMES,
) -> go.Figure:
    if resonance.empty:
        fig = go.Figure()
        fig.update_layout(title="Resonance signal (no data)", height=400)
        return fig

    dates = pd.to_datetime(pd.Index(resonance.index))
    vals = resonance.to_numpy()
    idx = _subsample_indices(len(dates), max_frames)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=[], y=[], name="RollingTimewave resonance", line=dict(color="rgb(148,103,189)"))
    )
    gate_dates = [pd.Timestamp(d) for d in gated_days if d in resonance.index]
    gate_y = [resonance.loc[d.date() if hasattr(d, "date") else d] for d in gate_dates]
    fig.add_trace(
        go.Scatter(
            x=gate_dates,
            y=gate_y,
            mode="markers",
            name="Gated betting days",
            marker=dict(color="rgb(214,39,40)", size=8, symbol="line-ns-open"),
        )
    )

    frames = []
    labels = []
    for end in idx:
        sl = slice(0, int(end) + 1)
        label = str(dates[end].date())
        labels.append(label)
        vis_gates = [d for d in gate_dates if d <= dates[end]]
        vis_y = [
            resonance.loc[d.date()] if d.date() in resonance.index else np.nan
            for d in vis_gates
        ]
        frames.append(
            go.Frame(
                name=label,
                data=[
                    go.Scatter(x=dates[sl], y=vals[sl]),
                    go.Scatter(x=vis_gates, y=vis_y, mode="markers"),
                ],
                traces=[0, 1],
            )
        )

    fig.frames = frames
    menus, sliders = _play_slider_menus(labels)
    fig.update_layout(
        title="Animated McKenna resonance signal",
        xaxis_title="Date",
        yaxis_title="Resonance",
        height=450,
        updatemenus=menus,
        sliders=sliders,
    )
    if frames:
        fig.update(data=list(frames[-1].data))
    return fig


def animate_novelty_distribution(
    scores: pd.DataFrame,
    metric: str = "trifecta_novelty",
    max_frames: int = MAX_ANIM_FRAMES,
) -> go.Figure:
    vals = scores[metric].dropna().to_numpy()
    if len(vals) == 0:
        fig = go.Figure()
        fig.update_layout(title="Novelty distribution (no data)", height=400)
        return fig

    idx = _subsample_indices(len(vals), max_frames)
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=[], name=metric, marker_color="rgb(31,119,180)", nbinsx=30))

    frames = []
    labels = []
    for i, end in enumerate(idx):
        n = int(end) + 1
        label = f"{n} races"
        labels.append(label)
        frames.append(
            go.Frame(
                name=label,
                data=[go.Histogram(x=vals[:n], nbinsx=30)],
                traces=[0],
            )
        )

    fig.frames = frames
    menus, sliders = _play_slider_menus(labels, frame_duration=100)
    fig.update_layout(
        title=f"Animated {metric} distribution",
        xaxis_title=metric,
        yaxis_title="Count",
        height=420,
        updatemenus=menus,
        sliders=sliders,
    )
    if frames:
        fig.update(data=list(frames[-1].data))
    return fig


def animate_lead_lag(lag: pd.DataFrame) -> go.Figure:
    idx = _subsample_indices(len(lag), MAX_ANIM_FRAMES)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=[], y=[], mode="lines+markers", name="Spearman r", line=dict(color="rgb(31,119,180)"))
    )

    frames = []
    labels = []
    for end in idx:
        sl = slice(0, int(end) + 1)
        sub = lag.iloc[sl]
        label = f"lag {int(sub['lag_days'].iloc[-1])}"
        labels.append(label)
        frames.append(
            go.Frame(
                name=label,
                data=[go.Scatter(x=sub["lag_days"], y=sub["spearman_r"], mode="lines+markers")],
                traces=[0],
            )
        )

    fig.frames = frames
    menus, sliders = _play_slider_menus(labels)
    fig.update_layout(
        title="Lead-lag: Spearman r vs lag days",
        xaxis_title="Lag (days)",
        yaxis_title="Spearman r",
        height=420,
        updatemenus=menus,
        sliders=sliders,
    )
    if frames:
        fig.update(data=list(frames[-1].data))
    return fig


def animate_roi_by_beta(
    runners: pd.DataFrame,
    gate_pct: float,
    k_max: int,
    takeout: float,
    seed: int,
    betas: list[float] = BETA_FRAMES,
) -> go.Figure:
    summaries = []
    for beta in betas:
        summary = selective_backtest(
            runners,
            beta=beta,
            gate_pct=gate_pct,
            k_max=k_max,
            takeout=takeout,
            seed=seed,
        )
        summaries.append((beta, summary))

    first = summaries[0][1].dropna(subset=["roi_pct"])
    fig = go.Figure()
    if not first.empty:
        fig.add_trace(
            go.Bar(
                x=first["strategy"],
                y=first["roi_pct"],
                marker_color=[
                    "rgb(44,160,44)" if v >= 0 else "rgb(214,39,40)"
                    for v in first["roi_pct"]
                ],
            )
        )

    frames = []
    for beta, summary in summaries:
        roi = summary.dropna(subset=["roi_pct"])
        if roi.empty:
            continue
        frames.append(
            go.Frame(
                name=f"β={beta:.2f}",
                data=[
                    go.Bar(
                        x=roi["strategy"],
                        y=roi["roi_pct"],
                        marker_color=[
                            "rgb(44,160,44)" if v >= 0 else "rgb(214,39,40)"
                            for v in roi["roi_pct"]
                        ],
                    )
                ],
                traces=[0],
            )
        )

    fig.frames = frames
    labels = [f.name for f in frames]
    menus, sliders = _play_slider_menus(labels, frame_duration=600)
    fig.update_layout(
        title="Animated ROI by strategy (vary pool bias β)",
        yaxis_title="ROI %",
        height=450,
        updatemenus=menus,
        sliders=sliders,
    )
    if frames:
        fig.update(data=list(frames[-1].data))
    return fig


def plot_sweep(sweep: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=sweep["threshold_pct"],
            y=sweep["roi_pct"],
            mode="lines+markers",
            name="ROI %",
            line=dict(color="rgb(214,39,40)"),
        )
    )
    fig.update_layout(
        title="Threshold sweep (exploratory — shape only)",
        xaxis_title="Threshold percentile (low wave = bet)",
        yaxis_title="ROI %",
        height=400,
    )
    return fig


# ---------------------------------------------------------------------------
# Pipeline & McKenna helpers
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def run_pipeline(
    runners: pd.DataFrame,
    number_set: str,
    threshold_pct: float,
    takeout: float,
    metric: str,
    do_sweep: bool,
    max_lag: int,
    seed: int,
    engine_gate_pct: float = 20.0,
) -> dict:
    scores = novelty.score_races(runners)
    daily = novelty.daily_novelty(scores, metric=metric)
    primary = compare.compare(daily, number_set=number_set, seed=seed)

    exploratory_rows = []
    for ns in ALL_SETS:
        r = (
            primary
            if ns == number_set
            else compare.compare(daily, number_set=ns, seed=seed)
        )
        exploratory_rows.append(
            {
                "number_set": ns,
                "pearson_r": round(r["pearson_r"], 4),
                "spearman_r": round(r["spearman_r"], 4),
                "permutation_p": r["permutation_p"],
                "bonferroni_p": min(1.0, r["permutation_p"] * len(ALL_SETS)),
            }
        )
    exploratory = pd.DataFrame(exploratory_rows)

    tw = primary["timewave"]
    res = bt.backtest(scores, tw, novelty_threshold_pct=threshold_pct, takeout=takeout)
    sweep = bt.threshold_sweep(scores, tw, takeout=takeout) if do_sweep else None
    lag = compare.lead_lag(daily, number_set, max_lag=max_lag) if max_lag > 0 else None

    from mckenna_derby.mckenna_engine import _compute_gated_days

    resonance = RollingTimewave().signal(daily)
    gated_days = _compute_gated_days(daily, engine_gate_pct, wave_factor=64, levels=3)

    return {
        "scores": scores,
        "daily": daily,
        "primary": primary,
        "exploratory": exploratory,
        "timewave": tw,
        "backtest": res,
        "sweep": sweep,
        "lag": lag,
        "resonance": resonance,
        "gated_days_default": gated_days,
    }


@st.cache_data(show_spinner=False)
def run_engine_summary(
    runners: pd.DataFrame,
    beta: float,
    gate_pct: float,
    k_max: int,
    takeout: float,
    seed: int,
) -> pd.DataFrame:
    return selective_backtest(
        runners,
        beta=beta,
        gate_pct=gate_pct,
        k_max=k_max,
        takeout=takeout,
        seed=seed,
    )


def mckenna_gated_daily_pnl(
    runners: pd.DataFrame,
    beta: float,
    gate_pct: float,
    k_max: int,
    takeout: float,
    seed: int,
) -> pd.Series:
    """Per-race P&L for selective_gated strategy (visualization only)."""
    from mckenna_derby.mckenna_engine import TICKET_PRICE, _harville_all
    from mckenna_derby.novelty import implied_probabilities

    from mckenna_derby.mckenna_engine import _compute_gated_days, _settlement_payout

    scores = novelty.score_races(runners)
    daily = novelty.daily_novelty(scores)
    resonance = RollingTimewave().signal(daily)
    gated_days = _compute_gated_days(daily, gate_pct, wave_factor=64, levels=3)

    iching = IChingSelector(seed=seed)
    ticket = TICKET_PRICE
    race_pnls: list[tuple[dt.date, float]] = []

    df = runners.sort_values(["date", "race_id"])
    for _, g in df.groupby("race_id", sort=False):
        g = g.sort_values("finish_position")
        p = implied_probabilities(g["decimal_odds"].to_numpy())
        fair = _harville_all(p)
        pool_w = fair ** beta
        pool = pool_w / pool_w.sum()
        payout = ticket * (1.0 - takeout) / pool
        ev = fair * payout - ticket
        winner = 0
        win_payout = _settlement_payout(g, float(payout[winner]), ticket)
        day = g["date"].iloc[0].date()

        qualifying = np.where(ev > 0.0)[0]
        if len(qualifying) > k_max:
            picked = iching.select_combinations(
                list(qualifying), k_max, weights=fair[qualifying] * ev[qualifying]
            )
            bought = np.array(picked)
        else:
            bought = qualifying

        pnl = 0.0
        if day in gated_days and len(bought) > 0:
            cost = len(bought) * ticket
            pay = win_payout if winner in set(bought.tolist()) else 0.0
            pnl = pay - cost
        race_pnls.append((day, pnl))

    if not race_pnls:
        return pd.Series(dtype=float)
    out = pd.Series({d: p for d, p in race_pnls})
    return out.groupby(level=0).sum()


def series_stats(s: pd.Series) -> dict:
    if s.empty:
        return {"mean": np.nan, "std": np.nan, "min": np.nan, "max": np.nan, "current": np.nan}
    return {
        "mean": float(s.mean()),
        "std": float(s.std(ddof=0)),
        "min": float(s.min()),
        "max": float(s.max()),
        "current": float(s.iloc[-1]),
    }


# ---------------------------------------------------------------------------
# UI sections
# ---------------------------------------------------------------------------


def render_sidebar(prereg: dict) -> dict | None:
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

        st.header("Pre-registration (prereg.json)")
        with st.expander("Frozen prereg settings", expanded=False):
            st.json(prereg)

        st.header("Run parameters")
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
        metric = st.selectbox(
            "Novelty metric",
            ["trifecta_novelty", "win_novelty"],
            index=0 if prereg["metric"] == "trifecta_novelty" else 1,
        )
        engine_seed = st.number_input("Random seed (I Ching)", 1, 99999, 1904)

        if source == "Synthetic demo":
            col1, col2 = st.columns(2)
            with col1:
                start = st.date_input("Start", dt.date(2010, 1, 1))
            with col2:
                end = st.date_input("End", dt.date(2010, 12, 31))
        else:
            start = end = None

        do_sweep = st.checkbox("Threshold sweep (exploratory)", value=True)
        max_lag = st.number_input("Lead-lag window (days, 0=off)", 0, 60, 10)

        st.header("McKenna Engine")
        run_engine = st.checkbox("Run McKenna Engine", value=True)
        engine_beta = st.slider(
            "Pool bias beta (ASSUMPTION; 1.0 = fair pool)",
            0.80, 1.50, 1.00, 0.05,
        )
        engine_gate_pct = st.slider("Resonance gate (top % of days)", 5.0, 100.0, 20.0, 5.0)
        engine_k_max = st.number_input("Max tickets per race (I Ching cap)", 1, 500, 50)

        run = st.button("Run Analysis", type="primary")

    if not run:
        return None

    return {
        "source": source,
        "uploaded": uploaded,
        "start": start,
        "end": end,
        "number_set": number_set,
        "threshold_pct": threshold_pct,
        "takeout": takeout,
        "metric": metric,
        "do_sweep": do_sweep,
        "max_lag": int(max_lag),
        "run_engine": run_engine,
        "engine_beta": float(engine_beta),
        "engine_gate_pct": float(engine_gate_pct),
        "engine_k_max": int(engine_k_max),
        "engine_seed": int(engine_seed),
    }


def load_runners(opts: dict) -> tuple[pd.DataFrame, str] | None:
    source = opts["source"]
    try:
        if source == "Synthetic demo":
            runners = data.synthetic_races(opts["start"], opts["end"])
            label = f"synthetic demo ({opts['start']} to {opts['end']})"
        elif source == "Hong Kong (rawdata/)":
            runners = data.load_hk_racing(HK_DIR)
            label = f"hkracing ({HK_DIR})"
        else:
            if opts["uploaded"] is None:
                st.error("Please upload a CSV file.")
                return None
            runners = data.load_generic_csv(opts["uploaded"])
            label = f"uploaded CSV ({opts['uploaded'].name})"
    except Exception as exc:
        st.error(f"Failed to load data: {exc}")
        return None
    return runners, label


def render_overview(state: dict) -> None:
    runners = state["runners"]
    result = state["result"]
    opts = state["opts"]
    primary = result["primary"]
    res = result["backtest"]
    daily = result["daily"]
    tw = result["timewave"]

    st.subheader("Overview")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Races", f"{runners['race_id'].nunique():,}")
    c2.metric("Runners", f"{len(runners):,}")
    c3.metric("Permutation p", f"{primary['permutation_p']:.4f}")
    c4.metric("Spearman r", f"{primary['spearman_r']:+.4f}")
    c5.metric("Days", f"{primary['n_days']:,}")

    with st.expander("All run settings & data summary", expanded=True):
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("Data source", state["source_label"])
        sc2.metric("Date range", f"{runners['date'].min().date()} → {runners['date'].max().date()}")
        sc3.metric("Number set", opts["number_set"])
        st.write(
            f"Threshold {opts['threshold_pct']}%, takeout {opts['takeout']:.0%}, "
            f"metric `{opts['metric']}`, seed {opts['engine_seed']}"
        )
        if state.get("engine_summary") is not None:
            best = state["engine_summary"].dropna(subset=["roi_pct"])
            if not best.empty:
                top = best.loc[best["roi_pct"].idxmax()]
                st.caption(
                    f"McKenna best strategy: **{top['strategy']}** "
                    f"(ROI {top['roi_pct']:+.2f}%)"
                )

    st.plotly_chart(
        animate_novelty_timewave(daily, tw),
        use_container_width=True,
        key="overview_timeline",
    )
    st.caption("Use **Play** or drag the slider to scrub through the timeline.")

    st.markdown("**Backtest at a glance**")
    bc1, bc2 = st.columns(2)
    s = res["strategy"]
    bc1.metric("Timewave-filtered", f"ROI {s['roi_pct']:+.2f}%", f"P&L ${s['total_pnl']:+,.0f}")
    s_all = res["bet_every_race"]
    bc2.metric("Bet every race", f"ROI {s_all['roi_pct']:+.2f}%", f"P&L ${s_all['total_pnl']:+,.0f}")


def render_novelty_timewave(state: dict) -> None:
    result = state["result"]
    opts = state["opts"]
    primary = result["primary"]
    daily = result["daily"]
    tw = result["timewave"]
    scores = result["scores"]

    st.subheader("Primary correlation (pre-registered)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Permutation p", f"{primary['permutation_p']:.4f}")
    c2.metric("Spearman r", f"{primary['spearman_r']:+.4f}")
    c3.metric("Days aligned", f"{primary['n_days']:,}")
    c4.metric("Naive Pearson p", f"{primary['pearson_p']:.4f}")
    st.caption(
        "Primary inference uses the circular-shift **permutation p**. "
        f"Naive (uncorrected) Spearman p = {primary['spearman_p']:.4f}; "
        f"naive Pearson p = {primary['pearson_p']:.4f}."
    )
    st.info(primary["interpretation"])

    st.subheader("Exploratory: all number sets (Bonferroni ×4)")
    st.dataframe(result["exploratory"], use_container_width=True, hide_index=True)

    st.subheader("Daily novelty statistics")
    dstat = series_stats(daily)
    dc1, dc2, dc3, dc4, dc5 = st.columns(5)
    dc1.metric("Mean", f"{dstat['mean']:.4f}")
    dc2.metric("Std", f"{dstat['std']:.4f}")
    dc3.metric("Min", f"{dstat['min']:.4f}")
    dc4.metric("Max", f"{dstat['max']:.4f}")
    dc5.metric("Current", f"{dstat['current']:.4f}")

    st.subheader("Timewave statistics (same dates)")
    tstat = series_stats(tw)
    tc1, tc2, tc3, tc4 = st.columns(4)
    tc1.metric("Mean", f"{tstat['mean']:.4f}")
    tc2.metric("Min", f"{tstat['min']:.4f}")
    tc3.metric("Max", f"{tstat['max']:.4f}")
    tc4.metric("Current", f"{tstat['current']:.4f}")

    resonance = result["resonance"]
    if not resonance.empty:
        st.subheader("RollingTimewave resonance statistics")
        rstat = series_stats(resonance)
        rc1, rc2, rc3, rc4, rc5 = st.columns(5)
        rc1.metric("Mean", f"{rstat['mean']:.4f}")
        rc2.metric("Std", f"{rstat['std']:.4f}")
        rc3.metric("Min", f"{rstat['min']:.4f}")
        rc4.metric("Max", f"{rstat['max']:.4f}")
        rc5.metric("Current", f"{rstat['current']:.4f}")

    st.plotly_chart(
        animate_novelty_timewave(daily, tw),
        use_container_width=True,
        key="novelty_timeline",
    )
    st.plotly_chart(
        animate_novelty_distribution(scores, metric=opts["metric"]),
        use_container_width=True,
        key="novelty_hist",
    )

    if result["lag"] is not None:
        lag = result["lag"]
        best = lag.loc[lag["spearman_r"].abs().idxmax()]
        st.subheader("Lead-lag (exploratory)")
        st.write(
            f"Strongest |r| at lag **{int(best['lag_days'])}** days "
            f"(r = {best['spearman_r']:+.4f})"
        )
        st.plotly_chart(animate_lead_lag(lag), use_container_width=True, key="lead_lag")
        with st.expander("Lead-lag table"):
            st.dataframe(lag, use_container_width=True, hide_index=True)

    with st.expander("Race-level scores (all columns)", expanded=False):
        display_cols = [
            c for c in scores.columns
            if c in scores.columns
        ]
        st.dataframe(scores[display_cols], use_container_width=True, hide_index=True)


def render_backtest(state: dict) -> None:
    result = state["result"]
    res = result["backtest"]
    mckenna_daily = state.get("mckenna_daily_pnl")

    st.subheader("Backtest summary")
    for label, key in [("Timewave-filtered", "strategy"), ("Bet every race", "bet_every_race")]:
        s = res[key]
        st.markdown(f"**{label}**")
        bc1, bc2, bc3, bc4, bc5, bc6 = st.columns(6)
        bc1.metric("Races", f"{s['races']:,}")
        bc2.metric("Cost", f"${s['total_cost']:,.0f}")
        bc3.metric("Payout", f"${s['total_payout']:,.0f}")
        bc4.metric("P&L", f"${s['total_pnl']:+,.0f}")
        bc5.metric("ROI", f"{s['roi_pct']:+.2f}%")
        bc6.metric("Hit rate", f"{s['hit_profit_pct']:.1f}%")

    st.metric("Wave threshold value", f"{res['threshold_wave_value']:.6f}")
    src_counts = res["per_race"]["payout_source"].value_counts().to_dict()
    st.caption(f"Payout sources: {src_counts}")

    st.plotly_chart(
        animate_cumulative_pnl(res["per_race"], mckenna_daily),
        use_container_width=True,
        key="cum_pnl",
    )
    st.caption("Play advances race-by-race cumulative P&L.")

    if result["sweep"] is not None:
        st.subheader("Threshold sweep (exploratory)")
        st.plotly_chart(plot_sweep(result["sweep"]), use_container_width=True, key="sweep")
        with st.expander("Sweep table"):
            st.dataframe(result["sweep"], use_container_width=True, hide_index=True)

    with st.expander("Per-race backtest detail"):
        st.dataframe(res["per_race"], use_container_width=True, hide_index=True)


def render_mckenna_engine(state: dict) -> None:
    opts = state["opts"]
    runners = state["runners"]
    result = state["result"]
    engine_summary = state.get("engine_summary")
    hexagram = state.get("hexagram")

    st.subheader("McKenna Engine")
    st.caption(
        "Selective trifecta betting: Harville-priced combos, beta-distorted pool "
        "payouts, fractal resonance gate, I Ching ticket selection. "
        "**beta is an assumption** — beta = 1.0 is the fair-pool null."
    )

    ec1, ec2, ec3, ec4 = st.columns(4)
    ec1.metric("Beta (pool bias)", f"{opts['engine_beta']:.2f}")
    ec2.metric("Gate %", f"{opts['engine_gate_pct']:.0f}")
    ec3.metric("k_max", opts["engine_k_max"])
    ec4.metric("Seed", opts["engine_seed"])

    if hexagram is not None:
        st.markdown(f"### Last I Ching cast: hexagram **{hexagram}** / 64")

    if engine_summary is None:
        st.info("Enable **Run McKenna Engine** in the sidebar and re-run analysis.")
        return

    st.dataframe(engine_summary, use_container_width=True, hide_index=True)

    for _, row in engine_summary.iterrows():
        with st.expander(f"Strategy: {row['strategy']}", expanded=False):
            sc1, sc2, sc3, sc4, sc5, sc6 = st.columns(6)
            sc1.metric("Races", f"{int(row['races']):,}")
            sc2.metric("Tickets", f"{int(row['tickets']):,}")
            sc3.metric("Cost", f"${row['cost']:,.2f}")
            sc4.metric("Payout", f"${row['payout']:,.2f}")
            sc5.metric("P&L", f"${row['pnl']:+,.2f}")
            roi = row["roi_pct"]
            sc6.metric("ROI", f"{roi:+.2f}%" if pd.notna(roi) else "N/A")

    from mckenna_derby.mckenna_engine import _compute_gated_days

    resonance = result["resonance"]
    gated_days = _compute_gated_days(
        result["daily"], opts["engine_gate_pct"], wave_factor=64, levels=3
    )

    st.plotly_chart(
        animate_resonance(resonance, gated_days),
        use_container_width=True,
        key="resonance",
    )

    with st.spinner("Building beta comparison animation …"):
        st.plotly_chart(
            animate_roi_by_beta(
                runners,
                gate_pct=opts["engine_gate_pct"],
                k_max=opts["engine_k_max"],
                takeout=opts["takeout"],
                seed=opts["engine_seed"],
            ),
            use_container_width=True,
            key="roi_beta",
        )
    st.caption("Slider steps through β = 1.00 … 1.20; Play auto-cycles strategies' ROI.")


def render_raw_data(state: dict) -> None:
    runners = state["runners"]
    result = state["result"]
    scores = result["scores"]
    daily = result["daily"]

    st.subheader("Raw data preview")
    st.write(f"First 100 rows of runner-level data ({len(runners):,} total rows)")
    st.dataframe(runners.head(100), use_container_width=True, hide_index=True)

    st.subheader("Downloads")
    dc1, dc2, dc3 = st.columns(3)
    dc1.download_button(
        "race_scores.csv",
        scores.to_csv(index=False),
        "race_scores.csv",
        "text/csv",
    )
    daily_df = daily.reset_index()
    daily_df.columns = ["date", "novelty_z"]
    dc2.download_button(
        "daily_novelty.csv",
        daily_df.to_csv(index=False),
        "daily_novelty.csv",
        "text/csv",
    )
    if state.get("engine_summary") is not None:
        dc3.download_button(
            "mckenna_engine.csv",
            state["engine_summary"].to_csv(index=False),
            "mckenna_engine.csv",
            "text/csv",
        )

    with st.expander("Full runners schema"):
        st.json({c: str(runners[c].dtype) for c in runners.columns})


def main() -> None:
    st.set_page_config(page_title="McKenna Derby", layout="wide")
    require_auth()
    st.title("McKenna Derby Dashboard")
    st.caption(
        "Horse-racing novelty vs Terence McKenna's Timewave Zero — "
        "full data transparency with animated Plotly charts"
    )

    prereg = load_prereg()
    opts = render_sidebar(prereg)

    if opts is None:
        st.info("Configure options in the sidebar and click **Run Analysis**.")
        if st.session_state.get("analysis"):
            st.markdown("---")
            st.markdown("Showing previous run — click **Run Analysis** to refresh.")
            state = st.session_state["analysis"]
            tab_over, tab_nt, tab_bt, tab_eng, tab_raw = st.tabs(
                ["Overview", "Novelty & Timewave", "Backtest", "McKenna Engine", "Raw Data"]
            )
            with tab_over:
                render_overview(state)
            with tab_nt:
                render_novelty_timewave(state)
            with tab_bt:
                render_backtest(state)
            with tab_eng:
                render_mckenna_engine(state)
            with tab_raw:
                render_raw_data(state)
        else:
            st.markdown(
                "**Quick start:** defaults run one year of synthetic demo data "
                "(2010, market-calibrated null fixture). Use Play on charts to animate."
            )
        return

    loaded = load_runners(opts)
    if loaded is None:
        return
    runners, source_label = loaded

    n_races = runners["race_id"].nunique()
    st.success(
        f"Loaded **{source_label}**: {n_races:,} races, {len(runners):,} runners, "
        f"{runners['date'].min().date()} to {runners['date'].max().date()}"
    )

    with st.spinner("Running analysis pipeline …"):
        result = run_pipeline(
            runners,
            opts["number_set"],
            opts["threshold_pct"],
            opts["takeout"],
            opts["metric"],
            opts["do_sweep"],
            opts["max_lag"],
            opts["engine_seed"],
            opts["engine_gate_pct"],
        )

    engine_summary = None
    hexagram = None
    mckenna_daily_pnl = None
    if opts["run_engine"]:
        with st.spinner("Running McKenna Engine (four strategies) …"):
            engine_summary = run_engine_summary(
                runners,
                opts["engine_beta"],
                opts["engine_gate_pct"],
                opts["engine_k_max"],
                opts["takeout"],
                opts["engine_seed"],
            )
            iching = IChingSelector(seed=opts["engine_seed"])
            hexagram = iching.cast_hexagram()
        with st.spinner("Computing McKenna gated P&L series …"):
            mckenna_daily_pnl = mckenna_gated_daily_pnl(
                runners,
                opts["engine_beta"],
                opts["engine_gate_pct"],
                opts["engine_k_max"],
                opts["takeout"],
                opts["engine_seed"],
            )

    state = {
        "runners": runners,
        "source_label": source_label,
        "opts": opts,
        "result": result,
        "engine_summary": engine_summary,
        "hexagram": hexagram,
        "mckenna_daily_pnl": mckenna_daily_pnl,
    }
    st.session_state["analysis"] = state

    tab_over, tab_nt, tab_bt, tab_eng, tab_raw = st.tabs(
        ["Overview", "Novelty & Timewave", "Backtest", "McKenna Engine", "Raw Data"]
    )
    with tab_over:
        render_overview(state)
    with tab_nt:
        render_novelty_timewave(state)
    with tab_bt:
        render_backtest(state)
    with tab_eng:
        render_mckenna_engine(state)
    with tab_raw:
        render_raw_data(state)


if __name__ == "__main__":
    main()

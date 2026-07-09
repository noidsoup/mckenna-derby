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
from mckenna_derby.tour import maybe_start_tour, render_tour_sidebar_controls

ROOT = Path(__file__).parent
PREREG_PATH = ROOT / "prereg.json"
ALL_SETS = ["kelley", "watkins", "sheliak", "huangti"]
BETA_FRAMES = [1.0, 1.05, 1.10, 1.15, 1.20]
MAX_ANIM_FRAMES = 80

# Observatory dark palette (Plotly + CSS share these accents)
PALETTE = {
    "surprise": "#38bdf8",       # cyan — daily surprise
    "wave": "#a78bfa",           # soft violet — McKenna wave
    "money_up": "#34d399",       # emerald
    "money_down": "#f87171",     # soft red
    "gate": "#fbbf24",           # amber — gated / picky days
    "trend": "#fb7185",          # rose — trend / accent lines
    "muted": "#94a3b8",
    "paper": "#0f1117",
    "plot": "#141722",
    "grid": "rgba(148, 163, 184, 0.18)",
    "text": "#e8e6f0",
    "fill_surprise": "rgba(56, 189, 248, 0.18)",
    "fill_wave": "rgba(167, 139, 250, 0.14)",
    "fill_money_up": "rgba(52, 211, 153, 0.18)",
    "fill_money_down": "rgba(248, 113, 113, 0.18)",
    "chaos_band": "rgba(167, 139, 250, 0.12)",
}


def apply_plotly_theme(fig: go.Figure) -> go.Figure:
    """Unify all charts on the observatory dark template."""
    # Preserve chart-specific margins when already set; animated figures need
    # extra top/bottom room for Play/Pause + the frame slider.
    cur_m = fig.layout.margin
    has_anim = bool(fig.layout.updatemenus)

    def _edge(name: str, default: int) -> int:
        val = getattr(cur_m, name, None) if cur_m is not None else None
        return default if val is None else int(val)

    default_t = 100 if has_anim else 64
    default_b = 72 if has_anim else 48
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=PALETTE["paper"],
        plot_bgcolor=PALETTE["plot"],
        font=dict(color=PALETTE["text"], size=13),
        colorway=[
            PALETTE["surprise"],
            PALETTE["wave"],
            PALETTE["money_up"],
            PALETTE["money_down"],
            PALETTE["gate"],
            PALETTE["trend"],
        ],
        margin=dict(
            l=_edge("l", 56),
            r=_edge("r", 36),
            t=_edge("t", default_t),
            b=_edge("b", default_b),
        ),
        legend=dict(
            bgcolor="rgba(20, 23, 34, 0.65)",
            bordercolor="rgba(167, 139, 250, 0.35)",
            borderwidth=1,
        ),
        hoverlabel=dict(
            bgcolor=PALETTE["plot"],
            font_color=PALETTE["text"],
            bordercolor=PALETTE["wave"],
        ),
    )
    fig.update_xaxes(
        gridcolor=PALETTE["grid"],
        zerolinecolor=PALETTE["grid"],
        linecolor=PALETTE["muted"],
    )
    fig.update_yaxes(
        gridcolor=PALETTE["grid"],
        zerolinecolor=PALETTE["grid"],
        linecolor=PALETTE["muted"],
    )
    return fig


def inject_app_css() -> None:
    """Light CSS polish for metrics, tabs, empty state, and sidebar."""
    st.markdown(
        f"""
<style>
  :root {{
    --md-accent: {PALETTE["wave"]};
    --md-cyan: {PALETTE["surprise"]};
    --md-paper: {PALETTE["paper"]};
  }}
  /* Metric cards */
  div[data-testid="stMetric"] {{
    background: linear-gradient(145deg, rgba(26, 29, 39, 0.95), rgba(20, 23, 34, 0.9));
    border: 1px solid rgba(167, 139, 250, 0.28);
    border-radius: 10px;
    padding: 0.65rem 0.85rem;
    box-shadow: 0 4px 18px rgba(0, 0, 0, 0.35);
  }}
  div[data-testid="stMetric"] label {{
    color: {PALETTE["muted"]} !important;
  }}
  /* Tabs */
  button[data-baseweb="tab"] {{
    color: {PALETTE["muted"]};
  }}
  button[data-baseweb="tab"][aria-selected="true"] {{
    color: {PALETTE["text"]} !important;
    border-bottom-color: var(--md-accent) !important;
  }}
  .block-container {{
    padding-top: 1.4rem;
  }}
  /* Soft radial wash behind main title area */
  section.main > div {{
    background:
      radial-gradient(ellipse 80% 40% at 15% 0%, rgba(167, 139, 250, 0.14), transparent 55%),
      radial-gradient(ellipse 60% 35% at 85% 5%, rgba(56, 189, 248, 0.08), transparent 50%);
  }}
  /* Empty-state intro: gentle accent on first markdown block */
  div[class*="st-key-tour_empty_intro"] {{
    border: 1px solid rgba(167, 139, 250, 0.22);
    border-radius: 12px;
    padding: 0.75rem 1rem;
    background: linear-gradient(145deg, rgba(26, 29, 39, 0.9), rgba(15, 17, 23, 0.85));
    box-shadow: 0 0 40px rgba(167, 139, 250, 0.08);
  }}
  /* Sidebar section headers */
  section[data-testid="stSidebar"] h1,
  section[data-testid="stSidebar"] h2,
  section[data-testid="stSidebar"] h3,
  section[data-testid="stSidebar"] h4,
  section[data-testid="stSidebar"] h5 {{
    color: {PALETTE["wave"]} !important;
    letter-spacing: 0.02em;
  }}
  section[data-testid="stSidebar"] {{
    border-right: 1px solid rgba(167, 139, 250, 0.18);
  }}
  /* Primary buttons */
  .stButton > button[kind="primary"],
  button[data-testid="baseButton-primary"] {{
    background: linear-gradient(135deg, #8b5cf6, #6366f1);
    border: 0;
    box-shadow: 0 0 20px rgba(167, 139, 250, 0.35);
  }}
  @media (prefers-reduced-motion: reduce) {{
    *, *::before, *::after {{
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
    }}
  }}
</style>
""",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Plain-English copy (shown in the UI)
# ---------------------------------------------------------------------------

EMPTY_STATE_MARKDOWN = """
### 🐴 What is this?

**Question:** Do weird 🐎 race days line up with Terence McKenna's 🌊 calendar wave
(his 🍄 map of when the world should feel more 🌀 chaotic)?

**Who was he?** Ethnobotanist, psychedelic philosopher, and legendary raconteur —
a **mystical genius** who tried to chart "novelty" (how wild history feels) as a
wave across time. Wild idea. We test it with honest stats 🎱.

**The wave:** Timewave Zero is his fractal calendar built from compressed
☯️ I Ching number tables. In his story, **low wave ↔ high chaos/novelty**.
The lore peaks at a "zero date" around **2012-12-21** — we use the historical
window before that.

**I Ching:** Ancient Chinese oracle of **64 hexagrams** 🔮. McKenna mined its
structure for the wave tables. This app's picky-betting mode also uses a
coin-cast hexagram-style picker 🃏 (same 64-pattern vibe — not a money tip).

**Data:** Real Hong Kong 🏇 races (1997–2005) are already loaded.

**What to do:** Click **🏇 Run Analysis** in the sidebar.

Then open **📊 Overview**. On this data the main answer is usually "no match" ☯️.
That is an honest finding, not a tip sheet 🔮.
"""

SIDEBAR_INTRO = (
    "This app asks two questions ☯️: Do surprising 🐎 race days line up with "
    "Terence McKenna's 🌊 Timewave Zero (his 🍄 map of when the world should feel "
    "more 🌀 chaotic)? And does betting only on those \"wave\" days help — or do "
    "you still lose the track's cut?\n\n"
    "McKenna was a mystical genius — ethnobotanist, psychedelic philosopher, "
    "raconteur — who built that wave from fractal ☯️ I Ching tables "
    "(low wave ↔ high novelty; zero-date lore ~2012). We keep the mystique in "
    "the story and the honesty in the numbers 🎱.\n\n"
    "Read the controls below top to bottom, then click **🏇 Run Analysis**."
)

WHO_IS_MCKENNA = """
**🍄 Who is Terence McKenna?**

A **mystical genius** of the late 20th century: ethnobotanist, psychedelic
philosopher, and spellbinding raconteur. He mapped "novelty" — how strange and
history-making a moment feels — onto a calendar wave he called **Timewave Zero** 🌊.

**Timewave Zero:** Built from fractal / compressed number tables drawn from the
☯️ **I Ching** (the ancient Chinese oracle of 64 hexagrams). In his telling,
**low wave = high chaos/novelty**; habit and boredom sit higher on the wave.
Pop lore ties the wave's climax to a **zero date** around **2012-12-21** —
this app's usable history sits before that cliff.

**I Ching here:** Same 64-hexagram DNA. McKenna used it for the wave tables;
our optional **picky betting** 🎲 also casts a coin-toss hexagram-style pattern
🃏 to thin tickets when too many look "hot." Theme emoji (☯️ 🔮 🍄 🎱 🐴) mark
that oracle vibe — **not** a claim the oracle prints money.
"""

SIDEBAR_HELP = {
    "data": (
        "**What is the Hong Kong data?** 🏇 Real horse races from the Hong Kong "
        "Jockey Club, years **1997–2005** — about 6,000 races with odds and "
        "finish order. They ship inside this app (from a public Kaggle set), "
        "so you do not need to upload anything.\n\n"
        "That history is the default for the main test. Open **Advanced options** "
        "only for a fake null demo 🎱 (should show no signal) or your own CSV."
    ),
    "locked": (
        "**What is this section?** ⭐ Before looking at results, we wrote down the "
        "recipe for the *main* claim (which wave table, cutoff, track cut, and "
        "surprise score). That recipe is locked so nobody can tweak knobs until "
        "the answer looks nicer.\n\n"
        "The run knobs below start on that recipe. You can change them to explore "
        "✨ — just don't treat a new combo as the official locked answer."
    ),
    "params": (
        "Knobs for this run of the main test 🏇. Defaults match the locked recipe "
        "above. Changing them is fine for curiosity 🔮 — not a new official result."
    ),
    "engine": (
        "A stricter side experiment 🎲: fewer days, fewer tickets, and an optional "
        "pool-bias guess. When too many tickets look good, a **coin-cast "
        "hexagram-style** picker 🃏 (☯️ I Ching vibe — 64 patterns) thins the field. "
        "**Bias guess = 1.0** means fair prices ☯️ (no free lunch). "
        "Higher values pretend favorites are overbet — a guess 🎱, not a fact."
    ),
}

# Visible captions under each sidebar control (no hover tooltips).
SIDEBAR_CONTROL_CAPTIONS = {
    "number_set": (
        "McKenna's 🌊 Timewave is built from ☯️ I Ching–derived number tables "
        "(Kelley, Watkins, and others). Different tables draw slightly different "
        "waves. **Kelley** is the locked default."
    ),
    "threshold_pct": (
        "Only treat days in the lowest X% of the wave as \"bet days\" 🏇. "
        "Lower cutoff = fewer, more extreme days. In McKenna's story, "
        "**low wave = high 🌀 chaos/novelty**."
    ),
    "takeout": (
        "The share the track keeps from every bet pool (the house edge) 🏁. "
        "With no real edge, expect to lose about this fraction over time."
    ),
    "metric": (
        "How we measure \"weird\" 🍄 finishes given the odds. "
        "Top-3 finish surprise looks at 1st–2nd–3rd together; "
        "Winner-only looks at just the winner 🐴."
    ),
    "engine_seed": (
        "A fixed starting number for any random ticket picks 🎱. "
        "Same seed → same choices every run, so results are repeatable."
    ),
    "do_sweep": (
        "Also try many cutoff values and plot returns ✨. "
        "Useful curiosity — not the locked main test."
    ),
    "max_lag": (
        "Check whether weird finishes lead or lag the wave by a few days "
        "(timing offset) 🌙. Set to 0 to skip this check."
    ),
    "run_engine": (
        "Turn on the stricter side experiment 🎲 (fewer days / tickets). "
        "Off = skip it and only run the main wave test 🌊."
    ),
    "engine_beta": (
        "1.0 assumes fair odds ☯️ (no free lunch expected). "
        "Above 1.0 pretends favorites are overbet — a guess 🎱 you can explore, "
        "not a fact about the track."
    ),
    "engine_gate_pct": (
        "Only bet on the hottest X% of days by the echo signal 🧿 "
        "(how strongly the day matches the wave idea). Lower % = pickier."
    ),
    "engine_k_max": (
        "Cap how many tickets we buy in one race 🏇. "
        "If too many look good, a coin-cast hexagram-style 🃏 pick "
        "(☯️ I Ching 64-pattern vibe) keeps this many — theme, not a tip."
    ),
}

TAB_INTROS = {
    "overview": (
        "Big picture 📊 for this run: how much 🐎 data you have, whether surprising "
        "race days lined up with McKenna's 🌊 Timewave Zero (his I Ching–built "
        "chaos calendar 🍄), and whether betting only on \"wave\" days beat betting "
        "every day. Mystique in the story; honesty in the numbers — on Hong Kong "
        "history the answer is usually \"no support\" ☯️, not a tip sheet 🔮."
    ),
    "novelty": (
        "**Surprise score** ✨ = how unexpected the finishes were, given the odds. "
        "**The wave** 🌊 = McKenna's Timewave Zero calendar of 🌀 chaos, built from "
        "☯️ I Ching number tables. His idea: **low wave ↔ high surprise** ☯️ "
        "(they should move opposite ways). Near-zero link + high chance score "
        "🎱 ≈ no support for that idea — null stays null."
    ),
    "backtest": (
        "Pretend we buy every top-3 ticket on chosen days 🏇. The track keeps a cut, "
        "so with no real edge you usually lose about that cut. Timing only helps "
        "if wave-picked days clearly beat betting every day — ROI near −track cut "
        "is the boring baseline 🏁. A pretty wave does not print money by itself."
    ),
    "engine": (
        "A pickier side experiment 🎲: fewer tickets, fewer days, optional pool-bias "
        "guess, and a coin-cast **hexagram-style** ticket thinner 🃏 (same 64-pattern "
        "☯️ I Ching vibe McKenna used for the wave tables). At bias = 1.0 (fair "
        "prices ☯️) you should not find a free lunch. Higher bias is a guess 🎱 — "
        "not a fact, and not a claim the oracle pays."
    ),
    "raw": (
        "The 🐎 race rows we scored, plus CSV downloads 📥 so you can check or reuse "
        "the numbers. This tab is the input and exports — not a new claim."
    ),
}

METRIC_LABELS = {
    "trifecta_novelty": "Top-3 finish surprise",
    "win_novelty": "Winner-only surprise",
}

TAB_LABELS = [
    "📊 Overview",
    "🌊 Surprise vs the wave",
    "🏁 Did timing help?",
    "🎲 Picky betting",
    "📁 Race data",
]


def _interpret_match(primary: dict) -> str:
    """Plain-English read of the main wave-vs-surprise result (friendly hippie voice)."""
    p = float(primary["permutation_p"])
    r = float(primary["spearman_r"])
    if p >= 0.05:
        return (
            f"**So what?** 🎱 Chance score {p:.4f} is not small, and the rank link "
            f"is {r:+.4f} (near 0 = little match). Sorry man! ☯️ That's a **null** "
            "result — these race days just don't line up with McKenna's 🌊 wave. "
            "On Hong Kong history that is the usual honest answer, far out as that sounds."
        )
    if r < 0:
        return (
            f"**So what?** 🔮 Chance score {p:.4f} is small and the rank link is "
            f"{r:+.4f} (negative). Far out dude! That's the direction McKenna guessed "
            "(low wave ↔ high surprise) ☯️ — interesting 🍄, but still not betting advice."
        )
    return (
        f"**So what?** 🎱 Chance score {p:.4f} is small, but the rank link is "
        f"{r:+.4f} (positive) — the **opposite** of McKenna's guess 🌀. "
        "Whoa, curious vibes only — not a tip, man."
    )


def _interpret_timing(strategy: dict, baseline: dict, takeout: float) -> str:
    """Plain-English read of wave-day betting vs bet-every-day (friendly hippie voice)."""
    s_roi = float(strategy["roi_pct"])
    b_roi = float(baseline["roi_pct"])
    cut_pct = -100.0 * float(takeout)
    delta = s_roi - b_roi
    if abs(s_roi - cut_pct) < 3 and abs(b_roi - cut_pct) < 3 and abs(delta) < 3:
        return (
            f"**So what?** 🏁 Wave-picked return {s_roi:+.2f}% vs every-day "
            f"{b_roi:+.2f}%. Both sit near the track's cut (~{cut_pct:.0f}%). "
            "Sorry man — that's the **boring baseline**: timing did not help. "
            "Peace and love, but no edge here ☯️."
        )
    if delta > 2:
        return (
            f"**So what?** ✨ Wave-picked return {s_roi:+.2f}% beats every-day "
            f"{b_roi:+.2f}% by about {delta:+.2f} points. Far out — **interesting** "
            "on this sample 🔮, but don't count on the cosmos keeping that groove."
        )
    if delta < -2:
        return (
            f"**So what?** 🎱 Wave-picked return {s_roi:+.2f}% is worse than every-day "
            f"{b_roi:+.2f}%. Sorry man! Filtering by the wave hurt here — a null/negative "
            "for the timing idea ☯️. Bummer vibes, but that's the honest trip."
        )
    return (
        f"**So what?** 🏇 Wave-picked {s_roi:+.2f}% vs every-day {b_roi:+.2f}% "
        f"(difference {delta:+.2f} points). Too close to call, dude — treat as "
        f"no clear timing edge. Expect ~{cut_pct:.0f}% with no edge."
    )


def _interpret_engine(opts: dict, engine_summary: pd.DataFrame | None) -> str:
    """Plain-English read of picky-betting results (friendly hippie voice)."""
    beta = float(opts["engine_beta"])
    if engine_summary is None or engine_summary.empty:
        return (
            "**So what?** 🎲 Picky betting was not run, man. Turn it on in the sidebar "
            "and click 🏇 Run Analysis again."
        )
    best = engine_summary.dropna(subset=["roi_pct"])
    if best.empty:
        return (
            "**So what?** 🎱 No usable returns in the picky-betting table for this run. "
            "Sorry man — nothing to groove on here."
        )
    top = best.loc[best["roi_pct"].idxmax()]
    roi = float(top["roi_pct"])
    name = top["strategy"]
    if abs(beta - 1.0) < 1e-9:
        if roi > 2:
            return (
                f"**So what?** 🔮 Bias is 1.0 (fair prices ☯️). Best rule **{name}** "
                f"shows {roi:+.2f}% — far out under a fair-pool assumption. "
                "Double-check, dude; do not treat as a free lunch."
            )
        return (
            f"**So what?** 🎱 Bias is 1.0 (fair prices ☯️). Best rule **{name}** "
            f"returns {roi:+.2f}%. Sorry man — near zero or negative is the "
            "**expected null** — no free lunch when the pool is fair. Keep the peace ☮️."
        )
    return (
        f"**So what?** 🃏 Bias guess is {beta:.2f} (not fair). Best rule **{name}** "
        f"returns {roi:+.2f}%. That only means \"if favorites were overbet that "
        "way\" — a guess, not proof the track is biased. Stay groovy, stay skeptical."
    )


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

    st.title("🐴 McKenna Derby")
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
    transition_ms: int = 100,
) -> tuple[list, dict]:
    """Build Plotly play/pause buttons + frame slider (no invalid slider props)."""
    steps = [
        {
            "args": [
                [label],
                {
                    "frame": {"duration": frame_duration, "redraw": True},
                    "mode": "immediate",
                    "transition": {"duration": transition_ms, "easing": "cubic-in-out"},
                },
            ],
            "label": label,
            "method": "animate",
        }
        for label in frame_labels
    ]
    # Top-right so Play/Pause does not sit on the centered figure title.
    updatemenus = [
        {
            "type": "buttons",
            "showactive": False,
            "x": 1.0,
            "y": 1.12,
            "xanchor": "right",
            "yanchor": "bottom",
            "direction": "left",
            "pad": {"r": 0, "t": 0, "l": 10},
            "buttons": [
                {
                    "label": "▶ Play",
                    "method": "animate",
                    "args": [
                        None,
                        {
                            "frame": {"duration": frame_duration, "redraw": True},
                            "fromcurrent": True,
                            "transition": {
                                "duration": transition_ms,
                                "easing": "cubic-in-out",
                            },
                        },
                    ],
                },
                {
                    "label": "❚❚ Pause",
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
            "bgcolor": "rgba(26, 29, 39, 0.9)",
            "bordercolor": PALETTE["wave"],
            "font": {"color": PALETTE["text"]},
        }
    ]
    # layout.slider has no `xaxis` property — axis titles belong on the figure axes.
    sliders = [
        {
            "active": max(len(frame_labels) - 1, 0),
            "currentvalue": {
                "prefix": "Frame: ",
                "font": {"color": PALETTE["text"], "size": 12},
            },
            "pad": {"t": 50},
            "steps": steps,
            "x": 0.1,
            "len": 0.85,
            "bgcolor": "rgba(26, 29, 39, 0.8)",
            "bordercolor": PALETTE["wave"],
            "tickcolor": PALETTE["muted"],
            "font": {"color": PALETTE["muted"]},
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

    # Chaos band: raw wave bottom quartile (McKenna "high chaos" zone) on primary axis
    # via a secondary-y rectangle band using the inverted series thresholds.
    chaos_hi = float(np.nanpercentile(tw_inv.to_numpy(dtype=float), 75))

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=[],
            y=[],
            name="Daily surprise",
            line=dict(color=PALETTE["surprise"], width=2.4),
            fill="tozeroy",
            fillcolor=PALETTE["fill_surprise"],
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=[],
            y=[],
            name="McKenna's wave (flipped)",
            line=dict(color=PALETTE["wave"], width=2.2, dash="dot"),
            fill="tozeroy",
            fillcolor=PALETTE["fill_wave"],
        ),
        secondary_y=True,
    )
    # Static chaos-band guide on secondary y (flipped wave high-chaos zone).
    # Annotation sits bottom-left inside the band so it clears the title / Play row.
    y0_band = float(np.nanmin(tw_inv)) if len(tw_inv) else 0.0
    fig.add_hrect(
        y0=y0_band,
        y1=chaos_hi,
        fillcolor=PALETTE["chaos_band"],
        line_width=0,
        layer="below",
        yref="y2",
        annotation_text="Chaos band (wave)",
        annotation_position="bottom left",
        annotation_font_color=PALETTE["muted"],
        annotation_font_size=11,
    )

    frames = []
    labels = []
    for end in idx:
        sl = slice(0, int(end) + 1)
        label = str(dates[end].date())
        labels.append(label)
        frames.append(
            go.Frame(
                name=label,
                data=[
                    go.Scatter(
                        x=dates[sl],
                        y=daily.iloc[sl],
                        line=dict(color=PALETTE["surprise"], width=2.4),
                        fill="tozeroy",
                        fillcolor=PALETTE["fill_surprise"],
                    ),
                    go.Scatter(
                        x=dates[sl],
                        y=tw_inv.iloc[sl],
                        line=dict(color=PALETTE["wave"], width=2.2, dash="dot"),
                        fill="tozeroy",
                        fillcolor=PALETTE["fill_wave"],
                    ),
                ],
                traces=[0, 1],
            )
        )

    fig.frames = frames
    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(title_text="Daily surprise", secondary_y=False)
    fig.update_yaxes(title_text="McKenna's wave (flipped)", secondary_y=True)
    menus, sliders = _play_slider_menus(labels)
    fig.update_layout(
        title="Surprise score and McKenna's wave over time",
        height=520,
        hovermode="x unified",
        # Extra top room: centered title + top-right Play/Pause.
        margin=dict(l=56, r=48, t=100, b=72),
        updatemenus=menus,
        sliders=sliders,
    )
    if labels:
        fig.update(data=list(frames[-1].data))
    return apply_plotly_theme(fig)


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
    fig.add_trace(
        go.Scatter(
            x=[],
            y=[],
            name="Bet every race",
            line=dict(color=PALETTE["money_down"], width=2.2),
            fill="tozeroy",
            fillcolor=PALETTE["fill_money_down"],
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[],
            y=[],
            name="Wave-picked days only",
            line=dict(color=PALETTE["money_up"], width=2.2),
            fill="tozeroy",
            fillcolor=PALETTE["fill_money_up"],
        )
    )
    if mckenna_cum is not None:
        fig.add_trace(
            go.Scatter(
                x=[],
                y=[],
                name="Picky betting (gated days)",
                line=dict(color=PALETTE["gate"], width=2.0),
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
            go.Scatter(
                x=sub["date"],
                y=cum_all.iloc[sl],
                line=dict(color=PALETTE["money_down"], width=2.2),
                fill="tozeroy",
                fillcolor=PALETTE["fill_money_down"],
            ),
            go.Scatter(
                x=sub["date"],
                y=cum_strat.iloc[sl],
                line=dict(color=PALETTE["money_up"], width=2.2),
                fill="tozeroy",
                fillcolor=PALETTE["fill_money_up"],
            ),
        ]
        if mckenna_cum is not None:
            days = sub["day"]
            mc = mckenna_daily.reindex(days, fill_value=0.0).cumsum()
            frame_data.append(
                go.Scatter(
                    x=sub["date"],
                    y=mc.to_numpy(),
                    line=dict(color=PALETTE["gate"], width=2.0),
                )
            )
        frames.append(go.Frame(name=label, data=frame_data, traces=list(range(len(frame_data)))))

    fig.frames = frames
    menus, sliders = _play_slider_menus(labels)
    fig.update_layout(
        title="Running money over time (race by race)",
        xaxis_title="Date",
        yaxis_title="Running profit or loss ($)",
        height=480,
        hovermode="x unified",
        updatemenus=menus,
        sliders=sliders,
    )
    if frames:
        fig.update(data=list(frames[-1].data))
    return apply_plotly_theme(fig)


def animate_resonance(
    resonance: pd.Series,
    gated_days: set,
    max_frames: int = MAX_ANIM_FRAMES,
) -> go.Figure:
    if resonance.empty:
        fig = go.Figure()
        fig.update_layout(title="Echo signal (no data)", height=400)
        return apply_plotly_theme(fig)

    dates = pd.to_datetime(pd.Index(resonance.index))
    vals = resonance.to_numpy()
    idx = _subsample_indices(len(dates), max_frames)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[],
            y=[],
            name="Echo of past surprise",
            line=dict(color=PALETTE["wave"], width=2.2),
            fill="tozeroy",
            fillcolor=PALETTE["fill_wave"],
        )
    )
    gate_dates = [pd.Timestamp(d) for d in gated_days if d in resonance.index]
    gate_y = [resonance.loc[d.date() if hasattr(d, "date") else d] for d in gate_dates]
    fig.add_trace(
        go.Scatter(
            x=gate_dates,
            y=gate_y,
            mode="markers",
            name="Days we would bet",
            marker=dict(
                color=PALETTE["gate"],
                size=9,
                symbol="diamond",
                line=dict(width=1, color=PALETTE["text"]),
            ),
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
                    go.Scatter(
                        x=dates[sl],
                        y=vals[sl],
                        line=dict(color=PALETTE["wave"], width=2.2),
                        fill="tozeroy",
                        fillcolor=PALETTE["fill_wave"],
                    ),
                    go.Scatter(x=vis_gates, y=vis_y, mode="markers"),
                ],
                traces=[0, 1],
            )
        )

    fig.frames = frames
    menus, sliders = _play_slider_menus(labels)
    fig.update_layout(
        title="Echo signal and the days we would bet",
        xaxis_title="Date",
        yaxis_title="Echo strength",
        height=450,
        updatemenus=menus,
        sliders=sliders,
    )
    if frames:
        fig.update(data=list(frames[-1].data))
    return apply_plotly_theme(fig)


def animate_novelty_distribution(
    scores: pd.DataFrame,
    metric: str = "trifecta_novelty",
    max_frames: int = MAX_ANIM_FRAMES,
) -> go.Figure:
    vals = scores[metric].dropna().to_numpy()
    metric_label = METRIC_LABELS.get(metric, metric)
    if len(vals) == 0:
        fig = go.Figure()
        fig.update_layout(title="Surprise score spread (no data)", height=400)
        return apply_plotly_theme(fig)

    idx = _subsample_indices(len(vals), max_frames)
    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=[],
            name=metric_label,
            marker_color=PALETTE["surprise"],
            nbinsx=30,
        )
    )

    frames = []
    labels = []
    for end in idx:
        n = int(end) + 1
        label = f"{n} races"
        labels.append(label)
        frames.append(
            go.Frame(
                name=label,
                data=[
                    go.Histogram(
                        x=vals[:n],
                        nbinsx=30,
                        marker_color=PALETTE["surprise"],
                    )
                ],
                traces=[0],
            )
        )

    fig.frames = frames
    menus, sliders = _play_slider_menus(labels, frame_duration=100)
    fig.update_layout(
        title=f"How {metric_label.lower()} is spread across races",
        xaxis_title=metric_label,
        yaxis_title="Number of races",
        height=420,
        updatemenus=menus,
        sliders=sliders,
    )
    if frames:
        fig.update(data=list(frames[-1].data))
    return apply_plotly_theme(fig)


def animate_lead_lag(lag: pd.DataFrame) -> go.Figure:
    idx = _subsample_indices(len(lag), MAX_ANIM_FRAMES)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[],
            y=[],
            mode="lines+markers",
            name="Rank link",
            line=dict(color=PALETTE["surprise"], width=2.2),
            marker=dict(size=6, color=PALETTE["wave"]),
        )
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
                data=[
                    go.Scatter(
                        x=sub["lag_days"],
                        y=sub["spearman_r"],
                        mode="lines+markers",
                        line=dict(color=PALETTE["surprise"], width=2.2),
                        marker=dict(size=6, color=PALETTE["wave"]),
                    )
                ],
                traces=[0],
            )
        )

    fig.frames = frames
    menus, sliders = _play_slider_menus(labels)
    fig.update_layout(
        title="Does surprise lead or lag the wave?",
        xaxis_title="Shift in days",
        yaxis_title="Rank link (how much they move together)",
        height=420,
        updatemenus=menus,
        sliders=sliders,
    )
    if frames:
        fig.update(data=list(frames[-1].data))
    return apply_plotly_theme(fig)


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

    def _bar_colors(rois: pd.Series) -> list[str]:
        return [
            PALETTE["money_up"] if v >= 0 else PALETTE["money_down"] for v in rois
        ]

    first = summaries[0][1].dropna(subset=["roi_pct"])
    fig = go.Figure()
    if not first.empty:
        fig.add_trace(
            go.Bar(
                x=first["strategy"],
                y=first["roi_pct"],
                marker_color=_bar_colors(first["roi_pct"]),
                marker_line=dict(width=1, color=PALETTE["muted"]),
            )
        )

    frames = []
    for beta, summary in summaries:
        roi = summary.dropna(subset=["roi_pct"])
        if roi.empty:
            continue
        frames.append(
            go.Frame(
                name=f"bias={beta:.2f}",
                data=[
                    go.Bar(
                        x=roi["strategy"],
                        y=roi["roi_pct"],
                        marker_color=_bar_colors(roi["roi_pct"]),
                        marker_line=dict(width=1, color=PALETTE["muted"]),
                    )
                ],
                traces=[0],
            )
        )

    fig.frames = frames
    labels = [f.name for f in frames]
    menus, sliders = _play_slider_menus(labels, frame_duration=600)
    fig.update_layout(
        title="Return by strategy as the bias guess changes",
        yaxis_title="Return on money spent (%)",
        height=450,
        updatemenus=menus,
        sliders=sliders,
    )
    if frames:
        fig.update(data=list(frames[-1].data))
    return apply_plotly_theme(fig)


def plot_verdict_gauge(permutation_p: float, spearman_r: float) -> go.Figure:
    """Radial gauge: chance score with null vs interesting zones.

    One title only: the big dial number is the chance score. Rank link sits as a
    small subtitle under the number. Green-zone meaning lives in the Streamlit
    caption under the chart (not a competing Plotly layout title).
    """
    p = float(permutation_p)
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=p,
            number={
                "valueformat": ".4f",
                "font": {"size": 36, "color": PALETTE["text"]},
                # Subtitle under the value — avoids stacking with a layout title.
                "suffix": (
                    f"<br><span style='font-size:0.45em;color:{PALETTE['muted']}'>"
                    f"rank link {spearman_r:+.4f}</span>"
                ),
            },
            # No indicator title — layout title also omitted (caption explains dial).
            gauge={
                "axis": {
                    "range": [0, 1],
                    "tickwidth": 1,
                    "tickcolor": PALETTE["muted"],
                    "tickfont": {"color": PALETTE["muted"]},
                },
                "bar": {"color": PALETTE["wave"], "thickness": 0.28},
                "bgcolor": PALETTE["plot"],
                "borderwidth": 1,
                "bordercolor": PALETTE["muted"],
                "steps": [
                    {"range": [0, 0.05], "color": "rgba(52, 211, 153, 0.35)"},
                    {"range": [0.05, 0.20], "color": "rgba(251, 191, 36, 0.22)"},
                    {"range": [0.20, 1.0], "color": "rgba(148, 163, 184, 0.18)"},
                ],
                "threshold": {
                    "line": {"color": PALETTE["gate"], "width": 2},
                    "thickness": 0.75,
                    "value": 0.05,
                },
            },
        )
    )
    fig.update_layout(
        height=340,
        margin=dict(l=28, r=28, t=36, b=24),
    )
    return apply_plotly_theme(fig)


def animate_scatter_reveal(
    daily: pd.Series, tw: pd.Series, max_frames: int = MAX_ANIM_FRAMES
) -> go.Figure:
    """Scatter of surprise vs wave with points revealed over time by date."""
    df = pd.DataFrame({"novelty": daily, "timewave_inv": -tw}).dropna()
    if df.empty:
        fig = go.Figure()
        fig.update_layout(title="Surprise vs the wave (no data)", height=400)
        return apply_plotly_theme(fig)

    dates = pd.to_datetime(pd.Index(df.index))
    order = np.argsort(dates.to_numpy())
    x_all = df["timewave_inv"].to_numpy()[order]
    y_all = df["novelty"].to_numpy()[order]
    date_all = dates.to_numpy()[order]
    day_num = (pd.to_datetime(date_all) - pd.to_datetime(date_all[0])).days.to_numpy(
        dtype=float
    )

    idx = _subsample_indices(len(x_all), max_frames)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[],
            y=[],
            mode="markers",
            name="Days",
            marker=dict(
                size=7,
                color=[],
                colorscale="Tealrose",
                cmin=float(day_num.min()) if len(day_num) else 0,
                cmax=float(day_num.max()) if len(day_num) else 1,
                colorbar=dict(
                    title="Days since start",
                    y=0.42,
                    len=0.72,
                    x=1.02,
                ),
                opacity=0.8,
                line=dict(width=0.5, color=PALETTE["muted"]),
            ),
            hovertemplate="wave (flipped) = %{x:.4f}<br>surprise = %{y:.3f}<extra></extra>",
        )
    )

    # Static OLS trend (full sample) so the reveal has a fixed reference
    if len(x_all) >= 2 and np.ptp(x_all) > 0:
        slope, intercept = np.polyfit(x_all, y_all, 1)
        xs = np.linspace(x_all.min(), x_all.max(), 50)
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=slope * xs + intercept,
                mode="lines",
                name=f"Trend line (slope {slope:+.3f})",
                line=dict(color=PALETTE["trend"], width=2, dash="dash"),
            )
        )

    frames = []
    labels = []
    for end in idx:
        n = int(end) + 1
        label = str(pd.Timestamp(date_all[end]).date())
        labels.append(label)
        frames.append(
            go.Frame(
                name=label,
                data=[
                    go.Scatter(
                        x=x_all[:n],
                        y=y_all[:n],
                        mode="markers",
                        marker=dict(
                            size=7,
                            color=day_num[:n],
                            colorscale="Tealrose",
                            cmin=float(day_num.min()),
                            cmax=float(day_num.max()),
                            opacity=0.8,
                            line=dict(width=0.5, color=PALETTE["muted"]),
                        ),
                    )
                ],
                traces=[0],
            )
        )

    fig.frames = frames
    menus, sliders = _play_slider_menus(labels, frame_duration=90)
    fig.update_layout(
        title="Days appear over time: surprise vs the wave",
        xaxis_title="McKenna's wave (flipped)",
        yaxis_title="Daily surprise score",
        height=460,
        # Legend left; Play is top-right — keep them on separate sides.
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, xanchor="left"),
        margin=dict(l=56, r=72, t=100, b=72),
        updatemenus=menus,
        sliders=sliders,
    )
    if frames:
        fig.update(data=[frames[-1].data[0]] + list(fig.data[1:]))
    return apply_plotly_theme(fig)


def animate_drawdown(
    per_race: pd.DataFrame, max_frames: int = MAX_ANIM_FRAMES
) -> go.Figure:
    """Animated drawdown reveal for both strategies."""
    pr = per_race.sort_values("date").reset_index(drop=True)
    idx = _subsample_indices(len(pr), max_frames)

    series = []
    for name, pnl, color, fill in [
        (
            "Bet every race",
            pr["pnl"],
            PALETTE["money_down"],
            PALETTE["fill_money_down"],
        ),
        (
            "Wave-picked days only",
            pr["pnl"].where(pr["selected"], 0.0),
            PALETTE["money_up"],
            PALETTE["fill_money_up"],
        ),
    ]:
        cum = pnl.cumsum()
        dd = cum - cum.cummax()
        series.append((name, dd, color, fill))

    fig = go.Figure()
    for name, dd, color, fill in series:
        fig.add_trace(
            go.Scatter(
                x=[],
                y=[],
                mode="lines",
                name=name,
                line=dict(color=color, width=2.2),
                fill="tozeroy",
                fillcolor=fill,
            )
        )

    frames = []
    labels = []
    for end in idx:
        sl = slice(0, int(end) + 1)
        sub = pr.iloc[sl]
        label = str(sub["date"].iloc[-1].date())
        labels.append(label)
        frame_data = []
        for _name, dd, color, fill in series:
            frame_data.append(
                go.Scatter(
                    x=sub["date"],
                    y=dd.iloc[sl],
                    mode="lines",
                    line=dict(color=color, width=2.2),
                    fill="tozeroy",
                    fillcolor=fill,
                )
            )
        frames.append(
            go.Frame(name=label, data=frame_data, traces=list(range(len(frame_data))))
        )

    fig.frames = frames
    menus, sliders = _play_slider_menus(labels)
    worst = min(float(dd.min()) for _n, dd, _c, _f in series)
    fig.update_layout(
        title=f"How far money fell from its best point (worst dip {worst:,.0f})",
        xaxis_title="Date",
        yaxis_title="Drop from peak ($)",
        height=400,
        hovermode="x unified",
        updatemenus=menus,
        sliders=sliders,
    )
    if frames:
        fig.update(data=list(frames[-1].data))
    return apply_plotly_theme(fig)


# ---------------------------------------------------------------------------
# Static "richer" visualizations (relationships, distributions, risk)
# ---------------------------------------------------------------------------


def plot_novelty_calendar_heatmap(daily: pd.Series) -> go.Figure:
    """Month × day heatmap of daily novelty z-scores (calendar view)."""
    df = daily.rename("novelty").reset_index()
    df.columns = ["date", "novelty"]
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.strftime("%Y-%m")
    df["day"] = df["date"].dt.day
    pivot = df.pivot_table(index="month", columns="day", values="novelty", aggfunc="mean")

    fig = go.Figure(
        go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=pivot.index,
            colorscale="Tealrose",
            zmid=0.0,
            colorbar=dict(title="Surprise"),
            hovertemplate="Month %{y}, day %{x}<br>surprise = %{z:.3f}<extra></extra>",
        )
    )
    fig.update_layout(
        title="Surprise score by calendar day",
        xaxis_title="Day of month",
        yaxis_title="Month",
        height=max(320, 24 * len(pivot.index) + 120),
    )
    return apply_plotly_theme(fig)


def plot_novelty_vs_timewave_scatter(daily: pd.Series, tw: pd.Series) -> go.Figure:
    """Scatter of daily novelty vs (inverted) timewave with an OLS trendline."""
    df = pd.DataFrame({"novelty": daily, "timewave_inv": -tw}).dropna()
    if df.empty:
        fig = go.Figure()
        fig.update_layout(title="Surprise vs the wave (no data)", height=400)
        return apply_plotly_theme(fig)

    dates = pd.to_datetime(pd.Index(df.index))
    day_num = (dates - dates.min()).days.to_numpy(dtype=float)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["timewave_inv"],
            y=df["novelty"],
            mode="markers",
            name="Days",
            marker=dict(
                size=7,
                color=day_num,
                colorscale="Tealrose",
                colorbar=dict(
                    title="Days since start",
                    y=0.42,
                    len=0.72,
                    x=1.02,
                ),
                opacity=0.75,
                line=dict(width=0.5, color=PALETTE["muted"]),
            ),
            text=[str(d.date()) for d in dates],
            hovertemplate="%{text}<br>wave (flipped) = %{x:.4f}<br>surprise = %{y:.3f}<extra></extra>",
        )
    )
    # OLS trendline (descriptive only — inference stays with the permutation test).
    x = df["timewave_inv"].to_numpy()
    y = df["novelty"].to_numpy()
    if len(x) >= 2 and np.ptp(x) > 0:
        slope, intercept = np.polyfit(x, y, 1)
        xs = np.linspace(x.min(), x.max(), 50)
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=slope * xs + intercept,
                mode="lines",
                name=f"Trend line (slope {slope:+.3f})",
                line=dict(color=PALETTE["trend"], width=2, dash="dash"),
            )
        )
    fig.update_layout(
        title="Each day: surprise score vs McKenna's wave",
        xaxis_title="McKenna's wave (flipped)",
        yaxis_title="Daily surprise score",
        height=460,
        # Horizontal legend on top-left; colorbar sits mid-right (no overlap).
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, xanchor="left"),
        margin=dict(l=56, r=72, t=80, b=48),
    )
    return apply_plotly_theme(fig)


def plot_rolling_correlation(daily: pd.Series, tw: pd.Series, window: int = 30) -> go.Figure:
    """Rolling Spearman correlation between novelty and inverted timewave."""
    df = pd.DataFrame({"novelty": daily, "timewave_inv": -tw}).dropna()
    fig = go.Figure()
    if len(df) < window + 1:
        fig.update_layout(
            title=f"Rolling match (needs more than {window} days)", height=360
        )
        return apply_plotly_theme(fig)

    # Spearman = Pearson on ranks; ranking inside each window keeps it exact.
    dates = pd.to_datetime(pd.Index(df.index))
    x = df["novelty"].to_numpy()
    y = df["timewave_inv"].to_numpy()
    vals = np.full(len(df), np.nan)
    for i in range(window, len(df)):
        xs = pd.Series(x[i - window : i + 1]).rank().to_numpy()
        ys = pd.Series(y[i - window : i + 1]).rank().to_numpy()
        if np.ptp(xs) > 0 and np.ptp(ys) > 0:
            vals[i] = float(np.corrcoef(xs, ys)[0, 1])

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=vals,
            mode="lines",
            name=f"{window}-day rank link",
            line=dict(color=PALETTE["surprise"], width=2.2),
            fill="tozeroy",
            fillcolor=PALETTE["fill_surprise"],
        )
    )
    fig.add_hline(y=0.0, line_dash="dot", line_color=PALETTE["muted"])
    fig.update_layout(
        title=f"How well surprise and the wave match ({window}-day window)",
        xaxis_title="Date",
        yaxis_title="Rank link (−1 to +1)",
        yaxis_range=[-1, 1],
        height=380,
    )
    return apply_plotly_theme(fig)


def plot_field_size_novelty(scores: pd.DataFrame, metric: str = "trifecta_novelty") -> go.Figure:
    """Distribution of raw novelty per field size — shows why we z-score within bucket."""
    metric_label = METRIC_LABELS.get(metric, metric)
    fig = go.Figure()
    for n, g in sorted(scores.groupby("n_runners"), key=lambda kv: kv[0]):
        fig.add_trace(
            go.Box(
                y=g[metric],
                name=f"{int(n)}",
                boxpoints="outliers",
                marker=dict(color=PALETTE["surprise"]),
                line=dict(color=PALETTE["surprise"]),
                fillcolor="rgba(56, 189, 248, 0.25)",
                showlegend=False,
            )
        )
    fig.update_layout(
        title=f"{metric_label} by how many horses ran (bigger fields look weirder raw)",
        xaxis_title="Horses in the race",
        yaxis_title=metric_label,
        height=420,
    )
    return apply_plotly_theme(fig)


def plot_winner_profile(scores: pd.DataFrame) -> go.Figure:
    """Winner odds distribution + monthly favorite strike rate."""
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("How long the winners paid", "How often the favorite won"),
    )
    fig.add_trace(
        go.Histogram(
            x=np.log10(scores["winner_odds"].clip(lower=1.01)),
            nbinsx=40,
            marker_color=PALETTE["surprise"],
            name="Winner odds (log scale)",
            showlegend=False,
        ),
        row=1,
        col=1,
    )
    monthly = (
        scores.assign(month=scores["date"].dt.to_period("M").dt.to_timestamp())
        .groupby("month")["winner_was_favorite"]
        .mean()
        * 100.0
    )
    fig.add_trace(
        go.Scatter(
            x=monthly.index,
            y=monthly.values,
            mode="lines+markers",
            name="Favorite win %",
            line=dict(color=PALETTE["money_up"], width=2.2),
            marker=dict(size=5, color=PALETTE["gate"]),
            showlegend=False,
        ),
        row=1,
        col=2,
    )
    fig.update_xaxes(title_text="Winner odds (log scale)", row=1, col=1)
    fig.update_yaxes(title_text="Races", row=1, col=1)
    fig.update_xaxes(title_text="Month", row=1, col=2)
    fig.update_yaxes(title_text="Favorite won (%)", row=1, col=2)
    fig.update_layout(title="Who won, and how often favorites did", height=400)
    return apply_plotly_theme(fig)


def plot_pnl_distribution(per_race: pd.DataFrame) -> go.Figure:
    """Per-race P&L distributions: timewave-selected days vs the rest."""
    sel = per_race.loc[per_race["selected"], "pnl"]
    rest = per_race.loc[~per_race["selected"], "pnl"]
    fig = go.Figure()
    fig.add_trace(
        go.Violin(
            y=rest,
            name=f"Other days (n={len(rest):,})",
            side="negative",
            line_color=PALETTE["money_down"],
            fillcolor="rgba(248, 113, 113, 0.35)",
            meanline_visible=True,
            points=False,
        )
    )
    fig.add_trace(
        go.Violin(
            y=sel,
            name=f"Wave-picked days (n={len(sel):,})",
            side="positive",
            line_color=PALETTE["money_up"],
            fillcolor="rgba(52, 211, 153, 0.35)",
            meanline_visible=True,
            points=False,
        )
    )
    fig.update_layout(
        title="Profit or loss per race: wave-picked days vs the rest",
        yaxis_title="Profit or loss per race ($)",
        violinmode="overlay",
        height=430,
    )
    return apply_plotly_theme(fig)


def plot_drawdown(per_race: pd.DataFrame) -> go.Figure:
    """Cumulative P&L drawdown for both strategies."""
    pr = per_race.sort_values("date").reset_index(drop=True)
    fig = go.Figure()
    for name, pnl, color, fill in [
        (
            "Bet every race",
            pr["pnl"],
            PALETTE["money_down"],
            PALETTE["fill_money_down"],
        ),
        (
            "Wave-picked days only",
            pr["pnl"].where(pr["selected"], 0.0),
            PALETTE["money_up"],
            PALETTE["fill_money_up"],
        ),
    ]:
        cum = pnl.cumsum()
        dd = cum - cum.cummax()
        fig.add_trace(
            go.Scatter(
                x=pr["date"],
                y=dd,
                mode="lines",
                name=f"{name} (worst dip {dd.min():,.0f})",
                line=dict(color=color, width=2.2),
                fill="tozeroy",
                fillcolor=fill,
            )
        )
    fig.update_layout(
        title="How far money fell from its best point",
        xaxis_title="Date",
        yaxis_title="Drop from peak ($)",
        height=400,
        hovermode="x unified",
    )
    return apply_plotly_theme(fig)


def plot_monthly_pnl_heatmap(per_race: pd.DataFrame) -> go.Figure:
    """Year × month heatmap of timewave-filtered strategy P&L."""
    pr = per_race.copy()
    strat_pnl = pr["pnl"].where(pr["selected"], 0.0)
    df = pd.DataFrame({"date": pr["date"], "pnl": strat_pnl})
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    pivot = df.pivot_table(index="year", columns="month", values="pnl", aggfunc="sum")
    pivot = pivot.reindex(columns=range(1, 13))
    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    fig = go.Figure(
        go.Heatmap(
            z=pivot.values,
            x=month_labels,
            y=[str(y) for y in pivot.index],
            colorscale=[
                [0.0, "#7f1d1d"],
                [0.35, "#f87171"],
                [0.5, "#1a1d27"],
                [0.65, "#34d399"],
                [1.0, "#065f46"],
            ],
            zmid=0.0,
            colorbar=dict(title="Profit/loss ($)"),
            hovertemplate="%{y} %{x}<br>$%{z:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        title="Wave-picked days: profit or loss by month",
        xaxis_title="Month",
        yaxis_title="Year",
        yaxis_type="category",
        height=max(300, 40 * len(pivot.index) + 140),
    )
    return apply_plotly_theme(fig)


def plot_sweep(sweep: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=sweep["threshold_pct"],
            y=sweep["roi_pct"],
            mode="lines+markers",
            name="Return %",
            line=dict(color=PALETTE["trend"], width=2.4),
            marker=dict(size=7, color=PALETTE["gate"]),
            fill="tozeroy",
            fillcolor="rgba(251, 113, 133, 0.12)",
        )
    )
    fig.update_layout(
        title="What if we change the wave cutoff? (curiosity only)",
        xaxis_title="Wave cutoff (lowest % of days we bet)",
        yaxis_title="Return on money spent (%)",
        height=400,
    )
    return apply_plotly_theme(fig)


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
        st.markdown("##### 🐴 What this software does")
        st.caption(SIDEBAR_INTRO)

        with st.expander("🍄 Who is Terence McKenna?", expanded=False):
            st.markdown(WHO_IS_MCKENNA)

        render_tour_sidebar_controls()

        with st.container(key="tour_data_source"):
            st.header("📁 Your data")
            st.markdown(SIDEBAR_HELP["data"])
            st.caption(
                f"Using: **Hong Kong 🏇 races (bundled)** · "
                f"{prereg.get('declared_on', 'locked')} recipe below ⭐."
            )
            source = "Hong Kong (bundled)"
            uploaded = None
            start = end = None

            with st.expander("Advanced options", expanded=False):
                st.caption(
                    "Leave the default alone for the real Hong Kong 🏇 test. "
                    "Synthetic demo builds fake races that should show no wave "
                    "signal 🎱. Upload CSV is for your own race file."
                )
                advanced = st.radio(
                    "Use a different source",
                    [
                        "Use default (Hong Kong bundled)",
                        "Synthetic demo",
                        "Upload CSV",
                    ],
                    index=0,
                    key="tour_source_radio",
                )
                if advanced == "Synthetic demo":
                    source = "Synthetic demo"
                    col1, col2 = st.columns(2)
                    with col1:
                        start = st.date_input(
                            "Start", dt.date(2010, 1, 1), key="tour_start"
                        )
                    with col2:
                        end = st.date_input(
                            "End", dt.date(2010, 12, 31), key="tour_end"
                        )
                elif advanced == "Upload CSV":
                    source = "Upload CSV"
                    uploaded = st.file_uploader(
                        "Your race CSV", type=["csv"]
                    )

        st.header("🏁 Locked main-test recipe")
        st.markdown(SIDEBAR_HELP["locked"])
        metric_label = METRIC_LABELS.get(prereg["metric"], prereg["metric"])
        st.markdown(
            f"- **Wave table:** `{prereg['primary_number_set']}`\n"
            f"- **Wave cutoff:** lowest **{prereg['primary_threshold_pct']:.0f}%** "
            f"of days (bet zone)\n"
            f"- **Track's cut:** **{100 * float(prereg['takeout']):.0f}%**\n"
            f"- **Surprise score:** {metric_label}\n"
            f"- **Written down:** {prereg.get('declared_on', 'see prereg.json')}"
        )
        st.caption(
            "Changing the knobs below does **not** rewrite this locked recipe ⭐. "
            "Only the locked combo counts as the official main answer."
        )

        with st.container(key="tour_run_params"):
            st.header("🏇 Run settings")
            st.caption(SIDEBAR_HELP["params"])
            number_set = st.selectbox(
                "Wave number table",
                ALL_SETS,
                index=ALL_SETS.index(prereg["primary_number_set"]),
                key="tour_number_set",
            )
            st.caption(SIDEBAR_CONTROL_CAPTIONS["number_set"])
            threshold_pct = st.slider(
                "Wave cutoff % (low = bet)",
                5.0, 100.0, float(prereg["primary_threshold_pct"]), 5.0,
                key="tour_threshold_pct",
            )
            st.caption(SIDEBAR_CONTROL_CAPTIONS["threshold_pct"])
            takeout = st.slider(
                "Track's cut",
                0.10, 0.35, float(prereg["takeout"]), 0.01,
                key="tour_takeout",
            )
            st.caption(SIDEBAR_CONTROL_CAPTIONS["takeout"])
            metric = st.selectbox(
                "Surprise score type",
                ["trifecta_novelty", "win_novelty"],
                index=0 if prereg["metric"] == "trifecta_novelty" else 1,
                format_func=lambda m: METRIC_LABELS.get(m, m),
                key="tour_metric",
            )
            st.caption(SIDEBAR_CONTROL_CAPTIONS["metric"])
            engine_seed = st.number_input(
                "Random seed",
                1, 99999, 1904,
                key="tour_engine_seed",
            )
            st.caption(SIDEBAR_CONTROL_CAPTIONS["engine_seed"])

            if source == "Synthetic demo" and start is None:
                # Defensive: dates only set inside Advanced expander.
                start = dt.date(2010, 1, 1)
                end = dt.date(2010, 12, 31)

            do_sweep = st.checkbox(
                "Try many wave cutoffs",
                value=True,
                key="tour_do_sweep",
            )
            st.caption(SIDEBAR_CONTROL_CAPTIONS["do_sweep"])
            max_lag = st.number_input(
                "Lead/lag window (days)",
                0, 60, 10,
                key="tour_max_lag",
            )
            st.caption(SIDEBAR_CONTROL_CAPTIONS["max_lag"])

        with st.container(key="tour_engine_params"):
            st.header("🎲 Picky betting")
            st.caption(SIDEBAR_HELP["engine"])
            run_engine = st.checkbox(
                "Run picky betting",
                value=True,
                key="tour_run_engine",
            )
            st.caption(SIDEBAR_CONTROL_CAPTIONS["run_engine"])
            engine_beta = st.slider(
                "Pool bias guess (1.0 = fair)",
                0.80, 1.50, 1.00, 0.05,
                key="tour_engine_beta",
            )
            st.caption(SIDEBAR_CONTROL_CAPTIONS["engine_beta"])
            engine_gate_pct = st.slider(
                "Hottest days to bet (%)",
                5.0, 100.0, 20.0, 5.0,
                key="tour_engine_gate_pct",
            )
            st.caption(SIDEBAR_CONTROL_CAPTIONS["engine_gate_pct"])
            engine_k_max = st.number_input(
                "Max tickets per race",
                1, 500, 50,
                key="tour_engine_k_max",
            )
            st.caption(SIDEBAR_CONTROL_CAPTIONS["engine_k_max"])

        st.caption(
            "Runs the 🌊 wave match test and (if enabled) 🎲 picky betting on the "
            "🐎 data above. Then open **📊 Overview** for the plain-English answer."
        )
        run = st.button("🏇 Run Analysis", type="primary", key="tour_run_button")

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
        if source == "Hong Kong (bundled)":
            runners = data.load_bundled_hk()
            label = "Hong Kong bundled (gdaley/hkracing 1997–2005)"
        elif source == "Synthetic demo":
            runners = data.synthetic_races(opts["start"], opts["end"])
            label = f"synthetic demo ({opts['start']} to {opts['end']})"
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

    st.subheader("📊 Overview")
    st.caption(TAB_INTROS["overview"])
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Races", f"{runners['race_id'].nunique():,}")
    c2.metric("Horses entered", f"{len(runners):,}")
    c3.metric("Chance score", f"{primary['permutation_p']:.4f}",
              help="Could this match happen by luck? Small (e.g. under 0.05) means unlikely by chance — not a tip.")
    c4.metric("Rank link", f"{primary['spearman_r']:+.4f}",
              help="Do surprise and the wave move together by rank? Near 0 = little match. Negative = McKenna's guess.")
    c5.metric("Days compared", f"{primary['n_days']:,}")
    st.caption(
        "**Chance score** 🎱 = how often a shuffled calendar looks this strong by luck. "
        "High (e.g. 0.2–1.0) ≈ null ☯️. Small (under ~0.05) ≈ unlikely by chance. "
        "**Rank link** near 0 = little match; McKenna guessed negative (low wave ↔ high surprise)."
    )
    st.info(_interpret_match(primary))

    with st.expander("All run settings & data summary", expanded=True):
        st.caption(
            "What this run used 🏇. Confirm the data source and locked-style knobs "
            "before reading the charts as an \"official\" answer ⭐."
        )
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("Data source", state["source_label"])
        sc2.metric("Date range", f"{runners['date'].min().date()} → {runners['date'].max().date()}")
        sc3.metric("Wave table", opts["number_set"])
        st.write(
            f"Wave cutoff {opts['threshold_pct']}%, track's cut {opts['takeout']:.0%}, "
            f"surprise type `{METRIC_LABELS.get(opts['metric'], opts['metric'])}`, "
            f"seed {opts['engine_seed']}"
        )
        if state.get("engine_summary") is not None:
            best = state["engine_summary"].dropna(subset=["roi_pct"])
            if not best.empty:
                top = best.loc[best["roi_pct"].idxmax()]
                st.caption(
                    f"Best picky strategy in this run 🎲: **{top['strategy']}** "
                    f"(return {top['roi_pct']:+.2f}%). At bias 1.0, a big positive "
                    "return would be surprising 🔮; near zero or negative is the null ☯️."
                )

    # Wider gauge column so the dial number/subtitle are not cramped.
    gc1, gc2 = st.columns([1.2, 1.8])
    with gc1:
        st.plotly_chart(
            plot_verdict_gauge(primary["permutation_p"], primary["spearman_r"]),
            use_container_width=True,
            key="overview_verdict_gauge",
        )
        st.caption(
            "Verdict dial 🎱 — green zone (under ~0.05) = unlikely by chance. "
            "Gray zone = the usual null ☯️. The big number is the chance score, not a tip."
        )
    with gc2:
        st.plotly_chart(
            animate_novelty_timewave(daily, tw),
            use_container_width=True,
            key="overview_timeline",
        )
        st.caption(
            "Blue = how weird race days were (cyan line) ✨. Purple = McKenna's wave "
            "(flipped so high means \"chaos\" 🌀 in his story). The shaded violet band "
            "is the high-chaos zone on the wave. **How to read:** if his idea worked, "
            "blue highs would tend to sit with purple highs ☯️. A messy overlap with no "
            "clear pattern is the null. Hit **Play** or drag the slider to walk through time."
        )

    oc1, oc2 = st.columns(2)
    with oc1:
        st.plotly_chart(
            plot_novelty_vs_timewave_scatter(daily, tw),
            use_container_width=True,
            key="overview_scatter",
        )
        st.caption(
            "Each dot is one day 🐴. A clear downward slope would match McKenna "
            "(high surprise on low wave) ☯️. A flat cloud = little match — the usual "
            "Hong Kong read 🎱."
        )
    with oc2:
        st.plotly_chart(
            plot_rolling_correlation(daily, tw),
            use_container_width=True,
            key="overview_rolling_corr",
        )
        st.caption(
            "Does the match come and go over time 🌙? Values near zero mean little "
            "link in that window. A brief spike is curiosity ✨, not a new main claim."
        )

    st.markdown("**🏁 Did the wave help pick better days?**")
    st.caption(
        "Wave-picked days = bet only when the wave is low 🌊. "
        "Bet every race = no filter (expect to lose about the track's cut) 🏇."
    )
    bc1, bc2 = st.columns(2)
    s = res["strategy"]
    bc1.metric("Wave-picked days", f"Return {s['roi_pct']:+.2f}%", f"Profit/loss ${s['total_pnl']:+,.0f}")
    s_all = res["bet_every_race"]
    bc2.metric("Bet every race", f"Return {s_all['roi_pct']:+.2f}%", f"Profit/loss ${s_all['total_pnl']:+,.0f}")
    st.caption(
        "Return is profit or loss as a percent of money spent. "
        "ROI near −track cut on both sides = timing did not help ☯️. "
        "Wave-picked clearly better than every-day would be interesting ✨ — rare on this data."
    )
    st.info(_interpret_timing(s, s_all, opts["takeout"]))


def render_novelty_timewave(state: dict) -> None:
    result = state["result"]
    opts = state["opts"]
    primary = result["primary"]
    daily = result["daily"]
    tw = result["timewave"]
    scores = result["scores"]

    st.subheader("🌊 Main match test")
    st.caption(TAB_INTROS["novelty"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Chance score", f"{primary['permutation_p']:.4f}",
              help="Main honesty check: could this match happen by luck?")
    c2.metric("Rank link", f"{primary['spearman_r']:+.4f}",
              help="Do surprise and the wave move together by rank?")
    c3.metric("Days compared", f"{primary['n_days']:,}")
    c4.metric("Simple linear check", f"{primary['pearson_p']:.4f}",
              help="A simpler line-fit check — not the main claim")
    st.caption(
        "We trust the **chance score** 🎱 for the main claim. "
        "High chance score + near-zero rank link = **null** ☯️ (no support). "
        "Small chance score + negative rank link = direction McKenna guessed 🍄. "
        f"Other checks are curiosity only "
        f"(rank-link chance {primary['spearman_p']:.4f}, "
        f"simple linear {primary['pearson_p']:.4f})."
    )
    st.info(_interpret_match(primary))
    st.caption(f"Engine note: {primary['interpretation']}")

    st.subheader("✨ Extra look: all wave tables")
    st.caption(
        "Same test on four number tables that build the wave 🌊 (Kelley, Watkins, "
        "and others). We raise the bar because we peeked at four versions — "
        "a \"hit\" on one table alone is weaker evidence 🎱."
    )
    st.dataframe(result["exploratory"], use_container_width=True, hide_index=True)
    st.caption(
        "Each row is one wave table. Chance score 🎱 is the honesty check; "
        "the raised bar is the same check made stricter for peeking. "
        "Mostly high chance scores across rows = still a null story ☯️."
    )

    st.subheader("✨ Daily surprise scores")
    st.caption(
        "How weird 🍄 finishes were, day by day. Higher = weirder given the odds. "
        "These numbers feed the blue line — they are not a betting tip by themselves."
    )
    dstat = series_stats(daily)
    dc1, dc2, dc3, dc4, dc5 = st.columns(5)
    dc1.metric("Average", f"{dstat['mean']:.4f}")
    dc2.metric("Spread", f"{dstat['std']:.4f}")
    dc3.metric("Lowest", f"{dstat['min']:.4f}")
    dc4.metric("Highest", f"{dstat['max']:.4f}")
    dc5.metric("Last day", f"{dstat['current']:.4f}")
    st.caption(
        "Summary of the blue surprise line ✨. Wide spread means some days were "
        "much weirder than others — expected in racing 🏇, not proof of a wave."
    )

    st.subheader("🌊 McKenna's wave (same days)")
    st.caption(
        "The calendar wave on the same days 🌌. In his story, low values = "
        "\"high chaos\" 🌀 zone — where surprise should pile up if the idea worked."
    )
    tstat = series_stats(tw)
    tc1, tc2, tc3, tc4 = st.columns(4)
    tc1.metric("Average", f"{tstat['mean']:.4f}")
    tc2.metric("Lowest", f"{tstat['min']:.4f}")
    tc3.metric("Highest", f"{tstat['max']:.4f}")
    tc4.metric("Last day", f"{tstat['current']:.4f}")
    st.caption(
        "Summary of the purple wave line 🌊. The main question is whether this "
        "line lines up with surprise — answered by the chance score 🎱 above, not "
        "by these averages alone."
    )

    resonance = result["resonance"]
    if not resonance.empty:
        st.subheader("🧿 Echo of past surprise")
        st.caption(
            "A delayed echo of past race surprise 🌙. Used to pick days in picky "
            "betting 🎲 — **not** for the main wave test. Do not read this as "
            "extra proof of McKenna's calendar 🍄."
        )
        rstat = series_stats(resonance)
        rc1, rc2, rc3, rc4, rc5 = st.columns(5)
        rc1.metric("Average", f"{rstat['mean']:.4f}")
        rc2.metric("Spread", f"{rstat['std']:.4f}")
        rc3.metric("Lowest", f"{rstat['min']:.4f}")
        rc4.metric("Highest", f"{rstat['max']:.4f}")
        rc5.metric("Last day", f"{rstat['current']:.4f}")
        st.caption(
            "Higher echo = a \"hotter\" day for the picky-betting gate 🎲. "
            "Interesting for that side experiment only ✨."
        )

    st.plotly_chart(
        animate_novelty_timewave(daily, tw),
        use_container_width=True,
        key="novelty_timeline",
    )
    st.caption(
        "Same timeline as Overview. Watch whether the two lines move opposite "
        "ways, as McKenna guessed ☯️. No clear opposite dance = null 🎱."
    )
    st.plotly_chart(
        animate_novelty_distribution(scores, metric=opts["metric"]),
        use_container_width=True,
        key="novelty_hist",
    )
    st.caption(
        "How surprise scores are spread across races 🏇. Play adds races one batch "
        "at a time. A wide spread is normal; it does not mean the wave matched 🎱."
    )

    st.subheader("🔮 Extra pictures of the match")
    st.caption(
        "More views of how surprise and the wave relate ☯️. "
        "The official answer still comes from the chance score 🎱 above — "
        "pretty pictures can mislead."
    )
    st.plotly_chart(
        animate_scatter_reveal(daily, tw),
        use_container_width=True,
        key="novelty_scatter_reveal",
    )
    st.caption(
        "Each dot is one day — Play reveals them in date order 🐴. "
        "Flat cloud = little match (null) ☯️. Clear downward slope = direction "
        "McKenna guessed 🍄."
    )
    nc1, nc2 = st.columns(2)
    with nc1:
        st.plotly_chart(
            plot_novelty_vs_timewave_scatter(daily, tw),
            use_container_width=True,
            key="novelty_scatter",
        )
        st.caption(
            "One dot per day. Flat cloud = little match (null) ☯️. "
            "Clear downward slope = direction McKenna guessed 🍄."
        )
    with nc2:
        st.plotly_chart(
            plot_rolling_correlation(daily, tw),
            use_container_width=True,
            key="novelty_rolling_corr",
        )
        st.caption(
            "Does the link strengthen or fade in different periods 🌙? "
            "Mostly near zero = still a null overall 🎱."
        )

    st.plotly_chart(
        plot_novelty_calendar_heatmap(daily),
        use_container_width=True,
        key="novelty_calendar",
    )
    st.caption(
        "Surprise by calendar day 🌌. Redder = weirder finishes that day of the "
        "month. Seasonal color is background — not the main wave claim."
    )

    st.subheader("🐎 What the races look like")
    st.caption(
        "Background on field size and favorites 🏇 — context for the surprise "
        "scores, not the main wave test."
    )
    st.plotly_chart(
        plot_field_size_novelty(scores, metric=opts["metric"]),
        use_container_width=True,
        key="field_size_box",
    )
    st.caption(
        "Bigger fields look \"weirder\" in raw scores, so we compare within "
        "similar field sizes before averaging by day. That keeps the main test fair ☯️."
    )
    st.plotly_chart(
        plot_winner_profile(scores),
        use_container_width=True,
        key="winner_profile",
    )
    st.caption(
        "Left: how long winners paid 🐴. Right: how often the favorite won each "
        "month. Useful market context — not evidence for or against the wave 🌊."
    )

    if result["lag"] is not None:
        lag = result["lag"]
        best = lag.loc[lag["spearman_r"].abs().idxmax()]
        st.subheader("🌙 Does surprise lead or lag?")
        st.caption(
            "Maybe surprise peaks a few days before or after the wave 🌀. "
            "Curiosity only — not the main claim. A peak at 0 days with a weak "
            "link is still a null for timing offsets 🎱."
        )
        st.write(
            f"Strongest link at a shift of **{int(best['lag_days'])}** days "
            f"(rank link = {best['spearman_r']:+.4f})"
        )
        st.plotly_chart(animate_lead_lag(lag), use_container_width=True, key="lead_lag")
        st.caption(
            "The peak shows the shift (in days) with the strongest link 🌙. "
            "A tall peak far from zero would be interesting ✨; a flat line is null 🎱."
        )
        with st.expander("Lead/lag numbers"):
            st.dataframe(lag, use_container_width=True, hide_index=True)
            st.caption("One row per day-shift tried. Exploratory only 🔮.")

    with st.expander("Race-level scores (all columns)", expanded=False):
        display_cols = [
            c for c in scores.columns
            if c in scores.columns
        ]
        st.dataframe(scores[display_cols], use_container_width=True, hide_index=True)
        st.caption(
            "One row per race with the surprise scores used above 🏇. "
            "For checking the math inputs — not a tip sheet 🔮."
        )


def render_backtest(state: dict) -> None:
    result = state["result"]
    opts = state["opts"]
    res = result["backtest"]
    mckenna_daily = state.get("mckenna_daily_pnl")

    st.subheader("🏁 Did timing help?")
    st.caption(TAB_INTROS["backtest"])
    for label, key in [("Wave-picked days", "strategy"), ("Bet every race", "bet_every_race")]:
        s = res[key]
        st.markdown(f"**{label}**")
        if key == "strategy":
            st.caption(
                "Only races on low-wave days 🌊. If the wave idea helped, this "
                "block should look clearly better than \"Bet every race\" 🏇."
            )
        else:
            st.caption(
                "Same ticket idea with no day filter — the baseline 🏁. "
                "Expect a return near −track cut when there is no edge ☯️."
            )
        bc1, bc2, bc3, bc4, bc5, bc6 = st.columns(6)
        bc1.metric("Races", f"{s['races']:,}")
        bc2.metric("Money spent", f"${s['total_cost']:,.0f}")
        bc3.metric("Money returned", f"${s['total_payout']:,.0f}")
        bc4.metric("Profit/loss", f"${s['total_pnl']:+,.0f}")
        bc5.metric("Return %", f"{s['roi_pct']:+.2f}%")
        bc6.metric("Winning races", f"{s['hit_profit_pct']:.1f}%")
        st.caption(
            "Return % is profit or loss divided by money spent 🏇. "
            "Winning races is the share of races that paid more than they cost. "
            "A high win rate with a bad return still loses money overall."
        )

    st.info(_interpret_timing(res["strategy"], res["bet_every_race"], opts["takeout"]))

    st.metric("Wave cutoff value", f"{res['threshold_wave_value']:.6f}")
    src_counts = res["per_race"]["payout_source"].value_counts().to_dict()
    st.caption(
        f"Wave cutoff value is the wave level that marks \"low enough to bet\" 🌊 "
        f"for this run's cutoff %. Payout sources: {src_counts}. "
        "Real dividends beat modeled ones when both exist ⭐."
    )

    st.plotly_chart(
        animate_cumulative_pnl(res["per_race"], mckenna_daily),
        use_container_width=True,
        key="cum_pnl",
    )
    st.caption(
        "Running profit or loss over time 🏁. Play walks race by race. "
        "**If wave timing helped**, the green (wave-picked) line should stay "
        "clearly above the red (every-day) one. Lines that both drift down near "
        "the track's cut = null ☯️."
    )

    st.subheader("🌀 Risk and spread")
    st.caption(
        "How bumpy the money ride was 🏇 — not just the final total. "
        "A slightly better average with huge drawdowns is still a bad ride."
    )
    rc1, rc2 = st.columns(2)
    with rc1:
        st.plotly_chart(
            plot_pnl_distribution(res["per_race"]),
            use_container_width=True,
            key="pnl_violin",
        )
        st.caption(
            "Shape of per-race wins and losses on wave-picked days vs other days ☯️. "
            "Similar shapes = timing did not change the ride much."
        )
    with rc2:
        st.plotly_chart(
            animate_drawdown(res["per_race"]),
            use_container_width=True,
            key="drawdown",
        )
        st.caption(
            "How far below its best point the running total fell 🏁. "
            "Play walks the drawdown over time. Deeper dips = a bumpier, "
            "riskier path even if the end looks okay."
        )
    st.plotly_chart(
        plot_monthly_pnl_heatmap(res["per_race"]),
        use_container_width=True,
        key="monthly_pnl_heatmap",
    )
    st.caption(
        "Green months made money on wave-picked days; red months lost 🏇. "
        "A checkerboard of red and green with no lasting green streak = no "
        "reliable timing edge ☯️."
    )

    if result["sweep"] is not None:
        st.subheader("🔮 What if we change the cutoff?")
        st.caption(
            "Returns across many wave cutoffs ✨. Good for intuition — "
            "not a replacement for the locked official cutoff ⭐. "
            "Shopping for the prettiest bump is how you fool yourself 🎱."
        )
        st.plotly_chart(plot_sweep(result["sweep"]), use_container_width=True, key="sweep")
        st.caption(
            "A bump at one cutoff is curiosity ✨, not a new official result. "
            "A flat line near −track cut across cutoffs = null everywhere ☯️."
        )
        with st.expander("Cutoff sweep numbers"):
            st.dataframe(result["sweep"], use_container_width=True, hide_index=True)
            st.caption("One row per cutoff tried. Exploratory only 🔮.")

    with st.expander("Per-race detail"):
        st.dataframe(res["per_race"], use_container_width=True, hide_index=True)
        st.caption(
            "One row per race with cost, payout, and whether that day was "
            "wave-picked 🏇. Use this to audit a strange month — not to cherry-pick 🧿."
        )


def render_mckenna_engine(state: dict) -> None:
    opts = state["opts"]
    runners = state["runners"]
    result = state["result"]
    engine_summary = state.get("engine_summary")
    hexagram = state.get("hexagram")

    st.subheader("🎲 Picky betting")
    st.caption(TAB_INTROS["engine"])
    st.info(
        "**Pool bias guess** 🃏 is an assumption about whether the pool overbets favorites. "
        "At 1.0 (fair prices ☯️), picky betting should find no edge — that is the honest null 🎱. "
        "A win at other values only means \"if the pool were biased that way,\" not that "
        "it is."
    )

    ec1, ec2, ec3, ec4 = st.columns(4)
    ec1.metric("Bias guess", f"{opts['engine_beta']:.2f}")
    ec2.metric("Hottest days %", f"{opts['engine_gate_pct']:.0f}")
    ec3.metric("Max tickets", opts["engine_k_max"])
    ec4.metric("Seed", opts["engine_seed"])
    st.caption(
        "These are the sidebar settings for this run 🎲. "
        "Bias 1.0 is the honest fair-price case ☯️. Lower \"hottest days %\" = pickier."
    )

    if hexagram is not None:
        st.markdown(f"### 🃏 Last coin-cast pick: pattern **{hexagram}** / 64")
        st.caption(
            "A repeatable random pick 🎴 used when too many tickets look good. "
            "Same seed → same pattern. It is a tie-breaker, not a prophecy 🔮."
        )

    if engine_summary is None:
        st.info("Turn on **Run picky betting** 🎲 in the sidebar, then run again 🏇.")
        return

    st.info(_interpret_engine(opts, engine_summary))

    st.dataframe(engine_summary, use_container_width=True, hide_index=True)
    st.caption(
        "Each row is a betting rule 🎲. Compare returns — at bias 1.0, none should "
        "look like a free lunch ☯️. Big positives only under bias ≠ 1.0 are "
        "\"interesting if that guess were true,\" not proof 🎱."
    )

    for _, row in engine_summary.iterrows():
        with st.expander(f"Rule: {row['strategy']}", expanded=False):
            sc1, sc2, sc3, sc4, sc5, sc6 = st.columns(6)
            sc1.metric("Races", f"{int(row['races']):,}")
            sc2.metric("Tickets", f"{int(row['tickets']):,}")
            sc3.metric("Money spent", f"${row['cost']:,.2f}")
            sc4.metric("Money returned", f"${row['payout']:,.2f}")
            sc5.metric("Profit/loss", f"${row['pnl']:+,.2f}")
            roi = row["roi_pct"]
            sc6.metric("Return %", f"{roi:+.2f}%" if pd.notna(roi) else "N/A")
            st.caption(
                "Detail for this one rule 🃏. Return near zero or negative at bias "
                "1.0 is the expected null ☯️; a large positive would be surprising 🔮."
            )

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
    st.caption(
        "The line is the echo of past surprise 🧿. Marks show the hottest days we "
        "would bet on under the gate %. Fewer marks = pickier. This chart shows "
        "*when* we bet, not whether we made money 🏇."
    )

    with st.spinner("Building bias comparison animation …"):
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
    st.caption(
        "Slider steps through bias guesses from 1.00 to 1.20 🎱. "
        "Play cycles returns for each rule. **Only 1.0 is the fair-price case** ☯️ — "
        "returns that appear only at higher bias are \"if favorites were overbet,\" "
        "not a claim that they are."
    )


def render_raw_data(state: dict) -> None:
    runners = state["runners"]
    result = state["result"]
    scores = result["scores"]
    daily = result["daily"]

    st.subheader("📁 Race data")
    st.caption(TAB_INTROS["raw"])
    st.write(f"First 100 rows ({len(runners):,} total)")
    st.dataframe(runners.head(100), use_container_width=True, hide_index=True)
    st.caption(
        "Each row is one horse in one race 🐴 — the raw input to the analysis. "
        "If something looks wrong here, the charts above are wrong too."
    )

    st.subheader("📥 Downloads")
    st.caption(
        "Save the scored races, daily surprise line, or picky-betting summary 📁. "
        "Useful for checking our work or plotting elsewhere — not a tip feed 🔮."
    )
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

    with st.expander("Column types"):
        st.json({c: str(runners[c].dtype) for c in runners.columns})
        st.caption(
            "Technical column types for the race table above 🐎. "
            "For debugging imports — skip unless you are fixing a CSV."
        )


def main() -> None:
    st.set_page_config(
        page_title="🐴 McKenna Derby",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_app_css()
    require_auth()
    with st.container(key="tour_app_header"):
        st.title("🐴 McKenna Derby")
        st.caption(
            "Do weird 🐎 horse-race days line up with Terence McKenna's 🌊 "
            "Timewave Zero? Mystique in the story — honest numbers in the charts. "
            "Click **🏇 Run Analysis** to find out 🔮."
        )

    prereg = load_prereg()
    opts = render_sidebar(prereg)

    def _render_result_tabs(state: dict) -> None:
        tab_over, tab_nt, tab_bt, tab_eng, tab_raw = st.tabs(TAB_LABELS)
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

    if opts is None:
        if st.session_state.get("analysis"):
            with st.container(key="tour_empty_intro"):
                st.caption(
                    "Weird 🐎 race days vs McKenna's 🌊 calendar wave. "
                    "Change the sidebar and click **🏇 Run Analysis** to refresh."
                )
            st.info(
                "Showing the last run. Change the sidebar and click "
                "**🏇 Run Analysis** to refresh ✨."
            )
            _render_result_tabs(st.session_state["analysis"])
            maybe_start_tour(has_results=True)
        else:
            with st.container(key="tour_empty_intro"):
                st.markdown(EMPTY_STATE_MARKDOWN)
            maybe_start_tour(has_results=False)
        return

    loaded = load_runners(opts)
    if loaded is None:
        return
    runners, source_label = loaded

    with st.container(key="tour_empty_intro"):
        st.caption(
            "Weird 🐎 race days vs McKenna's 🌊 calendar wave 🍄."
        )

    n_races = runners["race_id"].nunique()
    st.success(
        f"Loaded **{source_label}** 🏇: {n_races:,} races, {len(runners):,} horses "
        f"({runners['date'].min().date()} → {runners['date'].max().date()})"
    )

    with st.spinner("Running analysis …"):
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
        with st.spinner("Running picky betting (four rules) …"):
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
        with st.spinner("Computing picky-betting money series …"):
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

    _render_result_tabs(state)
    maybe_start_tour(has_results=True)


if __name__ == "__main__":
    main()

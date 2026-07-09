"""Regression tests for dashboard.py.

These are static-analysis tests for known-bad patterns rather than runtime
imports, because dashboard.py requires a live Streamlit context. If/when
the dashboard's helpers are factored into testable functions, this file
should grow runtime tests too.
"""

from pathlib import Path

DASHBOARD_PATH = Path(__file__).resolve().parents[1] / "dashboard.py"
DASHBOARD_SOURCE = DASHBOARD_PATH.read_text()


def test_dashboard_no_hardcoded_gate_20():
    """Resonance gate must not hard-code ``100.0 - 20.0``."""
    assert "100.0 - 20.0" not in DASHBOARD_SOURCE, (
        "dashboard.py still contains hard-coded `100.0 - 20.0`; "
        "the resonance gate is ignoring the gate_pct argument"
    )


def test_dashboard_uses_engine_gate_pct():
    """run_pipeline / engine viz should reference engine_gate_pct."""
    assert "engine_gate_pct" in DASHBOARD_SOURCE
    assert "_compute_gated_days" in DASHBOARD_SOURCE


def test_dashboard_passes_seed_to_compare():
    """seed must reach compare.compare (was a dead run_pipeline parameter)."""
    assert "compare.compare(daily, number_set=number_set, seed=seed)" in DASHBOARD_SOURCE


def test_dashboard_does_not_double_zscore_novelty():
    """animate_novelty_timewave should plot daily novelty as-is."""
    assert "Novelty z-score" not in DASHBOARD_SOURCE
    assert "Daily surprise" in DASHBOARD_SOURCE


def test_dashboard_observatory_dark_theme():
    """Dark observatory palette + Plotly theme helper should be wired in."""
    assert "def apply_plotly_theme" in DASHBOARD_SOURCE
    assert 'template="plotly_dark"' in DASHBOARD_SOURCE
    assert "def inject_app_css" in DASHBOARD_SOURCE
    assert "PALETTE" in DASHBOARD_SOURCE
    assert "plot_verdict_gauge" in DASHBOARD_SOURCE
    assert "animate_scatter_reveal" in DASHBOARD_SOURCE
    assert "animate_drawdown" in DASHBOARD_SOURCE
    assert "inject_app_css()" in DASHBOARD_SOURCE
    assert "return apply_plotly_theme(fig)" in DASHBOARD_SOURCE


def test_apply_plotly_theme_sets_dark_template():
    """Runtime check: apply_plotly_theme stamps plotly_dark on a figure."""
    import plotly.graph_objects as go

    ns: dict = {"go": go}
    src = DASHBOARD_SOURCE
    # Extract PALETTE + apply_plotly_theme only (no Streamlit import needed).
    start = src.index("PALETTE = {")
    end = src.index("\n# ---------------------------------------------------------------------------\n# Plain-English copy")
    code = "from __future__ import annotations\n" + src[start:end]
    exec(compile(code, "dashboard_theme.py", "exec"), ns)

    fig = go.Figure(go.Scatter(x=[1, 2], y=[3, 4]))
    themed = ns["apply_plotly_theme"](fig)
    assert themed.layout.template.layout.paper_bgcolor is not None or (
        themed.layout.template == "plotly_dark"
        or str(themed.layout.template) == "plotly_dark"
        or getattr(themed.layout.template, "layout", None) is not None
    )
    # Explicit paper/plot colors from our palette
    assert themed.layout.paper_bgcolor == ns["PALETTE"]["paper"]
    assert themed.layout.plot_bgcolor == ns["PALETTE"]["plot"]
    assert themed.layout.font.color == ns["PALETTE"]["text"]


def test_plot_verdict_gauge_no_competing_titles():
    """Gauge must not stack layout title + indicator title (screenshot bug)."""
    import plotly.graph_objects as go

    ns: dict = {"go": go}
    src = DASHBOARD_SOURCE
    start = src.index("PALETTE = {")
    theme_end = src.index("\ndef inject_app_css")
    g_start = src.index("def plot_verdict_gauge")
    g_end = src.index("\ndef animate_scatter_reveal")
    code = (
        "from __future__ import annotations\n"
        + src[start:theme_end]
        + "\n"
        + src[g_start:g_end]
    )
    exec(compile(code, "dashboard_gauge.py", "exec"), ns)

    fig = ns["plot_verdict_gauge"](0.4120, 0.0080)
    layout_title = getattr(fig.layout.title, "text", None)
    ind_title = fig.data[0].title
    ind_title_text = getattr(ind_title, "text", None) if ind_title is not None else None
    assert not layout_title, f"layout title should be empty, got {layout_title!r}"
    assert not ind_title_text, f"indicator title should be empty, got {ind_title_text!r}"
    assert "rank link" in (fig.data[0].number.suffix or "")
    assert abs(float(fig.data[0].value) - 0.4120) < 1e-9
    # Theme must preserve the gauge's tighter top margin (not overwrite to 64).
    assert fig.layout.margin.t == 36
    assert fig.layout.height == 340


def test_dashboard_has_plain_english_empty_state_copy():
    """Empty state should explain the app in plain English (no About tab)."""
    assert "EMPTY_STATE_MARKDOWN" in DASHBOARD_SOURCE
    assert "render_about" not in DASHBOARD_SOURCE
    assert "ABOUT_MARKDOWN" not in DASHBOARD_SOURCE
    assert "What is this?" in DASHBOARD_SOURCE
    assert "Run Analysis" in DASHBOARD_SOURCE
    assert "TAB_INTROS" in DASHBOARD_SOURCE
    assert "TAB_LABELS" in DASHBOARD_SOURCE
    assert "Surprise vs the wave" in DASHBOARD_SOURCE
    assert "Did timing help?" in DASHBOARD_SOURCE
    assert '"About"' not in DASHBOARD_SOURCE
    assert 'key="tour_empty_intro"' in DASHBOARD_SOURCE
    assert "Advanced options" in DASHBOARD_SOURCE
    assert "Wave number table" in DASHBOARD_SOURCE
    assert "Pool bias guess" in DASHBOARD_SOURCE
    # Mystique framing for newcomers
    assert "WHO_IS_MCKENNA" in DASHBOARD_SOURCE
    assert "mystical genius" in DASHBOARD_SOURCE
    assert "Timewave Zero" in DASHBOARD_SOURCE
    assert "I Ching" in DASHBOARD_SOURCE
    assert "64 hexagrams" in DASHBOARD_SOURCE
    assert "low wave" in DASHBOARD_SOURCE and "high chaos" in DASHBOARD_SOURCE
    assert "2012" in DASHBOARD_SOURCE
    assert "Who is Terence McKenna?" in DASHBOARD_SOURCE


def test_dashboard_sidebar_teaches_the_experiment():
    """Sidebar copy should explain the point and each control in plain English."""
    assert "SIDEBAR_INTRO" in DASHBOARD_SOURCE
    assert "SIDEBAR_CONTROL_CAPTIONS" in DASHBOARD_SOURCE
    assert "What this software does" in DASHBOARD_SOURCE
    assert "open **📊 Overview**" in DASHBOARD_SOURCE or "open **Overview**" in DASHBOARD_SOURCE
    assert "surprising" in DASHBOARD_SOURCE and "race days line up" in DASHBOARD_SOURCE
    assert "calendar wave" in DASHBOARD_SOURCE or "Timewave Zero" in DASHBOARD_SOURCE
    assert "What is the Hong Kong data?" in DASHBOARD_SOURCE
    assert "Jockey Club" in DASHBOARD_SOURCE
    assert "about 6,000 races" in DASHBOARD_SOURCE
    assert "Wave cutoff % (low = bet)" in DASHBOARD_SOURCE
    assert "Track's cut" in DASHBOARD_SOURCE
    assert "Surprise score type" in DASHBOARD_SOURCE
    assert "Random seed" in DASHBOARD_SOURCE
    assert "Try many wave cutoffs" in DASHBOARD_SOURCE
    assert "Lead/lag window" in DASHBOARD_SOURCE
    assert "Hottest days to bet" in DASHBOARD_SOURCE
    assert "Max tickets per race" in DASHBOARD_SOURCE
    assert "Locked main-test recipe" in DASHBOARD_SOURCE
    assert "What is this section?" in DASHBOARD_SOURCE
    assert "Official test settings" not in DASHBOARD_SOURCE
    assert "View locked settings" not in DASHBOARD_SOURCE
    assert "hexagram-style" in DASHBOARD_SOURCE
    # Sidebar controls should use visible captions, not hover help=
    sidebar_start = DASHBOARD_SOURCE.index("def render_sidebar")
    sidebar_end = DASHBOARD_SOURCE.index("\ndef load_runners")
    sidebar_src = DASHBOARD_SOURCE[sidebar_start:sidebar_end]
    assert "help=" not in sidebar_src
    assert 'st.caption(SIDEBAR_CONTROL_CAPTIONS["number_set"])' in sidebar_src
    assert "Who is Terence McKenna?" in sidebar_src
    assert "WHO_IS_MCKENNA" in sidebar_src


def test_dashboard_wires_first_visit_tour():
    """Dashboard should launch the guided tour and expose replay + anchors."""
    assert "maybe_start_tour" in DASHBOARD_SOURCE
    assert "render_tour_sidebar_controls" in DASHBOARD_SOURCE
    assert 'key="tour_app_header"' in DASHBOARD_SOURCE
    assert 'key="tour_empty_intro"' in DASHBOARD_SOURCE
    assert 'key="tour_data_source"' in DASHBOARD_SOURCE
    assert 'key="tour_run_button"' in DASHBOARD_SOURCE
    assert "from mckenna_derby.tour import" in DASHBOARD_SOURCE


def test_dashboard_blurbs_under_main_views():
    """Major charts and metric blocks should have captions underneath."""
    for needle in (
        "Blue = how weird race days were",
        "Each dot is one day",
        "Return is profit or loss",
        "If wave timing helped",
        "Green months made money",
        "Each row is a betting rule",
        "Each row is one horse in one race",
        "**So what?**",
        "_interpret_match",
        "_interpret_timing",
        "_interpret_engine",
        "boring baseline",
        "no free lunch",
        "usual honest answer",
        "fair-price case",
        "Sorry man",
        "Far out",
        "old lady",
        "bummer vibes",
        "gonna be broke",
        "if the wave flops",
    ):
        assert needle in DASHBOARD_SOURCE, f"missing blurb: {needle}"


def test_interpret_helpers_plain_english():
    """Interpretation helpers should label null vs interesting in hippie plain English."""
    assert "def _interpret_match" in DASHBOARD_SOURCE
    assert "def _interpret_timing" in DASHBOARD_SOURCE
    assert "def _interpret_engine" in DASHBOARD_SOURCE

    # Exec helpers alone (dashboard.py needs Streamlit; avoid importing the page).
    ns: dict = {"pd": __import__("pandas")}
    src = DASHBOARD_SOURCE
    start = src.index("def _interpret_match")
    end = src.index("\n# ---------------------------------------------------------------------------\n# Auth & config")
    # Python 3.9 needs postponed annotations for ``X | None`` in the helpers.
    code = "from __future__ import annotations\n" + src[start:end]
    exec(compile(code, "dashboard_helpers.py", "exec"), ns)

    # Mild null (p under 0.40): soft bummer.
    mild_null = ns["_interpret_match"]({"permutation_p": 0.12, "spearman_r": -0.01})
    assert "null" in mild_null.lower()
    assert "So what?" in mild_null
    assert "bummer" in mild_null.lower()
    assert "sorry man" in mild_null.lower()

    # Dead null (high p): escalate to old lady / broke lament.
    null_txt = ns["_interpret_match"]({"permutation_p": 0.42, "spearman_r": -0.01})
    assert "null" in null_txt.lower()
    assert "So what?" in null_txt
    assert "old lady" in null_txt.lower()
    assert "broke" in null_txt.lower()
    assert "0.4200" in null_txt and "-0.0100" in null_txt

    hit_txt = ns["_interpret_match"]({"permutation_p": 0.01, "spearman_r": -0.3})
    assert "interesting" in hit_txt.lower() or "McKenna" in hit_txt
    assert "far out" in hit_txt.lower()

    timing = ns["_interpret_timing"](
        {"roi_pct": -18.0}, {"roi_pct": -17.5}, 0.18
    )
    assert "baseline" in timing.lower() or "timing" in timing.lower()
    assert "bummer" in timing.lower()
    assert "old lady" in timing.lower()

    timing_hurt = ns["_interpret_timing"](
        {"roi_pct": -5.87}, {"roi_pct": 1.95}, 0.18
    )
    assert "null/negative" in timing_hurt.lower()
    assert "old lady" in timing_hurt.lower()
    assert "broke" in timing_hurt.lower()
    assert "-5.87%" in timing_hurt and "+1.95%" in timing_hurt

    # Mild fair-pool null (near-zero ROI).
    engine_mild = ns["_interpret_engine"](
        {"engine_beta": 1.0},
        ns["pd"].DataFrame([{"strategy": "demo", "roi_pct": -1.0, "tickets": 10}]),
    )
    assert "null" in engine_mild.lower() or "free lunch" in engine_mild.lower()
    assert "bummer" in engine_mild.lower() or "sorry man" in engine_mild.lower()

    # Really dead fair-pool (bad ROI): longer lament.
    engine = ns["_interpret_engine"](
        {"engine_beta": 1.0},
        ns["pd"].DataFrame([{"strategy": "demo", "roi_pct": -5.0, "tickets": 0}]),
    )
    assert "null" in engine.lower() or "free lunch" in engine.lower()
    assert "old lady" in engine.lower()
    assert "broke" in engine.lower()
    assert "-5.00%" in engine
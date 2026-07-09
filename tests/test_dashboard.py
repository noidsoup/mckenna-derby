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


def test_dashboard_sidebar_teaches_the_experiment():
    """Sidebar copy should explain the point and each control in plain English."""
    assert "SIDEBAR_INTRO" in DASHBOARD_SOURCE
    assert "What this software does" in DASHBOARD_SOURCE
    assert "surprising race days line up" in DASHBOARD_SOURCE
    assert "calendar wave" in DASHBOARD_SOURCE
    assert "Wave cutoff % (low = bet)" in DASHBOARD_SOURCE
    assert "Track's cut" in DASHBOARD_SOURCE
    assert "Surprise score type" in DASHBOARD_SOURCE
    assert "Random seed" in DASHBOARD_SOURCE
    assert "Try many wave cutoffs" in DASHBOARD_SOURCE
    assert "Lead/lag window" in DASHBOARD_SOURCE
    assert "Hottest days to bet" in DASHBOARD_SOURCE
    assert "Max tickets per race" in DASHBOARD_SOURCE
    assert "Official test settings" in DASHBOARD_SOURCE
    assert "View locked settings" in DASHBOARD_SOURCE
    assert "open **Overview**" in DASHBOARD_SOURCE


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
    ):
        assert needle in DASHBOARD_SOURCE, f"missing blurb: {needle}"


def test_interpret_helpers_plain_english():
    """Interpretation helpers should label null vs interesting without jargon dumps."""
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

    null_txt = ns["_interpret_match"]({"permutation_p": 0.42, "spearman_r": -0.01})
    assert "null" in null_txt.lower()
    assert "So what?" in null_txt

    hit_txt = ns["_interpret_match"]({"permutation_p": 0.01, "spearman_r": -0.3})
    assert "interesting" in hit_txt.lower() or "McKenna" in hit_txt

    timing = ns["_interpret_timing"](
        {"roi_pct": -18.0}, {"roi_pct": -17.5}, 0.18
    )
    assert "baseline" in timing.lower() or "timing" in timing.lower()

    engine = ns["_interpret_engine"](
        {"engine_beta": 1.0},
        ns["pd"].DataFrame([{"strategy": "demo", "roi_pct": -5.0}]),
    )
    assert "null" in engine.lower() or "free lunch" in engine.lower()
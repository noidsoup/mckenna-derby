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
    ):
        assert needle in DASHBOARD_SOURCE, f"missing blurb: {needle}"
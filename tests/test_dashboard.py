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
    assert "Daily novelty" in DASHBOARD_SOURCE


def test_dashboard_has_plain_english_about_copy():
    """Landing / About tab should explain the app in plain English."""
    assert "ABOUT_MARKDOWN" in DASHBOARD_SOURCE
    assert "render_about" in DASHBOARD_SOURCE
    assert "What is this?" in DASHBOARD_SOURCE
    assert "Principles we stick to" in DASHBOARD_SOURCE
    assert "TAB_INTROS" in DASHBOARD_SOURCE
    assert '"About"' in DASHBOARD_SOURCE


def test_dashboard_wires_first_visit_tour():
    """Dashboard should launch the guided tour and expose replay + anchors."""
    assert "maybe_start_tour" in DASHBOARD_SOURCE
    assert "render_tour_sidebar_controls" in DASHBOARD_SOURCE
    assert 'key="tour_app_header"' in DASHBOARD_SOURCE
    assert 'key="tour_about_panel"' in DASHBOARD_SOURCE
    assert 'key="tour_data_source"' in DASHBOARD_SOURCE
    assert 'key="tour_run_button"' in DASHBOARD_SOURCE
    assert "from mckenna_derby.tour import" in DASHBOARD_SOURCE

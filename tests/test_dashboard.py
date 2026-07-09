"""Regression tests for dashboard.py.

These are static-analysis tests for known-bad patterns rather than runtime
imports, because dashboard.py requires a live Streamlit context. If/when
the dashboard's helpers are factored into testable functions, this file
should grow runtime tests too.
"""

from pathlib import Path

DASHBOARD_PATH = Path(__file__).resolve().parents[1] / "dashboard.py"
DASHBOARD_SOURCE = DASHBOARD_PATH.read_text()


def test_dashboard_uses_gate_pct_not_magic_20():
    """Regression: run_pipeline must use the gate_pct argument, not a
    hard-coded ``100.0 - 20.0`` constant.

    The bug was that the visualization path bypassed the sidebar input
    and silently used 20% regardless of what the user picked.
    """
    assert "100.0 - 20.0" not in DASHBOARD_SOURCE, (
        "dashboard.py still contains hard-coded `100.0 - 20.0`; "
        "the resonance gate is ignoring the gate_pct argument"
    )


def test_dashboard_uses_threshold_pct_in_run_pipeline():
    """Verify the run_pipeline function references threshold_pct in its gate cutoff."""
    assert "100.0 - threshold_pct" in DASHBOARD_SOURCE, (
        "run_pipeline should compute cutoff as np.percentile(..., 100.0 - threshold_pct)"
    )

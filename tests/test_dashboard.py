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


def test_dashboard_clipart_and_extra_animations():
    """Local SVG/GIF clipart + randomized rows + click-dismiss + animated charts."""
    assert "from mckenna_derby.assets" in DASHBOARD_SOURCE
    assert "def render_clipart_row" in DASHBOARD_SOURCE
    assert "def pick_random_assets" in DASHBOARD_SOURCE or "pick_random_assets" in DASHBOARD_SOURCE
    assert "clipart_seed" in DASHBOARD_SOURCE
    assert "ensure_clipart_seed" in DASHBOARD_SOURCE
    assert "Shuffle stickers" not in DASHBOARD_SOURCE
    assert "render_shuffle_stickers_button" not in DASHBOARD_SOURCE
    assert "mckenna-sticker" in DASHBOARD_SOURCE
    assert "inject_sticker_click_js" in DASHBOARD_SOURCE
    assert "inject_scroll_autoplay_js" in DASHBOARD_SOURCE
    assert "inject_null_sparkle_js" in DASHBOARD_SOURCE
    assert "render_interpret_info" in DASHBOARD_SOURCE
    assert "_is_null_interpret_blurb" in DASHBOARD_SOURCE
    assert "md-null-sparkle" in DASHBOARD_SOURCE
    assert "md-metric-bounce" in DASHBOARD_SOURCE
    assert "md-bg-shift" in DASHBOARD_SOURCE
    assert "md-btn-glow" in DASHBOARD_SOURCE
    assert "md-tab-fade" in DASHBOARD_SOURCE
    assert "md-confetti-rain" in DASHBOARD_SOURCE
    assert "md-sticker-pop-in" in DASHBOARD_SOURCE
    assert "RESPAWN_MS" in DASHBOARD_SOURCE
    assert "respawn(el)" in DASHBOARD_SOURCE
    assert "IntersectionObserver" in DASHBOARD_SOURCE
    assert 'dataset.autoplayed' in DASHBOARD_SOURCE or 'data-autoplayed' in DASHBOARD_SOURCE or "autoplayed" in DASHBOARD_SOURCE
    assert "in-view" in DASHBOARD_SOURCE
    assert "_SCROLL_AUTOPLAY_JS" in DASHBOARD_SOURCE
    assert "_NULL_SPARKLE_JS" in DASHBOARD_SOURCE
    assert "md-exit-fly-left" in DASHBOARD_SOURCE
    assert "md-exit-spin-out" in DASHBOARD_SOURCE
    assert "md-exit-shatter" in DASHBOARD_SOURCE
    assert "md-clipart-anim-bobble" in DASHBOARD_SOURCE
    assert "prefers-reduced-motion" in DASHBOARD_SOURCE
    assert "def animate_odds_decile_roi" in DASHBOARD_SOURCE
    assert "def animate_hexagram_slots" in DASHBOARD_SOURCE
    assert "def plot_vibe_meter" in DASHBOARD_SOURCE
    assert "def animate_rolling_correlation" in DASHBOARD_SOURCE
    assert "def animate_monthly_pnl_heatmap" in DASHBOARD_SOURCE
    assert "MAX_ANIM_FRAMES" in DASHBOARD_SOURCE
    assert "render_clipart_row(" in DASHBOARD_SOURCE
    assert 'slot="header"' in DASHBOARD_SOURCE
    assert 'slot="empty_state"' in DASHBOARD_SOURCE
    assert "ensure_clipart_seed(reshuffle=True)" in DASHBOARD_SOURCE
    assert "overview_vibe_meter" in DASHBOARD_SOURCE
    assert "animate_odds_decile_roi(runners)" in DASHBOARD_SOURCE
    assert "animate_rolling_correlation(daily, tw)" in DASHBOARD_SOURCE
    assert "animate_monthly_pnl_heatmap" in DASHBOARD_SOURCE

    from mckenna_derby.assets import (
        CLIPART,
        CLIPART_GIF,
        CLIPART_SVG,
        clipart_path,
        list_clipart_names,
        pick_random_assets,
    )

    assert len(CLIPART_SVG) >= 10
    assert len(CLIPART_GIF) >= 4
    assert len(list_clipart_names()) >= 14

    for name in (
        "horse",
        "yin_yang",
        "mushroom",
        "crystal_ball",
        "eight_ball",
        "finish_flag",
        "peace",
        "vw_bus",
        "rainbow",
        "star",
        "bounce_mushroom",
        "spin_yinyang",
    ):
        assert name in CLIPART
        p = clipart_path(name)
        assert p.exists(), name
        assert p.suffix in {".svg", ".gif"}
        assert p.stat().st_size > 50
        if p.suffix == ".gif":
            assert p.stat().st_size < 50_000

    a = pick_random_assets(4, seed=42)
    b = pick_random_assets(4, seed=42)
    c = pick_random_assets(4, seed=99)
    assert len(a) == 4
    assert [x["name"] for x in a] == [x["name"] for x in b]
    assert [x["name"] for x in a] != [x["name"] for x in c]
    assert all(x["anim"] in {"bobble", "spin", "pulse", "wiggle"} for x in a)
    assert all(44 <= x["size"] <= 64 for x in a)


def test_null_interpret_sparkle_helpers():
    """Null blurbs get sparkle wrappers; interesting hits stay plain."""
    ns: dict = {}
    src = DASHBOARD_SOURCE
    start = src.index("def _is_null_interpret_blurb")
    end = src.index("\ndef ensure_clipart_seed")
    code = "from __future__ import annotations\n" + src[start:end]
    # Strip Streamlit-dependent render_interpret_info body for pure helper test.
    helper_only = code.split("\ndef render_interpret_info")[0]
    exec(compile(helper_only, "dashboard_null_helpers.py", "exec"), ns)

    is_null = ns["_is_null_interpret_blurb"]
    assert is_null("**So what?** 🎱 Chance score 0.42 — that's a **null** result. Sorry man.")
    assert is_null("**So what?** expected null, no free lunch. I'm gonna be broke.")
    assert is_null("**So what?** boring baseline near the track's cut. Bummer vibes.")
    assert not is_null("**So what?** Far out dude! That's interesting.")
    assert not is_null("Just a caption with null in it, no reveal header.")
    assert not is_null("")


def test_apply_plotly_theme_sets_dark_template():
    """Runtime check: apply_plotly_theme stamps plotly_dark on a figure."""
    import plotly.graph_objects as go

    ns: dict = {"go": go}
    src = DASHBOARD_SOURCE
    # Extract PALETTE + apply_plotly_theme only (stop before CSS / clipart helpers).
    start = src.index("PALETTE = {")
    end = src.index("\ndef inject_app_css")
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
    assert "UK/Ireland (free, exploratory)" in DASHBOARD_SOURCE
    assert "load_bundled_uk" in DASHBOARD_SOURCE
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


def test_dashboard_main_run_button_on_intro():
    """Primary Run lives on the main intro; sidebar only collects opts."""
    assert "def render_sidebar(prereg: dict) -> dict:" in DASHBOARD_SOURCE
    assert "pending_opts" in DASHBOARD_SOURCE
    assert 'key="tour_run_button"' in DASHBOARD_SOURCE
    # No dual-button / force_run bridge — one primary on main.
    assert "force_run" not in DASHBOARD_SOURCE
    assert "render_main_run_button" not in DASHBOARD_SOURCE
    assert 'key="tour_run_button_main"' not in DASHBOARD_SOURCE
    # Empty-state + sidebar copy point at the main-page button.
    assert "Click **🏇 Run Analysis** below (on this page)" in DASHBOARD_SOURCE
    assert "hit **🏇 Run Analysis** on the main page" in DASHBOARD_SOURCE
    assert "Settings above — then hit **🏇 Run Analysis** on the main page" in DASHBOARD_SOURCE
    # Sidebar must not own the primary Run button.
    sidebar_start = DASHBOARD_SOURCE.index("def render_sidebar")
    sidebar_end = DASHBOARD_SOURCE.index("\ndef load_runners")
    sidebar_src = DASHBOARD_SOURCE[sidebar_start:sidebar_end]
    assert 'key="tour_run_button"' not in sidebar_src
    assert "Run Analysis" not in sidebar_src or "on the main page" in sidebar_src
    # Main() wires the button inside tour_empty_intro.
    main_start = DASHBOARD_SOURCE.index("def main()")
    main_src = DASHBOARD_SOURCE[main_start:]
    assert 'key="tour_run_button"' in main_src
    assert "run_clicked" in main_src


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
        "_hippie_pick",
        "boring baseline",
        "no free lunch",
        "usual honest answer",
        "fair-price case",
        "Sorry man",
        "Far out",
        "old lady",
        "VW bus",
        "Burning Man",
        "commune",
        "ashram",
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
    assert "def _hippie_pick" in DASHBOARD_SOURCE

    # Exec helpers alone (dashboard.py needs Streamlit; avoid importing the page).
    ns: dict = {
        "pd": __import__("pandas"),
        "hashlib": __import__("hashlib"),
    }
    src = DASHBOARD_SOURCE
    start = src.index("def _hippie_pick")
    end = src.index("\n# ---------------------------------------------------------------------------\n# Auth & config")
    # Python 3.9 needs postponed annotations for ``X | None`` in the helpers.
    code = "from __future__ import annotations\n" + src[start:end]
    exec(compile(code, "dashboard_helpers.py", "exec"), ns)

    personas = ("old lady", "vw bus", "burning man", "commune", "ashram", "crystal ball")

    def _has_persona(text: str) -> bool:
        low = text.lower()
        return any(p in low for p in personas)

    # Mild null (p under 0.40): soft bummer.
    mild_null = ns["_interpret_match"]({"permutation_p": 0.12, "spearman_r": -0.01})
    assert "null" in mild_null.lower()
    assert "So what?" in mild_null
    assert "bummer" in mild_null.lower() or "sorry man" in mild_null.lower()
    assert "0.1200" in mild_null and "-0.0100" in mild_null

    # Dead null (high p): escalate to a dramatic persona lament.
    null_txt = ns["_interpret_match"]({"permutation_p": 0.42, "spearman_r": -0.01})
    assert "null" in null_txt.lower()
    assert "So what?" in null_txt
    assert "broke" in null_txt.lower()
    assert _has_persona(null_txt)
    assert "0.4200" in null_txt and "-0.0100" in null_txt
    # Same metrics → same persona (no Streamlit flicker).
    assert null_txt == ns["_interpret_match"]({"permutation_p": 0.42, "spearman_r": -0.01})

    hit_txt = ns["_interpret_match"]({"permutation_p": 0.01, "spearman_r": -0.3})
    assert "interesting" in hit_txt.lower() or "McKenna" in hit_txt
    assert "far out" in hit_txt.lower()
    assert "broke" not in hit_txt.lower()

    timing = ns["_interpret_timing"](
        {"roi_pct": -18.0}, {"roi_pct": -17.5}, 0.18
    )
    assert "baseline" in timing.lower() or "timing" in timing.lower()
    assert "bummer" in timing.lower() or "drag" in timing.lower()
    assert _has_persona(timing) or "sorry man" in timing.lower()

    timing_hurt = ns["_interpret_timing"](
        {"roi_pct": -5.87}, {"roi_pct": 1.95}, 0.18
    )
    assert "null/negative" in timing_hurt.lower()
    assert "broke" in timing_hurt.lower()
    assert _has_persona(timing_hurt)
    assert "-5.87%" in timing_hurt and "+1.95%" in timing_hurt
    assert timing_hurt == ns["_interpret_timing"](
        {"roi_pct": -5.87}, {"roi_pct": 1.95}, 0.18
    )

    # Different ROI seeds can rotate the timing-hurt persona.
    hurt_variants = {
        ns["_interpret_timing"]({"roi_pct": a}, {"roi_pct": b}, 0.18)
        for a, b in ((-5.87, 1.95), (-12.0, 3.0), (-8.5, 0.5), (-20.0, 5.0))
    }
    assert len(hurt_variants) >= 2

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
    assert "broke" in engine.lower()
    assert _has_persona(engine)
    assert "-5.00%" in engine
    assert engine == ns["_interpret_engine"](
        {"engine_beta": 1.0},
        ns["pd"].DataFrame([{"strategy": "demo", "roi_pct": -5.0, "tickets": 0}]),
    )
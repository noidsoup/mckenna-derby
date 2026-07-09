"""First-visit guided tour for the Streamlit dashboard.

Injects Driver.js into the parent Streamlit page and walks the user through
positioned popover steps anchored to keyed UI regions. Completion is stored
in the browser's localStorage so the tour only auto-starts once.
"""

from __future__ import annotations

import json
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

TOUR_STORAGE_KEY = "mckenna_derby_tour_v1"
TOUR_FORCE_STATE_KEY = "force_dashboard_tour"

# Steps use either element=None (centered info modal) or a Streamlit widget key
# that becomes CSS class `.st-key-<key>` on the rendered page.
TOUR_STEPS: list[dict[str, Any]] = [
    {
        "element": None,
        "popover": {
            "title": "🐴 Welcome to McKenna Derby",
            "description": (
                "Terence McKenna 🍄 — mystical genius, ethnobotanist, psychedelic "
                "philosopher, raconteur — mapped \"novelty\" onto <b>Timewave Zero</b> 🌊, "
                "a fractal calendar from ☯️ I Ching number tables "
                "(low wave ↔ high chaos; zero-date lore ~2012). "
                "We ask: do surprising 🐎 race days line up with that wave? "
                "And does betting only on \"wave\" days beat the track's cut? "
                "Mystique in the story; honest nulls in the numbers 🎱. "
                "If the wave flops, don't say we didn't warn you, man."
            ),
            "side": "over",
            "align": "center",
        },
    },
    {
        "element": "tour_app_header",
        "popover": {
            "title": "✨ The question",
            "description": (
                "The title is the research question. Charts and numbers below "
                "are the evidence — not betting tips 🔮."
            ),
            "side": "bottom",
            "align": "start",
        },
    },
    {
        "element": "tour_empty_intro",
        "popover": {
            "title": "🎠 Start here",
            "description": (
                "Plain-English intro: who McKenna was, what Timewave Zero is, "
                "and how the ☯️ I Ching ties in (wave tables + coin-cast "
                "hexagram-style picks 🃏). Real Hong Kong 🏇 races (1997–2005) "
                "are already loaded. Next: set knobs in the sidebar if you like, "
                "then click <b>🏇 Run Analysis</b> on the main page."
            ),
            "side": "left",
            "align": "start",
        },
    },
    {
        "element": "tour_data_source",
        "popover": {
            "title": "📁 Your data (sidebar)",
            "description": (
                "Default is <b>real Hong Kong races</b> 🐎 — no upload needed. "
                "Open Advanced options only for a fake null demo 🎱 (should show "
                "no signal) or your own CSV. Sidebar also has "
                "<b>Who is Terence McKenna?</b> for the mystique."
            ),
            "side": "right",
            "align": "start",
        },
    },
    {
        "element": "tour_run_params",
        "popover": {
            "title": "🏇 Run settings",
            "description": (
                "Knobs for this run of the main test (I Ching–derived wave table, "
                "cutoff, track's cut, surprise score). Change them to explore ✨ — "
                "don't treat a new combo as the official locked result ⭐."
            ),
            "side": "right",
            "align": "start",
        },
    },
    {
        "element": "tour_engine_params",
        "popover": {
            "title": "🎲 Picky betting (optional)",
            "description": (
                "A stricter side experiment: fewer days, fewer tickets, plus a "
                "coin-cast hexagram-style picker 🃏 (☯️ I Ching 64-pattern vibe). "
                "<b>Bias guess = 1.0</b> means fair prices ☯️ (no free lunch). "
                "Higher values pretend favorites are overbet — a guess 🎱, not a fact."
            ),
            "side": "right",
            "align": "start",
        },
    },
    {
        "element": "tour_run_button",
        "popover": {
            "title": "🏇 Run Analysis",
            "description": (
                "This big button is on the <b>main page</b> (not the sidebar). "
                "Click it, then open <b>📊 Overview</b> for the plain-English "
                "answer. On this data the main finding is often \"no match\" ☯️ — "
                "honest, not a tip sheet 🔮."
            ),
            "side": "bottom",
            "align": "center",
        },
    },
    {
        "element": None,
        "popover": {
            "title": "🏁 You're set",
            "description": (
                "Replay anytime from the sidebar (<b>Replay guided tour</b>). "
                "Reading the sidebar top→bottom explains each control; "
                "then hit <b>🏇 Run Analysis</b> on the main page. "
                "Stay skeptical of pretty numbers 🧿."
            ),
            "side": "over",
            "align": "center",
        },
    },
]


def _driver_steps_payload(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert our step dicts into Driver.js step objects (element selectors)."""
    out: list[dict[str, Any]] = []
    for step in steps:
        item: dict[str, Any] = {"popover": dict(step["popover"])}
        key = step.get("element")
        if key:
            # Streamlit emits .st-key-<key> on keyed widgets/containers.
            item["element"] = f".st-key-{key}"
        out.append(item)
    return out


def render_tour(
    *,
    force: bool = False,
    storage_key: str = TOUR_STORAGE_KEY,
    steps: list[dict[str, Any]] | None = None,
) -> None:
    """Inject and (optionally) auto-start the guided tour in the parent page.

    Parameters
    ----------
    force:
        If True, clear the one-time flag and start immediately (replay).
    storage_key:
        localStorage key used to remember completion.
    steps:
        Override the default tour steps (mainly for tests).
    """
    tour_steps = steps if steps is not None else TOUR_STEPS
    payload = _driver_steps_payload(tour_steps)
    steps_json = json.dumps(payload)
    force_js = "true" if force else "false"
    storage_js = json.dumps(storage_key)

    # Height 0 keeps the iframe invisible; scripts still run and reach parent.
    components.html(
        f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
</head>
<body>
<script>
(function () {{
  const STORAGE_KEY = {storage_js};
  const FORCE = {force_js};
  const STEPS = {steps_json};
  const PARENT = window.parent;
  const DOC = PARENT.document;

  function alreadyDone() {{
    try {{
      return PARENT.localStorage.getItem(STORAGE_KEY) === "done";
    }} catch (e) {{
      return false;
    }}
  }}

  function markDone() {{
    try {{
      PARENT.localStorage.setItem(STORAGE_KEY, "done");
    }} catch (e) {{}}
  }}

  function clearDone() {{
    try {{
      PARENT.localStorage.removeItem(STORAGE_KEY);
    }} catch (e) {{}}
  }}

  function ensureAssets(cb) {{
    if (PARENT.driver && PARENT.driver.js && PARENT.driver.js.driver) {{
      cb();
      return;
    }}
    if (!DOC.getElementById("mckenna-driver-css")) {{
      const link = DOC.createElement("link");
      link.id = "mckenna-driver-css";
      link.rel = "stylesheet";
      link.href = "https://cdn.jsdelivr.net/npm/driver.js@1.3.1/dist/driver.css";
      DOC.head.appendChild(link);
    }}
    if (!DOC.getElementById("mckenna-driver-theme")) {{
      const style = DOC.createElement("style");
      style.id = "mckenna-driver-theme";
      style.textContent = `
        .driver-popover.mckenna-tour-popover {{
          max-width: 360px;
          background: #1a1d27;
          color: #e8e6f0;
          border: 1px solid rgba(167, 139, 250, 0.45);
          border-radius: 10px;
          box-shadow: 0 16px 48px rgba(0, 0, 0, 0.55), 0 0 24px rgba(167, 139, 250, 0.18);
        }}
        .driver-popover.mckenna-tour-popover .driver-popover-title {{
          font-size: 1.05rem;
          font-weight: 700;
          color: #a78bfa;
        }}
        .driver-popover.mckenna-tour-popover .driver-popover-description {{
          font-size: 0.92rem;
          line-height: 1.45;
          color: #e8e6f0;
        }}
        .driver-popover.mckenna-tour-popover .driver-popover-next-btn,
        .driver-popover.mckenna-tour-popover .driver-popover-done-btn {{
          background: linear-gradient(135deg, #8b5cf6, #6366f1);
          color: #fff;
          border: 0;
          text-shadow: none;
        }}
        .driver-popover.mckenna-tour-popover .driver-popover-prev-btn {{
          background: transparent;
          color: #94a3b8;
          border: 1px solid rgba(167, 139, 250, 0.4);
          text-shadow: none;
        }}
        .driver-popover.mckenna-tour-popover .driver-popover-close-btn {{
          color: #94a3b8;
        }}
        .driver-overlay {{
          background: rgba(8, 10, 16, 0.72) !important;
        }}
      `;
      DOC.head.appendChild(style);
    }}
    const existing = DOC.getElementById("mckenna-driver-js");
    if (existing) {{
      existing.addEventListener("load", cb);
      // If already loaded, invoke soon.
      if (PARENT.driver && PARENT.driver.js) cb();
      return;
    }}
    const script = DOC.createElement("script");
    script.id = "mckenna-driver-js";
    script.src = "https://cdn.jsdelivr.net/npm/driver.js@1.3.1/dist/driver.js.iife.js";
    script.onload = cb;
    DOC.head.appendChild(script);
  }}

  function resolveElement(selector) {{
    if (!selector) return undefined;
    const el = DOC.querySelector(selector);
    return el || undefined;
  }}

  function startTour() {{
    const driverFactory =
      PARENT.driver && PARENT.driver.js && PARENT.driver.js.driver;
    if (!driverFactory) return;

    const resolved = STEPS.map((step) => {{
      const copy = {{
        popover: Object.assign({{
          showButtons: ["next", "previous", "close"],
          popoverClass: "mckenna-tour-popover",
        }}, step.popover),
      }};
      if (step.element) {{
        const el = resolveElement(step.element);
        if (el) copy.element = el;
        // If the anchor is missing (e.g. collapsed sidebar on mobile),
        // fall back to a floating info step so the tour still advances.
      }}
      return copy;
    }});

    const driverObj = driverFactory({{
      showProgress: true,
      animate: true,
      allowClose: true,
      overlayOpacity: 0.55,
      stagePadding: 8,
      stageRadius: 8,
      nextBtnText: "Next",
      prevBtnText: "Back",
      doneBtnText: "Done",
      onDestroyStarted: () => {{
        markDone();
        driverObj.destroy();
      }},
      steps: resolved,
    }});
    driverObj.drive();
  }}

  if (FORCE) clearDone();
  if (!FORCE && alreadyDone()) return;

  // Wait a beat so Streamlit finishes painting keyed anchors.
  ensureAssets(function () {{
    setTimeout(startTour, FORCE ? 200 : 600);
  }});
}})();
</script>
</body>
</html>
        """,
        height=0,
        width=0,
    )


def maybe_start_tour(*, has_results: bool = False) -> None:
    """Auto-start on first visit; honor a sidebar replay request."""
    force = bool(st.session_state.pop(TOUR_FORCE_STATE_KEY, False))
    # After results load, still allow replay; auto-start only on the landing view
    # or when forced, so we do not interrupt an active analysis read.
    if force:
        render_tour(force=True)
        return
    if not has_results:
        render_tour(force=False)


def render_tour_sidebar_controls() -> None:
    """Sidebar button to replay the guided tour."""
    st.markdown("##### Guided tour")
    st.caption(
        "First visit walks you through the page with popover tips. "
        "Replay anytime if you want the walkthrough again."
    )
    if st.button("Replay guided tour", key="tour_replay_btn"):
        st.session_state[TOUR_FORCE_STATE_KEY] = True
        st.rerun()

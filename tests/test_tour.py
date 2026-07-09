"""Tests for the first-visit guided tour helpers."""

from mckenna_derby.tour import TOUR_STEPS, TOUR_STORAGE_KEY, _driver_steps_payload


def test_tour_steps_have_titles_and_descriptions():
    assert len(TOUR_STEPS) >= 5
    for step in TOUR_STEPS:
        pop = step["popover"]
        assert pop["title"]
        assert pop["description"]
        assert pop["side"] in {"over", "top", "bottom", "left", "right"}


def test_driver_payload_maps_keys_to_st_key_selectors():
    payload = _driver_steps_payload(TOUR_STEPS)
    assert payload[0].get("element") is None  # welcome is floating
    anchored = [s for s in payload if "element" in s and s["element"]]
    assert anchored
    for step in anchored:
        assert step["element"].startswith(".st-key-")
    keys = {s["element"] for s in anchored}
    assert ".st-key-tour_app_header" in keys
    assert ".st-key-tour_empty_intro" in keys
    assert ".st-key-tour_data_source" in keys
    assert ".st-key-tour_run_button" in keys
    assert ".st-key-tour_about_panel" not in keys


def test_tour_storage_key_stable():
    assert TOUR_STORAGE_KEY == "mckenna_derby_tour_v1"


def test_tour_module_exposes_replay_control_label():
    from pathlib import Path

    src = (Path(__file__).resolve().parents[1] / "mckenna_derby" / "tour.py").read_text()
    assert "Replay guided tour" in src
    assert "render_tour_sidebar_controls" in src
    assert "calendar wave" in src
    assert "Picky betting" in src
    assert "Bias guess" in src
    assert "popover tips" in src
    assert "track's cut" in src
    assert "no upload needed" in src
    assert "sidebar top→bottom" in src

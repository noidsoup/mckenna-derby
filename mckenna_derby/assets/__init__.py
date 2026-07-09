"""Local flat clipart SVGs for the Streamlit dashboard (no web hotlinks)."""

from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent

CLIPART = {
    "horse": ASSETS_DIR / "horse.svg",
    "yin_yang": ASSETS_DIR / "yin_yang.svg",
    "mushroom": ASSETS_DIR / "mushroom.svg",
    "crystal_ball": ASSETS_DIR / "crystal_ball.svg",
    "eight_ball": ASSETS_DIR / "eight_ball.svg",
    "finish_flag": ASSETS_DIR / "finish_flag.svg",
}


def clipart_path(name: str) -> Path:
    """Return path to a named clipart asset."""
    try:
        return CLIPART[name]
    except KeyError as exc:
        raise KeyError(f"Unknown clipart {name!r}; choose from {sorted(CLIPART)}") from exc

"""Local flat clipart SVGs + tiny GIFs for the Streamlit dashboard (no web hotlinks)."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Optional, Sequence

ASSETS_DIR = Path(__file__).resolve().parent

# Static flat SVGs (cheesy clipart)
CLIPART_SVG = {
    "horse": ASSETS_DIR / "horse.svg",
    "yin_yang": ASSETS_DIR / "yin_yang.svg",
    "mushroom": ASSETS_DIR / "mushroom.svg",
    "crystal_ball": ASSETS_DIR / "crystal_ball.svg",
    "eight_ball": ASSETS_DIR / "eight_ball.svg",
    "finish_flag": ASSETS_DIR / "finish_flag.svg",
    "peace": ASSETS_DIR / "peace.svg",
    "vw_bus": ASSETS_DIR / "vw_bus.svg",
    "rainbow": ASSETS_DIR / "rainbow.svg",
    "star": ASSETS_DIR / "star.svg",
    "incense": ASSETS_DIR / "incense.svg",
    "dice": ASSETS_DIR / "dice.svg",
    "spiral": ASSETS_DIR / "spiral.svg",
    "lotus": ASSETS_DIR / "lotus.svg",
    "horseshoe": ASSETS_DIR / "horseshoe.svg",
    "lava_lamp": ASSETS_DIR / "lava_lamp.svg",
}

# Tiny Pillow-generated animated GIFs (<5KB each)
CLIPART_GIF = {
    "bounce_mushroom": ASSETS_DIR / "bounce_mushroom.gif",
    "spin_yinyang": ASSETS_DIR / "spin_yinyang.gif",
    "pulse_crystal": ASSETS_DIR / "pulse_crystal.gif",
    "cycle_rainbow": ASSETS_DIR / "cycle_rainbow.gif",
    "twinkle_star": ASSETS_DIR / "twinkle_star.gif",
}

CLIPART = {**CLIPART_SVG, **CLIPART_GIF}

# CSS animation class names assigned randomly per sticker
ANIM_CLASSES = ("bobble", "spin", "pulse", "wiggle")

__all__ = [
    "ASSETS_DIR",
    "CLIPART",
    "CLIPART_SVG",
    "CLIPART_GIF",
    "ANIM_CLASSES",
    "clipart_path",
    "list_clipart_names",
    "pick_random_assets",
]


def clipart_path(name: str) -> Path:
    """Return path to a named clipart asset."""
    try:
        return CLIPART[name]
    except KeyError as exc:
        raise KeyError(f"Unknown clipart {name!r}; choose from {sorted(CLIPART)}") from exc


def list_clipart_names(
    *,
    include_svg: bool = True,
    include_gif: bool = True,
    only_existing: bool = True,
) -> list[str]:
    """Return available clipart names, optionally filtered by type."""
    names: list[str] = []
    if include_svg:
        names.extend(CLIPART_SVG)
    if include_gif:
        names.extend(CLIPART_GIF)
    if only_existing:
        names = [n for n in names if CLIPART[n].exists()]
    return names


def pick_random_assets(
    n: int,
    seed: Optional[int] = None,
    *,
    pool: Optional[Sequence[str]] = None,
    include_gif: bool = True,
    with_anim: bool = True,
) -> list[dict]:
    """Pick ``n`` random clipart stickers (name, path, size, anim class).

    Uses ``random.Random(seed)`` so a Streamlit session can keep a stable
    layout until the seed is re-rolled.
    """
    rng = random.Random(seed)
    if pool is None:
        names = list_clipart_names(include_gif=include_gif)
    else:
        names = [n for n in pool if n in CLIPART and CLIPART[n].exists()]
    if not names:
        return []
    k = min(max(0, int(n)), len(names))
    chosen = rng.sample(names, k=k)
    # Shuffle display order independently of sample order
    rng.shuffle(chosen)
    out: list[dict] = []
    for name in chosen:
        path = CLIPART[name]
        # Size in px — small range so rows stay tidy
        size = rng.choice((44, 48, 52, 56, 60, 64))
        anim = rng.choice(ANIM_CLASSES) if with_anim else "none"
        out.append(
            {
                "name": name,
                "path": path,
                "size": size,
                "anim": anim,
                "kind": "gif" if path.suffix.lower() == ".gif" else "svg",
            }
        )
    return out

"""Amulet generator. Takes a seed, returns a 600x448 RGB PIL Image.

The grammar (frame x spoke x charge x protrusions) lives here. This stub draws a
single placeholder circle so the rest of the pipeline can be wired and tested end
to end before the real composition logic exists.
"""

from __future__ import annotations

import hashlib
import random
from datetime import datetime
from typing import Optional

from PIL import Image, ImageDraw

from . import WIDTH, HEIGHT

CREAM = (244, 235, 208)
BLACK = (15, 15, 15)


def seed_for_minute(hh: int, mm: int) -> int:
    return int(hashlib.sha256(f"{hh:02d}:{mm:02d}".encode()).hexdigest()[:8], 16)


def seed_for_now(now: Optional[datetime] = None) -> int:
    now = now or datetime.now()
    return seed_for_minute(now.hour, now.minute)


def render(seed: int) -> Image.Image:
    """Render one amulet. Placeholder: cream background + concentric circle frame
    + a small central dot. Real grammar will replace this."""
    rng = random.Random(seed)

    img = Image.new("RGB", (WIDTH, HEIGHT), CREAM)
    draw = ImageDraw.Draw(img)

    cx, cy = WIDTH // 2, HEIGHT // 2
    outer_r = min(WIDTH, HEIGHT) // 2 - 20

    draw.ellipse(
        (cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r),
        outline=BLACK,
        width=3,
    )
    inner_r = outer_r - 14
    draw.ellipse(
        (cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r),
        outline=BLACK,
        width=1,
    )

    dot_r = 6 + rng.randint(0, 4)
    draw.ellipse(
        (cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r),
        fill=BLACK,
    )

    return img

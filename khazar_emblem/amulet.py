"""Amulet generator. Takes a seed, returns a 600x448 RGB PIL Image.

The grammar (frame x spoke x charge x protrusions) lives here. This stub draws a
single placeholder circle so the rest of the pipeline can be wired and tested end
to end before the real composition logic exists.
"""

from __future__ import annotations

import hashlib
import math
import random
from datetime import datetime
from typing import Optional

from PIL import Image, ImageDraw

from . import WIDTH, HEIGHT
from .strokes import wobble_ring, wobble_line

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

    wobble_ring(draw, (cx, cy), outer_r, rng, color=BLACK, width=2.6, wobble=1.0)
    wobble_ring(draw, (cx, cy), outer_r - 14, rng, color=BLACK, width=1.4, wobble=0.7)

    n_spokes = rng.choice([4, 6, 8])
    inner_start = 18
    spoke_end = outer_r - 22
    for k in range(n_spokes):
        theta = 2 * math.pi * k / n_spokes + rng.uniform(-0.02, 0.02)
        x0 = cx + inner_start * math.cos(theta)
        y0 = cy + inner_start * math.sin(theta)
        x1 = cx + spoke_end * math.cos(theta)
        y1 = cy + spoke_end * math.sin(theta)
        wobble_line(draw, (x0, y0), (x1, y1), rng, color=BLACK, width=1.6, wobble=0.5)

    dot_r = 6 + rng.randint(0, 4)
    draw.ellipse(
        (cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r),
        fill=BLACK,
    )

    return img

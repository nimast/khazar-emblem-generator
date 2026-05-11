"""Hand-drawn stroke primitives.

Replaces ImageDraw.line / ImageDraw.arc with versions that have:
- Slight perpendicular wobble (correlated, not per-pixel noise)
- Variable width along the stroke (slow drift, not jitter)
- Brush-stamp rendering (overlapping filled discs) so width can change smoothly

Every subsequent visual layer of the amulet draws through these, so the
hand-drawn feel is inherited rather than added.
"""

from __future__ import annotations

import math
import random
from typing import Sequence

import numpy as np
from PIL import ImageDraw

Color = tuple[int, int, int]
Point = tuple[float, float]


def _brownian_bridge(n: int, rng: random.Random, scale: float) -> np.ndarray:
    """Return n offsets that start and end at zero, with smooth-ish drift between.

    Random walk minus the linear trend through (0, walk[-1]). Endpoints anchored.
    """
    if n < 2:
        return np.zeros(n)
    steps = np.array([rng.gauss(0.0, scale) for _ in range(n)])
    walk = np.cumsum(steps)
    t = np.linspace(0.0, 1.0, n)
    return walk - (walk[0] * (1 - t) + walk[-1] * t)


def _periodic_wobble(theta: np.ndarray, rng: random.Random, amplitude: float) -> np.ndarray:
    """Smooth, periodic wobble along an angular parameter. Sum of a few sines with
    random phase. Naturally closes on itself, no seam at the wrap-around."""
    result = np.zeros_like(theta)
    for k in (2, 3, 5, 7):
        phase = rng.uniform(0.0, 2.0 * math.pi)
        amp = amplitude * rng.uniform(0.4, 1.0) / k
        result += amp * np.sin(k * theta + phase)
    return result


def _width_profile(n: int, rng: random.Random, base: float, variation: float) -> np.ndarray:
    """Slow-drift width along a stroke. Stays in [0.5px, base * 1.5]."""
    widths = np.empty(n)
    w = base
    for i in range(n):
        w = 0.85 * w + 0.15 * base + rng.uniform(-variation, variation) * 0.4
        widths[i] = max(0.5, min(base * 1.6, w))
    return widths


def _stamp(draw: ImageDraw.ImageDraw, x: float, y: float, r: float, color: Color) -> None:
    """One brush stamp: a filled disc. For r < 1 the ellipse degenerates so we
    fall back to a single pixel."""
    if r < 0.6:
        draw.point((round(x), round(y)), fill=color)
        return
    draw.ellipse((x - r, y - r, x + r, y + r), fill=color)


def wobble_line(
    draw: ImageDraw.ImageDraw,
    p0: Point,
    p1: Point,
    rng: random.Random,
    *,
    color: Color = (15, 15, 15),
    width: float = 2.0,
    wobble: float = 0.6,
    stamp_step: float = 1.2,
) -> None:
    """Draw a line from p0 to p1 with hand-drawn character. `wobble` is the per-step
    standard deviation of the perpendicular drift; `width` is the average brush
    diameter in pixels."""
    x0, y0 = p0
    x1, y1 = p1
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    if length < 0.5:
        _stamp(draw, x0, y0, width / 2, color)
        return

    n = max(4, int(length / stamp_step))
    px, py = -dy / length, dx / length

    offsets = _brownian_bridge(n, rng, scale=wobble * 0.5)
    widths = _width_profile(n, rng, base=width, variation=width * 0.35)

    t = np.linspace(0.0, 1.0, n)
    xs = x0 + t * dx + offsets * px
    ys = y0 + t * dy + offsets * py

    for x, y, w in zip(xs, ys, widths):
        _stamp(draw, float(x), float(y), float(w) / 2, color)


def wobble_arc(
    draw: ImageDraw.ImageDraw,
    center: Point,
    radius: float,
    start_deg: float,
    end_deg: float,
    rng: random.Random,
    *,
    color: Color = (15, 15, 15),
    width: float = 2.0,
    wobble: float = 0.8,
    stamp_step: float = 1.2,
) -> None:
    """Draw an arc (or full ring) with radial wobble. start/end in degrees, CW from
    +X axis. If end - start is a full turn, the wobble is periodic so the seam at
    the wrap-around is invisible."""
    cx, cy = center
    start = math.radians(start_deg)
    end = math.radians(end_deg)
    span = end - start

    arc_len = abs(span) * radius
    n = max(16, int(arc_len / stamp_step))
    theta = np.linspace(start, end, n)

    is_closed = abs(abs(span) - 2 * math.pi) < 1e-3
    if is_closed:
        r_off = _periodic_wobble(theta, rng, amplitude=wobble)
    else:
        r_off = _brownian_bridge(n, rng, scale=wobble * 0.4)

    widths = _width_profile(n, rng, base=width, variation=width * 0.35)
    rs = radius + r_off
    xs = cx + rs * np.cos(theta)
    ys = cy + rs * np.sin(theta)

    for x, y, w in zip(xs, ys, widths):
        _stamp(draw, float(x), float(y), float(w) / 2, color)


def wobble_ring(
    draw: ImageDraw.ImageDraw,
    center: Point,
    radius: float,
    rng: random.Random,
    *,
    color: Color = (15, 15, 15),
    width: float = 2.0,
    wobble: float = 0.8,
) -> None:
    """Shorthand for a full closed ring."""
    wobble_arc(
        draw,
        center,
        radius,
        0.0,
        360.0,
        rng,
        color=color,
        width=width,
        wobble=wobble,
    )


def wobble_polyline(
    draw: ImageDraw.ImageDraw,
    points: Sequence[Point],
    rng: random.Random,
    *,
    color: Color = (15, 15, 15),
    width: float = 2.0,
    wobble: float = 0.6,
) -> None:
    """Connect a sequence of points with wobble_line. Each segment carries the
    same line style; the overall path inherits hand-drawn character."""
    for a, b in zip(points, points[1:]):
        wobble_line(draw, a, b, rng, color=color, width=width, wobble=wobble)

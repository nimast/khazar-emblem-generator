"""Hand-drawn stroke primitives.

Replaces ImageDraw.line / ImageDraw.arc with versions that have:
- Slight perpendicular wobble (correlated, not per-pixel noise)
- Variable width along the stroke with a pen-pressure bell envelope
- Brush-stamp rendering (overlapping filled discs) so width can change smoothly
- Optional ink-pool dots at endpoints

`wobble_line`, `wobble_polyline`, `curved_line` all share a `_stamp_path` core
so the width profile is global across the whole stroke instead of restarting per
segment. That's what gives long curves a single pen-pressure bell instead of a
zigzagging width.

Every visual layer of the amulet draws through these, so the hand-drawn feel is
inherited rather than added.
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
    """n offsets that start and end at zero with smooth drift between. Random walk
    minus the linear trend through (0, walk[-1])."""
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


def _width_profile(
    n: int,
    rng: random.Random,
    base: float,
    variation: float,
    *,
    pressure: float = 0.3,
    closed: bool = False,
) -> np.ndarray:
    """Width along a stroke, two bounded components combined:

    1. Pen-pressure envelope: bell that thins at endpoints and fills out mid-stroke.
       Peak shifted slightly off-center per stroke. Disabled for closed strokes.
    2. Slow-drift random component (Ornstein-Uhlenbeck — mean-reverting so it
       can't drift arbitrarily far from base on long strokes).

    Returns widths clipped to [base * 0.55, base * 1.6].
    """
    if n < 2:
        return np.full(n, base)
    t = np.linspace(0.0, 1.0, n)
    if closed or pressure <= 0:
        envelope = np.ones(n)
    else:
        peak = 0.5 + rng.uniform(-0.15, 0.15)
        u = (t - peak) / max(peak, 1 - peak)
        envelope = 1.0 - pressure * np.clip(np.abs(u), 0.0, 1.0) ** 1.4

    # Mean-reverting drift around 0
    drift = np.empty(n)
    w = 0.0
    for i in range(n):
        w = 0.88 * w + rng.uniform(-variation, variation) * 0.35
        drift[i] = w

    widths = base * envelope + drift
    return np.clip(widths, base * 0.55, base * 1.6)


def _stamp(draw: ImageDraw.ImageDraw, x: float, y: float, r: float, color: Color) -> None:
    """One brush stamp: a filled disc. Sub-pixel falls back to a point."""
    if r < 0.6:
        draw.point((round(x), round(y)), fill=color)
        return
    draw.ellipse((x - r, y - r, x + r, y + r), fill=color)


def _stamp_path(
    draw: ImageDraw.ImageDraw,
    pts: Sequence[Point],
    rng: random.Random,
    *,
    color: Color,
    width: float,
    wobble: float,
    pressure: float = 0.45,
    pool_at_ends: bool = False,
    pool_scale: float = 1.7,
) -> None:
    """Core stamper: walk a polyline path, computing ONE global width profile and
    ONE global perpendicular wobble across the whole path. Used by wobble_line,
    wobble_polyline, and curved_line so multi-segment strokes get a single pen
    pressure envelope instead of zigzagging at every segment boundary.

    If `pool_at_ends`, drops a darker (slightly larger) blob at the first and
    last point — mimics where a real pen sits on paper at stroke start/stop.
    """
    n = len(pts)
    if n == 0:
        return
    if n == 1:
        _stamp(draw, pts[0][0], pts[0][1], width / 2, color)
        return

    widths = _width_profile(n, rng, base=width, variation=width * 0.4, pressure=pressure)
    offsets = _brownian_bridge(n, rng, scale=wobble * 0.5)

    xs = np.empty(n)
    ys = np.empty(n)
    for i in range(n):
        if i == 0:
            tx, ty = pts[1][0] - pts[0][0], pts[1][1] - pts[0][1]
        elif i == n - 1:
            tx, ty = pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]
        else:
            tx, ty = pts[i + 1][0] - pts[i - 1][0], pts[i + 1][1] - pts[i - 1][1]
        tn = math.hypot(tx, ty) or 1.0
        px, py = -ty / tn, tx / tn
        xs[i] = pts[i][0] + offsets[i] * px
        ys[i] = pts[i][1] + offsets[i] * py
        _stamp(draw, float(xs[i]), float(ys[i]), float(widths[i]) / 2, color)

    if pool_at_ends and n >= 2:
        _stamp(draw, float(xs[0]), float(ys[0]), float(widths[0]) * pool_scale / 2, color)
        _stamp(draw, float(xs[-1]), float(ys[-1]), float(widths[-1]) * pool_scale / 2, color)


def _densify(points: Sequence[Point], step: float = 0.7) -> list[Point]:
    """Insert intermediate points so no consecutive pair is more than ~`step` apart.
    Needed so _stamp_path has enough sample points for a smooth path."""
    if len(points) < 2:
        return list(points)
    out: list[Point] = [points[0]]
    for a, b in zip(points, points[1:]):
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        n_seg = max(1, int(length / step))
        for i in range(1, n_seg + 1):
            t = i / n_seg
            out.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
    return out


def wobble_line(
    draw: ImageDraw.ImageDraw,
    p0: Point,
    p1: Point,
    rng: random.Random,
    *,
    color: Color = (15, 15, 15),
    width: float = 2.0,
    wobble: float = 0.6,
    stamp_step: float = 0.7,
    pool_at_ends: bool = False,
) -> None:
    """Draw a line from p0 to p1 with hand-drawn character."""
    x0, y0 = p0
    x1, y1 = p1
    length = math.hypot(x1 - x0, y1 - y0)
    if length < 0.5:
        _stamp(draw, x0, y0, width / 2, color)
        return
    n = max(4, int(length / stamp_step))
    t = np.linspace(0.0, 1.0, n)
    pts = [(float(x0 + ti * (x1 - x0)), float(y0 + ti * (y1 - y0))) for ti in t]
    _stamp_path(draw, pts, rng, color=color, width=width, wobble=wobble, pool_at_ends=pool_at_ends)


def wobble_polyline(
    draw: ImageDraw.ImageDraw,
    points: Sequence[Point],
    rng: random.Random,
    *,
    color: Color = (15, 15, 15),
    width: float = 2.0,
    wobble: float = 0.6,
    pool_at_ends: bool = False,
) -> None:
    """Stamp along a multi-segment polyline with a single global width/wobble
    profile so the whole path looks like one pen stroke."""
    pts = _densify(points, step=0.7)
    _stamp_path(draw, pts, rng, color=color, width=width, wobble=wobble, pool_at_ends=pool_at_ends)


def curved_line(
    draw: ImageDraw.ImageDraw,
    p0: Point,
    p1: Point,
    rng: random.Random,
    *,
    curvature: float = 0.15,
    color: Color = (15, 15, 15),
    width: float = 2.0,
    wobble: float = 0.3,
    pool_at_ends: bool = False,
) -> None:
    """Smooth curve from p0 to p1 bowing perpendicular to the chord. Positive
    curvature bows CCW (left of travel)."""
    x0, y0 = p0
    x1, y1 = p1
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    if length < 1.0:
        _stamp(draw, x0, y0, width / 2, color)
        return
    px, py = -dy / length, dx / length
    mx, my = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    bulge = length * curvature
    ctrl_x, ctrl_y = mx + px * bulge, my + py * bulge

    n = max(20, int(length / 2))
    t = np.linspace(0.0, 1.0, n)
    bx = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * ctrl_x + t**2 * x1
    by = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * ctrl_y + t**2 * y1
    pts = [(float(bx[i]), float(by[i])) for i in range(n)]
    _stamp_path(draw, pts, rng, color=color, width=width, wobble=wobble, pool_at_ends=pool_at_ends)


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
    stamp_step: float = 0.7,
    pool_at_ends: bool = False,
) -> None:
    """Arc (or full ring) with radial wobble. start/end in degrees CW from +X. When
    the span is a full turn the wobble is periodic so the wrap-around is seamless,
    and the pen-pressure envelope is disabled (no real endpoints)."""
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

    widths = _width_profile(n, rng, base=width, variation=width * 0.35, closed=is_closed)
    rs = radius + r_off
    xs = cx + rs * np.cos(theta)
    ys = cy + rs * np.sin(theta)

    for x, y, w in zip(xs, ys, widths):
        _stamp(draw, float(x), float(y), float(w) / 2, color)

    if pool_at_ends and not is_closed and n >= 2:
        _stamp(draw, float(xs[0]), float(ys[0]), float(widths[0]) * 1.7 / 2, color)
        _stamp(draw, float(xs[-1]), float(ys[-1]), float(widths[-1]) * 1.7 / 2, color)


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
    wobble_arc(draw, center, radius, 0.0, 360.0, rng, color=color, width=width, wobble=wobble)

"""Amulet generator. Takes a seed, returns a 600x448 RGB PIL Image.

Composition is sampled from independent pickers, one per axis:

    frame       outer ring style
    loop        suspension loop attachment style
    rim_deco    optional decoration just inside the frame (beaded rim, inner ring)
    spokes      radial element style
    inner_deco  optional inner ring of marks
    charge      central charge style
    protrusions optional things sticking out past the frame

Each picker draws into the same canvas and returns whatever the next layer
needs (e.g. the radius the spokes should stop at). All visual elements draw
through the wobble primitives in strokes.py so the hand-drawn feel is inherited.
"""

from __future__ import annotations

import hashlib
import math
import random
from datetime import datetime
from typing import Optional

from PIL import Image, ImageDraw

from . import WIDTH, HEIGHT
from .strokes import wobble_arc, wobble_line, wobble_polyline, wobble_ring, curved_line

CREAM = (244, 235, 208)
BLACK = (15, 15, 15)


# ---------------------------------------------------------------------------
# Seeding
# ---------------------------------------------------------------------------


def seed_for_minute(hh: int, mm: int) -> int:
    return int(hashlib.sha256(f"{hh:02d}:{mm:02d}".encode()).hexdigest()[:8], 16)


def seed_for_now(now: Optional[datetime] = None) -> int:
    now = now or datetime.now()
    return seed_for_minute(now.hour, now.minute)


# ---------------------------------------------------------------------------
# Frame
# ---------------------------------------------------------------------------


def draw_frame(draw, cx, cy, r, rng):
    """Draws the outer frame. Returns (spoke_outer_radius, inner_decoration_allowed)."""
    style = rng.choices(
        ["single", "double_close", "single_thick", "scalloped"],
        weights=[5, 3, 2, 2],
    )[0]
    if style == "single":
        wobble_ring(draw, (cx, cy), r, rng, color=BLACK, width=2.4, wobble=0.45)
        return r - 4, True
    if style == "double_close":
        wobble_ring(draw, (cx, cy), r, rng, color=BLACK, width=2.0, wobble=0.4)
        wobble_ring(draw, (cx, cy), r - 5, rng, color=BLACK, width=1.6, wobble=0.4)
        return r - 9, False
    if style == "single_thick":
        wobble_ring(draw, (cx, cy), r, rng, color=BLACK, width=4.0, wobble=0.35)
        return r - 6, True
    # scalloped: main ring + small outward bumps creating a frilly edge.
    # The main ring keeps the pendant boundary clear; bumps are decoration.
    wobble_ring(draw, (cx, cy), r, rng, color=BLACK, width=1.8, wobble=0.4)
    n = rng.choice([16, 20, 24, 28])
    arc_r = rng.uniform(4, 6)
    for k in range(n):
        theta = 2 * math.pi * k / n
        x = cx + (r + arc_r * 0.5) * math.cos(theta)
        y = cy + (r + arc_r * 0.5) * math.sin(theta)
        wobble_ring(draw, (x, y), arc_r, rng, color=BLACK, width=1.1, wobble=0.2)
    return r - 4, True


# ---------------------------------------------------------------------------
# Rim decoration (inside the frame, before spokes)
# ---------------------------------------------------------------------------


def draw_rim_decoration(draw, cx, cy, r_outer, rng):
    """Returns the radius spokes should extend to."""
    if not rng.choices([True, False], weights=[6, 4])[0]:
        return r_outer
    style = rng.choices(
        ["inner_ring", "beaded_rim", "dot_rim"],
        weights=[5, 3, 2],
    )[0]
    if style == "inner_ring":
        inner_r = r_outer - rng.uniform(10, 18)
        wobble_ring(draw, (cx, cy), inner_r, rng, color=BLACK, width=1.3, wobble=0.35)
        return inner_r - 2
    if style == "beaded_rim":
        n = rng.choice([12, 16, 20, 24])
        bead_r = rng.uniform(2.0, 3.2)
        rim_r = r_outer - rng.uniform(6, 12)
        for k in range(n):
            theta = 2 * math.pi * k / n
            x = cx + rim_r * math.cos(theta)
            y = cy + rim_r * math.sin(theta)
            draw.ellipse((x - bead_r, y - bead_r, x + bead_r, y + bead_r), fill=BLACK)
        return rim_r - bead_r - 3
    # dot_rim: ring of small open circles
    n = rng.choice([8, 10, 12])
    ring_r = rng.uniform(2.5, 3.5)
    rim_r = r_outer - rng.uniform(8, 14)
    for k in range(n):
        theta = 2 * math.pi * k / n
        x = cx + rim_r * math.cos(theta)
        y = cy + rim_r * math.sin(theta)
        wobble_ring(draw, (x, y), ring_r, rng, color=BLACK, width=1.0, wobble=0.2)
    return rim_r - ring_r - 3


# ---------------------------------------------------------------------------
# Spokes
# ---------------------------------------------------------------------------


def draw_spokes(draw, cx, cy, r_inner, r_outer, rng):
    """Radial elements connecting the central charge to the rim region."""
    style = rng.choices(
        ["straight", "straight_dotted", "petal", "crossbar", "sunburst", "partial"],
        weights=[5, 3, 3, 2, 2, 2],
    )[0]
    n = rng.choice([3, 4, 4, 5, 6, 6, 8])
    phase = rng.choice([0.0, math.pi / n])
    width = rng.uniform(1.4, 1.9)

    if style == "straight":
        endpoint_r = rng.uniform(2.5, 3.5)
        for k in range(n):
            theta = phase + 2 * math.pi * k / n + rng.uniform(-0.015, 0.015)
            p0 = (cx + r_inner * math.cos(theta), cy + r_inner * math.sin(theta))
            p1 = (cx + r_outer * math.cos(theta), cy + r_outer * math.sin(theta))
            wobble_line(draw, p0, p1, rng, color=BLACK, width=width, wobble=0.3, pool_at_ends=True)
            x1, y1 = p1
            draw.ellipse((x1 - endpoint_r, y1 - endpoint_r, x1 + endpoint_r, y1 + endpoint_r), fill=BLACK)
        return

    if style == "straight_dotted":
        # Straight spokes but with no endpoint marks
        for k in range(n):
            theta = phase + 2 * math.pi * k / n + rng.uniform(-0.015, 0.015)
            p0 = (cx + r_inner * math.cos(theta), cy + r_inner * math.sin(theta))
            p1 = (cx + r_outer * math.cos(theta), cy + r_outer * math.sin(theta))
            wobble_line(draw, p0, p1, rng, color=BLACK, width=width, wobble=0.3, pool_at_ends=True)
        return

    if style == "petal":
        # Pairs of curved lines meeting at center, bowing outward to form petals.
        # Pool at both ends so each petal tip terminates in a clear ink dot like
        # a real pen lifted off paper.
        curvature = rng.uniform(0.18, 0.32)
        for k in range(n):
            theta = phase + 2 * math.pi * k / n
            p0 = (cx + r_inner * math.cos(theta), cy + r_inner * math.sin(theta))
            p1 = (cx + r_outer * math.cos(theta), cy + r_outer * math.sin(theta))
            curved_line(draw, p0, p1, rng, curvature=curvature, color=BLACK, width=width, wobble=0.25, pool_at_ends=True)
            curved_line(draw, p0, p1, rng, curvature=-curvature, color=BLACK, width=width, wobble=0.25, pool_at_ends=True)
        return

    if style == "crossbar":
        # Straight spokes with small perpendicular tick at the outer end
        endpoint_r = rng.uniform(2.5, 3.2)
        bar_len = rng.uniform(8, 14)
        for k in range(n):
            theta = phase + 2 * math.pi * k / n + rng.uniform(-0.015, 0.015)
            p0 = (cx + r_inner * math.cos(theta), cy + r_inner * math.sin(theta))
            p1 = (cx + r_outer * math.cos(theta), cy + r_outer * math.sin(theta))
            wobble_line(draw, p0, p1, rng, color=BLACK, width=width, wobble=0.3, pool_at_ends=True)
            # Crossbar: perpendicular line at p1
            ppx, ppy = -math.sin(theta), math.cos(theta)
            bar_a = (p1[0] - ppx * bar_len / 2, p1[1] - ppy * bar_len / 2)
            bar_b = (p1[0] + ppx * bar_len / 2, p1[1] + ppy * bar_len / 2)
            wobble_line(draw, bar_a, bar_b, rng, color=BLACK, width=width * 0.85, wobble=0.2, pool_at_ends=True)
            draw.ellipse((p1[0] - endpoint_r, p1[1] - endpoint_r, p1[0] + endpoint_r, p1[1] + endpoint_r), fill=BLACK)
        return

    if style == "sunburst":
        # Few main spokes + many short rays just inside the rim
        main_n = rng.choice([4, 6, 8])
        ray_n = main_n * rng.choice([3, 4])
        for k in range(main_n):
            theta = phase + 2 * math.pi * k / main_n
            p0 = (cx + r_inner * math.cos(theta), cy + r_inner * math.sin(theta))
            p1 = (cx + r_outer * math.cos(theta), cy + r_outer * math.sin(theta))
            wobble_line(draw, p0, p1, rng, color=BLACK, width=width, wobble=0.3)
        ray_inner = r_outer - rng.uniform(10, 16)
        for k in range(ray_n):
            theta = 2 * math.pi * k / ray_n
            p0 = (cx + ray_inner * math.cos(theta), cy + ray_inner * math.sin(theta))
            p1 = (cx + r_outer * math.cos(theta), cy + r_outer * math.sin(theta))
            wobble_line(draw, p0, p1, rng, color=BLACK, width=width * 0.7, wobble=0.25)
        return

    if style == "partial":
        # Spokes stop short of the rim
        stop_r = r_inner + (r_outer - r_inner) * rng.uniform(0.55, 0.8)
        endpoint_r = rng.uniform(2.8, 3.8)
        for k in range(n):
            theta = phase + 2 * math.pi * k / n + rng.uniform(-0.015, 0.015)
            p0 = (cx + r_inner * math.cos(theta), cy + r_inner * math.sin(theta))
            p1 = (cx + stop_r * math.cos(theta), cy + stop_r * math.sin(theta))
            wobble_line(draw, p0, p1, rng, color=BLACK, width=width, wobble=0.3)
            draw.ellipse((p1[0] - endpoint_r, p1[1] - endpoint_r, p1[0] + endpoint_r, p1[1] + endpoint_r), fill=BLACK)
        return


# ---------------------------------------------------------------------------
# Inner decoration (between charge and rim)
# ---------------------------------------------------------------------------


def draw_inner_decoration(draw, cx, cy, r_charge, r_spokes_outer, rng):
    if rng.random() > 0.35:
        return
    style = rng.choice(["dot_ring", "small_circle_ring"])
    n = rng.choice([6, 8, 12])
    ring_r = (r_charge + r_spokes_outer) * 0.5
    offset = rng.uniform(0, 2 * math.pi)
    if style == "dot_ring":
        dot_r = rng.uniform(2.0, 3.0)
        for k in range(n):
            theta = offset + 2 * math.pi * k / n
            x = cx + ring_r * math.cos(theta)
            y = cy + ring_r * math.sin(theta)
            draw.ellipse((x - dot_r, y - dot_r, x + dot_r, y + dot_r), fill=BLACK)
    else:
        circle_r = rng.uniform(3.0, 4.5)
        for k in range(n):
            theta = offset + 2 * math.pi * k / n
            x = cx + ring_r * math.cos(theta)
            y = cy + ring_r * math.sin(theta)
            wobble_ring(draw, (x, y), circle_r, rng, color=BLACK, width=1.0, wobble=0.2)


# ---------------------------------------------------------------------------
# Central charge
# ---------------------------------------------------------------------------


def draw_charge(draw, cx, cy, rng):
    """Returns the outer radius the spokes should clear."""
    style = rng.choices(
        ["dot", "ring", "ring_dot", "concentric", "cross_in_circle", "sunburst_core"],
        weights=[4, 3, 3, 2, 2, 2],
    )[0]
    if style == "dot":
        r = rng.uniform(5, 9)
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=BLACK)
        return r + 4
    if style == "ring":
        r = rng.uniform(10, 16)
        wobble_ring(draw, (cx, cy), r, rng, color=BLACK, width=1.8, wobble=0.3)
        return r + 4
    if style == "ring_dot":
        r = rng.uniform(14, 20)
        wobble_ring(draw, (cx, cy), r, rng, color=BLACK, width=1.8, wobble=0.3)
        dot_r = rng.uniform(3, 5)
        draw.ellipse((cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r), fill=BLACK)
        return r + 4
    if style == "concentric":
        r_big = rng.uniform(16, 22)
        wobble_ring(draw, (cx, cy), r_big, rng, color=BLACK, width=1.6, wobble=0.3)
        wobble_ring(draw, (cx, cy), r_big - 5, rng, color=BLACK, width=1.2, wobble=0.25)
        dot_r = rng.uniform(2.5, 4.0)
        draw.ellipse((cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r), fill=BLACK)
        return r_big + 4
    if style == "cross_in_circle":
        r = rng.uniform(13, 18)
        wobble_ring(draw, (cx, cy), r, rng, color=BLACK, width=1.6, wobble=0.3)
        # Cross or X inside
        axis_rot = rng.choice([0.0, math.pi / 4])
        arm = r - 3
        for k in range(4):
            theta = axis_rot + math.pi / 2 * k
            x1 = cx + arm * math.cos(theta)
            y1 = cy + arm * math.sin(theta)
            wobble_line(draw, (cx, cy), (x1, y1), rng, color=BLACK, width=1.4, wobble=0.2)
        return r + 4
    # sunburst_core: small dot with short radiating lines
    r = rng.uniform(12, 18)
    dot_r = rng.uniform(2.5, 4.0)
    draw.ellipse((cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r), fill=BLACK)
    rays = rng.choice([6, 8, 12])
    for k in range(rays):
        theta = 2 * math.pi * k / rays
        x0 = cx + (dot_r + 2) * math.cos(theta)
        y0 = cy + (dot_r + 2) * math.sin(theta)
        x1 = cx + r * math.cos(theta)
        y1 = cy + r * math.sin(theta)
        wobble_line(draw, (x0, y0), (x1, y1), rng, color=BLACK, width=1.2, wobble=0.2)
    return r + 4


# ---------------------------------------------------------------------------
# Edge protrusions (past the frame)
# ---------------------------------------------------------------------------


def draw_protrusions(draw, cx, cy, r, rng):
    if rng.random() > 0.5:
        return
    style = rng.choices(
        ["bump", "ray", "trefoil_bump", "spike", "long_ray"],
        weights=[3, 3, 2, 2, 1],
    )[0]
    n = rng.choice([3, 4, 6, 8])
    phase = rng.uniform(0, 2 * math.pi)

    if style == "bump":
        bump_r = rng.uniform(4, 7)
        for k in range(n):
            theta = phase + 2 * math.pi * k / n
            x = cx + (r + bump_r * 0.6) * math.cos(theta)
            y = cy + (r + bump_r * 0.6) * math.sin(theta)
            wobble_ring(draw, (x, y), bump_r, rng, color=BLACK, width=1.6, wobble=0.3)
        return

    if style == "ray":
        ray_len = rng.uniform(8, 14)
        for k in range(n):
            theta = phase + 2 * math.pi * k / n
            x0 = cx + r * math.cos(theta)
            y0 = cy + r * math.sin(theta)
            x1 = cx + (r + ray_len) * math.cos(theta)
            y1 = cy + (r + ray_len) * math.sin(theta)
            wobble_line(draw, (x0, y0), (x1, y1), rng, color=BLACK, width=1.8, wobble=0.3)
        return

    if style == "trefoil_bump":
        # Three dots in a tight triangular cluster at each position. Use cartesian
        # offsets in the local (radial, tangential) frame so spacing reads correctly
        # regardless of r.
        dot_r = rng.uniform(2.4, 3.2)
        spacing = dot_r * 2.2  # touching-ish
        cluster_offset = rng.uniform(6, 10)
        for k in range(n):
            theta = phase + 2 * math.pi * k / n
            # Radial unit vector and tangential unit vector
            rx, ry = math.cos(theta), math.sin(theta)
            tx, ty = -math.sin(theta), math.cos(theta)
            base_x = cx + (r + cluster_offset) * rx
            base_y = cy + (r + cluster_offset) * ry
            positions = [
                (base_x + rx * dot_r * 0.8, base_y + ry * dot_r * 0.8),  # outer
                (base_x - tx * spacing * 0.5, base_y - ty * spacing * 0.5),  # left
                (base_x + tx * spacing * 0.5, base_y + ty * spacing * 0.5),  # right
            ]
            for (x, y) in positions:
                draw.ellipse((x - dot_r, y - dot_r, x + dot_r, y + dot_r), fill=BLACK)
        return

    if style == "spike":
        # Sharp triangular spikes — narrow, pointing radially outward
        spike_len = rng.uniform(10, 16)
        half_base = rng.uniform(3, 5)
        for k in range(n):
            theta = phase + 2 * math.pi * k / n
            tip = (cx + (r + spike_len) * math.cos(theta), cy + (r + spike_len) * math.sin(theta))
            ppx, ppy = -math.sin(theta), math.cos(theta)
            base_a = (cx + r * math.cos(theta) + ppx * half_base, cy + r * math.sin(theta) + ppy * half_base)
            base_b = (cx + r * math.cos(theta) - ppx * half_base, cy + r * math.sin(theta) - ppy * half_base)
            wobble_polyline(draw, [base_a, tip, base_b], rng, color=BLACK, width=1.6, wobble=0.2)
        return

    # long_ray: long line with a small dot at the end
    ray_len = rng.uniform(16, 26)
    end_dot_r = rng.uniform(2.5, 3.5)
    for k in range(n):
        theta = phase + 2 * math.pi * k / n
        x0 = cx + r * math.cos(theta)
        y0 = cy + r * math.sin(theta)
        x1 = cx + (r + ray_len) * math.cos(theta)
        y1 = cy + (r + ray_len) * math.sin(theta)
        wobble_line(draw, (x0, y0), (x1, y1), rng, color=BLACK, width=1.4, wobble=0.25)
        draw.ellipse((x1 - end_dot_r, y1 - end_dot_r, x1 + end_dot_r, y1 + end_dot_r), fill=BLACK)


# ---------------------------------------------------------------------------
# Suspension loop
# ---------------------------------------------------------------------------


def draw_loop(draw, cx, cy_top, rng):
    style = rng.choices(["stem", "yoke", "wide_loop"], weights=[4, 4, 2])[0]
    loop_r = rng.uniform(11, 17)
    stem = rng.uniform(4, 8)
    loop_cy = cy_top - stem - loop_r

    if style == "stem":
        neck_half = loop_r * 0.45
        wobble_line(draw, (cx - neck_half, cy_top), (cx - neck_half * 0.7, loop_cy + loop_r * 0.85),
                    rng, color=BLACK, width=1.8, wobble=0.2)
        wobble_line(draw, (cx + neck_half, cy_top), (cx + neck_half * 0.7, loop_cy + loop_r * 0.85),
                    rng, color=BLACK, width=1.8, wobble=0.2)
    elif style == "yoke":
        # Triangular gusset: two lines from the body splaying out, joining a horizontal top
        base_half = loop_r * 0.9
        top_half = loop_r * 0.5
        top_y = loop_cy + loop_r * 0.85
        wobble_polyline(
            draw,
            [(cx - base_half, cy_top), (cx - top_half, top_y), (cx + top_half, top_y), (cx + base_half, cy_top)],
            rng, color=BLACK, width=1.8, wobble=0.2,
        )
    else:
        # wide_loop: short stems and a flatter, wider loop
        loop_r *= 1.2
        loop_cy = cy_top - stem * 0.6 - loop_r * 0.7
        neck_half = loop_r * 0.55
        wobble_line(draw, (cx - neck_half, cy_top), (cx - neck_half, loop_cy + loop_r * 0.7),
                    rng, color=BLACK, width=1.8, wobble=0.2)
        wobble_line(draw, (cx + neck_half, cy_top), (cx + neck_half, loop_cy + loop_r * 0.7),
                    rng, color=BLACK, width=1.8, wobble=0.2)

    wobble_ring(draw, (cx, loop_cy), loop_r, rng, color=BLACK, width=2.0, wobble=0.4)


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------


def render(seed: int) -> Image.Image:
    rng = random.Random(seed)

    img = Image.new("RGB", (WIDTH, HEIGHT), CREAM)
    draw = ImageDraw.Draw(img)

    cx, cy = WIDTH // 2, HEIGHT // 2 + 14
    outer_r = min(WIDTH, HEIGHT) // 2 - 38

    # 1. Frame
    r_after_frame, allow_rim_deco = draw_frame(draw, cx, cy, outer_r, rng)

    # 2. Rim decoration (only if frame style allows)
    if allow_rim_deco:
        r_spokes_outer = draw_rim_decoration(draw, cx, cy, r_after_frame, rng)
    else:
        r_spokes_outer = r_after_frame

    # 3. Central charge
    r_charge = draw_charge(draw, cx, cy, rng)

    # 4. Inner decoration (between charge and rim)
    draw_inner_decoration(draw, cx, cy, r_charge, r_spokes_outer, rng)

    # 5. Spokes
    draw_spokes(draw, cx, cy, r_charge, r_spokes_outer, rng)

    # 6. Edge protrusions (past the outer frame)
    draw_protrusions(draw, cx, cy, outer_r, rng)

    # 7. Suspension loop (always last so its strokes sit cleanly on top)
    draw_loop(draw, cx, cy - outer_r, rng)

    return img

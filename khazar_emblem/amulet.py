"""Amulet generator. Takes a seed, returns a 600x448 RGB PIL Image.

Internally renders at SUPERSAMPLE x the output resolution and downsamples with
LANCZOS. Lines come out smoother after the e-paper's palette dithering, sub-pixel
wobble becomes legible, brush stamps stay continuous at thin widths.

Composition is sampled from independent pickers, one per axis (frame, loop,
rim_deco, spokes, inner_deco, charge, protrusions). Each helper takes a `s`
(scale) factor and multiplies its pixel quantities — coords, radii, widths,
offsets, wobble amplitudes — by it. Angles, counts, and probabilities don't
scale.
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

SUPERSAMPLE = 2  # render at WIDTH*S x HEIGHT*S, downsample with LANCZOS at the end


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


def draw_frame(draw, cx, cy, r, rng, s=1):
    style = rng.choices(
        ["single", "double_close", "single_thick", "scalloped"],
        weights=[5, 3, 2, 2],
    )[0]
    if style == "single":
        wobble_ring(draw, (cx, cy), r, rng, color=BLACK, width=2.4 * s, wobble=0.45 * s)
        return r - 4 * s, True
    if style == "double_close":
        wobble_ring(draw, (cx, cy), r, rng, color=BLACK, width=2.0 * s, wobble=0.4 * s)
        wobble_ring(draw, (cx, cy), r - 5 * s, rng, color=BLACK, width=1.6 * s, wobble=0.4 * s)
        return r - 9 * s, False
    if style == "single_thick":
        wobble_ring(draw, (cx, cy), r, rng, color=BLACK, width=4.0 * s, wobble=0.35 * s)
        return r - 6 * s, True
    # scalloped: main ring + small outward bumps creating a frilly edge
    wobble_ring(draw, (cx, cy), r, rng, color=BLACK, width=1.8 * s, wobble=0.4 * s)
    n = rng.choice([16, 20, 24, 28])
    arc_r = rng.uniform(4 * s, 6 * s)
    for k in range(n):
        theta = 2 * math.pi * k / n
        x = cx + (r + arc_r * 0.5) * math.cos(theta)
        y = cy + (r + arc_r * 0.5) * math.sin(theta)
        wobble_ring(draw, (x, y), arc_r, rng, color=BLACK, width=1.1 * s, wobble=0.2 * s)
    return r - 4 * s, True


# ---------------------------------------------------------------------------
# Rim decoration
# ---------------------------------------------------------------------------


def draw_rim_decoration(draw, cx, cy, r_outer, rng, s=1):
    if not rng.choices([True, False], weights=[6, 4])[0]:
        return r_outer
    style = rng.choices(["inner_ring", "beaded_rim", "dot_rim"], weights=[5, 3, 2])[0]
    if style == "inner_ring":
        inner_r = r_outer - rng.uniform(10 * s, 18 * s)
        wobble_ring(draw, (cx, cy), inner_r, rng, color=BLACK, width=1.3 * s, wobble=0.35 * s)
        return inner_r - 2 * s
    if style == "beaded_rim":
        n = rng.choice([12, 16, 20, 24])
        bead_r = rng.uniform(2.0 * s, 3.2 * s)
        rim_r = r_outer - rng.uniform(6 * s, 12 * s)
        for k in range(n):
            theta = 2 * math.pi * k / n
            x = cx + rim_r * math.cos(theta)
            y = cy + rim_r * math.sin(theta)
            draw.ellipse((x - bead_r, y - bead_r, x + bead_r, y + bead_r), fill=BLACK)
        return rim_r - bead_r - 3 * s
    # dot_rim: ring of small open circles
    n = rng.choice([8, 10, 12])
    ring_r = rng.uniform(2.5 * s, 3.5 * s)
    rim_r = r_outer - rng.uniform(8 * s, 14 * s)
    for k in range(n):
        theta = 2 * math.pi * k / n
        x = cx + rim_r * math.cos(theta)
        y = cy + rim_r * math.sin(theta)
        wobble_ring(draw, (x, y), ring_r, rng, color=BLACK, width=1.0 * s, wobble=0.2 * s)
    return rim_r - ring_r - 3 * s


# ---------------------------------------------------------------------------
# Spokes
# ---------------------------------------------------------------------------


def draw_spokes(draw, cx, cy, r_inner, r_outer, rng, s=1):
    style = rng.choices(
        ["straight", "straight_dotted", "petal", "crossbar", "sunburst", "partial"],
        weights=[5, 3, 3, 2, 2, 2],
    )[0]
    n = rng.choice([3, 4, 4, 5, 6, 6, 8])
    phase = rng.choice([0.0, math.pi / n])
    width = rng.uniform(1.4 * s, 1.9 * s)

    if style == "straight":
        endpoint_r = rng.uniform(2.5 * s, 3.5 * s)
        for k in range(n):
            theta = phase + 2 * math.pi * k / n + rng.uniform(-0.015, 0.015)
            p0 = (cx + r_inner * math.cos(theta), cy + r_inner * math.sin(theta))
            p1 = (cx + r_outer * math.cos(theta), cy + r_outer * math.sin(theta))
            wobble_line(draw, p0, p1, rng, color=BLACK, width=width, wobble=0.3 * s, pool_at_ends=True)
            x1, y1 = p1
            draw.ellipse((x1 - endpoint_r, y1 - endpoint_r, x1 + endpoint_r, y1 + endpoint_r), fill=BLACK)
        return

    if style == "straight_dotted":
        for k in range(n):
            theta = phase + 2 * math.pi * k / n + rng.uniform(-0.015, 0.015)
            p0 = (cx + r_inner * math.cos(theta), cy + r_inner * math.sin(theta))
            p1 = (cx + r_outer * math.cos(theta), cy + r_outer * math.sin(theta))
            wobble_line(draw, p0, p1, rng, color=BLACK, width=width, wobble=0.3 * s, pool_at_ends=True)
        return

    if style == "petal":
        curvature = rng.uniform(0.18, 0.32)  # fraction of chord, not pixels
        for k in range(n):
            theta = phase + 2 * math.pi * k / n
            p0 = (cx + r_inner * math.cos(theta), cy + r_inner * math.sin(theta))
            p1 = (cx + r_outer * math.cos(theta), cy + r_outer * math.sin(theta))
            curved_line(draw, p0, p1, rng, curvature=curvature, color=BLACK, width=width, wobble=0.25 * s, pool_at_ends=True)
            curved_line(draw, p0, p1, rng, curvature=-curvature, color=BLACK, width=width, wobble=0.25 * s, pool_at_ends=True)
        return

    if style == "crossbar":
        endpoint_r = rng.uniform(2.5 * s, 3.2 * s)
        bar_len = rng.uniform(8 * s, 14 * s)
        for k in range(n):
            theta = phase + 2 * math.pi * k / n + rng.uniform(-0.015, 0.015)
            p0 = (cx + r_inner * math.cos(theta), cy + r_inner * math.sin(theta))
            p1 = (cx + r_outer * math.cos(theta), cy + r_outer * math.sin(theta))
            wobble_line(draw, p0, p1, rng, color=BLACK, width=width, wobble=0.3 * s, pool_at_ends=True)
            ppx, ppy = -math.sin(theta), math.cos(theta)
            bar_a = (p1[0] - ppx * bar_len / 2, p1[1] - ppy * bar_len / 2)
            bar_b = (p1[0] + ppx * bar_len / 2, p1[1] + ppy * bar_len / 2)
            wobble_line(draw, bar_a, bar_b, rng, color=BLACK, width=width * 0.85, wobble=0.2 * s, pool_at_ends=True)
            draw.ellipse((p1[0] - endpoint_r, p1[1] - endpoint_r, p1[0] + endpoint_r, p1[1] + endpoint_r), fill=BLACK)
        return

    if style == "sunburst":
        main_n = rng.choice([4, 6, 8])
        ray_n = main_n * rng.choice([3, 4])
        for k in range(main_n):
            theta = phase + 2 * math.pi * k / main_n
            p0 = (cx + r_inner * math.cos(theta), cy + r_inner * math.sin(theta))
            p1 = (cx + r_outer * math.cos(theta), cy + r_outer * math.sin(theta))
            wobble_line(draw, p0, p1, rng, color=BLACK, width=width, wobble=0.3 * s)
        ray_inner = r_outer - rng.uniform(10 * s, 16 * s)
        for k in range(ray_n):
            theta = 2 * math.pi * k / ray_n
            p0 = (cx + ray_inner * math.cos(theta), cy + ray_inner * math.sin(theta))
            p1 = (cx + r_outer * math.cos(theta), cy + r_outer * math.sin(theta))
            wobble_line(draw, p0, p1, rng, color=BLACK, width=width * 0.7, wobble=0.25 * s)
        return

    if style == "partial":
        stop_r = r_inner + (r_outer - r_inner) * rng.uniform(0.55, 0.8)
        endpoint_r = rng.uniform(2.8 * s, 3.8 * s)
        for k in range(n):
            theta = phase + 2 * math.pi * k / n + rng.uniform(-0.015, 0.015)
            p0 = (cx + r_inner * math.cos(theta), cy + r_inner * math.sin(theta))
            p1 = (cx + stop_r * math.cos(theta), cy + stop_r * math.sin(theta))
            wobble_line(draw, p0, p1, rng, color=BLACK, width=width, wobble=0.3 * s)
            draw.ellipse((p1[0] - endpoint_r, p1[1] - endpoint_r, p1[0] + endpoint_r, p1[1] + endpoint_r), fill=BLACK)
        return


# ---------------------------------------------------------------------------
# Inner decoration
# ---------------------------------------------------------------------------


def draw_inner_decoration(draw, cx, cy, r_charge, r_spokes_outer, rng, s=1):
    if rng.random() > 0.35:
        return
    style = rng.choice(["dot_ring", "small_circle_ring"])
    n = rng.choice([6, 8, 12])
    ring_r = (r_charge + r_spokes_outer) * 0.5
    offset = rng.uniform(0, 2 * math.pi)
    if style == "dot_ring":
        dot_r = rng.uniform(2.0 * s, 3.0 * s)
        for k in range(n):
            theta = offset + 2 * math.pi * k / n
            x = cx + ring_r * math.cos(theta)
            y = cy + ring_r * math.sin(theta)
            draw.ellipse((x - dot_r, y - dot_r, x + dot_r, y + dot_r), fill=BLACK)
    else:
        circle_r = rng.uniform(3.0 * s, 4.5 * s)
        for k in range(n):
            theta = offset + 2 * math.pi * k / n
            x = cx + ring_r * math.cos(theta)
            y = cy + ring_r * math.sin(theta)
            wobble_ring(draw, (x, y), circle_r, rng, color=BLACK, width=1.0 * s, wobble=0.2 * s)


# ---------------------------------------------------------------------------
# Central charge
# ---------------------------------------------------------------------------


def draw_charge(draw, cx, cy, rng, s=1):
    style = rng.choices(
        ["dot", "ring", "ring_dot", "concentric", "cross_in_circle", "sunburst_core"],
        weights=[4, 3, 3, 2, 2, 2],
    )[0]
    if style == "dot":
        r = rng.uniform(5 * s, 9 * s)
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=BLACK)
        return r + 4 * s
    if style == "ring":
        r = rng.uniform(10 * s, 16 * s)
        wobble_ring(draw, (cx, cy), r, rng, color=BLACK, width=1.8 * s, wobble=0.3 * s)
        return r + 4 * s
    if style == "ring_dot":
        r = rng.uniform(14 * s, 20 * s)
        wobble_ring(draw, (cx, cy), r, rng, color=BLACK, width=1.8 * s, wobble=0.3 * s)
        dot_r = rng.uniform(3 * s, 5 * s)
        draw.ellipse((cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r), fill=BLACK)
        return r + 4 * s
    if style == "concentric":
        r_big = rng.uniform(16 * s, 22 * s)
        wobble_ring(draw, (cx, cy), r_big, rng, color=BLACK, width=1.6 * s, wobble=0.3 * s)
        wobble_ring(draw, (cx, cy), r_big - 5 * s, rng, color=BLACK, width=1.2 * s, wobble=0.25 * s)
        dot_r = rng.uniform(2.5 * s, 4.0 * s)
        draw.ellipse((cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r), fill=BLACK)
        return r_big + 4 * s
    if style == "cross_in_circle":
        r = rng.uniform(13 * s, 18 * s)
        wobble_ring(draw, (cx, cy), r, rng, color=BLACK, width=1.6 * s, wobble=0.3 * s)
        axis_rot = rng.choice([0.0, math.pi / 4])
        arm = r - 3 * s
        for k in range(4):
            theta = axis_rot + math.pi / 2 * k
            x1 = cx + arm * math.cos(theta)
            y1 = cy + arm * math.sin(theta)
            wobble_line(draw, (cx, cy), (x1, y1), rng, color=BLACK, width=1.4 * s, wobble=0.2 * s)
        return r + 4 * s
    # sunburst_core
    r = rng.uniform(12 * s, 18 * s)
    dot_r = rng.uniform(2.5 * s, 4.0 * s)
    draw.ellipse((cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r), fill=BLACK)
    rays = rng.choice([6, 8, 12])
    for k in range(rays):
        theta = 2 * math.pi * k / rays
        x0 = cx + (dot_r + 2 * s) * math.cos(theta)
        y0 = cy + (dot_r + 2 * s) * math.sin(theta)
        x1 = cx + r * math.cos(theta)
        y1 = cy + r * math.sin(theta)
        wobble_line(draw, (x0, y0), (x1, y1), rng, color=BLACK, width=1.2 * s, wobble=0.2 * s)
    return r + 4 * s


# ---------------------------------------------------------------------------
# Edge protrusions
# ---------------------------------------------------------------------------


def draw_protrusions(draw, cx, cy, r, rng, s=1):
    if rng.random() > 0.5:
        return
    style = rng.choices(
        ["bump", "ray", "trefoil_bump", "spike", "long_ray"],
        weights=[3, 3, 2, 2, 1],
    )[0]
    n = rng.choice([3, 4, 6, 8])
    phase = rng.uniform(0, 2 * math.pi)

    if style == "bump":
        bump_r = rng.uniform(4 * s, 7 * s)
        for k in range(n):
            theta = phase + 2 * math.pi * k / n
            x = cx + (r + bump_r * 0.6) * math.cos(theta)
            y = cy + (r + bump_r * 0.6) * math.sin(theta)
            wobble_ring(draw, (x, y), bump_r, rng, color=BLACK, width=1.6 * s, wobble=0.3 * s)
        return

    if style == "ray":
        ray_len = rng.uniform(8 * s, 14 * s)
        for k in range(n):
            theta = phase + 2 * math.pi * k / n
            x0 = cx + r * math.cos(theta)
            y0 = cy + r * math.sin(theta)
            x1 = cx + (r + ray_len) * math.cos(theta)
            y1 = cy + (r + ray_len) * math.sin(theta)
            wobble_line(draw, (x0, y0), (x1, y1), rng, color=BLACK, width=1.8 * s, wobble=0.3 * s)
        return

    if style == "trefoil_bump":
        dot_r = rng.uniform(2.4 * s, 3.2 * s)
        spacing = dot_r * 2.2
        cluster_offset = rng.uniform(6 * s, 10 * s)
        for k in range(n):
            theta = phase + 2 * math.pi * k / n
            rx, ry = math.cos(theta), math.sin(theta)
            tx, ty = -math.sin(theta), math.cos(theta)
            base_x = cx + (r + cluster_offset) * rx
            base_y = cy + (r + cluster_offset) * ry
            positions = [
                (base_x + rx * dot_r * 0.8, base_y + ry * dot_r * 0.8),
                (base_x - tx * spacing * 0.5, base_y - ty * spacing * 0.5),
                (base_x + tx * spacing * 0.5, base_y + ty * spacing * 0.5),
            ]
            for (x, y) in positions:
                draw.ellipse((x - dot_r, y - dot_r, x + dot_r, y + dot_r), fill=BLACK)
        return

    if style == "spike":
        spike_len = rng.uniform(10 * s, 16 * s)
        half_base = rng.uniform(3 * s, 5 * s)
        for k in range(n):
            theta = phase + 2 * math.pi * k / n
            tip = (cx + (r + spike_len) * math.cos(theta), cy + (r + spike_len) * math.sin(theta))
            ppx, ppy = -math.sin(theta), math.cos(theta)
            base_a = (cx + r * math.cos(theta) + ppx * half_base, cy + r * math.sin(theta) + ppy * half_base)
            base_b = (cx + r * math.cos(theta) - ppx * half_base, cy + r * math.sin(theta) - ppy * half_base)
            wobble_polyline(draw, [base_a, tip, base_b], rng, color=BLACK, width=1.6 * s, wobble=0.2 * s)
        return

    # long_ray
    ray_len = rng.uniform(16 * s, 26 * s)
    end_dot_r = rng.uniform(2.5 * s, 3.5 * s)
    for k in range(n):
        theta = phase + 2 * math.pi * k / n
        x0 = cx + r * math.cos(theta)
        y0 = cy + r * math.sin(theta)
        x1 = cx + (r + ray_len) * math.cos(theta)
        y1 = cy + (r + ray_len) * math.sin(theta)
        wobble_line(draw, (x0, y0), (x1, y1), rng, color=BLACK, width=1.4 * s, wobble=0.25 * s)
        draw.ellipse((x1 - end_dot_r, y1 - end_dot_r, x1 + end_dot_r, y1 + end_dot_r), fill=BLACK)


# ---------------------------------------------------------------------------
# Suspension loop
# ---------------------------------------------------------------------------


def draw_loop(draw, cx, cy_top, rng, s=1):
    style = rng.choices(["stem", "yoke", "wide_loop"], weights=[4, 4, 2])[0]
    loop_r = rng.uniform(11 * s, 17 * s)
    stem = rng.uniform(4 * s, 8 * s)
    loop_cy = cy_top - stem - loop_r

    if style == "stem":
        neck_half = loop_r * 0.45
        wobble_line(draw, (cx - neck_half, cy_top), (cx - neck_half * 0.7, loop_cy + loop_r * 0.85),
                    rng, color=BLACK, width=1.8 * s, wobble=0.2 * s)
        wobble_line(draw, (cx + neck_half, cy_top), (cx + neck_half * 0.7, loop_cy + loop_r * 0.85),
                    rng, color=BLACK, width=1.8 * s, wobble=0.2 * s)
    elif style == "yoke":
        base_half = loop_r * 0.9
        top_half = loop_r * 0.5
        top_y = loop_cy + loop_r * 0.85
        wobble_polyline(
            draw,
            [(cx - base_half, cy_top), (cx - top_half, top_y), (cx + top_half, top_y), (cx + base_half, cy_top)],
            rng, color=BLACK, width=1.8 * s, wobble=0.2 * s,
        )
    else:
        loop_r *= 1.2
        loop_cy = cy_top - stem * 0.6 - loop_r * 0.7
        neck_half = loop_r * 0.55
        wobble_line(draw, (cx - neck_half, cy_top), (cx - neck_half, loop_cy + loop_r * 0.7),
                    rng, color=BLACK, width=1.8 * s, wobble=0.2 * s)
        wobble_line(draw, (cx + neck_half, cy_top), (cx + neck_half, loop_cy + loop_r * 0.7),
                    rng, color=BLACK, width=1.8 * s, wobble=0.2 * s)

    wobble_ring(draw, (cx, loop_cy), loop_r, rng, color=BLACK, width=2.0 * s, wobble=0.4 * s)


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------


def render(seed: int) -> Image.Image:
    rng = random.Random(seed)
    s = SUPERSAMPLE
    W = WIDTH * s
    H = HEIGHT * s

    img = Image.new("RGB", (W, H), CREAM)
    draw = ImageDraw.Draw(img)

    cx, cy = W // 2, H // 2 + 14 * s
    outer_r = (min(WIDTH, HEIGHT) // 2 - 38) * s

    r_after_frame, allow_rim_deco = draw_frame(draw, cx, cy, outer_r, rng, s)
    r_spokes_outer = draw_rim_decoration(draw, cx, cy, r_after_frame, rng, s) if allow_rim_deco else r_after_frame
    r_charge = draw_charge(draw, cx, cy, rng, s)
    draw_inner_decoration(draw, cx, cy, r_charge, r_spokes_outer, rng, s)
    draw_spokes(draw, cx, cy, r_charge, r_spokes_outer, rng, s)
    draw_protrusions(draw, cx, cy, outer_r, rng, s)
    draw_loop(draw, cx, cy - outer_r, rng, s)

    if s != 1:
        img = img.resize((WIDTH, HEIGHT), Image.LANCZOS)
    return img

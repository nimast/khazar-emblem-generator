"""Mac/Linux preview entry point. Renders one amulet (or a fast loop) and shows
it without touching the Inky hardware.

Examples:
    python -m khazar_emblem.preview
    python -m khazar_emblem.preview --at 14:23
    python -m khazar_emblem.preview --png out.png
    python -m khazar_emblem.preview --loop --interval 1
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime
from pathlib import Path

from . import amulet
from .sinks import PreviewSink


def parse_hhmm(s: str) -> tuple[int, int]:
    hh, mm = s.split(":")
    return int(hh), int(mm)


def main() -> None:
    ap = argparse.ArgumentParser(description="Preview the Khazar emblem generator.")
    ap.add_argument(
        "--at",
        help="Render this specific HH:MM instead of the current time.",
    )
    ap.add_argument(
        "--png",
        type=Path,
        help="Save to PNG instead of opening a window.",
    )
    ap.add_argument(
        "--loop",
        action="store_true",
        help="Advance every --interval seconds, simulating a fast wall clock.",
    )
    ap.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Seconds between renders when --loop is set (default: 1).",
    )
    args = ap.parse_args()

    sink = PreviewSink(png_path=args.png, show_window=args.png is None)

    if args.loop:
        minute = 0
        while True:
            hh, mm = (minute // 60) % 24, minute % 60
            seed = amulet.seed_for_minute(hh, mm)
            img = amulet.render(seed)
            print(f"{hh:02d}:{mm:02d}  seed={seed}")
            sink.push(img)
            minute += 1
            time.sleep(args.interval)
        return

    if args.at:
        hh, mm = parse_hhmm(args.at)
        seed = amulet.seed_for_minute(hh, mm)
        print(f"{hh:02d}:{mm:02d}  seed={seed}")
    else:
        now = datetime.now()
        seed = amulet.seed_for_now(now)
        print(f"{now:%H:%M}  seed={seed}")

    img = amulet.render(seed)
    sink.push(img)


if __name__ == "__main__":
    main()

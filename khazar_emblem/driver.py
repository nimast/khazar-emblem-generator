"""Pi driver. Sleeps until the next minute boundary, renders the amulet for that
minute, pushes to the Inky Impression, repeats forever.

Run on the Pi:
    python -m khazar_emblem.driver
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta

from . import amulet
from .sinks import InkySink


def sleep_until_next_minute() -> datetime:
    """Block until the next HH:MM:00 boundary. Returns the new clock time."""
    now = datetime.now()
    nxt = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
    time.sleep(max(0.0, (nxt - now).total_seconds()))
    return nxt


def main() -> None:
    sink = InkySink()
    while True:
        now = sleep_until_next_minute()
        seed = amulet.seed_for_minute(now.hour, now.minute)
        print(f"{now:%H:%M}  seed={seed}", flush=True)
        img = amulet.render(seed)
        sink.push(img)


if __name__ == "__main__":
    main()

"""Pi driver. Renders the amulet for the current clock minute, pushes to the Inky
Impression, sleeps until the next refresh slot, repeats forever.

Cadence: REFRESH_INTERVAL seconds between render starts. With the e-paper
refresh taking ~30-35s, a 90s interval gives a smooth ~1.5 min visible rhythm
without the device feeling frantic.

Run on the Pi:
    python -m khazar_emblem.driver
"""

from __future__ import annotations

import time
from datetime import datetime

from . import amulet
from .sinks import InkySink

REFRESH_INTERVAL = 120.0  # seconds between render starts


def main() -> None:
    sink = InkySink()
    while True:
        cycle_start = time.monotonic()
        now = datetime.now()
        seed = amulet.seed_for_minute(now.hour, now.minute)
        print(f"{now:%H:%M:%S}  seed={seed}", flush=True)
        img = amulet.render(seed)
        sink.push(img)
        elapsed = time.monotonic() - cycle_start
        sleep_for = max(0.0, REFRESH_INTERVAL - elapsed)
        time.sleep(sleep_for)


if __name__ == "__main__":
    main()

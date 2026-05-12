"""Pi driver. Renders the amulet for the current clock minute, pushes to the
Inky Impression, sleeps until the next refresh slot, repeats forever.

Cadence: REFRESH_INTERVAL seconds between render starts. With the e-paper push
taking ~30-35s, a 120s interval gives a smooth ~2 min visible rhythm.

Logging is minimal but explicit: a single line per event (start, render, push,
error). Inky's busy-wait UserWarnings are filtered out so the log stays clean.
Exceptions in the loop are caught and logged — the driver doesn't die on a
transient error.

Run on the Pi:
    python -m khazar_emblem.driver
"""

from __future__ import annotations

import logging
import sys
import time
import warnings
from datetime import datetime

from . import amulet
from .sinks import InkySink

REFRESH_INTERVAL = 120.0  # seconds between render starts
ERROR_BACKOFF = 30.0  # seconds to wait after an exception before retrying

# Suppress inky's per-refresh "Busy Wait" UserWarnings — they're normal, not errors.
warnings.filterwarnings("ignore", message="Busy Wait:.*")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("khazar")


def main() -> None:
    log.info("driver start")
    try:
        sink = InkySink()
    except Exception as e:
        log.error(f"InkySink init failed: {e!r}")
        raise
    log.info("inky ready")

    while True:
        cycle_start = time.monotonic()
        try:
            now = datetime.now()
            seed = amulet.seed_for_minute(now.hour, now.minute)
            log.info(f"render {now:%H:%M} seed={seed}")
            t0 = time.monotonic()
            img = amulet.render(seed)
            t_render = time.monotonic() - t0
            t0 = time.monotonic()
            sink.push(img)
            t_push = time.monotonic() - t0
            log.info(f"pushed  render={t_render:.2f}s push={t_push:.2f}s")
        except Exception as e:
            log.error(f"cycle failed: {e!r}")
            time.sleep(ERROR_BACKOFF)
            continue

        elapsed = time.monotonic() - cycle_start
        sleep_for = max(0.0, REFRESH_INTERVAL - elapsed)
        time.sleep(sleep_for)


if __name__ == "__main__":
    main()

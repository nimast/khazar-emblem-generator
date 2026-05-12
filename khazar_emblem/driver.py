"""Pi driver. Renders the amulet for the current clock minute, pushes to the
Inky Impression, sleeps until the next refresh slot, repeats forever.

Cadence: REFRESH_INTERVAL seconds between render starts. With the e-paper push
taking ~30-35s, a 120s interval gives a smooth ~2 min visible rhythm.

Logging policy: silent unless something is worth knowing. One line on
successful startup (after the first render+push), and one line per error. No
per-cycle chatter — for a long-running process you don't need to know each
2-minute heartbeat. Inky's per-refresh busy-wait UserWarnings are suppressed
so the log doesn't fill with normal hardware polling messages.

Errors don't crash the driver: each cycle is wrapped in try/except, on failure
it logs and backs off ERROR_BACKOFF seconds, then retries.

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

# Suppress inky's per-refresh "Busy Wait" UserWarnings — normal hardware polling.
warnings.filterwarnings("ignore", message="Busy Wait:.*")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("khazar")


def main() -> None:
    try:
        sink = InkySink()
    except Exception as e:
        log.error(f"inky init failed: {e!r}")
        raise

    first_cycle = True
    while True:
        cycle_start = time.monotonic()
        try:
            now = datetime.now()
            seed = amulet.seed_for_minute(now.hour, now.minute)
            img = amulet.render(seed)
            sink.push(img)
        except Exception as e:
            log.error(f"cycle failed at {datetime.now():%H:%M}: {e!r}")
            time.sleep(ERROR_BACKOFF)
            continue

        if first_cycle:
            log.info(f"driver started — first render at {now:%H:%M} OK")
            first_cycle = False

        elapsed = time.monotonic() - cycle_start
        time.sleep(max(0.0, REFRESH_INTERVAL - elapsed))


if __name__ == "__main__":
    main()

# Khazar Emblem Generator

A wall-mounted Raspberry Pi + Pimoroni Inky Impression 5.7" e-paper display that renders one synthetic Khazar-style round sun-amulet every minute. The amulet is deterministic from clock time, so the device is a 1440-face wall clock: 14:23 today renders the same artifact as 14:23 tomorrow. Black ink on cream parchment, hand-drawn feel, no text. Part of the *Light The Same Fire* art project.

## Two run modes

The generator is split from the display "sink" so you can iterate fast on a Mac without flashing an e-paper display every change.

- **Preview mode** (Mac / Linux / anywhere with PIL): renders the same 600×448 image and either pops a window or writes a PNG to disk. Tight loop, sub-second feedback.
- **Hardware mode** (Pi + Inky Impression HAT): renders the same image, palette-quantizes, and pushes to the e-paper via `inky.set_image()` + `inky.show()`. Real artifact, ~30s refresh.

The render code is identical in both modes — only the sink differs.

## Hardware

- Raspberry Pi (any recent model)
- Pimoroni Inky Impression 5.7" 7-color e-paper HAT (600×448 px)
- Wall power (continuous 1/min refresh)

## Setup

### Preview (Mac / Linux dev loop)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m khazar_emblem.preview              # one render, opens a window
python -m khazar_emblem.preview --loop       # advances every "minute" (fast clock)
python -m khazar_emblem.preview --at 14:23   # render a specific minute
python -m khazar_emblem.preview --png out.png  # save instead of window
```

### Hardware (Pi)

```bash
python -m venv ~/.virtualenvs/pimoroni
source ~/.virtualenvs/pimoroni/bin/activate
pip install -r requirements.txt -r requirements-pi.txt
```

Follow Pimoroni's Inky setup: <https://learn.pimoroni.com/article/getting-started-with-inky-impression>

```bash
python -m khazar_emblem.driver               # loop forever, real minute boundaries
```

Or install the systemd unit (`systemd/khazar-emblem.service` — added later).

## Design

Full design doc: `~/.gstack/projects/nimast-khazar-emblem-generator/`.

Locked decisions: minute-seeded determinism, restrained palette (black + cream, rare accent), hand-drawn line work (variable weight + wobble), no text on the output, no persistence (render-and-forget).

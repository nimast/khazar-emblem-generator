# Khazar Emblem Generator — Design Constraints

This document captures the locked decisions, the vocabulary, and what's still
open. It's the offline-friendly reference. The richer reasoning, alternatives,
and original /office-hours brainstorm lives outside the repo at
`~/.gstack/projects/nimast-khazar-emblem-generator/`.

---

## What this is

A wall-plugged Raspberry Pi + Pimoroni Inky Impression 5.7" e-paper display
that renders **one synthetic Khazar-style round sun-amulet pendant** per
refresh. The artifact is deterministic from clock time, so the device is a
**1440-face wall clock** — 14:23 today renders the same amulet as 14:23
tomorrow. Part of the larger *Light The Same Fire* art project.

## What it's NOT

- Not a generative-art wallpaper that shows infinite novelty
- Not a composite plate of multiple finds
- Not a faithful reproduction of any single real Khazar pendant
- Not displaying any text, runes, item numbers, scale bars, captions, or
  catalog chrome — the amulet is the whole image, unmediated

---

## Hardware constraints (locked)

- **Display**: Pimoroni Inky Impression 5.7" e-paper, 600 × 448 px, 7 colors
  (BLACK, WHITE, YELLOW, RED, BLUE, GREEN, ORANGE)
- **Refresh**: ~30-35s per full e-paper update
- **Computer**: Raspberry Pi Zero 2 W (aarch64, 416MB RAM)
- **Power**: wall-plugged (continuous refresh negates battery)
- **Lifespan**: ~2 years at current cadence (acceptable)

## Software constraints (locked)

- **Render library**: Pimoroni `inky` (`inky[rpi]`) v2.4+
- **Image format**: PIL RGB image sized to `inky_display.width × inky_display.height`
  (600 × 448). The inky lib palette-quantizes + dithers to the 7-color palette
  internally.
- **Render path**: `set_image(img)` → `show()` (blocks until refresh complete)
- **SPI config**: kernel SPI on (`dtparam=spi=on`) **plus** `dtoverlay=spi0-0cs`
  in `/boot/firmware/config.txt` — inky 2.x needs the SPI bus device AND
  unbound GPIO8 so it can drive CS directly via gpiod
- **Driver virtualenv**: `~/.virtualenvs/pimoroni/` on the Pi
- **Auto-start**: crontab `@reboot` does `git pull && start driver`

## Refresh cadence

- **Current**: 120s between render starts (controlled by `REFRESH_INTERVAL` in
  `khazar_emblem/driver.py`)
- **Compute budget per cycle**: ~25s after the e-paper push. Currently using
  ~0.15-2s. Lots of headroom.

---

## Aesthetic premises (locked)

1. **Restrained palette.** Black ink + cream parchment dominate. Accent colors
   (red/blue/green/yellow/orange) used rarely if at all (≤1-2 elements per
   amulet). The 7-color blast is wrong — restraint reads as artifact, saturation
   reads as toy.

2. **Algorithmic compositional grammar.** Each amulet is sampled from
   independent axes (frame × rim_deco × spokes × inner_deco × charge ×
   protrusions × loop). Vocabulary is drawn from items 1-12 of the round-amulets
   archaeology plate at:
   `/Users/nimast/insync-nimast/Art/2025 Light The Same Fire/Research/Prejudices about Archeology and Ethnicity/Screenshot 2025-08-18 at 12.17.16.png`

3. **Hand-drawn feel.** Variable line weight, slight wobble, pen-pressure
   envelope on each stroke, ink-pooling at endpoints. Vector-perfect strokes
   read digital and break the archaeological-line-drawing illusion. All visual
   layers draw through `khazar_emblem/strokes.py`.

4. **Minute-seeded determinism.** `seed = sha256("HH:MM")[:8]`. Same minute
   always renders the same amulet. Device functions as a clock with 1440
   unique faces. Lets you photograph "your" minute (birthday, etc.) and it
   stays stable.

5. **Render-and-forget.** No snapshot persistence. Each refresh recomputes
   from the seed. If a "favorite minute" feature is wanted, it's a one-liner
   add later — for now the artifact is ephemeral.

6. **No text. No chrome.** No runic captions, no item numbers, no scale bars,
   no inscriptions. Pure visual artifact. (User reaffirmed this twice.)

---

## Compositional vocabulary (current)

Implemented in `khazar_emblem/amulet.py` as independent pickers.

### Frame styles
- `single` — one thick ring
- `double_close` — two parallel rings ~5px apart
- `single_thick` — extra-bold single ring
- `scalloped` — main ring + small outward arc bumps for a frilly edge

### Rim decoration (inside frame)
- None (40%) | `inner_ring` (~30%) | `beaded_rim` (~20%) | `dot_rim` (~10%)

### Spoke styles
- `straight` — solid spokes with endpoint dot at rim
- `straight_dotted` — spokes without endpoint dots
- `petal` — pairs of curved Bezier arcs forming quatrefoil/hexafoil silhouettes
- `crossbar` — straight spoke + perpendicular tick at outer end
- `sunburst` — few main spokes + many short rays just inside rim
- `partial` — spokes stopping short of the rim
- Counts: 3, 4, 5, 6, or 8

### Central charge
- `dot` — filled disc
- `ring` — open circle
- `ring_dot` — ring with center dot
- `concentric` — two nested rings + center dot
- `cross_in_circle` — + or × inside a circle
- `sunburst_core` — center dot with short radiating rays

### Inner decoration (optional, ~35%)
- `dot_ring` — scattered small filled dots
- `small_circle_ring` — small open circles in a ring

### Edge protrusions (optional, ~50%)
- `bump` — small open circles outside the rim
- `ray` — short outward lines
- `trefoil_bump` — tight 3-dot clusters
- `spike` — narrow triangular spikes
- `long_ray` — long lines with dot at the end

### Suspension loop (always)
- `stem` — two parallel necks + ring
- `yoke` — triangular gusset → ring
- `wide_loop` — flatter, wider variant

---

## Rendering pipeline

`render(seed) → PIL.Image`:

1. Seed RNG from `seed`.
2. Allocate RGB canvas at `WIDTH * SUPERSAMPLE × HEIGHT * SUPERSAMPLE` (1200×896 with `SUPERSAMPLE=2`).
3. Compose: frame → rim_deco → charge → inner_deco → spokes → protrusions → loop.
   Each helper takes a scale factor `s` and multiplies pixel quantities by it.
4. Downsample to `WIDTH × HEIGHT` with `Image.LANCZOS`.

The supersample → downsample path is what makes lines read smoothly after the
e-paper's palette dither. Helpers all draw through `strokes.py` primitives
(`wobble_line`, `wobble_arc`, `wobble_ring`, `curved_line`, `wobble_polyline`),
which apply:

- Brush-stamp rendering (overlapping filled discs along the path)
- Pen-pressure bell envelope (thin endpoints, fills out mid-stroke)
- Ornstein-Uhlenbeck width drift (mean-reverting, bounded)
- Perpendicular wobble (Brownian bridge for open paths, periodic Fourier for
  closed rings)
- Optional ink-pool dots at stroke endpoints

---

## Sink abstraction

`render()` returns a plain RGB PIL image. Two sinks pick where it goes:

- `PreviewSink` (Mac/Linux dev): saves PNG or pops a window. Sub-second
  iteration — no e-paper hardware needed.
- `InkySink` (Pi only): lazy-imports `inky.auto`, palette-quantizes, calls
  `set_image()` + `show()`. ~35s refresh.

This lets all design iteration happen on a laptop without burning e-paper
refresh cycles.

---

## Open / queued

Things that are reasonable next moves, not blocking and not yet implemented:

- **Color** — introduce the rare-accent rule. 15-25% chance one structural
  element gets a non-black color (weighted toward red ochre/carnelian). Risk:
  could compromise the restraint aesthetic if overdone.
- **Multi-pass strokes** — for bold elements (frame, outer ring), draw the
  stroke twice with slight offset, mimicking pen retracing for emphasis.
- **Asymmetry probability** — small chance per amulet that one element is
  irregular (one spoke different length, one protrusion missing). Adds
  humanity.
- **Zoomorphic edge protrusions** — animal-head bumps like items 9-11 of the
  source plate. Procedural-ish, suggestive rather than literal.
- **Splash frame** — single bundled PNG for the boot-to-first-render gap.
- **Convert crontab to systemd** — proper service unit with auto-restart on
  crash, not just on reboot.
- **Captive portal / AP fallback** — comitup is installed and active on the
  Pi (when no known WiFi is reachable, it advertises `comitup-204` and serves
  a captive portal at `http://10.41.0.1` for provisioning new WiFi). Not yet
  end-to-end tested.

---

## File layout (in this repo)

```
khazar_emblem/
  __init__.py      # WIDTH=600, HEIGHT=448 constants
  amulet.py        # render(seed) and compositional pickers
  strokes.py       # wobble_line, wobble_arc, wobble_ring, curved_line, _stamp_path
  sinks.py         # PreviewSink (Mac) + InkySink (Pi)
  preview.py       # CLI: python -m khazar_emblem.preview
  driver.py        # Pi-side: python -m khazar_emblem.driver, REFRESH_INTERVAL=120
```

## How to iterate offline

```bash
# Tight visual loop on Mac (no Pi needed)
python -m khazar_emblem.preview --at 14:23 --png /tmp/x.png
open /tmp/x.png

# Sweep many minutes
for t in 00:00 04:37 12:00 18:45 23:59; do
  python -m khazar_emblem.preview --at $t --png ~/Desktop/khazar-samples/$(echo $t | tr ':' '-').png
done

# When happy: commit + push
git add khazar_emblem/
git commit -m "..."
git push

# Pi picks up changes on next reboot (crontab does git pull first).
# Manual push to Pi if reachable:
ssh pi@inkypi.local 'cd ~/khazar-emblem-generator && git pull && pkill -f khazar_emblem && (nohup ~/.virtualenvs/pimoroni/bin/python -m khazar_emblem.driver >> driver.log 2>&1 </dev/null & disown -h)'
```

## Success criteria

This works when:

1. **It runs.** Pi boots, driver starts within 60s, an amulet appears. No
   crashes for 7 consecutive days.
2. **It looks right.** A friend who doesn't know it's generated mistakes the
   output for a scanned page from a real archaeology publication.
3. **It's a clock.** Photograph 14:23 today, photograph 14:23 tomorrow,
   side-by-side — same artifact. Conceit holds.
4. **It feels hand-drawn.** No part reads as vector art or SVG export.
5. **It's restrained.** A casual viewer doesn't notice the 7-color palette
   exists. Most amulets are black-on-cream.

If all five hold, the project is done.

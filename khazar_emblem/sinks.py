"""Sinks: where a rendered amulet goes.

Two implementations:
- PreviewSink: shows in a window or writes a PNG (Mac/Linux dev loop)
- InkySink:    palette-quantizes and pushes to the Pimoroni Inky Impression

Both accept an RGB PIL Image. The Inky sink does the palette conversion internally
so the amulet code stays display-agnostic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Protocol

from PIL import Image


class Sink(Protocol):
    def push(self, img: Image.Image) -> None: ...


class PreviewSink:
    """Show the rendered image. Either pops a window or writes a PNG."""

    def __init__(self, png_path: Optional[Path] = None, show_window: bool = True):
        self.png_path = png_path
        self.show_window = show_window and png_path is None

    def push(self, img: Image.Image) -> None:
        if self.png_path is not None:
            img.save(self.png_path)
            print(f"wrote {self.png_path}")
            return
        if self.show_window:
            img.show()


class InkySink:
    """Push to a real Pimoroni Inky Impression. Lazy-imports the inky library so
    this module is importable on machines without the Pi hardware stack."""

    def __init__(self):
        from inky.auto import auto  # noqa: PLC0415  (lazy by design)

        self._display = auto()

    def push(self, img: Image.Image) -> None:
        # The inky library accepts an image and handles palette mapping + dithering
        # against the board's native 7-color palette.
        self._display.set_image(img)
        self._display.show()

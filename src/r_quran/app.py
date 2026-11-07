"""Application entry point and GTK lifecycle management."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio

from .constants import APP_ID
from .window import QuranWindow

_LOGGER = logging.getLogger(__name__)


class RQuranApp(Adw.Application):
    """Native Quran reading application for Linux."""

    def __init__(self, pdf_path: str | Path | None = None) -> None:
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        self.pdf_path = str(pdf_path) if pdf_path else None
        self.connect("activate", self.on_activate)

    def on_activate(self, _app: Adw.Application) -> None:
        """Present the main application window."""
        win = QuranWindow(self, pdf_path=self.pdf_path)
        win.present()


def main(argv: list[str] | None = None) -> int:
    """Parse command line arguments and execute the application."""
    args = argv if argv is not None else sys.argv
    pdf: str | None = None

    if len(args) > 1 and args[1] not in ("--help", "-h"):
        candidate = Path(os.path.expanduser(args[1]))
        if candidate.is_file():
            pdf = str(candidate)
        else:
            _LOGGER.warning(
                "Specified PDF not found: %s; using standard search paths", candidate
            )

    app = RQuranApp(pdf_path=pdf)
    return app.run(args)


if __name__ == "__main__":
    raise SystemExit(main())

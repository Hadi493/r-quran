"""PDF document management using Poppler."""

from __future__ import annotations

import os
from pathlib import Path

import gi

gi.require_version("Poppler", "0.18")
from gi.repository import Gio, Poppler

DEFAULT_PDF = os.path.expanduser("~/Documents/Quran/Imdadia-Hafezi-Quran.pdf")


def resolve_pdf_path(path: str | Path | None = None) -> Path:
    """Find and return an existing PDF path based on search locations.

    Checks:
    1. Explicit path parameter.
    2. R_QURAN_PDF environment variable.
    3. Bundled assets in share/r-quran.
    4. User's Documents/Quran directory.
    5. Standard system /usr/share/r-quran location.
    """
    if path:
        expanded = Path(os.path.expanduser(str(path)))
        if expanded.is_file():
            return expanded

    candidates: list[Path | None] = [
        Path(os.path.expanduser(os.environ["R_QURAN_PDF"]))
        if "R_QURAN_PDF" in os.environ
        else None,
        Path(__file__).resolve().parents[2]
        / "share"
        / "r-quran"
        / "Imdadia-Hafezi-Quran.pdf",
        Path(__file__).resolve().parents[1]
        / "share"
        / "r-quran"
        / "imdadia-hafezi-quran.pdf",
        Path(os.path.expanduser("~/Documents/Quran/Imdadia-Hafezi-Quran.pdf")),
        Path("/usr/share/r-quran/Imdadia-Hafezi-Quran.pdf"),
    ]

    for candidate in candidates:
        if candidate and candidate.is_file():
            return candidate

    return Path(os.path.expanduser(str(path) if path else DEFAULT_PDF))


class QuranDocument:
    """Wrapper around a Poppler PDF document."""

    def __init__(self, path: str | Path | None = None) -> None:
        """Initialize the document from a file path or standard search locations."""
        resolved = resolve_pdf_path(path)
        if not resolved.is_file():
            raise FileNotFoundError(f"PDF not found: {resolved}")

        self.path = str(resolved)
        uri = Gio.File.new_for_path(self.path).get_uri()

        # Handle empty password decryption for encrypted Mushaf PDFs
        self.doc = Poppler.Document.new_from_file(uri, "")
        if self.doc is None:
            self.doc = Poppler.Document.new_from_file(uri, None)

        if self.doc is None:
            raise RuntimeError(f"Failed to open PDF document: {self.path}")

        self._page_count = self.doc.get_n_pages()
        self._size_cache: dict[int, tuple[float, float]] = {}

    def get_n_pages(self) -> int:
        """Return the total number of pages in the document."""
        return self._page_count

    def get_page(self, index: int) -> Poppler.Page:
        """Retrieve a 0-indexed page from the document."""
        if not 0 <= index < self._page_count:
            raise IndexError(
                f"Page index {index} out of range 0..{self._page_count - 1}"
            )
        return self.doc.get_page(index)

    def get_page_size(self, index: int) -> tuple[float, float]:
        """Return cached (width, height) dimensions for a 0-indexed page."""
        if index in self._size_cache:
            return self._size_cache[index]

        page = self.get_page(index)
        size = page.get_size()
        self._size_cache[index] = size
        return size

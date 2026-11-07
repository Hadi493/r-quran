"""Bookmark storage and management."""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import TypedDict

from .config import get_config_dir

_LOGGER = logging.getLogger(__name__)


class BookmarkItem(TypedDict):
    """Structure of a stored bookmark entry."""

    page: int
    label: str
    ts: int


def get_bookmarks_path() -> Path:
    """Return the filesystem path for the bookmarks file."""
    return get_config_dir() / "bookmarks.json"


# Backwards compatibility reference
BM_PATH = get_bookmarks_path()


def load() -> list[dict]:
    """Load bookmarks from disk, returning an empty list on failure."""
    path = get_bookmarks_path()
    if not path.is_file():
        return []

    try:
        content = path.read_text(encoding="utf-8")
        if not content.strip():
            return []
        data = json.loads(content)
        if isinstance(data, list):
            return data
        return []
    except (json.JSONDecodeError, OSError) as exc:
        _LOGGER.warning("Failed to load bookmarks: %s", exc)
        return []


def save(bookmarks_list: list[dict]) -> None:
    """Save bookmarks list to disk atomically."""
    config_dir = get_config_dir()
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
        path = get_bookmarks_path()
        payload = json.dumps(bookmarks_list, indent=2, ensure_ascii=False)

        fd, temp_file_path = tempfile.mkstemp(
            prefix="bookmarks_",
            suffix=".tmp",
            dir=config_dir,
        )
        try:
            with open(fd, "w", encoding="utf-8") as temp_file:
                temp_file.write(payload)
            os.replace(temp_file_path, path)
        except Exception:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            raise
    except OSError as exc:
        _LOGGER.warning("Failed to save bookmarks: %s", exc)


def add(page_1based: int, label: str = "") -> list[dict]:
    """Add a new bookmark for a 1-based page number and persist it."""
    bms = load()
    bms.append(
        {
            "page": page_1based,
            "label": label or f"Page {page_1based}",
            "ts": int(time.time()),
        }
    )
    save(bms)
    return bms


def remove(idx: int) -> list[dict]:
    """Remove a bookmark at the specified index and persist changes."""
    bms = load()
    if 0 <= idx < len(bms):
        del bms[idx]
        save(bms)
    return bms


def clear() -> None:
    """Clear all bookmarks and persist changes."""
    save([])

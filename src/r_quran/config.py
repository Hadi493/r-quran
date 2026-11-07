"""User settings persistence and cache management."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from .constants import (
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    DEFAULT_ZOOM,
    MAX_ZOOM,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    MIN_ZOOM,
)

_LOGGER = logging.getLogger(__name__)

ThemeMode = Literal["system", "light", "dark", "sepia", "high_contrast"]
VALID_THEMES: set[str] = {"system", "light", "dark", "sepia", "high_contrast"}


@dataclass
class AppSettings:
    """Cached user settings restored on application launch."""

    theme_mode: ThemeMode = "system"
    current_page: int = 2  # 1-based page number (page 2 is Surah Al-Fatiha)
    two_page: bool = True
    fit_width: bool = True
    zoom: float = DEFAULT_ZOOM
    window_width: int = DEFAULT_WINDOW_WIDTH
    window_height: int = DEFAULT_WINDOW_HEIGHT
    is_maximized: bool = False


def get_config_dir() -> Path:
    """Return the configuration directory path based on XDG specifications."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config) / "r-quran"
    return Path.home() / ".config" / "r-quran"


def get_settings_path() -> Path:
    """Return the filesystem path for the settings JSON cache file."""
    return get_config_dir() / "settings.json"


def load_settings() -> AppSettings:
    """Load settings from the user cache.

    Returns default settings when the cache file does not exist or contains
    invalid data.
    """
    settings_file = get_settings_path()
    if not settings_file.is_file():
        return AppSettings()

    try:
        content = settings_file.read_text(encoding="utf-8")
        if not content.strip():
            return AppSettings()
        raw = json.loads(content)
        if not isinstance(raw, dict):
            return AppSettings()

        # Sanitize and validate fields
        theme = str(raw.get("theme_mode", "system"))
        if theme not in VALID_THEMES:
            theme = "system"

        try:
            page = int(raw.get("current_page", 2))
            page = max(page, 1)
        except (ValueError, TypeError):
            page = 2

        two_page = bool(raw.get("two_page", True))
        fit_width = bool(raw.get("fit_width", True))

        try:
            zoom = float(raw.get("zoom", DEFAULT_ZOOM))
            zoom = max(MIN_ZOOM, min(zoom, MAX_ZOOM))
        except (ValueError, TypeError):
            zoom = DEFAULT_ZOOM

        try:
            w = int(raw.get("window_width", DEFAULT_WINDOW_WIDTH))
            w = max(MIN_WINDOW_WIDTH, w)
        except (ValueError, TypeError):
            w = DEFAULT_WINDOW_WIDTH

        try:
            h = int(raw.get("window_height", DEFAULT_WINDOW_HEIGHT))
            h = max(MIN_WINDOW_HEIGHT, h)
        except (ValueError, TypeError):
            h = DEFAULT_WINDOW_HEIGHT

        is_maximized = bool(raw.get("is_maximized", False))

        return AppSettings(
            theme_mode=theme,  # type: ignore[arg-type]
            current_page=page,
            two_page=two_page,
            fit_width=fit_width,
            zoom=zoom,
            window_width=w,
            window_height=h,
            is_maximized=is_maximized,
        )
    except (json.JSONDecodeError, OSError) as exc:
        _LOGGER.warning("Failed to load settings cache: %s", exc)
        return AppSettings()


def save_settings(settings: AppSettings) -> None:
    """Persist settings to the user cache atomically."""
    config_dir = get_config_dir()
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
        target_file = get_settings_path()
        payload = json.dumps(asdict(settings), indent=2, ensure_ascii=False)

        # Write to temporary file in the target directory, then atomic rename
        fd, temp_file_path = tempfile.mkstemp(
            prefix="settings_",
            suffix=".tmp",
            dir=config_dir,
        )
        try:
            with open(fd, "w", encoding="utf-8") as temp_file:
                temp_file.write(payload)
            os.replace(temp_file_path, target_file)
        except Exception:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            raise
    except OSError as exc:
        _LOGGER.warning("Failed to persist settings cache: %s", exc)

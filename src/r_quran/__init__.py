"""R-Quran: Native Quran reading application for Linux."""

from .config import AppSettings, load_settings, save_settings
from .pdf import QuranDocument
from .window import QuranWindow

__version__ = "0.1.0"

__all__ = [
    "AppSettings",
    "QuranDocument",
    "QuranWindow",
    "load_settings",
    "save_settings",
]

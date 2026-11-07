"""Theme management integrating Libadwaita color schemes and GTK CSS."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from .config import VALID_THEMES, ThemeMode
from .constants import CSS_BASE, CSS_HIGH_CONTRAST, CSS_SEPIA

if TYPE_CHECKING:
    from gi.repository import Gdk

_LOGGER = logging.getLogger(__name__)


def is_dark_mode() -> bool:
    """Return whether the current Libadwaita theme is dark."""
    try:
        return Adw.StyleManager.get_default().get_dark()
    except (GLib.Error, TypeError, AttributeError):
        return False


def is_high_contrast() -> bool:
    """Return whether the current Libadwaita theme is high contrast."""
    try:
        return Adw.StyleManager.get_default().get_high_contrast()
    except (GLib.Error, TypeError, AttributeError):
        return False


class ThemeManager:
    """Coordinates GTK CSS stylesheets and Libadwaita color schemes."""

    def __init__(self, window: Gtk.Window) -> None:
        self.window = window
        self.css_provider = Gtk.CssProvider()
        self.current_theme: ThemeMode = "system"
        self._provider_attached = False

    def attach_to_display(self, display: Gdk.Display | None) -> None:
        """Attach the CSS provider to the specified GDK display."""
        if not display or self._provider_attached:
            return
        Gtk.StyleContext.add_provider_for_display(
            display,
            self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )
        self._provider_attached = True
        self.apply_theme(self.current_theme)

    def apply_theme(self, theme: str) -> ThemeMode:
        """Apply the specified theme and update styling and color scheme."""
        normalized: ThemeMode = theme if theme in VALID_THEMES else "system"  # type: ignore[assignment]
        self.current_theme = normalized

        style_mgr = Adw.StyleManager.get_default()

        if normalized == "system":
            style_mgr.set_color_scheme(Adw.ColorScheme.DEFAULT)
            self._set_css(CSS_BASE)
            self.window.remove_css_class("quran-sepia")

        elif normalized == "light":
            style_mgr.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
            self._set_css(CSS_BASE)
            self.window.remove_css_class("quran-sepia")

        elif normalized == "dark":
            style_mgr.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
            self._set_css(CSS_BASE)
            self.window.remove_css_class("quran-sepia")

        elif normalized == "sepia":
            style_mgr.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
            self._set_css(CSS_SEPIA)
            self.window.add_css_class("quran-sepia")

        elif normalized == "high_contrast":
            style_mgr.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
            self._set_css(CSS_HIGH_CONTRAST)
            self.window.remove_css_class("quran-sepia")

        return self.current_theme

    def _set_css(self, css_rules: str) -> None:
        """Load CSS rules into the provider."""
        self.css_provider.load_from_string(css_rules)

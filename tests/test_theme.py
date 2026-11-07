"""Unit tests for theme switching and CSS generation."""

import unittest

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from r_quran.theme import ThemeManager


class TestTheme(unittest.TestCase):
    """Test ThemeManager states."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = Adw.Application(application_id="com.test.rquran.theme")

    def test_theme_application(self) -> None:
        window = Gtk.Window()
        manager = ThemeManager(window)

        for theme in ("system", "light", "dark", "sepia", "high_contrast"):
            applied = manager.apply_theme(theme)
            self.assertEqual(applied, theme)

        # Invalid fallback
        applied = manager.apply_theme("non_existent")
        self.assertEqual(applied, "system")


if __name__ == "__main__":
    unittest.main()

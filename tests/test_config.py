"""Unit tests for configuration cache persistence."""

import json
import os
import shutil
import tempfile
import unittest

from r_quran.config import (
    AppSettings,
    get_settings_path,
    load_settings,
    save_settings,
)


class TestConfig(unittest.TestCase):
    """Test user settings caching and sanitization."""

    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp(prefix="rquran_test_config_")
        self.orig_xdg = os.environ.get("XDG_CONFIG_HOME")
        os.environ["XDG_CONFIG_HOME"] = self.test_dir

    def tearDown(self) -> None:
        if self.orig_xdg is not None:
            os.environ["XDG_CONFIG_HOME"] = self.orig_xdg
        else:
            os.environ.pop("XDG_CONFIG_HOME", None)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_default_settings(self) -> None:
        settings = load_settings()
        self.assertEqual(settings.theme_mode, "system")
        self.assertEqual(settings.current_page, 2)
        self.assertTrue(settings.two_page)
        self.assertTrue(settings.fit_width)
        self.assertEqual(settings.zoom, 1.0)
        self.assertEqual(settings.window_width, 1000)
        self.assertEqual(settings.window_height, 700)
        self.assertFalse(settings.is_maximized)

    def test_save_and_load_roundtrip(self) -> None:
        initial = AppSettings(
            theme_mode="dark",
            current_page=45,
            two_page=False,
            fit_width=False,
            zoom=1.45,
            window_width=1280,
            window_height=800,
            is_maximized=True,
        )
        save_settings(initial)

        loaded = load_settings()
        self.assertEqual(loaded.theme_mode, "dark")
        self.assertEqual(loaded.current_page, 45)
        self.assertFalse(loaded.two_page)
        self.assertFalse(loaded.fit_width)
        self.assertAlmostEqual(loaded.zoom, 1.45, places=2)
        self.assertEqual(loaded.window_width, 1280)
        self.assertEqual(loaded.window_height, 800)
        self.assertTrue(loaded.is_maximized)

    def test_corrupted_json_recovery(self) -> None:
        path = get_settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{this is corrupted json!", encoding="utf-8")

        settings = load_settings()
        self.assertEqual(settings.theme_mode, "system")
        self.assertEqual(settings.current_page, 2)

    def test_sanitization_invalid_values(self) -> None:
        path = get_settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "theme_mode": "invalid_neon_theme",
            "current_page": -10,
            "zoom": 99.9,
            "window_width": 50,
            "window_height": 20,
        }
        path.write_text(json.dumps(payload), encoding="utf-8")

        settings = load_settings()
        self.assertEqual(settings.theme_mode, "system")
        self.assertEqual(settings.current_page, 1)
        self.assertEqual(settings.zoom, 3.0)  # Clamped to MAX_ZOOM
        self.assertEqual(settings.window_width, 400)  # Clamped to MIN_WINDOW_WIDTH
        self.assertEqual(settings.window_height, 300)  # Clamped to MIN_WINDOW_HEIGHT


if __name__ == "__main__":
    unittest.main()

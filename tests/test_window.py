"""Integration test for QuranWindow state restoration and caching."""

import os
import shutil
import tempfile
import unittest

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib

from r_quran.config import AppSettings, load_settings, save_settings
from r_quran.window import QuranWindow


class TestQuranWindowState(unittest.TestCase):
    """Test state persistence and restoration across window launches."""

    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp(prefix="rquran_test_win_")
        self.orig_xdg = os.environ.get("XDG_CONFIG_HOME")
        os.environ["XDG_CONFIG_HOME"] = self.test_dir

    def tearDown(self) -> None:
        if self.orig_xdg is not None:
            os.environ["XDG_CONFIG_HOME"] = self.orig_xdg
        else:
            os.environ.pop("XDG_CONFIG_HOME", None)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_window_restores_and_updates_settings(self) -> None:
        # Pre-populate settings cache
        initial_settings = AppSettings(
            theme_mode="dark",
            current_page=15,  # 1-based page 15 -> index 14
            two_page=False,
            fit_width=False,
            zoom=1.3,
            window_width=1100,
            window_height=750,
            is_maximized=False,
        )
        save_settings(initial_settings)

        app = Adw.Application(application_id="com.test.rquran.state")

        def run_test(app_instance: Adw.Application) -> None:
            win = QuranWindow(app_instance)
            # Verify restored state
            self.assertEqual(win.current_page, 14)  # 0-based index for page 15
            self.assertFalse(win.two_page)
            self.assertFalse(win._fit)
            self.assertAlmostEqual(win.zoom, 1.3, places=2)

            # Change state: turn page, change theme, toggle two_page
            win.go_to_page(30)
            self.assertEqual(win.current_page, 29)

            win.set_theme("sepia")
            self.assertEqual(win.theme_manager.current_theme, "sepia")

            win.two_btn.set_active(True)
            self.assertTrue(win.two_page)

            # Close window to trigger settings persistence
            win.close()
            GLib.timeout_add(50, app_instance.quit)

        app.connect("activate", run_test)
        app.run([])

        # Verify disk settings were updated
        cached = load_settings()
        self.assertEqual(cached.current_page, 30)
        self.assertEqual(cached.theme_mode, "sepia")
        self.assertTrue(cached.two_page)


if __name__ == "__main__":
    unittest.main()

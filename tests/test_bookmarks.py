"""Unit tests for bookmarks persistence and operations."""

import os
import shutil
import tempfile
import unittest

from r_quran import bookmarks


class TestBookmarks(unittest.TestCase):
    """Test bookmark additions, removals, and persistence."""

    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp(prefix="rquran_test_bm_")
        self.orig_xdg = os.environ.get("XDG_CONFIG_HOME")
        os.environ["XDG_CONFIG_HOME"] = self.test_dir

    def tearDown(self) -> None:
        if self.orig_xdg is not None:
            os.environ["XDG_CONFIG_HOME"] = self.orig_xdg
        else:
            os.environ.pop("XDG_CONFIG_HOME", None)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_empty_bookmarks(self) -> None:
        items = bookmarks.load()
        self.assertEqual(items, [])

    def test_add_and_load_bookmark(self) -> None:
        bookmarks.add(42, label="Surah Ash-Shura")
        items = bookmarks.load()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["page"], 42)
        self.assertEqual(items[0]["label"], "Surah Ash-Shura")
        self.assertIn("ts", items[0])

    def test_remove_bookmark(self) -> None:
        bookmarks.add(10)
        bookmarks.add(20)
        bookmarks.add(30)
        self.assertEqual(len(bookmarks.load()), 3)

        bookmarks.remove(1)
        items = bookmarks.load()
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["page"], 10)
        self.assertEqual(items[1]["page"], 30)

    def test_clear_bookmarks(self) -> None:
        bookmarks.add(1)
        bookmarks.add(2)
        self.assertEqual(len(bookmarks.load()), 2)

        bookmarks.clear()
        self.assertEqual(bookmarks.load(), [])


if __name__ == "__main__":
    unittest.main()

"""Unit tests for Cairo surface rendering and inversion."""

import unittest

import cairo

from r_quran.pdf import QuranDocument
from r_quran.renderer import (
    draw_dropshadow,
    render_page_to_surface,
    render_spread_surface,
)


class TestRenderer(unittest.TestCase):
    """Test Cairo rendering routines."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.doc = QuranDocument()

    def test_single_page_rendering(self) -> None:
        page = self.doc.get_page(1)
        surface, pw, ph = render_page_to_surface(page, scale=0.5, invert=False)
        self.assertIsInstance(surface, cairo.ImageSurface)
        self.assertEqual(surface.get_width(), int(pw * 0.5))
        self.assertEqual(surface.get_height(), int(ph * 0.5))

    def test_single_page_inverted(self) -> None:
        page = self.doc.get_page(1)
        surface, _, _ = render_page_to_surface(
            page,
            scale=0.5,
            invert=True,
            high_contrast=False,
        )
        self.assertIsInstance(surface, cairo.ImageSurface)

    def test_spread_surface_rendering_rtl(self) -> None:
        surface, spread_w, spread_h = render_spread_surface(
            self.doc,
            start_page=1,
            scale=0.5,
            rtl=True,
            invert=False,
        )
        self.assertIsInstance(surface, cairo.ImageSurface)
        self.assertEqual(surface.get_width(), int(spread_w))
        self.assertEqual(surface.get_height(), int(spread_h))

    def test_draw_dropshadow(self) -> None:
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 200, 200)
        cr = cairo.Context(surface)
        # Verify no crash
        draw_dropshadow(cr, ox=10, oy=10, w=100, h=100)


if __name__ == "__main__":
    unittest.main()

"""Cairo graphics rendering pipeline for pages and two-page spreads."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import cairo
from gi.repository import GLib

from .constants import PAGE_GAP
from .theme import is_dark_mode, is_high_contrast

if TYPE_CHECKING:
    from gi.repository import Poppler

    from .pdf import QuranDocument

_LOGGER = logging.getLogger(__name__)


def invert_surface(
    surface: cairo.ImageSurface, high_contrast: bool = False
) -> cairo.ImageSurface:
    """Invert colors on an image surface using Cairo DIFFERENCE operator.

    A difference operator against white (1.0) creates pure negative inversion.
    A difference operator against 0.88 creates a softer dark gray mode suitable
    for eye comfort.
    """
    context = cairo.Context(surface)
    context.set_operator(cairo.Operator.DIFFERENCE)
    if high_contrast:
        context.set_source_rgb(1.0, 1.0, 1.0)
    else:
        context.set_source_rgb(0.88, 0.88, 0.88)
    context.paint()
    return surface


def render_page_to_surface(
    page: Poppler.Page,
    scale: float,
    invert: bool | None = None,
    high_contrast: bool | None = None,
) -> tuple[cairo.ImageSurface, float, float]:
    """Render a single Poppler page to a Cairo ImageSurface."""
    if invert is None:
        invert = is_dark_mode()
    if high_contrast is None:
        high_contrast = is_high_contrast()

    page_w, page_h = page.get_size()
    scaled_w = max(1, int(page_w * scale))
    scaled_h = max(1, int(page_h * scale))

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, scaled_w, scaled_h)
    cr = cairo.Context(surface)

    # White page background
    cr.scale(scale, scale)
    cr.set_source_rgb(1.0, 1.0, 1.0)
    cr.rectangle(0, 0, page_w, page_h)
    cr.fill()

    page.render(cr)

    if invert:
        invert_surface(surface, high_contrast=high_contrast)

    return (surface, page_w, page_h)


def render_spread_surface(
    doc: QuranDocument,
    start_page: int,
    scale: float,
    rtl: bool = True,
    invert: bool | None = None,
    high_contrast: bool | None = None,
) -> tuple[cairo.ImageSurface, float, float]:
    """Render a two-page spread to an offscreen Cairo ImageSurface."""
    if invert is None:
        invert = is_dark_mode()
    if high_contrast is None:
        high_contrast = is_high_contrast()

    total_pages = doc.get_n_pages()
    pw_cur, ph_cur = doc.get_page_size(start_page)
    has_second = (start_page + 1) < total_pages

    if has_second:
        pw_nxt, ph_nxt = doc.get_page_size(start_page + 1)
    else:
        pw_nxt, ph_nxt = (pw_cur, ph_cur)

    gap = PAGE_GAP

    if rtl and has_second:
        # In RTL (traditional Quran): left page is next, right page is current
        total_w = pw_nxt + pw_cur + gap
        max_h = max(ph_nxt, ph_cur)
        surf_w = max(1, int(total_w * scale))
        surf_h = max(1, int(max_h * scale))

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, surf_w, surf_h)
        cr = cairo.Context(surface)

        # Gutter fill
        cr.set_source_rgb(0.85, 0.85, 0.85)
        cr.rectangle(pw_nxt * scale, 0, gap * scale, surf_h)
        cr.fill()

        # Render left (start_page + 1) then right (start_page)
        pages_to_draw = [
            (pw_nxt, ph_nxt, start_page + 1, 0.0),
            (pw_cur, ph_cur, start_page, (pw_nxt + gap) * scale),
        ]
        for pw, ph, p_idx, xoff in pages_to_draw:
            yoff = (max_h * scale - ph * scale) / 2.0
            cr.save()
            cr.translate(xoff, yoff)
            cr.scale(scale, scale)
            cr.set_source_rgb(1.0, 1.0, 1.0)
            cr.rectangle(0, 0, pw, ph)
            cr.fill()
            try:
                doc.get_page(p_idx).render(cr)
            except (GLib.Error, RuntimeError, cairo.Error) as exc:
                _LOGGER.warning("Error rendering page %d: %s", p_idx, exc)
            cr.restore()

            # Gutter shadow overlay
            if p_idx == start_page + 1:
                cr.set_source_rgba(0, 0, 0, 0.08)
                cr.rectangle(pw_nxt * scale, 0, 4 * scale, surf_h)
                cr.fill()
            else:
                cr.set_source_rgba(0, 0, 0, 0.06)
                cr.rectangle((pw_nxt + gap) * scale, 0, 4 * scale, surf_h)
                cr.fill()
    else:
        # Standard LTR or single page fallback
        total_w = pw_cur + (pw_nxt + gap if has_second else 0)
        max_h = max(ph_cur, ph_nxt if has_second else ph_cur)
        surf_w = max(1, int(total_w * scale))
        surf_h = max(1, int(max_h * scale))

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, surf_w, surf_h)
        cr = cairo.Context(surface)

        if has_second:
            cr.set_source_rgb(0.85, 0.85, 0.85)
            cr.rectangle(pw_cur * scale, 0, gap * scale, surf_h)
            cr.fill()

        pages = [(pw_cur, ph_cur, start_page)]
        if has_second:
            pages.append((pw_nxt, ph_nxt, start_page + 1))

        for idx, (pw, ph, p_idx) in enumerate(pages):
            xoff = 0.0 if idx == 0 else (pw_cur + gap) * scale
            yoff = (max_h * scale - ph * scale) / 2.0
            cr.save()
            cr.translate(xoff, yoff)
            cr.scale(scale, scale)
            cr.set_source_rgb(1.0, 1.0, 1.0)
            cr.rectangle(0, 0, pw, ph)
            cr.fill()
            try:
                doc.get_page(p_idx).render(cr)
            except (GLib.Error, RuntimeError, cairo.Error) as exc:
                _LOGGER.warning("Error rendering page %d: %s", p_idx, exc)
            cr.restore()

    if invert:
        invert_surface(surface, high_contrast=high_contrast)

    return (surface, total_w * scale, max_h * scale)


def draw_dropshadow(
    cr: cairo.Context, ox: float, oy: float, w: float, h: float
) -> None:
    """Draw a soft drop shadow and border around the page spread."""
    cr.save()
    cr.translate(ox, oy)

    # Outer blur layer
    cr.set_source_rgba(0.0, 0.0, 0.0, 0.25)
    cr.rectangle(4, 4, w, h)
    cr.fill()

    # Inner blur layer
    cr.set_source_rgba(0.0, 0.0, 0.0, 0.12)
    cr.rectangle(2, 2, w, h)
    cr.fill()

    # Subtle outline
    cr.set_source_rgb(0.55, 0.50, 0.45)
    cr.rectangle(-1, -1, w + 2, h + 2)
    cr.stroke()

    cr.restore()

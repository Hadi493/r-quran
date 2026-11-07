"""Main application window and user interface controllers."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

import cairo
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib, Gtk

from . import bookmarks
from .config import AppSettings, load_settings, save_settings
from .constants import (
    APP_TITLE,
    DATA_CANDIDATES,
    DEFAULT_FIRST_PAGE,
    DEFAULT_ZOOM,
    MAX_ZOOM,
    MIN_ZOOM,
    PAGE_GAP,
    ZOOM_STEP,
)
from .pdf import QuranDocument
from .renderer import (
    draw_dropshadow,
    render_page_to_surface,
    render_spread_surface,
)
from .theme import ThemeManager, is_dark_mode

if TYPE_CHECKING:
    from pathlib import Path

_LOGGER = logging.getLogger(__name__)


def _find_data_dir() -> Path:
    """Locate the directory containing surah and juz metadata files."""
    for candidate in DATA_CANDIDATES:
        if candidate.is_dir():
            return candidate
    return DATA_CANDIDATES[0]


def _load_data_file(filename: str) -> list[dict[str, Any]]:
    """Load JSON array from the data directory."""
    path = _find_data_dir() / filename
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, OSError) as exc:
        _LOGGER.warning("Failed to load metadata file %s: %s", filename, exc)
    return []


JUZ_DATA = _load_data_file("juz.json")
SURAH_DATA = _load_data_file("surah.json")


class QuranWindow(Adw.ApplicationWindow):
    """Primary window providing reading canvas, navigation, and controls."""

    def __init__(self, app: Adw.Application, pdf_path: str | None = None) -> None:
        super().__init__(application=app, title=APP_TITLE)

        # Load persisted user settings cache
        self._settings: AppSettings = load_settings()

        # Geometry restoration
        self.set_default_size(self._settings.window_width, self._settings.window_height)
        if self._settings.is_maximized:
            self.maximize()

        # Document loading
        self.first_page = DEFAULT_FIRST_PAGE
        self.doc: QuranDocument | None = None
        self._error: str | None = None
        try:
            self.doc = QuranDocument(pdf_path)
        except (FileNotFoundError, RuntimeError, OSError) as exc:
            self._error = str(exc)

        # Page index restoration (0-based)
        if self.doc:
            total_pages = self.doc.get_n_pages()
            target_0based = self._settings.current_page - 1
            self.current_page = max(
                self.first_page, min(target_0based, total_pages - 1)
            )
        else:
            self.current_page = self.first_page

        # Viewing options restoration
        self.zoom = max(MIN_ZOOM, min(self._settings.zoom, MAX_ZOOM))
        self._fit = self._settings.fit_width
        self.two_page = self._settings.two_page
        self.rtl = True

        # Theme manager
        self.theme_manager = ThemeManager(self)

        # UI Components
        self.header = Adw.HeaderBar()
        self.prev_btn: Gtk.Button
        self.next_btn: Gtk.Button
        self.two_btn: Gtk.ToggleButton
        self.theme_btn: Gtk.MenuButton
        self.juz_btn: Gtk.MenuButton
        self.surah_btn: Gtk.MenuButton
        self.bm_btn: Gtk.MenuButton
        self._bm_box: Gtk.Box
        self._bm_pop: Gtk.Popover

        self._build_header_bar()
        self._build_content_area()
        self._setup_event_controllers()

        # Signal connections
        self.connect("realize", self._on_realize)
        self.connect("close-request", self._on_close_request)

        # Listen for system theme toggles
        Adw.StyleManager.get_default().connect("notify::dark", self._on_dark_changed)

        self.update_ui()
        if self._error:
            self.status.set_label(f"Error: {self._error}")

    def _build_header_bar(self) -> None:
        """Construct the top header bar and navigation actions."""
        self.header.set_show_start_title_buttons(False)
        self.header.set_show_end_title_buttons(False)
        self.header.set_decoration_layout("")
        self.header.add_css_class("compact-header")

        # Previous page button
        self.prev_btn = Gtk.Button(
            icon_name="go-previous-symbolic",
            tooltip_text="Previous (←/p)",
        )
        self.prev_btn.connect("clicked", lambda *_: self.go_prev())
        self.header.pack_start(self.prev_btn)

        # Navigation index buttons
        self.juz_btn = Gtk.MenuButton(label="Juz", tooltip_text="Juz — 30 parts")
        self.header.pack_start(self.juz_btn)
        self._build_juz_menu()

        self.surah_btn = Gtk.MenuButton(
            label="Surah", tooltip_text="Surah — 114 chapters"
        )
        self.header.pack_start(self.surah_btn)
        self._build_surah_menu()

        self.bm_btn = Gtk.MenuButton(
            icon_name="bookmark-new-symbolic",
            tooltip_text="Bookmarks (b)",
        )
        self.header.pack_start(self.bm_btn)
        self._build_bookmark_menu()

        add_bm_btn = Gtk.Button(
            icon_name="bookmark-add-symbolic",
            tooltip_text="Add bookmark (b)",
        )
        add_bm_btn.add_css_class("suggested-action")
        add_bm_btn.connect("clicked", lambda *_: self.on_add_bookmark())
        self.header.pack_start(add_bm_btn)
        self.header.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        # Center spacer box
        nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        nav_box.set_halign(Gtk.Align.CENTER)
        self.header.set_title_widget(nav_box)

        # Next page button
        self.next_btn = Gtk.Button(
            icon_name="go-next-symbolic",
            tooltip_text="Next (→/n)",
        )
        self.next_btn.connect("clicked", lambda *_: self.go_next())
        self.header.pack_end(self.next_btn)

        # Two-page spread toggle
        self.two_btn = Gtk.ToggleButton(
            icon_name="view-dual-symbolic",
            tooltip_text="Two pages like book (t)",
        )
        self.two_btn.set_active(self.two_page)
        self.two_btn.connect("toggled", self.on_two_toggled)
        self.header.pack_end(self.two_btn)

        # Theme menu button
        self.theme_btn = Gtk.MenuButton(
            icon_name="night-light-symbolic",
            tooltip_text="Theme",
        )
        self.header.pack_end(self.theme_btn)
        self._build_theme_menu()

        # Zoom buttons
        zoom_box = Gtk.Box(spacing=2)
        zoom_out_btn = Gtk.Button(
            icon_name="zoom-out-symbolic",
            tooltip_text="Zoom out (-)",
        )
        zoom_out_btn.connect("clicked", lambda *_: self.set_zoom(self.zoom - ZOOM_STEP))
        zoom_box.append(zoom_out_btn)

        zoom_fit_btn = Gtk.Button(
            icon_name="zoom-fit-best-symbolic",
            tooltip_text="Fit width",
        )
        zoom_fit_btn.connect(
            "clicked", lambda *_: self.set_zoom(DEFAULT_ZOOM, fit=True)
        )
        zoom_box.append(zoom_fit_btn)

        zoom_in_btn = Gtk.Button(
            icon_name="zoom-in-symbolic",
            tooltip_text="Zoom in (+)",
        )
        zoom_in_btn.connect("clicked", lambda *_: self.set_zoom(self.zoom + ZOOM_STEP))
        zoom_box.append(zoom_in_btn)

        self.header.pack_end(zoom_box)
        self.header.pack_end(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

    def _build_content_area(self) -> None:
        """Construct the canvas scroll view, progress bar, and status display."""
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.append(self.header)

        self.scrolled = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        self.scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.scrolled.add_css_class("quran-scrolled")

        self.drawing = Gtk.DrawingArea(hexpand=True, vexpand=True)
        self.drawing.set_draw_func(self.on_draw, None)
        self.drawing.set_content_width(600)
        self.drawing.set_content_height(800)
        self.scrolled.set_child(self.drawing)
        vbox.append(self.scrolled)

        self.progress = Gtk.ProgressBar()
        self.progress.set_show_text(False)
        self.progress.add_css_class("quran-progress")
        self.progress.set_fraction(0.0)
        vbox.append(self.progress)

        self.status = Gtk.Label(xalign=0)
        self.status.add_css_class("dim-label")
        self.status.set_margin_start(6)
        self.status.set_margin_end(6)
        vbox.append(self.status)

        self.set_content(vbox)

    def _setup_event_controllers(self) -> None:
        """Configure keyboard shortcuts, swipe gestures, and click zones."""
        key_controller = Gtk.EventControllerKey()
        key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_controller.connect("key-pressed", self.on_key)
        self.add_controller(key_controller)

        swipe = Gtk.GestureSwipe()
        swipe.connect("swipe", self.on_swipe)
        self.drawing.add_controller(swipe)

        click = Gtk.GestureClick()
        click.connect("pressed", self.on_click)
        self.drawing.add_controller(click)

    def _on_realize(self, *_args: Any) -> None:
        """Initialize display-dependent providers on window realization."""
        display = self.get_display() or Gdk.Display.get_default()
        if display:
            self.theme_manager.attach_to_display(display)
            self.theme_manager.apply_theme(self._settings.theme_mode)

    def _on_dark_changed(self, *_args: Any) -> None:
        """Redraw canvas when the system or application dark mode changes."""
        self.drawing.queue_draw()

    def _on_close_request(self, *_args: Any) -> bool:
        """Persist window state and reading progress when closing."""
        self._settings.window_width = self.get_width()
        self._settings.window_height = self.get_height()
        self._settings.is_maximized = self.is_maximized()
        self._settings.current_page = self.current_page + 1
        self._settings.two_page = self.two_page
        self._settings.fit_width = self._fit
        self._settings.zoom = self.zoom
        save_settings(self._settings)
        return False

    def _persist_current_state(self) -> None:
        """Save active reading state to disk cache."""
        self._settings.current_page = self.current_page + 1
        self._settings.two_page = self.two_page
        self._settings.fit_width = self._fit
        self._settings.zoom = self.zoom
        self._settings.theme_mode = self.theme_manager.current_theme
        save_settings(self._settings)

    def _build_theme_menu(self) -> None:
        """Build the theme selection popover menu."""
        popover = Gtk.Popover()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(6)
        box.set_margin_end(6)

        themes = [
            ("Follow System", "system"),
            ("Light", "light"),
            ("Dark", "dark"),
            ("Sepia", "sepia"),
            ("High Contrast", "high_contrast"),
        ]

        for label, theme_key in themes:
            btn = Gtk.Button(label=label)
            btn.connect("clicked", self._create_theme_callback(theme_key, popover))
            box.append(btn)

        popover.set_child(box)
        self.theme_btn.set_popover(popover)

    def _create_theme_callback(self, theme_key: str, popover: Gtk.Popover) -> Any:
        def on_click(_button: Gtk.Button) -> None:
            self.set_theme(theme_key)
            popover.popdown()

        return on_click

    def set_theme(self, theme_name: str) -> None:
        """Apply a theme and cache the selection."""
        applied = self.theme_manager.apply_theme(theme_name)
        self._settings.theme_mode = applied
        save_settings(self._settings)
        self.drawing.queue_draw()

    # Backwards-compatible aliases
    def apply_sepia(self) -> None:
        self.set_theme("sepia")

    def apply_high_contrast(self) -> None:
        self.set_theme("high_contrast")

    def _build_juz_menu(self) -> None:
        """Build the Juz navigation popover grid."""
        popover = Gtk.Popover()
        grid = Gtk.Grid(column_spacing=4, row_spacing=4)
        grid.set_margin_top(6)
        grid.set_margin_bottom(6)
        grid.set_margin_start(6)
        grid.set_margin_end(6)

        for i, item in enumerate(JUZ_DATA):
            page_num = item["page"]
            btn = Gtk.Button(label=f"Juz {item['juz']}")
            btn.set_tooltip_text(f"Page {page_num}")
            btn.connect("clicked", self._create_jump_callback(page_num, popover))
            grid.attach(btn, i % 5, i // 5, 1, 1)

        popover.set_child(grid)
        self.juz_btn.set_popover(popover)

    def _build_surah_menu(self) -> None:
        """Build the Surah search and selection popover."""
        popover = Gtk.Popover()
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        vbox.set_margin_top(6)
        vbox.set_margin_bottom(6)
        vbox.set_margin_start(6)
        vbox.set_margin_end(6)

        search = Gtk.SearchEntry(placeholder_text="Search surah…")
        scrolled = Gtk.ScrolledWindow(vexpand=True)
        scrolled.set_min_content_height(300)
        scrolled.set_min_content_width(340)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.add_css_class("surah-scrolled")

        list_box = Gtk.ListBox()
        list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        list_box.add_css_class("surah-list")
        rows: list[tuple[Gtk.ListBoxRow, dict[str, Any]]] = []

        for surah in SURAH_DATA:
            row = Gtk.ListBoxRow()
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            hbox.set_margin_top(4)
            hbox.set_margin_bottom(4)
            hbox.set_margin_start(6)
            hbox.set_margin_end(6)

            title_label = Gtk.Label(
                label=f"{surah['id']:3d}. {surah['name']}",
                xalign=0,
                hexpand=True,
            )
            arabic_label = Gtk.Label(label=surah["arabic"], xalign=1)
            page_label = Gtk.Label(label=f"p.{surah['page']}", xalign=1)

            hbox.append(title_label)
            hbox.append(arabic_label)
            hbox.append(page_label)
            row.set_child(hbox)
            row._page = surah["page"]  # type: ignore[attr-defined]

            list_box.append(row)
            rows.append((row, surah))

        def on_filter(_entry: Gtk.SearchEntry) -> None:
            query = search.get_text().lower().strip()
            for row_widget, data in rows:
                match = (
                    not query
                    or query in data["name"].lower()
                    or query in data["arabic"]
                    or query in str(data["id"])
                )
                row_widget.set_visible(match)

        search.connect("search-changed", on_filter)

        def on_row_activated(_box: Gtk.ListBox, activated_row: Gtk.ListBoxRow) -> None:
            self.go_to_page(activated_row._page)  # type: ignore[attr-defined]
            popover.popdown()

        list_box.connect("row-activated", on_row_activated)
        scrolled.set_child(list_box)
        vbox.append(search)
        vbox.append(scrolled)
        popover.set_child(vbox)
        self.surah_btn.set_popover(popover)

    def _build_bookmark_menu(self) -> None:
        """Build the bookmarks list popover."""
        self._bm_pop = Gtk.Popover()
        self._bm_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._bm_box.set_margin_top(6)
        self._bm_box.set_margin_bottom(6)
        self._bm_box.set_margin_start(6)
        self._bm_box.set_margin_end(6)

        self._bm_pop.set_child(self._bm_box)
        self.bm_btn.set_popover(self._bm_pop)
        self._bm_pop.connect("notify::visible", lambda *_: self._refresh_bookmarks())

    def _refresh_bookmarks(self) -> None:
        """Re-render items inside the bookmarks popover."""
        child = self._bm_box.get_first_child()
        while child:
            next_sibling = child.get_next_sibling()
            self._bm_box.remove(child)
            child = next_sibling

        items = bookmarks.load()
        if not items:
            self._bm_box.append(Gtk.Label(label="No bookmarks", xalign=0))

        for idx, item in enumerate(items):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            page_num = item["page"]
            btn = Gtk.Button(label=item.get("label", f"Page {page_num}"))
            btn.set_tooltip_text(f"Page {page_num}")
            btn.connect("clicked", self._create_jump_callback(page_num, self._bm_pop))
            row.append(btn)

            del_btn = Gtk.Button(icon_name="edit-delete-symbolic")
            del_btn.connect("clicked", self._create_delete_bookmark_callback(idx))
            row.append(del_btn)
            self._bm_box.append(row)

        actions_box = Gtk.Box(spacing=4)
        clear_btn = Gtk.Button(label="Clear all")
        clear_btn.connect("clicked", lambda *_: self._clear_all_bookmarks())
        actions_box.append(clear_btn)
        self._bm_box.append(actions_box)

    def _create_jump_callback(self, page_num: int, popover: Gtk.Popover) -> Any:
        def on_jump(_btn: Gtk.Button) -> None:
            self.go_to_page(page_num)
            popover.popdown()

        return on_jump

    def _create_delete_bookmark_callback(self, idx: int) -> Any:
        def on_delete(_btn: Gtk.Button) -> None:
            bookmarks.remove(idx)
            self._refresh_bookmarks()

        return on_delete

    def _clear_all_bookmarks(self) -> None:
        bookmarks.clear()
        self._refresh_bookmarks()

    def on_add_bookmark(self) -> None:
        """Add a bookmark for the active 1-based page number."""
        page_1based = self.current_page + 1
        bookmarks.add(page_1based, label=f"Page {page_1based}")
        self.status.set_label(f"Bookmarked page {page_1based}")
        self._refresh_bookmarks()

    def go_to_page(self, page_1based: int) -> None:
        """Navigate directly to the specified 1-based page number."""
        if not self.doc:
            return
        total = self.doc.get_n_pages()
        clamped_1based = max(self.first_page + 1, min(page_1based, total))
        target_0based = clamped_1based - 1

        if target_0based == self.current_page:
            return

        self.current_page = target_0based
        self.update_ui()
        self._persist_current_state()

    def go_prev(self) -> None:
        """Navigate backward by one step."""
        if not self.doc:
            return
        if self.current_page <= self.first_page:
            return

        step = 2 if self.two_page else 1
        target = max(self.first_page, self.current_page - step)
        self.current_page = target
        self.update_ui()
        self._persist_current_state()

    def go_next(self) -> None:
        """Navigate forward by one step."""
        if not self.doc:
            return
        total = self.doc.get_n_pages()
        if self.two_page:
            step = 2
            if self.current_page + step < total:
                target = self.current_page + step
            elif self.current_page + 1 < total:
                target = self.current_page + 1
            else:
                return
        else:
            if self.current_page >= total - 1:
                return
            target = self.current_page + 1

        self.current_page = target
        self.update_ui()
        self._persist_current_state()

    def on_two_toggled(self, btn: Gtk.ToggleButton) -> None:
        """Handle two-page view toggle."""
        self.two_page = btn.get_active()
        self.update_ui()
        self.drawing.queue_draw()
        self._persist_current_state()

    def set_zoom(self, zoom_level: float, fit: bool = False) -> None:
        """Adjust canvas zoom level or toggle fit-to-width."""
        if fit:
            self._fit = True
            self.zoom = 1.0
        else:
            self._fit = False
            self.zoom = max(MIN_ZOOM, min(zoom_level, MAX_ZOOM))

        self.drawing.queue_draw()
        self.status.set_label("")
        self._persist_current_state()

    def _toggle_fullscreen(self) -> None:
        """Toggle fullscreen mode on or off."""
        if self.is_fullscreen():
            self.unfullscreen()
            self.header.set_visible(True)
            self.status.set_visible(True)
            self.progress.set_visible(True)
        else:
            self.fullscreen()
            self.header.set_visible(False)
            self.status.set_visible(False)
            self.progress.set_visible(False)

    def on_key(self, _ctrl: Any, keyval: int, _keycode: int, _state: Any) -> bool:
        """Handle keyboard navigation and shortcuts."""
        # Page navigation (RTL aware: Right goes prev, Left goes next)
        if self.rtl:
            if keyval in (Gdk.KEY_Right, Gdk.KEY_p, Gdk.KEY_Page_Up):
                self.go_prev()
                return True
            if keyval in (Gdk.KEY_Left, Gdk.KEY_n, Gdk.KEY_Page_Down):
                self.go_next()
                return True
        else:
            if keyval in (Gdk.KEY_Right, Gdk.KEY_n, Gdk.KEY_Page_Down):
                self.go_next()
                return True
            if keyval in (Gdk.KEY_Left, Gdk.KEY_p, Gdk.KEY_Page_Up):
                self.go_prev()
                return True

        if keyval == Gdk.KEY_Home:
            self.go_to_page(1)
            return True
        if keyval == Gdk.KEY_End and self.doc:
            self.go_to_page(self.doc.get_n_pages())
            return True
        if keyval in (Gdk.KEY_plus, Gdk.KEY_equal):
            self.set_zoom(self.zoom + ZOOM_STEP)
            return True
        if keyval == Gdk.KEY_minus:
            self.set_zoom(self.zoom - ZOOM_STEP)
            return True
        if keyval == Gdk.KEY_b:
            self.on_add_bookmark()
            return True
        if keyval == Gdk.KEY_t:
            self.two_btn.set_active(not self.two_btn.get_active())
            return True
        if keyval in (Gdk.KEY_F, Gdk.KEY_f, Gdk.KEY_F11):
            self._toggle_fullscreen()
            return True
        if keyval == Gdk.KEY_Escape and self.is_fullscreen():
            self._toggle_fullscreen()
            return True

        return False

    def on_swipe(self, _gesture: Gtk.GestureSwipe, vx: float, _vy: float) -> None:
        """Handle touch swipe navigation."""
        if self.rtl:
            if vx < -120:
                self.go_prev()
            elif vx > 120:
                self.go_next()
        else:
            if vx < -120:
                self.go_next()
            elif vx > 120:
                self.go_prev()

    def on_click(
        self, _gesture: Gtk.GestureClick, _n: int, x: float, _y: float
    ) -> None:
        """Handle side-tap page flipping."""
        width = self.drawing.get_width()
        if width == 0:
            return

        if self.rtl:
            if x < width * 0.28:
                self.go_next()
            elif x > width * 0.72:
                self.go_prev()
        else:
            if x < width * 0.28:
                self.go_prev()
            elif x > width * 0.72:
                self.go_next()

    def update_ui(self) -> None:
        """Update navigation button sensitivity and progress indicators."""
        if not self.doc:
            return

        total_pages = self.doc.get_n_pages()
        self.prev_btn.set_sensitive(self.current_page > self.first_page)
        self.next_btn.set_sensitive(self.current_page < total_pages - 1)

        total_reading = total_pages - self.first_page
        current_reading = self.current_page - self.first_page + 1
        if total_reading > 0:
            fraction = max(0.0, min(1.0, current_reading / total_reading))
            self.progress.set_fraction(fraction)

        self.drawing.queue_draw()

    def on_draw(
        self,
        area: Gtk.DrawingArea,
        cr: cairo.Context,
        _w: int,
        _h: int,
        _data: Any,
    ) -> None:
        """Render the reading canvas for single or dual page layouts."""
        if not self.doc:
            cr.set_source_rgb(0.2, 0.2, 0.2)
            cr.select_font_face(
                "Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL
            )
            cr.set_font_size(14)
            cr.move_to(20, 30)
            cr.show_text(self._error or "No document loaded")
            return

        alloc_w = self.scrolled.get_width() or area.get_width() or 900
        alloc_h = self.scrolled.get_height() or area.get_height() or 700

        # Background fill
        cr.save()
        if is_dark_mode():
            cr.set_source_rgb(0.08, 0.08, 0.08)
        elif self.theme_manager.current_theme == "sepia":
            cr.set_source_rgb(0.91, 0.86, 0.75)
        else:
            cr.set_source_rgb(0.84, 0.80, 0.71)
        cr.paint()
        cr.restore()

        avail_w = max(200, alloc_w - 56)
        avail_h = max(200, alloc_h - 76)

        if self.two_page:
            self._draw_two_page(area, cr, alloc_w, alloc_h, avail_w, avail_h)
        else:
            self._draw_single_page(area, cr, alloc_w, alloc_h, avail_w, avail_h)

    def _draw_two_page(
        self,
        area: Gtk.DrawingArea,
        cr: cairo.Context,
        alloc_w: int,
        alloc_h: int,
        avail_w: int,
        avail_h: int,
    ) -> None:
        """Draw two-page book spread layout."""
        assert self.doc is not None
        total_pages = self.doc.get_n_pages()
        pw_cur, ph_cur = self.doc.get_page_size(self.current_page)
        has_second = self.current_page + 1 < total_pages

        if has_second:
            pw_nxt, ph_nxt = self.doc.get_page_size(self.current_page + 1)
        else:
            pw_nxt, ph_nxt = (pw_cur, ph_cur)

        gap = PAGE_GAP
        if self.rtl and has_second:
            total_w = pw_nxt + pw_cur + gap
            max_h = max(ph_nxt, ph_cur)
        else:
            total_w = pw_cur + (pw_nxt + gap if has_second else 0)
            max_h = max(ph_cur, ph_nxt if has_second else ph_cur)

        if self._fit:
            scale = min(avail_w / total_w, avail_h / max_h)
            self.zoom = scale
        else:
            scale = self.zoom

        w = int(total_w * scale)
        h = int(max_h * scale)

        if w + 40 < alloc_w:
            area.set_content_width(alloc_w)
            area.set_content_height(max(h + 80, alloc_h))
            ox = (alloc_w - w) // 2
            oy = max((alloc_h - h) // 2, 20)
        else:
            area.set_content_width(w + 40)
            area.set_content_height(h + 40)
            ox = 20
            oy = 20

        draw_dropshadow(cr, ox, oy, w, h)

        if is_dark_mode():
            surface, _, _ = render_spread_surface(
                self.doc,
                self.current_page,
                scale,
                rtl=self.rtl,
            )
            cr.save()
            cr.translate(ox, oy)
            cr.set_source_surface(surface, 0, 0)
            cr.paint()
            cr.restore()
        else:
            cr.save()
            cr.translate(ox, oy)
            cr.scale(scale, scale)
            if self.theme_manager.current_theme == "sepia":
                cr.set_source_rgb(0.89, 0.84, 0.73)
            else:
                cr.set_source_rgb(0.88, 0.86, 0.82)

            if has_second:
                gutter_x = pw_nxt if self.rtl else pw_cur
                cr.rectangle(gutter_x, 0, gap, max_h)
                cr.fill()

            if self.rtl and has_second:
                pages = [
                    (pw_nxt, ph_nxt, self.current_page + 1, 0.0),
                    (pw_cur, ph_cur, self.current_page, pw_nxt + gap),
                ]
            else:
                pages = [(pw_cur, ph_cur, self.current_page, 0.0)]
                if has_second:
                    pages.append((pw_nxt, ph_nxt, self.current_page + 1, pw_cur + gap))

            for pw, ph, p_idx, xoff in pages:
                yoff = (max_h - ph) / 2.0
                cr.save()
                cr.translate(xoff, yoff)
                cr.set_source_rgb(1.0, 1.0, 1.0)
                cr.rectangle(0, 0, pw, ph)
                cr.fill()
                try:
                    self.doc.get_page(p_idx).render(cr)
                except (GLib.Error, RuntimeError, cairo.Error) as exc:
                    _LOGGER.warning("Poppler render failed on page %d: %s", p_idx, exc)
                cr.restore()

                if has_second:
                    self._draw_spine_shadow(cr, pw_nxt, max_h, gap, p_idx)

            # Top and bottom trim borders
            cr.set_source_rgba(0.0, 0.0, 0.0, 0.06)
            cr.rectangle(0, 0, total_w, 1)
            cr.fill()
            cr.rectangle(0, max_h - 1, total_w, 1)
            cr.fill()
            cr.restore()

    def _draw_spine_shadow(
        self,
        cr: cairo.Context,
        pw_left: float,
        max_h: float,
        gap: float,
        page_idx: int,
    ) -> None:
        """Render realistic soft gradient shadows along the inner book spine."""
        if self.rtl:
            if page_idx == self.current_page + 1:
                grad = cairo.LinearGradient(pw_left - 8, 0, pw_left + 4, 0)
                grad.add_color_stop_rgba(0.0, 0.0, 0.0, 0.0, 0.0)
                grad.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 0.16)
                cr.set_source(grad)
                cr.rectangle(pw_left - 8, 0, 12, max_h)
                cr.fill()
            else:
                grad = cairo.LinearGradient(pw_left + gap - 4, 0, pw_left + gap + 8, 0)
                grad.add_color_stop_rgba(0.0, 0.0, 0.0, 0.0, 0.14)
                grad.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 0.0)
                cr.set_source(grad)
                cr.rectangle(pw_left + gap - 4, 0, 12, max_h)
                cr.fill()
        else:
            if page_idx == self.current_page:
                grad = cairo.LinearGradient(pw_left - 8, 0, pw_left + 4, 0)
                grad.add_color_stop_rgba(0.0, 0.0, 0.0, 0.0, 0.0)
                grad.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 0.16)
                cr.set_source(grad)
                cr.rectangle(pw_left - 8, 0, 12, max_h)
                cr.fill()
            else:
                grad = cairo.LinearGradient(pw_left + gap - 4, 0, pw_left + gap + 8, 0)
                grad.add_color_stop_rgba(0.0, 0.0, 0.0, 0.0, 0.14)
                grad.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 0.0)
                cr.set_source(grad)
                cr.rectangle(pw_left + gap - 4, 0, 12, max_h)
                cr.fill()

    def _draw_single_page(
        self,
        area: Gtk.DrawingArea,
        cr: cairo.Context,
        alloc_w: int,
        alloc_h: int,
        avail_w: int,
        avail_h: int,
    ) -> None:
        """Draw single page layout centered."""
        assert self.doc is not None
        pw, ph = self.doc.get_page_size(self.current_page)

        if self._fit:
            scale = min(avail_w / pw, avail_h / ph)
            self.zoom = scale
        else:
            scale = self.zoom

        w = int(pw * scale)
        h = int(ph * scale)

        if w + 40 < alloc_w:
            area.set_content_width(alloc_w)
            area.set_content_height(max(h + 80, alloc_h))
            ox = (alloc_w - w) // 2
            oy = max((alloc_h - h) // 2, 20)
        else:
            area.set_content_width(w + 40)
            area.set_content_height(h + 40)
            ox = 20
            oy = 20

        draw_dropshadow(cr, ox, oy, w, h)

        if is_dark_mode():
            surface, _, _ = render_page_to_surface(
                self.doc.get_page(self.current_page),
                scale,
            )
            cr.save()
            cr.translate(ox, oy)
            cr.set_source_surface(surface, 0, 0)
            cr.paint()
            cr.restore()
        else:
            cr.save()
            cr.translate(ox, oy)
            cr.scale(scale, scale)
            cr.set_source_rgb(1.0, 1.0, 1.0)
            cr.rectangle(0, 0, pw, ph)
            cr.fill()
            try:
                self.doc.get_page(self.current_page).render(cr)
            except (GLib.Error, RuntimeError, cairo.Error) as exc:
                _LOGGER.warning("Poppler single-page render failed: %s", exc)
            cr.restore()

            # Subtle page border
            cr.save()
            cr.translate(ox, oy)
            cr.set_source_rgba(0.0, 0.0, 0.0, 0.06)
            cr.rectangle(0, 0, w, 1)
            cr.fill()
            cr.rectangle(0, h - 1, w, 1)
            cr.fill()
            cr.rectangle(0, 0, 1, h)
            cr.fill()
            cr.rectangle(w - 1, 0, 1, h)
            cr.fill()
            cr.restore()

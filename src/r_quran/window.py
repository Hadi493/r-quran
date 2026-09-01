import gi, json, os, math, cairo
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, Gdk, GLib
from pathlib import Path
from .pdf import QuranDocument
from . import bookmarks
_DATA_CANDIDATES = [Path(__file__).resolve().parents[2] / 'data', Path(__file__).resolve().parents[2] / 'share' / 'r-quran' / 'data', Path(__file__).resolve().parents[1] / 'data', Path('/usr/share/r-quran/data')]
DATA_DIR = next((p for p in _DATA_CANDIDATES if p.exists()), _DATA_CANDIDATES[0])

def load_json(name):
    try:
        return json.loads((DATA_DIR / name).read_text())
    except Exception:
        return []
JUZ_DATA = load_json('juz.json')
SURAH_DATA = load_json('surah.json')

def _is_dark():
    try:
        sm = Adw.StyleManager.get_default()
        return sm.get_dark()
    except Exception:
        return False

def _invert_surface(surf):
    try:
        high = Adw.StyleManager.get_default().get_high_contrast()
    except Exception:
        high = False
    cr = cairo.Context(surf)
    cr.set_operator(cairo.Operator.DIFFERENCE)
    if high:
        cr.set_source_rgb(1, 1, 1)
    else:
        cr.set_source_rgb(0.88, 0.88, 0.88)
    cr.paint()
    return surf

def render_page_to_surface(page, scale: float):
    pw, ph = page.get_size()
    w, h = (int(pw * scale), int(ph * scale))
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, max(1, w), max(1, h))
    cr = cairo.Context(surf)
    cr.scale(scale, scale)
    cr.set_source_rgb(1, 1, 1)
    cr.rectangle(0, 0, pw, ph)
    cr.fill()
    page.render(cr)
    if _is_dark():
        _invert_surface(surf)
    return (surf, pw, ph)

class QuranWindow(Adw.ApplicationWindow):

    def __init__(self, app, pdf_path=None):
        super().__init__(application=app, title='R-Quran')
        self.set_default_size(1000, 700)
        try:
            self.doc = QuranDocument(pdf_path)
        except Exception as e:
            self.doc = None
            self._error = str(e)
        else:
            self._error = None
        self.first_page = 1
        self.current_page = 1
        if self.doc and self.current_page >= self.doc.get_n_pages():
            self.current_page = self.first_page
        self.zoom = 1.0
        self._fit = True
        self.two_page = True
        self.rtl = True
        self._css_provider = Gtk.CssProvider()
        self.header = Adw.HeaderBar()
        self.header.set_show_start_title_buttons(False)
        self.header.set_show_end_title_buttons(False)
        self.header.set_decoration_layout('')
        self.header.add_css_class('compact-header')
        self.prev_btn = Gtk.Button(icon_name='go-previous-symbolic', tooltip_text='Previous (←/p)')
        self.prev_btn.connect('clicked', lambda *_: self.go_prev())
        self.header.pack_start(self.prev_btn)
        nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        nav_box.set_halign(Gtk.Align.CENTER)
        self.header.set_title_widget(nav_box)
        self.next_btn = Gtk.Button(icon_name='go-next-symbolic', tooltip_text='Next (→/n)')
        self.next_btn.connect('clicked', lambda *_: self.go_next())
        self.header.pack_end(self.next_btn)
        self.two_btn = Gtk.ToggleButton(icon_name='view-dual-symbolic', tooltip_text='Two pages like book (t)')
        self.two_btn.set_active(True)
        self._two_handler = self.two_btn.connect('toggled', self.on_two_toggled)
        self.header.pack_end(self.two_btn)
        self.theme_btn = Gtk.MenuButton(icon_name='night-light-symbolic', tooltip_text='Theme')
        self.header.pack_end(self.theme_btn)
        self._build_theme_menu()
        zoom_box = Gtk.Box(spacing=2)
        for icon, cb, tip in [('zoom-out-symbolic', lambda *_: self.set_zoom(self.zoom - 0.15), 'Zoom out'), ('zoom-fit-best-symbolic', lambda *_: self.set_zoom(0, fit=True), 'Fit width'), ('zoom-in-symbolic', lambda *_: self.set_zoom(self.zoom + 0.15), 'Zoom in')]:
            b = Gtk.Button(icon_name=icon, tooltip_text=tip)
            b.connect('clicked', cb)
            zoom_box.append(b)
        self.header.pack_end(zoom_box)
        self.header.pack_end(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        self.juz_btn = Gtk.MenuButton(label='Juz', tooltip_text='Juz — 30 parts')
        self.header.pack_start(self.juz_btn)
        self._build_juz_menu()
        self.surah_btn = Gtk.MenuButton(label='Surah', tooltip_text='Surah — 114 chapters')
        self.header.pack_start(self.surah_btn)
        self._build_surah_menu()
        self.bm_btn = Gtk.MenuButton(icon_name='bookmark-new-symbolic', tooltip_text='Bookmarks (b)')
        self.header.pack_start(self.bm_btn)
        self._build_bookmark_menu()
        add_bm = Gtk.Button(icon_name='bookmark-add-symbolic', tooltip_text='Add bookmark (b)')
        add_bm.add_css_class('suggested-action')
        add_bm.connect('clicked', self.on_add_bookmark)
        self.header.pack_start(add_bm)
        self.header.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.append(self.header)
        self.scrolled = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        self.scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.scrolled.add_css_class('quran-scrolled')
        self.drawing = Gtk.DrawingArea(hexpand=True, vexpand=True)
        self.drawing.set_draw_func(self.on_draw, None)
        self.drawing.set_content_width(600)
        self.drawing.set_content_height(800)
        self.scrolled.set_child(self.drawing)
        vbox.append(self.scrolled)
        self.progress = Gtk.ProgressBar()
        self.progress.set_show_text(False)
        self.progress.add_css_class('quran-progress')
        self.progress.set_fraction(0.0)
        vbox.append(self.progress)
        self.status = Gtk.Label(xalign=0)
        self.status.add_css_class('dim-label')
        self.status.set_margin_start(6)
        self.status.set_margin_end(6)
        vbox.append(self.status)
        self.set_content(vbox)
        key = Gtk.EventControllerKey()
        key.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key.connect('key-pressed', self.on_key)
        self.add_controller(key)
        swipe = Gtk.GestureSwipe()
        swipe.connect('swipe', self.on_swipe)
        self.drawing.add_controller(swipe)
        click = Gtk.GestureClick()
        click.connect('pressed', self.on_click)
        self.drawing.add_controller(click)
        self.update_ui()
        if self._error:
            self.status.set_label(f'Error: {self._error}')
        self.connect('realize', self._on_realize)

    def _on_realize(self, *_):
        display = self.get_display() or Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(display, self._css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            self._css_provider.load_from_string('.quran-scrolled{background:#d8cfb8}.quran-scrolled viewport{background:#d8cfb8}.compact-header{min-height:28px;padding:1px 4px}.compact-header button{min-height:22px;min-width:22px;padding:2px 6px;margin:1px}.compact-header entry{min-height:22px;padding:2px 6px}.quran-progress{min-height:3px}.quran-progress trough{min-height:3px;background:rgba(0,0,0,0.08)}.quran-progress progress{min-height:3px;background:#8a7a5a}')

    def _build_theme_menu(self):
        pop = Gtk.Popover()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(6)
        box.set_margin_end(6)
        sm = Adw.StyleManager.get_default()

        def set_scheme(s):
            sm.set_color_scheme(s)
            GLib.idle_add(lambda: (self.drawing.queue_draw(), False)[1])
        themes = [('Follow System', lambda: (set_scheme(Adw.ColorScheme.DEFAULT), self._clear_css_book())), ('Light', lambda: (set_scheme(Adw.ColorScheme.FORCE_LIGHT), self._clear_css_book())), ('Dark', lambda: (set_scheme(Adw.ColorScheme.FORCE_DARK), self._clear_css_book())), ('Sepia', self.apply_sepia), ('High Contrast', self.apply_high_contrast)]
        for label, cb in themes:
            b = Gtk.Button(label=label)
            b.connect('clicked', lambda _btn, c=cb: (c(), pop.popdown(), self.drawing.queue_draw()))
            box.append(b)
        pop.set_child(box)
        self.theme_btn.set_popover(pop)

    def _clear_css_book(self):
        self._css_provider.load_from_string('.quran-scrolled{background:#d8cfb8}.quran-scrolled viewport{background:#d8cfb8}.compact-header{min-height:28px;padding:1px 4px}.compact-header button{min-height:22px;min-width:22px;padding:2px 6px;margin:1px}.compact-header entry{min-height:22px;padding:2px 6px}')
        self.remove_css_class('quran-sepia')
        self.drawing.queue_draw()

    def apply_sepia(self):
        sm = Adw.StyleManager.get_default()
        sm.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        self._css_provider.load_from_string('window{background:#f4ecd8}.quran-scrolled{background:#e8dcc0}.quran-scrolled viewport{background:#e8dcc0}headerbar{background:#e8dcc0}.compact-header{min-height:28px;padding:1px 4px}.compact-header button{min-height:22px;min-width:22px;padding:2px 6px;margin:1px}')
        self.add_css_class('quran-sepia')
        self.drawing.queue_draw()

    def apply_high_contrast(self):
        sm = Adw.StyleManager.get_default()
        sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        self._css_provider.load_from_string('window,.quran-scrolled,.quran-scrolled viewport{background:#000;color:#fff}headerbar{background:#111}.compact-header{min-height:28px;padding:1px 4px}.compact-header button{min-height:22px;min-width:22px;padding:2px 6px;margin:1px}')
        self.remove_css_class('quran-sepia')
        self.drawing.queue_draw()

    def _build_juz_menu(self):
        pop = Gtk.Popover()
        grid = Gtk.Grid(column_spacing=4, row_spacing=4)
        grid.set_margin_top(6)
        grid.set_margin_bottom(6)
        grid.set_margin_start(6)
        grid.set_margin_end(6)
        for i, j in enumerate(JUZ_DATA):
            b = Gtk.Button(label=f"Juz {j['juz']}")
            b.set_tooltip_text(f"Page {j['page']}")
            b.connect('clicked', lambda _b, p=j['page']: (self.go_to_page(p), pop.popdown()))
            grid.attach(b, i % 5, i // 5, 1, 1)
        pop.set_child(grid)
        self.juz_btn.set_popover(pop)

    def _build_surah_menu(self):
        pop = Gtk.Popover()
        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        v.set_margin_top(6)
        v.set_margin_bottom(6)
        v.set_margin_start(6)
        v.set_margin_end(6)
        search = Gtk.SearchEntry(placeholder_text='Search surah…')
        sc = Gtk.ScrolledWindow(vexpand=True)
        sc.set_min_content_height(300)
        sc.set_min_content_width(340)
        sc.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        lb = Gtk.ListBox()
        lb.set_selection_mode(Gtk.SelectionMode.SINGLE)
        rows = []
        for s in SURAH_DATA:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            box.set_margin_top(4)
            box.set_margin_bottom(4)
            box.set_margin_start(6)
            box.set_margin_end(6)
            box.append(Gtk.Label(label=f"{s['id']:3d}. {s['name']}", xalign=0, hexpand=True))
            box.append(Gtk.Label(label=s['arabic'], xalign=1))
            box.append(Gtk.Label(label=f"p.{s['page']}", xalign=1))
            row.set_child(box)
            row._page = s['page']
            lb.append(row)
            rows.append((row, s))

        def on_filter(_e):
            q = search.get_text().lower().strip()
            for row, s in rows:
                visible = not q or q in s['name'].lower() or q in s['arabic'] or (q in str(s['id']))
                row.set_visible(visible)
        search.connect('search-changed', on_filter)

        def on_activate(_lb, row):
            self.go_to_page(row._page)
            pop.popdown()
        lb.connect('row-activated', on_activate)
        sc.set_child(lb)
        v.append(search)
        v.append(sc)
        pop.set_child(v)
        self.surah_btn.set_popover(pop)

    def _build_bookmark_menu(self):
        pop = Gtk.Popover()
        self._bm_pop = pop
        self._bm_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._bm_box.set_margin_top(6)
        self._bm_box.set_margin_bottom(6)
        self._bm_box.set_margin_start(6)
        self._bm_box.set_margin_end(6)
        pop.set_child(self._bm_box)
        self.bm_btn.set_popover(pop)
        pop.connect('notify::visible', lambda *_: self._refresh_bm())

    def _refresh_bm(self):
        child = self._bm_box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self._bm_box.remove(child)
            child = nxt
        bms = bookmarks.load()
        if not bms:
            self._bm_box.append(Gtk.Label(label='No bookmarks', xalign=0))
        for idx, bm in enumerate(bms):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            btn = Gtk.Button(label=bm.get('label', f"Page {bm['page']}"))
            btn.set_tooltip_text(f"Page {bm['page']}")
            btn.connect('clicked', lambda _b, p=bm['page']: (self.go_to_page(p), self._bm_pop.popdown()))
            row.append(btn)
            rm = Gtk.Button(icon_name='edit-delete-symbolic')
            rm.connect('clicked', lambda _b, i=idx: (bookmarks.remove(i), self._refresh_bm()))
            row.append(rm)
            self._bm_box.append(row)
        hb = Gtk.Box(spacing=4)
        clear = Gtk.Button(label='Clear all')
        clear.connect('clicked', lambda *_: (bookmarks.clear(), self._refresh_bm()))
        hb.append(clear)
        self._bm_box.append(hb)

    def on_add_bookmark(self, *_):
        page1 = self.current_page + 1
        bookmarks.add(page1, label=f'Page {page1}')
        self.status.set_label(f'Bookmarked page {page1}')
        self._refresh_bm()

    def go_to_page(self, p_1based: int):
        if not self.doc:
            return
        n = self.doc.get_n_pages()
        p = max(self.first_page + 1, min(p_1based, n))
        target = p - 1
        if target == self.current_page:
            return
        direction = 1 if target > self.current_page else -1
        self._animate_to(target, direction)

    def go_prev(self):
        if not self.doc:
            return
        if self.two_page:
            step = 2
            if self.current_page <= self.first_page:
                return
            target = max(self.first_page, self.current_page - step)
        else:
            if self.current_page <= self.first_page:
                return
            target = self.current_page - 1
        self._animate_to(target, -1)

    def go_next(self):
        if not self.doc:
            return
        n = self.doc.get_n_pages()
        if self.two_page:
            step = 2
            if self.current_page + step < n:
                target = self.current_page + step
            elif self.current_page + 1 < n:
                target = self.current_page + 1
            else:
                return
        else:
            if self.current_page >= n - 1:
                return
            target = self.current_page + 1
        self._animate_to(target, 1)

    def _compute_scale(self, pw, ph, avail_w, for_two=False, pw1=0, ph1=0):
        if for_two:
            gap = 12
            total_w = pw + pw1 + gap
            max_h = max(ph, ph1)
            if self._fit:
                scale = avail_w / total_w
                return (scale, total_w, max_h)
            else:
                return (self.zoom, total_w, max_h)
        elif self._fit:
            scale = avail_w / pw
            return (scale, pw, ph)
        else:
            return (self.zoom, pw, ph)

    def _animate_to(self, target: int, direction: int):
        if not self.doc:
            self.current_page = target
            self.update_ui()
            return
        self.current_page = target
        self.update_ui()

    def _render_spread_surface(self, start_page: int, scale: float):
        n = self.doc.get_n_pages()
        pw_cur, ph_cur = self.doc.get_page_size(start_page)
        has_second = start_page + 1 < n
        if has_second:
            pw_nxt, ph_nxt = self.doc.get_page_size(start_page + 1)
        else:
            pw_nxt, ph_nxt = (pw_cur, ph_cur)
        gap = 12
        if self.rtl and has_second:
            total_w = pw_nxt + pw_cur + gap
            max_h = max(ph_nxt, ph_cur)
            w, h = (int(total_w * scale), int(max_h * scale))
            surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, max(1, w), max(1, h))
            cr = cairo.Context(surf)
            cr.set_source_rgb(0.85, 0.85, 0.85)
            cr.rectangle(pw_nxt * scale, 0, gap * scale, h)
            cr.fill()
            for pw, ph, p_idx, xoff in [(pw_nxt, ph_nxt, start_page + 1, 0), (pw_cur, ph_cur, start_page, (pw_nxt + gap) * scale)]:
                yoff = (max_h * scale - ph * scale) / 2
                cr.save()
                cr.translate(xoff, yoff)
                cr.scale(scale, scale)
                cr.set_source_rgb(1, 1, 1)
                cr.rectangle(0, 0, pw, ph)
                cr.fill()
                try:
                    self.doc.get_page(p_idx).render(cr)
                except:
                    pass
                cr.restore()
                if p_idx == start_page + 1:
                    cr.set_source_rgba(0, 0, 0, 0.08)
                    cr.rectangle(pw_nxt * scale, 0, 4 * scale, h)
                    cr.fill()
                else:
                    cr.set_source_rgba(0, 0, 0, 0.06)
                    cr.rectangle((pw_nxt + gap) * scale, 0, 4 * scale, h)
                    cr.fill()
        else:
            total_w = pw_cur + (pw_nxt if has_second else 0) + (gap if has_second else 0)
            max_h = max(ph_cur, ph_nxt if has_second else ph_cur)
            w, h = (int(total_w * scale), int(max_h * scale))
            surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, max(1, w), max(1, h))
            cr = cairo.Context(surf)
            cr.set_source_rgb(0.85, 0.85, 0.85)
            if has_second:
                cr.rectangle(pw_cur * scale, 0, gap * scale, h)
                cr.fill()
            for idx, (pw, ph) in enumerate([(pw_cur, ph_cur), (pw_nxt, ph_nxt)] if has_second else [(pw_cur, ph_cur)]):
                xoff = 0 if idx == 0 else (pw_cur + gap) * scale
                yoff = (max_h * scale - ph * scale) / 2
                cr.save()
                cr.translate(xoff, yoff)
                cr.scale(scale, scale)
                cr.set_source_rgb(1, 1, 1)
                cr.rectangle(0, 0, pw, ph)
                cr.fill()
                try:
                    self.doc.get_page(start_page + idx).render(cr)
                except:
                    pass
                cr.restore()
                if has_second:
                    if idx == 0:
                        cr.set_source_rgba(0, 0, 0, 0.08)
                        cr.rectangle(pw_cur * scale, 0, 4 * scale, h)
                        cr.fill()
                    else:
                        cr.set_source_rgba(0, 0, 0, 0.06)
                        cr.rectangle((pw_cur + gap) * scale, 0, 4 * scale, h)
                        cr.fill()
        if _is_dark():
            _invert_surface(surf)
        return (surf, total_w * scale, max_h * scale)

    def on_two_toggled(self, btn):
        self.two_page = btn.get_active()
        self.update_ui()
        self.drawing.queue_draw()

    def _toggle_fullscreen(self):
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

    def on_key(self, _ctrl, keyval, _keycode, _state):
        if self.rtl:
            if keyval in (Gdk.KEY_Right, Gdk.KEY_p):
                self.go_prev()
                return True
            if keyval in (Gdk.KEY_Left, Gdk.KEY_n):
                self.go_next()
                return True
            if keyval == Gdk.KEY_Page_Down:
                self.go_next()
                return True
            if keyval == Gdk.KEY_Page_Up:
                self.go_prev()
                return True
        else:
            if keyval in (Gdk.KEY_Right, Gdk.KEY_Page_Down, Gdk.KEY_n):
                self.go_next()
                return True
            if keyval in (Gdk.KEY_Left, Gdk.KEY_Page_Up, Gdk.KEY_p):
                self.go_prev()
                return True
        if keyval == Gdk.KEY_Home:
            self.go_to_page(1)
            return True
        if keyval == Gdk.KEY_End and self.doc:
            self.go_to_page(self.doc.get_n_pages())
            return True
        if keyval in (Gdk.KEY_plus, Gdk.KEY_equal):
            self.set_zoom(self.zoom + 0.15)
            return True
        if keyval == Gdk.KEY_minus:
            self.set_zoom(self.zoom - 0.15)
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

    def on_swipe(self, _gesture, vx, _vy):
        if self.rtl:
            if vx < -120:
                self.go_prev()
            elif vx > 120:
                self.go_next()
        elif vx < -120:
            self.go_next()
        elif vx > 120:
            self.go_prev()

    def on_click(self, _gesture, _n, x, _y):
        w = self.drawing.get_width()
        if w == 0:
            return
        if self.rtl:
            if x < w * 0.28:
                self.go_next()
            elif x > w * 0.72:
                self.go_prev()
        elif x < w * 0.28:
            self.go_prev()
        elif x > w * 0.72:
            self.go_next()

    def set_zoom(self, z, fit=False):
        if fit:
            self._fit = True
            self.zoom = 1.0
        else:
            self._fit = False
            self.zoom = max(0.3, min(z, 3.0))
        self.drawing.queue_draw()
        self.status.set_label('')

    def update_ui(self):
        if not self.doc:
            return
        self.prev_btn.set_sensitive(self.current_page > self.first_page)
        self.next_btn.set_sensitive(self.current_page < self.doc.get_n_pages() - 1)
        try:
            total = self.doc.get_n_pages() - self.first_page
            cur = self.current_page - self.first_page + 1
            self.progress.set_fraction(max(0.0, min(1.0, cur / total)) if total else 0)
        except:
            pass
        self.drawing.queue_draw()

    def on_draw(self, area, cr, _w, _h, _data):
        if not self.doc:
            cr.set_source_rgb(0.2, 0.2, 0.2)
            cr.select_font_face('Sans', 0, 0)
            cr.set_font_size(14)
            cr.move_to(20, 30)
            cr.show_text(self._error or 'No document')
            return
        alloc_w = self.scrolled.get_width() or area.get_width() or 900
        alloc_h = self.scrolled.get_height() or area.get_height() or 700
        cr.save()
        if _is_dark():
            cr.set_source_rgb(0.08, 0.08, 0.08)
        else:
            cr.set_source_rgb(0.84, 0.8, 0.71)
        cr.paint()
        cr.restore()
        avail_w = max(200, alloc_w - 56)
        avail_h = max(200, alloc_h - 76)
        if self.two_page:
            pw_cur, ph_cur = self.doc.get_page_size(self.current_page)
            has_second = self.current_page + 1 < self.doc.get_n_pages()
            if has_second:
                pw_nxt, ph_nxt = self.doc.get_page_size(self.current_page + 1)
            else:
                pw_nxt, ph_nxt = (pw_cur, ph_cur)
            gap = 12
            if self.rtl and has_second:
                pw_left, ph_left = (pw_nxt, ph_nxt)
                pw_right, ph_right = (pw_cur, ph_cur)
                total_w = pw_left + pw_right + gap
                max_h = max(ph_left, ph_right)
            else:
                pw_left, ph_left = (None, None)
                pw_right, ph_right = (None, None)
                total_w = pw_cur + (pw_nxt if has_second else 0) + (gap if has_second else 0)
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
                oy = (alloc_h - h) // 2
                if oy < 20:
                    oy = 20
            else:
                area.set_content_width(w + 40)
                area.set_content_height(h + 40)
                ox = 20
                oy = 20
            cr.save()
            cr.translate(ox, oy)
            cr.set_source_rgba(0, 0, 0, 0.25)
            cr.rectangle(4, 4, w, h)
            cr.fill()
            cr.set_source_rgba(0, 0, 0, 0.12)
            cr.rectangle(2, 2, w, h)
            cr.fill()
            cr.set_source_rgb(0.55, 0.5, 0.45)
            cr.rectangle(-1, -1, w + 2, h + 2)
            cr.stroke()
            cr.restore()
            if _is_dark():
                surf, _, _ = self._render_spread_surface(self.current_page, scale)
                cr.save()
                cr.translate(ox, oy)
                cr.set_source_surface(surf, 0, 0)
                cr.paint()
                cr.restore()
            else:
                cr.save()
                cr.translate(ox, oy)
                cr.scale(scale, scale)
                cr.set_source_rgb(0.88, 0.86, 0.82)
                if has_second:
                    if self.rtl:
                        cr.rectangle(pw_nxt, 0, gap, max_h)
                        cr.fill()
                    else:
                        cr.rectangle(pw_cur, 0, gap, max_h)
                        cr.fill()
                if self.rtl and has_second:
                    pages = [(pw_nxt, ph_nxt, self.current_page + 1, 0), (pw_cur, ph_cur, self.current_page, pw_nxt + gap)]
                else:
                    pages = [(pw_cur, ph_cur, self.current_page, 0)]
                    if has_second:
                        pages.append((pw_nxt, ph_nxt, self.current_page + 1, pw_cur + gap))
                for pw, ph, p_idx, xoff in pages:
                    yoff = (max_h - ph) / 2
                    cr.save()
                    cr.translate(xoff, yoff)
                    cr.set_source_rgb(1, 1, 1)
                    cr.rectangle(0, 0, pw, ph)
                    cr.fill()
                    try:
                        self.doc.get_page(p_idx).render(cr)
                    except Exception as e:
                        cr.set_source_rgb(0.8, 0, 0)
                        cr.move_to(10, 20)
                        cr.show_text(str(e))
                    cr.restore()
                    if has_second:
                        if self.rtl:
                            if p_idx == self.current_page + 1:
                                grad = cairo.LinearGradient(pw_nxt - 8, 0, pw_nxt + 4, 0)
                                grad.add_color_stop_rgba(0, 0, 0, 0, 0)
                                grad.add_color_stop_rgba(1, 0, 0, 0, 0.16)
                                cr.set_source(grad)
                                cr.rectangle(pw_nxt - 8, 0, 12, max_h)
                                cr.fill()
                            else:
                                grad = cairo.LinearGradient(pw_nxt + gap - 4, 0, pw_nxt + gap + 8, 0)
                                grad.add_color_stop_rgba(0, 0, 0, 0, 0.14)
                                grad.add_color_stop_rgba(1, 0, 0, 0, 0)
                                cr.set_source(grad)
                                cr.rectangle(pw_nxt + gap - 4, 0, 12, max_h)
                                cr.fill()
                        elif p_idx == self.current_page:
                            grad = cairo.LinearGradient(pw_cur - 8, 0, pw_cur + 4, 0)
                            grad.add_color_stop_rgba(0, 0, 0, 0, 0)
                            grad.add_color_stop_rgba(1, 0, 0, 0, 0.16)
                            cr.set_source(grad)
                            cr.rectangle(pw_cur - 8, 0, 12, max_h)
                            cr.fill()
                        else:
                            grad = cairo.LinearGradient(pw_cur + gap - 4, 0, pw_cur + gap + 8, 0)
                            grad.add_color_stop_rgba(0, 0, 0, 0, 0.14)
                            grad.add_color_stop_rgba(1, 0, 0, 0, 0)
                            cr.set_source(grad)
                            cr.rectangle(pw_cur + gap - 4, 0, 12, max_h)
                            cr.fill()
                cr.set_source_rgba(0, 0, 0, 0.06)
                cr.rectangle(0, 0, total_w, 1)
                cr.fill()
                cr.rectangle(0, max_h - 1, total_w, 1)
                cr.fill()
                cr.restore()
        else:
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
                oy = (alloc_h - h) // 2
                if oy < 20:
                    oy = 20
            else:
                area.set_content_width(w + 40)
                area.set_content_height(h + 40)
                ox = 20
                oy = 20
            cr.save()
            cr.translate(ox, oy)
            cr.set_source_rgba(0, 0, 0, 0.25)
            cr.rectangle(4, 4, w, h)
            cr.fill()
            cr.set_source_rgba(0, 0, 0, 0.12)
            cr.rectangle(2, 2, w, h)
            cr.fill()
            if _is_dark():
                surf, _, _ = render_page_to_surface(self.doc.get_page(self.current_page), scale)
                cr.set_source_surface(surf, 0, 0)
                cr.paint()
            else:
                cr.save()
                cr.scale(scale, scale)
                cr.set_source_rgb(1, 1, 1)
                cr.rectangle(0, 0, pw, ph)
                cr.fill()
                try:
                    self.doc.get_page(self.current_page).render(cr)
                except Exception as e:
                    cr.set_source_rgb(0.8, 0, 0)
                    cr.move_to(10, 20)
                    cr.show_text(str(e))
                cr.restore()
                cr.set_source_rgba(0, 0, 0, 0.06)
                cr.rectangle(0, 0, w, 1)
                cr.fill()
                cr.rectangle(0, h - 1, w, 1)
                cr.fill()
                cr.rectangle(0, 0, 1, h)
                cr.fill()
                cr.rectangle(w - 1, 0, 1, h)
                cr.fill()
            cr.restore()

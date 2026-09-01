import sys, os
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, Gio
from .window import QuranWindow
APP_ID = 'com.example.rquran'

class RQuranApp(Adw.Application):

    def __init__(self, pdf_path=None):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.pdf_path = pdf_path
        self.connect('activate', self.on_activate)

    def on_activate(self, _app):
        win = QuranWindow(self, pdf_path=self.pdf_path)
        win.present()

def main(argv=None):
    pdf = None
    if argv and len(argv) > 1:
        cand = os.path.expanduser(argv[1])
        if os.path.exists(cand):
            pdf = cand
        elif argv[1] not in ('--help', '-h'):
            print(f'PDF not found: {cand}, using default', file=sys.stderr)
    app = RQuranApp(pdf_path=pdf)
    return app.run(argv or sys.argv)
if __name__ == '__main__':
    raise SystemExit(main())
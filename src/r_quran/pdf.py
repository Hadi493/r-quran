import os
import gi
gi.require_version('Poppler', '0.18')
from gi.repository import Poppler, Gio
DEFAULT_PDF = os.path.expanduser('~/Documents/Quran/Imdadia-Hafezi-Quran.pdf')

def _find_pdf(path=None):
    if path:
        p = os.path.expanduser(path)
        if os.path.exists(p):
            return p
    for cand in [os.environ.get('R_QURAN_PDF'), os.path.join(os.path.dirname(__file__), '..', '..', 'share', 'r-quran', 'Imdadia-Hafezi-Quran.pdf'), os.path.join(os.path.dirname(__file__), '..', 'share', 'r-quran', 'Imdadia-Hafezi-Quran.pdf'.lower()), os.path.expanduser('~/Documents/Quran/Imdadia-Hafezi-Quran.pdf'), '/usr/share/r-quran/Imdadia-Hafezi-Quran.pdf']:
        if cand and os.path.exists(os.path.expanduser(cand)):
            return os.path.expanduser(cand)
    return os.path.expanduser(path or DEFAULT_PDF)

class QuranDocument:

    def __init__(self, path: str | None=None):
        self.path = _find_pdf(path)
        if not os.path.exists(self.path):
            raise FileNotFoundError(f'PDF not found: {self.path}')
        uri = Gio.File.new_for_path(self.path).get_uri()
        self.doc = Poppler.Document.new_from_file(uri, '')
        if self.doc is None:
            self.doc = Poppler.Document.new_from_file(uri, None)
        if self.doc is None:
            raise RuntimeError(f'Failed to open PDF: {self.path}')

    def get_n_pages(self) -> int:
        return self.doc.get_n_pages()

    def get_page(self, index: int):
        if not 0 <= index < self.get_n_pages():
            raise IndexError(f'page {index} out of range 0..{self.get_n_pages() - 1}')
        return self.doc.get_page(index)

    def get_page_size(self, index: int) -> tuple[float, float]:
        page = self.get_page(index)
        w, h = page.get_size()
        return (w, h)
"""Constants and configuration defaults for R-Quran."""

from pathlib import Path

APP_ID = "com.example.rquran"
APP_TITLE = "R-Quran"

# Default window dimensions
DEFAULT_WINDOW_WIDTH = 1000
DEFAULT_WINDOW_HEIGHT = 700
MIN_WINDOW_WIDTH = 400
MIN_WINDOW_HEIGHT = 300

# Zoom boundaries
DEFAULT_ZOOM = 1.0
MIN_ZOOM = 0.3
MAX_ZOOM = 3.0
ZOOM_STEP = 0.15

# Reading view layout
PAGE_GAP = 12
DEFAULT_FIRST_PAGE = 1  # 0-indexed page 1 is page 2 (Al-Fatiha in standard Quran)

# Asset search locations for data directory
DATA_CANDIDATES = [
    Path(__file__).resolve().parents[2] / "data",
    Path(__file__).resolve().parents[2] / "share" / "r-quran" / "data",
    Path(__file__).resolve().parents[1] / "data",
    Path("/usr/share/r-quran/data"),
]

# CSS stylesheet rules
CSS_BASE = """
.quran-scrolled {
    background: #d8cfb8;
}

.quran-scrolled viewport {
    background: #d8cfb8;
}

.compact-header {
    min-height: 28px;
    padding: 1px 4px;
}

.compact-header button {
    min-height: 22px;
    min-width: 22px;
    padding: 2px 6px;
    margin: 1px;
}

.compact-header entry {
    min-height: 22px;
    padding: 2px 6px;
}

.quran-progress {
    min-height: 3px;
}

.quran-progress trough {
    min-height: 3px;
    background: rgba(0, 0, 0, 0.08);
}

.quran-progress progress {
    min-height: 3px;
    background: #8a7a5a;
}
"""

CSS_SEPIA = """
window,
window.quran-sepia {
    background-color: #f4ecd8;
    color: #4a3828;
}

headerbar,
window.quran-sepia headerbar,
.compact-header {
    background-color: #e8dcc0;
    color: #4a3828;
    border-bottom: 1px solid #d5c49f;
    box-shadow: none;
    min-height: 28px;
    padding: 1px 4px;
}

.compact-header button,
.compact-header menubutton > button {
    min-height: 22px;
    min-width: 22px;
    padding: 2px 6px;
    margin: 1px;
    color: #4a3828;
    background-color: rgba(74, 56, 40, 0.08);
    border: 1px solid rgba(74, 56, 40, 0.16);
    border-radius: 5px;
    box-shadow: none;
}

.compact-header button:hover,
.compact-header menubutton > button:hover {
    background-color: rgba(74, 56, 40, 0.16);
    border-color: rgba(74, 56, 40, 0.28);
    color: #352618;
}

.compact-header button:active,
.compact-header menubutton > button:active {
    background-color: rgba(74, 56, 40, 0.24);
    color: #281c10;
}

.compact-header button:checked,
.compact-header togglebutton:checked {
    background-color: #6e5033;
    color: #fbf5ea;
    border-color: #5a4026;
}

.compact-header button:checked:hover,
.compact-header togglebutton:checked:hover {
    background-color: #5e432a;
    color: #ffffff;
}

.compact-header button.suggested-action {
    background-color: #8c683e;
    color: #fbf5ea;
    border-color: #74542e;
}

.compact-header button.suggested-action:hover {
    background-color: #7a5a33;
    color: #ffffff;
}

.compact-header button.suggested-action:active {
    background-color: #694c29;
}

headerbar separator {
    background-color: rgba(74, 56, 40, 0.20);
    min-width: 1px;
    margin: 3px 2px;
}

.compact-header entry {
    min-height: 22px;
    padding: 2px 6px;
    background-color: #fbf6ea;
    color: #4a3828;
    border: 1px solid #d5c49f;
    border-radius: 5px;
}

.quran-scrolled,
.quran-scrolled viewport {
    background-color: #e8dcc0;
}

.quran-progress {
    min-height: 3px;
}

.quran-progress trough {
    min-height: 3px;
    background-color: rgba(74, 56, 40, 0.12);
}

.quran-progress progress {
    min-height: 3px;
    background-color: #8c683e;
}

.dim-label {
    color: #7d654c;
}

popover,
popover contents {
    background-color: #f4ecda;
    color: #4a3828;
    border: 1px solid #d5c49f;
    border-radius: 0px;
    box-shadow: 0 0px 0px rgba(60, 44, 30, 0.15);
}

popover scrolledwindow,
popover scrolledwindow viewport,
popover viewport,
popover listbox,
popover listview,
.surah-scrolled,
.surah-scrolled viewport,
.surah-list {
    background-color: #f4ecda;
    color: #4a3828;
}

popover listbox row,
popover row,
.surah-list row {
    background-color: transparent;
    color: #4a3828;
    border-radius: 4px;
    padding: 0px;
}

popover listbox row:hover,
popover row:hover,
.surah-list row:hover {
    background-color: rgba(74, 56, 40, 0.10);
    color: #352618;
}

popover listbox row:selected,
popover row:selected,
.surah-list row:selected {
    background-color: rgba(74, 56, 40, 0.18);
    color: #281c10;
}

popover label,
.surah-list label {
    color: #4a3828;
}

popover listbox row:hover label,
popover row:hover label,
.surah-list row:hover label {
    color: #352618;
}

popover listbox row:selected label,
popover row:selected label,
.surah-list row:selected label {
    color: #281c10;
}

popover button {
    color: #4a3828;
    background-color: rgba(74, 56, 40, 0.07);
    border: 1px solid rgba(74, 56, 40, 0.14);
    border-radius: 4px;
}

popover button:hover {
    background-color: rgba(74, 56, 40, 0.15);
    color: #352618;
}

popover entry,
popover searchentry,
popover searchentry text,
popover entry text {
    background-color: #fbf6ea;
    color: #4a3828;
    border: 1px solid #d5c49f;
    border-radius: 6px;
}

popover searchentry image {
    color: #7d654c;
}

popover scrollbar trough {
    background-color: rgba(74, 56, 40, 0.08);
}

popover scrollbar slider {
    background-color: rgba(74, 56, 40, 0.25);
    border-radius: 4px;
}

popover scrollbar slider:hover {
    background-color: rgba(74, 56, 40, 0.40);
}
"""

CSS_HIGH_CONTRAST = """
window,
.quran-scrolled,
.quran-scrolled viewport {
    background: #000000;
    color: #ffffff;
}

headerbar {
    background: #111111;
}

.compact-header {
    min-height: 28px;
    padding: 1px 4px;
}

.compact-header button {
    min-height: 22px;
    min-width: 22px;
    padding: 2px 6px;
    margin: 1px;
}

.compact-header entry {
    min-height: 22px;
    padding: 2px 6px;
}

.quran-progress {
    min-height: 3px;
}

.quran-progress trough {
    min-height: 3px;
    background: rgba(255, 255, 255, 0.15);
}

.quran-progress progress {
    min-height: 3px;
    background: #ffffff;
}
"""

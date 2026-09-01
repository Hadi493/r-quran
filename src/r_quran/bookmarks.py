import json, os, time
from pathlib import Path
BM_PATH = Path.home() / '.config' / 'r-quran' / 'bookmarks.json'

def _ensure():
    BM_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not BM_PATH.exists():
        BM_PATH.write_text('[]')

def load():
    _ensure()
    try:
        return json.loads(BM_PATH.read_text() or '[]')
    except Exception:
        return []

def save(bms):
    _ensure()
    BM_PATH.write_text(json.dumps(bms, indent=2, ensure_ascii=False))

def add(page_1based: int, label: str=''):
    bms = load()
    bms.append({'page': page_1based, 'label': label or f'Page {page_1based}', 'ts': int(time.time())})
    save(bms)
    return bms

def remove(idx: int):
    bms = load()
    if 0 <= idx < len(bms):
        del bms[idx]
        save(bms)
    return bms

def clear():
    save([])
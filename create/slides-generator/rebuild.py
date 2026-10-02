#!/usr/bin/env python3
"""Rebuild an existing deck on the current template.html + config.json — no LLM.

Keeps the deck's slides (<section class="slide">…) as is and swaps everything around them
(CSS, JS, menu, counter, SVG defs) for the current template, applying config.json:
colors.green / colors.amber, brand, decktag, ratio (9:16 class), art (false → hide .art).
Settings that need re-layout (type, layouts) only apply on a full regeneration.

Usage: python3 rebuild.py "/path/Deck.html"      (also called by settings.py POST /rebuild)
A copy of the previous version goes to backups/ next to this script (last 30 kept).
"""
import json
import re
import shutil
import sys
import time
from pathlib import Path

DIR = Path(__file__).resolve().parent
TEMPLATE = DIR / "template.html"
CONFIG = DIR / "config.json"
BACKUPS = DIR / "backups"
DEFAULT_GREEN, DEFAULT_AMBER = "#4ade80", "#fbbf24"


def _between(s, start, end):
    m = re.search(re.escape(start) + r"(.*?)" + re.escape(end), s, re.S)
    return m.group(1) if m else None


def _rgb(hexc):
    h = hexc.lstrip("#")
    return ",".join(str(int(h[i:i + 2], 16)) for i in (0, 2, 4))


def rebuild(deck_path):
    deck = Path(deck_path).expanduser().resolve()
    src = deck.read_text(encoding="utf-8")
    a, b = src.find('<section class="slide'), src.rfind("</section>")
    if a < 0 or b < 0 or 'id="deck"' not in src:
        raise ValueError("не похоже на деск slides-generator (нет слайдов или #deck)")
    slides = src[a:b + len("</section>")]
    title = _between(src, "<title>", "</title>") or deck.stem
    decktag = _between(src, '<div class="corner-tag">', "</div>") or ""
    brand = _between(src, '<div class="brand">', "</div>") or ""
    ratio916 = bool(re.search(r'<div class="deck[^"]*ratio-9-16', src))

    cfg = json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}
    decktag = cfg.get("decktag") or decktag
    brand = cfg.get("brand") or brand
    if cfg.get("ratio") in ("16:9", "9:16"):
        ratio916 = cfg["ratio"] == "9:16"

    shell = TEMPLATE.read_text(encoding="utf-8")
    colors = cfg.get("colors") or {}
    for key, default in (("green", DEFAULT_GREEN), ("amber", DEFAULT_AMBER)):
        new = (colors.get(key) or default).lower()
        if re.fullmatch(r"#[0-9a-f]{6}", new) and new != default:
            shell = re.sub(re.escape(default), new, shell, flags=re.I)
            shell = shell.replace(f"rgba({_rgb(default)},", f"rgba({_rgb(new)},")
    if cfg.get("art") is False:
        shell = shell.replace("</style>", "  .slide .art{display:none!important}\n</style>", 1)
    if ratio916:
        shell = re.sub(r'<div class="deck"', '<div class="deck ratio-9-16"', shell, count=1)

    out = (shell.replace("<!-- TITLE_PLACEHOLDER -->", title)
                .replace("<!-- DECKTAG_PLACEHOLDER -->", decktag)
                .replace("<!-- BRAND_PLACEHOLDER -->", brand)
                .replace("<!-- SLIDES_PLACEHOLDER -->", slides))
    if "PLACEHOLDER -->" in out:
        raise ValueError("в template.html не хватает плейсхолдеров")

    BACKUPS.mkdir(exist_ok=True)
    shutil.copy2(deck, BACKUPS / f"{deck.stem} · {time.strftime('%Y-%m-%d %H-%M-%S')}.html")
    for old in sorted(BACKUPS.glob("*.html"), key=lambda p: p.stat().st_mtime)[:-30]:
        old.unlink()
    deck.write_text(out, encoding="utf-8")
    return {"slides": out.count('<section class="slide'), "path": str(deck)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for p in sys.argv[1:]:
        r = rebuild(p)
        print(f"✓ {Path(r['path']).name}: {r['slides']} слайдов")

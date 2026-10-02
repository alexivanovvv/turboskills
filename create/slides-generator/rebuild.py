#!/usr/bin/env python3
"""Rebuild an existing deck on the current template.html + config.json — no LLM.

Keeps the deck's slides (<section class="slide">…) as is and swaps everything around them
(CSS, JS, menu, counter, SVG defs) for the current template, applying config.json the same
way settings.html draws its previews: theme/colors (all 14 keys), fonts, ui (cornerTag, menu,
brand, progress, size, tone), art, animate, brand, decktag, ratio.
Settings that need re-layout (type, layouts, motifs, images) only apply on a full regeneration.

The palette applied last time is stored in <meta name="sg-colors">, so switching themes
back and forth recolors the slides' inline colors correctly.

Usage: python3 rebuild.py "/path/Deck.html"      (also called by settings.py POST /rebuild)
A copy of the previous version goes to backups/ next to this script (last 30 kept).
"""
import json
import re
import shutil
import sys
import time
from pathlib import Path
from urllib.parse import quote

DIR = Path(__file__).resolve().parent
TEMPLATE = DIR / "template.html"
CONFIG = DIR / "config.json"
BACKUPS = DIR / "backups"

# Палитра «Ночь» = цвета, зашитые в template.html (как THEMES.night в settings.html)
NIGHT = {"bg": "#080a0c", "bg2": "#0e1117", "fg": "#e8eaf0", "muted": "#a7adbe", "dim": "#5b6276",
         "card": "#111318", "card2": "#181c25", "line": "#1e232f", "green": "#4ade80", "amber": "#fbbf24",
         "blue": "#38bdf8", "violet": "#c084fc", "orange": "#fb923c", "pink": "#f472b6"}
NEUTRAL = {"bg", "bg2", "fg", "muted", "dim", "card", "card2", "line"}
DEFAULT_FONTS = {"display": "Unbounded", "head": "Manrope", "body": "Golos Text"}
FONT_W = {"Unbounded": "400;600;700", "Manrope": "400;600;700", "Golos Text": "400;500;600",
          "Playfair Display": "400;700", "Lora": "400;600", "Inter Tight": "400;600;700", "Inter": "400;600;700",
          "Russo One": "", "JetBrains Mono": "400;600", "Rubik": "400;600;700", "Nunito": "400;600;700",
          "PT Serif": "400;700", "PT Sans": "400;700", "Oswald": "400;600;700", "Montserrat": "400;600;700",
          "Onest": "400;600;700"}
SERIF = {"Playfair Display", "Lora", "PT Serif"}
UI_SEL = ".corner-tag,.brand,.counter"
HEX = re.compile(r"#[0-9a-f]{6}", re.I)


def _between(s, start, end):
    m = re.search(re.escape(start) + r"(.*?)" + re.escape(end), s, re.S)
    return m.group(1) if m else None


def _rgb(hexc):
    h = hexc.lstrip("#")
    return ",".join(str(int(h[i:i + 2], 16)) for i in (0, 2, 4))


def _recolor(text, src, dst):
    """Каждый hex из src → hex из dst; rgb-тройки акцентов в rgba(...) тоже (как recolor() в settings.html)."""
    hexmap, trip = {}, {}
    for k, new in dst.items():
        old = src.get(k)
        if not old or old.lower() == new.lower():
            continue
        hexmap[old.lower()] = new
        if k not in NEUTRAL:
            trip[_rgb(old)] = _rgb(new)
    if hexmap:
        text = re.sub("|".join(map(re.escape, hexmap)), lambda m: hexmap[m.group(0).lower()], text, flags=re.I)
    if trip:
        pat = "|".join(k.replace(",", r",\s*") for k in trip)
        text = re.sub(pat, lambda m: trip[re.sub(r"\s", "", m.group(0))], text)
    return text


def _is_light(bg):
    r, g, b = (int(x) for x in _rgb(bg).split(","))
    return 0.299 * r + 0.587 * g + 0.114 * b > 140


def _font_stack(n):
    tail = "Georgia, serif" if n in SERIF else "Menlo, monospace" if n == "JetBrains Mono" else "-apple-system, sans-serif"
    return f"'{n}', {tail}"


def _fonts_url(names):
    fam = []
    for n in dict.fromkeys(names):
        w = FONT_W.get(n)
        fam.append("family=" + quote(n).replace("%20", "+") + (f":wght@{w}" if w else ""))
    return "https://fonts.googleapis.com/css2?" + "&".join(fam) + "&display=swap"


def _ui_css(u):
    s = ""
    if u.get("cornerTag") is False: s += ".corner-tag{display:none!important}"
    if u.get("brand") is False: s += ".brand{display:none!important}"
    menu = u.get("menu")
    if menu == "hover": s += '.menu-btn{opacity:0}.menu-btn:hover,.menu-btn[aria-expanded="true"]{opacity:.95}'
    if menu == "off": s += ".menu-btn{display:none!important}"
    prog = u.get("progress")
    if prog == "counter": s += ".counter-bar{display:none!important}"
    if prog == "bar": s += ".counter{display:none!important}"
    if prog == "off": s += ".counter-wrap{display:none!important}"
    if u.get("size") == "s": s += UI_SEL + "{font-size:.62rem}"
    if u.get("size") == "l": s += UI_SEL + "{font-size:.88rem}"
    if u.get("tone") == "dim": s += UI_SEL + "{color:var(--dim)}"
    if u.get("tone") == "bright": s += UI_SEL + "{color:var(--fg)}"
    return s


def _strip_anim(t):
    t = re.sub(r"<(animate|animateTransform|animateMotion|set)\b[^>]*/>", "", t)
    return re.sub(r"<(animate|animateTransform|animateMotion|set)\b[^>]*>.*?</\1>", "", t, flags=re.S)


def rebuild(deck_path, dry=False):
    """dry=True — ничего не пишет, только {"outdated": bool}: отличается ли дек от пересборки."""
    deck = Path(deck_path).expanduser().resolve()
    src = deck.read_text(encoding="utf-8")
    a, b = src.find('<section class="slide'), src.rfind("</section>")
    if a < 0 or b < 0 or 'id="deck"' not in src:
        raise ValueError("не похоже на дек slides-generator (нет слайдов или #deck)")
    slides = src[a:b + len("</section>")]
    title = _between(src, "<title>", "</title>") or deck.stem
    decktag = _between(src, '<div class="corner-tag">', "</div>") or ""
    brand = _between(src, '<div class="brand">', "</div>") or ""
    ratio916 = bool(re.search(r'<div class="deck[^"]*ratio-9-16', src))
    prev = _between(src, '<meta name="sg-colors" content=\'', "'>")
    prev_colors = json.loads(prev) if prev else dict(NIGHT)

    cfg = json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}
    decktag = cfg.get("decktag") or decktag
    brand = cfg.get("brand") or brand
    if cfg.get("ratio") in ("16:9", "9:16"):
        ratio916 = cfg["ratio"] == "9:16"
    colors = dict(NIGHT)
    for k, v in (cfg.get("colors") or {}).items():
        if k in NIGHT and isinstance(v, str) and HEX.fullmatch(v):
            colors[k] = v.lower()

    # слайды: из прошлой палитры обратно в «Ночь», шаблон и так в «Ночи»
    slides = _recolor(slides, prev_colors, NIGHT)
    shell = TEMPLATE.read_text(encoding="utf-8")
    if ratio916:
        shell = re.sub(r'<div class="deck"', '<div class="deck ratio-9-16"', shell, count=1)
    out = (shell.replace("<!-- TITLE_PLACEHOLDER -->", title)
                .replace("<!-- DECKTAG_PLACEHOLDER -->", decktag)
                .replace("<!-- BRAND_PLACEHOLDER -->", brand)
                .replace("<!-- SLIDES_PLACEHOLDER -->", slides))
    if "PLACEHOLDER -->" in out:
        raise ValueError("в template.html не хватает плейсхолдеров")

    out = _recolor(out, NIGHT, colors)
    if _is_light(colors["bg"]):
        out = re.sub(r"color:\s*#fff\b", "color:var(--fg)", out, flags=re.I)
        out = re.sub(r"rgba\(255,\s*255,\s*255", "rgba(0,0,0", out)
        out = re.sub(r'(fill|stroke)="#fff(fff)?"', lambda m: f'{m.group(1)}="{colors["fg"]}"', out, flags=re.I)
    animate = cfg.get("animate") is not False
    if not animate:
        out = _strip_anim(out)

    fonts = {**DEFAULT_FONTS, **(cfg.get("fonts") or {})}
    css = ""
    if fonts != DEFAULT_FONTS:
        css += (f"@import url('{_fonts_url([fonts['display'], fonts['head'], fonts['body']])}');\n"
                f":root{{--font-display:{_font_stack(fonts['display'])};--font-head:{_font_stack(fonts['head'])};"
                f"--font-body:{_font_stack(fonts['body'])}}}\n")
    css += _ui_css(cfg.get("ui") or {})
    if cfg.get("art") is False:
        css += '.art:not(.pic):not([style*="z-index:1"]){display:none!important}'
    if not animate:
        css += "*,*::before,*::after{animation:none!important;transition:none!important}"
    meta = f"<meta name=\"sg-colors\" content='{json.dumps(colors)}'>\n"
    style = f'<style id="sg-config">\n{css}\n</style>\n' if css else ""
    out = out.replace("</head>", meta + style + "</head>", 1)
    if dry:
        return {"outdated": out != src, "slides": out.count('<section class="slide')}

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

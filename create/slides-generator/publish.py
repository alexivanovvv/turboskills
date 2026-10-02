#!/usr/bin/env python3
"""Публикует деск «для слушателей»: копия деска с QR на Q&A-слайде + мета-теги + og.png + PDF → Netlify.

Usage: python3 publish.py "/path/Deck — Slides Content.html" [--deploy] [--no-qr] [--base-url URL] [--site NAME]
  config.json → "publish": {"site": "<netlify site name|id>", "baseUrl": "https://<name>.netlify.app"}
  --base-url / --site переопределяют config. Без --deploy — только локальная сборка + dry run.
Собирает published/{slug}/ (index.html, handout.pdf, og.png, favicon.png, apple-touch-icon.png)
и published/index.html — список всех опубликованных десков. Источник деска не меняется.
`netlify deploy --dir published` заменяет весь сайт, поэтому published/ хранит ВСЕ деcки.
"""
import argparse, html, json, re, shutil, subprocess, sys
from datetime import date
from pathlib import Path
from urllib.parse import quote

DIR = Path(__file__).resolve().parent
PUB = DIR / "published"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
NETLIFY = "/usr/local/bin/netlify"
SITE_NAME, LOCALE = "Alexey Ivanov", "ru_RU"
TR = dict(zip("абвгдеёзийклмнопрстуфхыэ", "abvgdeeziyklmnoprstufhye")) | {
    "ж": "zh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ь": "", "ю": "yu", "я": "ya"}
MARK = re.compile(r"\s*<!--sg-pub-->.*?<!--/sg-pub-->", re.S)
QR_RE = re.compile(r'<div id="sg-qr".*?<!--/sg-qr--></div>', re.S)

def slugify(s):
    s = "".join(TR.get(c, c) for c in s.lower())
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "deck"

def text(frag):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", frag or ""))).strip()

def css_var(doc, name, default):
    m = re.search(rf"--{name}:\s*(#[0-9a-fA-F]{{3,8}})", doc)
    return m.group(1) if m else default

def qr_svg(url):
    import qrcode
    q = qrcode.QRCode(border=0, error_correction=qrcode.constants.ERROR_CORRECT_M)
    q.add_data(url); q.make(fit=True)
    m = q.get_matrix(); n = len(m)
    d = "".join(f"M{x} {y}h1v1h-1z" for y, row in enumerate(m) for x, v in enumerate(row) if v)
    return (f'<svg viewBox="-1 -1 {n+2} {n+2}" shape-rendering="crispEdges" role="img" aria-label="QR: {url}">'
            f'<path fill="currentColor" d="{d}"/></svg>')

def qr_block(url):
    host, _, path = re.sub(r"^https?://", "", url).rstrip("/").partition("/")
    return f"""<div id="sg-qr"><style>
#sg-qr{{position:absolute;right:4cqw;bottom:5vh;z-index:3;display:flex;align-items:center;gap:1.1rem;
 padding:1rem 1.2rem;border-radius:16px;background:color-mix(in srgb,var(--bg) 82%,transparent);
 border:1px solid var(--line,rgba(255,255,255,.08));backdrop-filter:blur(6px);color:var(--fg);pointer-events:auto}}
#sg-qr svg{{width:clamp(110px,11vw,170px);height:auto;display:block}}
#sg-qr .c{{font-family:var(--font-body);font-size:clamp(.95rem,1.25cqw,1.15rem);font-weight:600;color:var(--fg);line-height:1.3}}
#sg-qr .u{{font-family:var(--font-body);font-size:clamp(.72rem,.9cqw,.85rem);color:var(--muted);margin-top:.35rem;white-space:nowrap}}
@media print{{.slide:has(#sg-qr){{position:relative!important}} #sg-qr{{color:#000;background:#fff;border-color:#ddd}} #sg-qr .c{{color:#000}}}}
</style>{qr_svg(url)}<div><div class="c">Слайды и PDF</div><div class="u">{html.escape(host)}<br>/{html.escape(path)}</div></div><!--/sg-qr--></div>"""

def head_tags(title, desc, url, image, theme, prefix=""):
    e = lambda s: html.escape(s, quote=True)
    t = [f"<title>{e(title)}</title>", f'<meta name="description" content="{e(desc)}">',
         f'<link rel="canonical" href="{e(url)}">', f'<meta name="theme-color" content="{theme}">',
         f'<link rel="icon" type="image/png" href="{prefix}favicon.png">',
         f'<link rel="apple-touch-icon" href="{prefix}apple-touch-icon.png">']
    og = dict(title=title, description=desc, image=image, url=url, type="website", site_name=SITE_NAME, locale=LOCALE)
    t += [f'<meta property="og:{k}" content="{e(v)}">' for k, v in og.items() if v]
    t += ['<meta property="og:image:width" content="1200">', '<meta property="og:image:height" content="630">'] if image else []
    tw = dict(card="summary_large_image", title=title, description=desc, image=image)
    t += [f'<meta name="twitter:{k}" content="{e(v)}">' for k, v in tw.items() if v]
    return "\n<!--sg-pub-->\n" + "\n".join(x for x in t if 'href=""' not in x) + "\n<!--/sg-pub-->"

def set_head(doc, tags, extra_css=""):
    doc = MARK.sub("", doc)
    doc = re.sub(r'\s*<(title>.*?</title|meta (name|property)="(description|theme-color|og:[^"]*|twitter:[^"]*)"[^>]*|'
                 r'link rel="(canonical|icon|apple-touch-icon)"[^>]*)>', "", doc, flags=re.S)
    doc = re.sub(r"<html(?![^>]*lang=)", '<html lang="ru"', doc, count=1)
    doc = re.sub(r'(<html[^>]*lang=")[^"]*', r"\1ru", doc, count=1)
    if extra_css: tags = tags.replace("<!--/sg-pub-->", f"<style>{extra_css}</style>\n<!--/sg-pub-->")
    return re.sub(r"(<meta charset=[^>]*>)", lambda m: m.group(1) + tags, doc, count=1)

def icons(dst, bg):
    from PIL import Image, ImageDraw
    for name, size in (("apple-touch-icon.png", 180), ("favicon.png", 64)):
        im = Image.new("RGB", (size, size), bg); r = size * .28
        ImageDraw.Draw(im).rounded_rectangle([r, r, size - r, size - r], radius=size * .1, fill="#4ade80")
        im.save(dst / name)

def chrome(*args):
    try: subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", *args],
                        timeout=60, capture_output=True)
    except subprocess.TimeoutExpired: print("  ! Chrome не уложился в 60 с:", args[-1], file=sys.stderr)

def build_index(base, theme):
    items = []
    for d in sorted(p for p in PUB.iterdir() if (p / "index.html").exists()):
        doc = (d / "index.html").read_text(encoding="utf-8")
        g = lambda n: (re.search(rf'<meta name="{n}" content="([^"]*)"', doc) or [None, ""])[1]
        items.append((html.unescape(g("sg-date")), html.unescape(text(re.search(r"<title>(.*?)</title>", doc).group(1))), d.name))
    items.sort(reverse=True)
    rows = "\n".join(f'<li><span class="d">{d}</span><a href="{s}/">{html.escape(t)}</a><a class="pdf" href="{s}/handout.pdf">PDF</a></li>'
                     for d, t, s in items)
    img = f"{base}/{items[0][2]}/og.png" if base and items else ""
    tags = head_tags("Слайды — Alexey Ivanov", "Слайды и PDF с выступлений и сессий Алексея Иванова.",
                     f"{base}/" if base else "", img, theme, f"{base}/" if base else "")
    doc = f"""<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">{tags}
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@500;700;800&display=swap" rel="stylesheet"><style>
body{{margin:0;background:{theme};color:#e8eaf0;font-family:Manrope,system-ui,sans-serif}} main{{max-width:760px;margin:0 auto;padding:12vh 24px}}
h1{{font-size:clamp(1.8rem,4vw,2.6rem);margin:0 0 2.5rem;font-weight:800}} h1 b{{color:#4ade80}} ul{{list-style:none;padding:0;margin:0}}
li{{display:flex;gap:1rem;align-items:baseline;padding:1rem 0;border-top:1px solid #1e232f}} .d{{color:#5b6276;font-size:.85rem;min-width:6.5rem}}
a{{color:#e8eaf0;text-decoration:none;font-weight:700;flex:1}} a:hover{{color:#4ade80}} a.pdf{{flex:none;color:#a7adbe;font-size:.85rem}}
</style></head><body><main><h1>Слайды<b>.</b></h1><ul>
{rows}
</ul></main></body></html>"""
    (PUB / "index.html").write_text(doc, encoding="utf-8")
    for f in ("favicon.png", "apple-touch-icon.png"):
        if items: shutil.copy(PUB / items[0][2] / f, PUB / f)
    return len(items)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deck"); ap.add_argument("--deploy", action="store_true"); ap.add_argument("--no-qr", action="store_true")
    ap.add_argument("--base-url"); ap.add_argument("--site")
    a = ap.parse_args()
    src = Path(a.deck).expanduser().resolve()
    if not src.is_file(): sys.exit(f"Нет файла: {src}")
    try: cfg = json.loads((DIR / "config.json").read_text(encoding="utf-8")).get("publish") or {}
    except (OSError, ValueError): cfg = {}
    base = (a.base_url or cfg.get("baseUrl") or "").rstrip("/"); site = a.site or cfg.get("site") or ""

    doc = src.read_text(encoding="utf-8")
    title = text((re.search(r"<title>(.*?)</title>", doc, re.S) or [None, ""])[1]) or src.stem.split(" — Slides")[0]
    slug = slugify(title); url = f"{base}/{slug}/" if base else ""
    first = re.search(r'<section class="slide.*?</section>', doc, re.S).group(0)
    h1 = text((re.search(r"<h1[^>]*>(.*?)</h1>", first, re.S) or [None, ""])[1])
    lead = text((re.search(r'<p class="lead"[^>]*>(.*?)</p>', first, re.S) or [None, ""])[1])
    desc = ". ".join(x.rstrip(".") for x in (h1, lead) if x) or title
    m = re.match(r"(\d{4}-\d{2}-\d{2})", src.parent.name); ddate = m.group(1) if m else date.today().isoformat()
    theme = css_var(doc, "bg", "#0b0d12")

    out = PUB / slug; out.mkdir(parents=True, exist_ok=True)
    doc = QR_RE.sub("", doc)
    qr = bool(url) and not a.no_qr
    if qr:
        last = list(re.finditer(r'<section class="slide[^"]*"[^>]*>.*?(?=</section>)', doc, re.S))[-1]
        doc = doc[:last.end()] + qr_block(url) + "\n" + doc[last.end():]
    hide = ("#rebuild-btn,#settings-btn,#comment-btn,#menu-status,.menu-sep:has(+#rebuild-btn){display:none!important}")
    tags = head_tags(title, desc, url, f"{url}og.png" if url else "", theme, url).replace(
        "<!--sg-pub-->", f'<!--sg-pub-->\n<meta name="sg-date" content="{ddate}">')
    (out / "index.html").write_text(set_head(doc, tags, hide), encoding="utf-8")
    icons(out, theme)

    print("→ og.png (скриншот слайда 1)…")
    page = "file://" + quote(str(out / "index.html"))
    chrome("--window-size=1200,630", "--timeout=6000", f"--screenshot={out / 'og.png'}", page + "#slide-1")
    print("→ handout.pdf…")
    try: subprocess.run([str(DIR / "export.sh"), str(out / "index.html"), "pdf"], timeout=120, capture_output=True)
    except subprocess.TimeoutExpired: print("  ! export.sh не уложился в 120 с", file=sys.stderr)
    if (out / "index.pdf").exists(): (out / "index.pdf").replace(out / "handout.pdf")
    n = build_index(base, theme)

    print(f"\nГотово: {title}\n  Папка: {out}\n  URL:   {url or '— (baseUrl не задан)'}" + ("" if qr else "  [без QR]"))
    for f in sorted(out.iterdir()): print(f"    {f.name:<22}{f.stat().st_size / 1024:>9.0f} КБ")
    print(f"  Список: {PUB / 'index.html'} ({n} деск(ов) в published/)")
    if not base or not site:
        name = f"slides-{slugify(SITE_NAME)}"
        print(f"\n⚠ Публикация не настроена. Один раз (с вашего разрешения):\n  {NETLIFY} sites:create --name {name}\n"
              f'  затем в config.json: "publish": {{"site": "{name}", "baseUrl": "https://{name}.netlify.app"}}'
              f"\n  и пересоберите (без baseUrl QR и абсолютные мета-теги не создаются).")
    cmd = [NETLIFY, "deploy", "--prod", "--dir", str(PUB), "--site", site or "<site>"]
    if a.deploy and base and site:
        print("\n→ netlify deploy…"); r = subprocess.run(cmd)
        if r.returncode: sys.exit("Deploy не удался")
        print(f"Опубликовано: {url}")
    else:
        size = sum(f.stat().st_size for f in PUB.rglob("*") if f.is_file()) / 1048576
        print(f"\nDry run — будет задеплоено (весь сайт заменится содержимым published/, {size:.1f} МБ):")
        for d in sorted(p.name for p in PUB.iterdir() if p.is_dir()): print(f"  /{d}/")
        print("Команда: " + " ".join(f'"{c}"' if " " in c else c for c in cmd) + ("" if a.deploy else "   (запустите с --deploy)"))

if __name__ == "__main__":
    main()

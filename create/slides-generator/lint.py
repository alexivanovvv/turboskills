#!/usr/bin/env python3
"""Автопроверка качества дека вместо разглядывания скриншотов.

Рендерит дек в headless Chrome (копия во временной папке, оригинал не трогается),
по очереди активирует каждый слайд и меряет: переполнение, обрезанный текст, мелкий шрифт,
перегруженность, повтор мотива на соседних слайдах, плейсхолдеры, битые картинки,
мелкий inline font-size. Если рядом лежит .md с тем же именем — запускает validate.py.

Usage: python3 lint.py "/path/Deck.html" [--json] [--size 1600x900]
Exit code: 1 если есть ошибки (✗), иначе 0 (предупреждения ! не валят).
"""
import argparse
import html
import json
import os
import re
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

DIR = Path(__file__).resolve().parent
def find_chrome():
    """Chrome/Chromium: $CHROME, стандартные пути macOS/Windows, затем PATH."""
    cands = [os.environ.get("CHROME", ""),
             "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
             "/Applications/Chromium.app/Contents/MacOS/Chromium",
             os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
             os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe")]
    cands += [shutil.which(n) or "" for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome")]
    return next((c for c in cands if c and os.path.isfile(c)), "")


CHROME = find_chrome()

# Внедряется перед </body>: глушит анимации, ждёт шрифты, меряет каждый слайд → <pre id="sg-lint">
PROBE = r"""<script>(async()=>{
const css=document.createElement('style');
css.textContent='*,*::before,*::after{animation:none!important;transition:none!important}';
document.head.appendChild(css);
document.querySelectorAll('animate,animateTransform,animateMotion,set').forEach(e=>e.remove());
try{await Promise.race([document.fonts.ready,new Promise(r=>setTimeout(r,4000))])}catch(e){}
const W=innerWidth,H=innerHeight,THR=15*W/1600;
const slides=[...document.querySelectorAll('.deck section.slide')];
const PH=/PLACEHOLDER|\bTODO\b|\b[Ll]orem\b|\{\{/, CARDS='.card,.colcard,.pcard,.numcard,.demo-item';
const short=t=>t.replace(/\s+/g,' ').trim().slice(0,50);
const ownText=el=>[...el.childNodes].filter(n=>n.nodeType===3).map(n=>n.textContent).join(' ').replace(/\s+/g,' ').trim();
const out=[];
for(const s of slides){
  slides.forEach(x=>x.classList.toggle('active',x===s)); void s.offsetHeight;
  const sr=s.getBoundingClientRect(), r={issues:[]};
  const hd=s.querySelector('h1,h2,.sec-title,.qa-big'); r.title=hd?short(hd.textContent):'';
  const deco=new Map(); // элемент внутри .art/.notes/svg или absolute/fixed-ветки — декор, не меряем
  const isDeco=el=>{if(el===s)return false;if(deco.has(el))return deco.get(el);
    const p=getComputedStyle(el).position;
    const v=el.matches('.art,.notes,svg')||p==='absolute'||p==='fixed'||isDeco(el.parentElement);
    deco.set(el,v);return v;};
  // переполнение
  const scroll=Math.max(s.scrollHeight-s.clientHeight,s.scrollWidth-s.clientWidth);let down=0,up=0,right=0;
  const small=[],words=[],inl=[],clipped=[];
  for(const el of s.querySelectorAll('*')){
    if(isDeco(el))continue;
    const b=el.getBoundingClientRect(); if(!b.width||!b.height)continue;
    const cs=getComputedStyle(el); if(cs.visibility==='hidden'||+cs.opacity===0)continue;
    down=Math.max(down,b.bottom-sr.bottom-4>0?b.bottom-sr.bottom:0); up=Math.max(up,sr.top-b.top-4>0?sr.top-b.top:0);
    right=Math.max(right,b.right-sr.right-4>0?b.right-sr.right:0);
    const t=ownText(el), tt=el.textContent.replace(/\s+/g,' ').trim(), fs=parseFloat(cs.fontSize);
    // eyebrow-лейблы (UPPERCASE, ≤60 симв.), номера «01» и kbd/code мельче по дизайну — для них порог 11px
    const label=!/\p{L}/u.test(tt)||el.closest('kbd,code')||(cs.textTransform==='uppercase'&&tt.length<=60);
    const tiny=tt&&fs<(label?11*W/1600:THR)-0.05;
    const m=(el.getAttribute('style')||'').match(/font-size:\s*([\d.]+)(rem|em|px)/);
    if(tiny&&m&&(m[2]==='px'?+m[1]<14:+m[1]<.9))inl.push(`${m[1]}${m[2]} «${short(tt)}»`);
    else if(t&&tiny)small.push([fs,short(t)]);
    if(t){ words.push(...t.split(' ').filter(w=>/[\p{L}\d]/u.test(w)));
      if(PH.test(t))r.issues.push(['E','placeholder',`плейсхолдер в тексте: «${short(t)}»`]); }
    if(tt&&/hidden|clip/.test(cs.overflowX+cs.overflowY)&&(el.scrollWidth>el.clientWidth+2||el.scrollHeight>el.clientHeight+2))
      clipped.push(short(tt));
  }
  if(inl.length)r.issues.push(['W','inline-font',`мелкий inline font-size (${inl.length} эл.): `+inl.slice(0,3).join(', ')]);
  const ov=[[down,'ниже'],[up,'выше'],[right,'правее']].filter(x=>x[0]>0).map(x=>`${x[1]} края на ${Math.round(x[0])}px`);
  if(ov.length)r.issues.push(['E','overflow','переполнение: контент '+ov.join(', ')]);
  // не за краем, но съел поле (padding) и слайд прокручивается — визуально впритык, это WARN
  else if(scroll>2)r.issues.push(['W','overflow',`впритык: контент залез в поля, слайд прокручивается на ${Math.round(scroll)}px`]);
  clipped.slice(0,3).forEach(t=>r.issues.push(['E','clipped',`обрезанный текст: «${t}»`]));
  if(small.length){small.sort((a,b)=>a[0]-b[0]);
    r.issues.push(['W','small',`мелкий текст ${small[0][0].toFixed(1)}px (${small.length} эл.): `+[...new Set(small.map(x=>'«'+x[1]+'»'))].slice(0,3).join(', ')]);}
  const vis=q=>[...s.querySelectorAll(q)].filter(e=>!isDeco(e)&&e.getClientRects().length).length;
  const li=vis('li'),cards=vis(CARDS);
  if(li>7)r.issues.push(['W','dense',`перегруз: ${li} пунктов списка`]);
  if(cards>6)r.issues.push(['W','dense',`перегруз: ${cards} карточек`]);
  if(words.length>90)r.issues.push(['W','dense',`перегруз: ${words.length} слов на слайде`]);
  s.querySelectorAll('h1,h2').forEach(h=>{if(!h.textContent.trim())r.issues.push(['E','placeholder','пустой заголовок '+h.tagName.toLowerCase()])});
  s.querySelectorAll('img').forEach(i=>{if(i.complete&&!i.naturalWidth)r.issues.push(['W','image','битая картинка: '+(i.getAttribute('src')||'').slice(0,60)])});
  r.motifs=[...new Set([...s.querySelectorAll('use')].map(u=>(u.getAttribute('href')||u.getAttribute('xlink:href')||'').replace(/^#/,'')).filter(id=>id&&!id.startsWith('i-')))];
  out.push(r);
}
const pre=document.createElement('pre');pre.id='sg-lint';pre.textContent=JSON.stringify({w:W,h:H,slides:out});document.body.appendChild(pre);
})()</script>"""


def render(deck, size):
    """Копия дека + PROBE → headless Chrome --dump-dom → dict из <pre id="sg-lint">."""
    if not CHROME:
        sys.exit("lint.py: Chrome/Chromium не найден — установите его или задайте $CHROME")
    w, h = size
    with tempfile.TemporaryDirectory() as tmp:
        src = deck.read_text(encoding="utf-8")
        cut = src.rfind("</body>")
        src = src[:cut] + PROBE + src[cut:] if cut >= 0 else src + PROBE
        page = Path(tmp) / "deck.html"
        page.write_text(src, encoding="utf-8")
        cmd = [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={tmp}/prof",
               f"--window-size={w},{h}", "--virtual-time-budget=8000", "--dump-dom", page.as_uri()]
        # Chrome печатает DOM, но на некоторых деках потом не завершается → читаем до </html> и убиваем сами
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True)
        dom, deadline = b"", time.time() + 60
        try:
            while b"</html>" not in dom[-64:] and time.time() < deadline:
                if select.select([p.stdout], [], [], 1)[0]:
                    chunk = os.read(p.stdout.fileno(), 1 << 20)
                    if not chunk:
                        break
                    dom += chunk
        finally:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            p.wait()
        if b"</html>" not in dom[-64:]:
            sys.exit("✗ Chrome не уложился в 60 с (анимации/скрипты дека?)")
    m = re.search(r'<pre id="sg-lint">(.*?)</pre>', dom.decode("utf-8", "replace"), re.S)
    if not m:
        sys.exit("✗ Chrome отработал, но замеров нет (скрипт дека упал или не успели шрифты)")
    return json.loads(html.unescape(m.group(1)))


def run_validate(deck):
    md = deck.with_suffix(".md")
    if not md.exists():
        return None
    r = subprocess.run([sys.executable, str(DIR / "validate.py"), str(deck), str(md)],
                       capture_output=True, text=True, timeout=60)
    lines = [l for l in r.stdout.splitlines() if l.strip()]
    return {"exit": r.returncode, "summary": [l for l in lines if l.lstrip().startswith(("✗", "⚠"))] or lines[:1]}


def main():
    ap = argparse.ArgumentParser(description="Lint HTML-дека slides-generator")
    ap.add_argument("deck")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--size", default="1600x900")
    a = ap.parse_args()
    deck = Path(a.deck).expanduser().resolve()
    if not deck.exists():
        sys.exit(f"✗ Нет файла: {deck}")
    size = tuple(int(x) for x in a.size.lower().split("x"))

    data = render(deck, size)
    slides = data["slides"]
    for i in range(1, len(slides)):  # один и тот же мотив на соседних слайдах
        same = sorted(set(slides[i - 1]["motifs"]) & set(slides[i]["motifs"]))
        if same:
            slides[i]["issues"].append(["W", "motif", f"{i:02d} / {i + 1:02d} — один и тот же мотив "
                                        + ", ".join(f"`{m}`" for m in same) + " подряд"])
    data["validate"] = run_validate(deck)
    data["deck"] = str(deck)
    errors = sum(1 for s in slides for k, *_ in s["issues"] if k == "E") + bool(data["validate"] and data["validate"]["exit"])
    warns = sum(1 for s in slides for k, *_ in s["issues"] if k == "W")
    data["errors"], data["warnings"] = errors, warns

    if a.json:
        print(json.dumps(data, ensure_ascii=False, indent=1))
    else:
        name = deck.stem.replace(" — Slides Content", "")
        print(f"Дек: {name} ({len(slides)} слайдов, {size[0]}x{size[1]})")
        for n, s in enumerate(slides, 1):
            for kind, code, msg in s["issues"]:
                mark = "✗" if kind == "E" else "!"
                print(f"{mark} {msg}" if code == "motif" else f"{mark} {n:02d} «{s['title'] or '—'}» — {msg}")
        v = data["validate"]
        if v:
            warn = [l for l in v["summary"] if l.lstrip().startswith(("✗", "⚠"))]
            print(("✓" if v["exit"] == 0 else "✗") + " validate.py (MD↔HTML): " + ("; ".join(warn) if warn else "ок"))
        print(f"Итого: {errors} ошиб., {warns} предупр." if errors or warns else "Итого: чисто ✓")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Проверяет синхронность деска: число и порядок слайдов в HTML должны совпадать с MD.
Usage: validate.py "/path/to/Deck.html" ["/path/to/Deck.md"]
Если путь к MD не передан, ищет файл с тем же базовым именем и расширением .md рядом с HTML.
"""
import sys
import re
from pathlib import Path


def slide_titles_from_md(text):
    titles = []
    for m in re.finditer(r"^##\s*Слайд\s+(\d+)\s*(?:—|-)?\s*(.*)$", text, re.MULTILINE):
        num, rest = m.group(1), m.group(2).strip()
        titles.append((int(num), rest))
    return titles


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s).strip()


def slide_titles_from_html(text):
    sections = re.findall(r'<section class="slide[^"]*".*?>(.*?)</section>', text, re.DOTALL)
    titles = []
    for sec in sections:
        m = re.search(r"<h[1-4][^>]*>(.*?)</h[1-4]>", sec, re.DOTALL)
        if not m:
            m = re.search(r'class="(?:sec-title|qa-big)"[^>]*>(.*?)</', sec, re.DOTALL)
        title = strip_tags(m.group(1)) if m else "(без заголовка)"
        titles.append(title)
    return titles


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    html_path = Path(sys.argv[1])
    if len(sys.argv) >= 3:
        md_path = Path(sys.argv[2])
    else:
        md_path = html_path.with_name(html_path.stem.replace("Slides Content", "Slides Content") + ".md")
        if not md_path.exists():
            candidates = list(html_path.parent.glob("*.md"))
            md_path = candidates[0] if candidates else None

    if not html_path.exists():
        print(f"HTML не найден: {html_path}")
        sys.exit(1)
    if not md_path or not md_path.exists():
        print(f"MD не найден рядом с HTML — укажи путь вторым аргументом")
        sys.exit(1)

    html_text = html_path.read_text(encoding="utf-8")
    md_text = md_path.read_text(encoding="utf-8")

    md_slides = slide_titles_from_md(md_text)
    html_count = len(re.findall(r'<section class="slide', html_text))
    html_titles = slide_titles_from_html(html_text)

    ok = True

    if len(md_slides) != html_count:
        ok = False
        print(f"✗ Число слайдов не совпадает: MD={len(md_slides)}, HTML={html_count}")
    else:
        print(f"✓ Число слайдов совпадает: {html_count}")

    # проверка нумерации MD (без пропусков/дублей)
    nums = [n for n, _ in md_slides]
    expected = list(range(1, len(nums) + 1))
    if nums != expected:
        ok = False
        print(f"✗ Нумерация слайдов в MD нарушена: {nums}")

    # сопоставление заголовков по порядку (мягкая проверка, только предупреждение)
    mismatches = []
    for i, ((num, md_title), html_title) in enumerate(zip(md_slides, html_titles), 1):
        md_norm = re.sub(r"\(.*?\)", "", md_title).strip().lower()
        html_norm = html_title.strip().lower()
        if md_norm and html_norm and md_norm[:12] not in html_norm and html_norm[:12] not in md_norm:
            mismatches.append((i, md_title, html_title))

    if mismatches:
        print(f"⚠ Возможные расхождения заголовков по порядку ({len(mismatches)}):")
        for i, md_t, html_t in mismatches:
            print(f"   #{i}: MD «{md_t}» ↔ HTML «{html_t}»")

    balance_checks = [
        ("<section", "</section>"),
        ("<svg", "</svg>"),
        ("<div", "</div>"),
    ]
    for open_tag, close_tag in balance_checks:
        o, c = html_text.count(open_tag), html_text.count(close_tag)
        if o != c:
            ok = False
            print(f"✗ Незакрытые теги: {open_tag}={o} vs {close_tag}={c}")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

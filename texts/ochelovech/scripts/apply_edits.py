#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# START_MODULE_CONTRACT
# PURPOSE: Apply a list of point edits (quote -> replacement, with a reason) to a text, so
#          everything the agent did not quote stays byte-for-byte the same. Reports each
#          edit, the edit budget (via edit_budget.py) and can write a review page.
# SCOPE: deterministic, stdlib only. Finds quotes exactly, then tolerant to whitespace,
#        ё/е, dash, quote and apostrophe variants (' = \u2019), so English and Russian quotes
#        are found alike. Refuses ambiguous, missing and overlapping quotes. The review page UI
#        is in Russian whatever the language of the text.
# DEPENDS: Python 3.8+ standard library; edit_budget.py from the same folder.
# LINKS: M-APPLY-EDITS; M-EDIT-BUDGET; V-M-APPLY-EDITS.
# END_MODULE_CONTRACT
# START_MODULE_MAP
# parse: edits text -> (list of Edit, list of errors).
# locate: (text, edit) -> list of (start, end) spans or an error.
# apply: (text, edits, skip) -> (new text, applied, errors).
# review_html: (text, applied, budget) -> standalone HTML page with every edit in context.
# main: CLI, see the docstring; exit 0 applied and in budget, 1 applied but over budget,
#       2 nothing written (bad quote, overlap, unreadable file).
# END_MODULE_MAP
"""Применение точечных правок к тексту.

    python apply_edits.py текст.txt правки.txt                 # чистовик в stdout, отчет в stderr
    python apply_edits.py текст.txt правки.txt -o чистовик.txt
    python apply_edits.py страница.html правки.txt --in-place  # копия в страница.html.bak
    python apply_edits.py текст.txt правки.txt --skip 3,7      # без правок 3 и 7
    python apply_edits.py текст.txt правки.txt --review обзор.html
    python apply_edits.py текст.txt правки.txt --check         # только проверить цитаты

Формат правок:

    @@ 9 концовка-мораль
    - Это и есть реальное топливо системы.
    + С него система и работает.

`@@ причина` открывает правку, причина обязательна. Строки `- ` - точная цитата из
исходника (несколько строк - фрагмент с переводами строк), строки `+ ` - замена;
без строк `+` фрагмент удаляется. `@@*` меняет все вхождения (единый термин).
Цитата без `*` должна встречаться в тексте ровно один раз. Строки до первой `@@`
и ограды ``` пропускаются.

Код выхода: 0 - правки применены и в бюджете, 1 - применены, но вышли за бюджет,
2 - ничего не записано: цитата не найдена, неоднозначна, правки пересекаются
или файл не читается.
"""
from __future__ import annotations

import html
import re
import shutil
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import edit_budget  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")


@dataclass
class Edit:
    n: int
    reason: str
    old: str
    new: str
    every: bool = False
    line: int = 0
    spans: Tuple[Tuple[int, int], ...] = ()


# START_CONTRACT: parse
# PURPOSE: Read the edit list.
# INPUTS: src (str) in the @@ / - / + format.
# OUTPUTS: (edits numbered from 1, errors with line numbers).
# SIDE_EFFECTS: none.
# END_CONTRACT: parse
def parse(src: str) -> Tuple[List[Edit], List[str]]:
    edits: List[Edit] = []
    errors: List[str] = []
    cur: Optional[dict] = None

    def flush() -> None:
        if cur is None:
            return
        n = len(edits) + 1
        if not cur["old"]:
            errors.append("правка %d (строка %d): нет цитаты `- `" % (n, cur["line"]))
        edits.append(Edit(n, cur["reason"], "\n".join(cur["old"]), "\n".join(cur["new"]),
                          cur["every"], cur["line"]))

    for i, raw in enumerate(src.splitlines(), 1):
        if raw.startswith("```"):
            continue
        if raw.startswith("@@"):
            flush()
            every = raw.startswith("@@*")
            reason = raw[3 if every else 2:].strip()
            if not reason:
                errors.append("строка %d: правка без причины - назови признак или поправку" % i)
            cur = {"reason": reason, "old": [], "new": [], "every": every, "line": i}
            continue
        if cur is None:
            continue
        if raw[:1] in "-+" and raw:
            body = raw[2:] if raw[1:2] == " " else raw[1:]
            if raw[0] == "-":
                if cur["new"]:
                    errors.append("строка %d: цитата `- ` после замены `+ ` - начни новую правку с @@" % i)
                cur["old"].append(body)
            else:
                cur["new"].append(body)
        elif raw.strip():
            errors.append("строка %d: непонятная строка (нужно `@@`, `- ` или `+ `): %s" % (i, raw[:60]))
    flush()
    return edits, errors


QUOTES = "«»\"“”„"
DASHES = "—–-"
APOSTROPHES = "'\u2019\u2018\u02bc"  # don't = don\u2019t: agents and editors swap them


def _tolerant(old: str) -> "re.Pattern[str]":
    out = []
    for token in re.split(r"(\s+)", old.strip()):
        if not token:
            continue
        if token.isspace():
            out.append(r"\s+")
            continue
        for ch in token:
            if ch in "её":
                out.append("[её]")
            elif ch in "ЕЁ":
                out.append("[ЕЁ]")
            elif ch in DASHES:
                out.append("[%s]" % DASHES)
            elif ch in QUOTES:
                out.append("[%s]" % re.escape(QUOTES))
            elif ch in APOSTROPHES:
                out.append("[%s]" % APOSTROPHES)
            else:
                out.append(re.escape(ch))
    return re.compile("".join(out))


# START_CONTRACT: locate
# PURPOSE: Find where an edit's quote sits in the text.
# INPUTS: text (str), edit (Edit).
# OUTPUTS: (spans, error or None); one span unless edit.every.
# SIDE_EFFECTS: none.
# END_CONTRACT: locate
def locate(text: str, e: Edit) -> Tuple[List[Tuple[int, int]], Optional[str]]:
    spans = []
    start = text.find(e.old)
    while start != -1 and e.old:
        spans.append((start, start + len(e.old)))
        start = text.find(e.old, start + len(e.old))
    if not spans and e.old.strip():
        spans = [m.span() for m in _tolerant(e.old).finditer(text)]
    short = edit_budget._short(e.old, 60)
    if not spans:
        return [], "правка %d: цитата не найдена в тексте: «%s»" % (e.n, short)
    if len(spans) > 1 and not e.every:
        return [], "правка %d: цитата встречается %d раз, расширь ее: «%s»" % (e.n, len(spans), short)
    return spans, None


# START_CONTRACT: apply
# PURPOSE: Apply all edits except the skipped ones; refuse on any bad quote or overlap.
# INPUTS: text (str), edits (list of Edit), skip (set of edit numbers).
# OUTPUTS: (new text, applied edits with spans, errors); on errors new text == text.
# SIDE_EFFECTS: fills Edit.spans.
# END_CONTRACT: apply
def apply(text: str, edits: List[Edit], skip=frozenset()) -> Tuple[str, List[Edit], List[str]]:
    errors: List[str] = []
    applied: List[Edit] = []
    cuts = []
    for e in edits:
        if e.n in skip:
            continue
        if e.new == e.old:
            errors.append("правка %d ничего не меняет" % e.n)
            continue
        spans, err = locate(text, e)
        if err:
            errors.append(err)
            continue
        e.spans = tuple(spans)
        applied.append(e)
        cuts += [(s, t, e) for s, t in spans]
    cuts.sort(key=lambda c: c[0])
    for (s1, t1, e1), (s2, t2, e2) in zip(cuts, cuts[1:]):
        if s2 < t1:
            errors.append("правки %d и %d задевают один фрагмент - объедини их" % (e1.n, e2.n))
    if errors:
        return text, [], errors
    out, pos = [], 0
    for s, t, e in cuts:
        out += [text[pos:s], e.new]
        pos = t
    out.append(text[pos:])
    return "".join(out), applied, []


def visible(text: str) -> str:
    """Text without markup, for the budget of HTML pages."""
    text = re.sub(r"<(script|style)\b.*?</\1>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<(?:p|div|li|h\d|tr|br|section|article|blockquote)\b[^>]*>", "\n\n", text, flags=re.I)
    return html.unescape(re.sub(r"<[^>]+>", " ", text))


def _plain(s: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s)).split())


# START_CONTRACT: review_html
# PURPOSE: One page for the author: every applied edit with a bit of context and its reason.
# INPUTS: text (original), applied edits, budget dict from edit_budget.measure, title.
# OUTPUTS: HTML string (no external scripts; Google Font with system fallback).
# SIDE_EFFECTS: none.
# END_CONTRACT: review_html
def review_html(text: str, applied: List[Edit], budget: dict, title: str) -> str:
    cards = []
    for e in applied:
        s, t = e.spans[0]
        before = _plain(text[max(0, s - 160):s])[-90:]
        after = _plain(text[t:t + 160])[:90]
        more = " <span class=x>×%d</span>" % len(e.spans) if len(e.spans) > 1 else ""
        cards.append(
            "<article><header><b>%d</b><span>%s</span>%s</header>"
            "<p>…%s <del>%s</del><ins>%s</ins> %s…</p></article>"
            % (e.n, html.escape(e.reason), more, html.escape(before), html.escape(_plain(e.old)),
               html.escape(_plain(e.new)), html.escape(after)))
    verdict = "за бюджетом" if edit_budget.over_budget(budget) else "в бюджете"
    head = ("Правок: %d · сохранено слов исходника: %d%% · переписано абзацев: %d · удалено: %d · %s"
            % (len(applied), round(budget["kept"] * 100), len(budget["rewritten"]),
               len(budget["deleted"]), verdict))
    return """<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Правки: %s</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Golos+Text:wght@400;600&display=swap">
<style>
body{font:16px/1.55 "Golos Text",system-ui,sans-serif;max-width:860px;margin:40px auto;padding:0 20px;color:#1d1d1f;background:#fafaf7}
h1{font-size:22px;margin:0 0 6px}.sum{color:#555;margin:0 0 6px}.how{color:#777;font-size:14px;margin:0 0 28px}
article{background:#fff;border:1px solid #e6e4dc;border-radius:10px;padding:12px 16px;margin:0 0 12px}
header{display:flex;gap:10px;align-items:baseline;font-size:13px;color:#666;margin-bottom:4px}
header b{font-size:15px;color:#1d1d1f;min-width:22px}.x{color:#b26a00}
p{margin:0}del{background:#fde2e1;color:#8a1c1c}ins{background:#dff3e3;color:#13541f;text-decoration:none}
</style></head><body><h1>%s</h1><p class="sum">%s</p>
<p class="how">Не нравится правка - назови ее номер, она не войдет в чистовик.</p>
%s</body></html>""" % (html.escape(title), html.escape(title), head, "\n".join(cards))


def _report(applied: List[Edit], budget: dict, skipped: int) -> str:
    lines = ["Правок применено: %d%s" % (len(applied), ", пропущено: %d" % skipped if skipped else "")]
    for e in applied:
        lines.append("  %d. [%s] «%s» -> «%s»%s" % (
            e.n, e.reason, edit_budget._short(e.old, 50), edit_budget._short(e.new, 50) or "(удалено)",
            " ×%d" % len(e.spans) if len(e.spans) > 1 else ""))
    tally = Counter((e.reason.split() or ["?"])[0].rstrip(":,.;") for e in applied)
    if tally:
        lines.append("По причинам: " + ", ".join("%s ×%d" % kv for kv in tally.most_common()))
    lines.append("")
    lines.append(edit_budget.render(budget))
    return "\n".join(lines)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    opts = {}
    pos = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("-o", "--review", "--skip"):
            if i + 1 >= len(argv):
                print("%s ждет значение" % a, file=sys.stderr)
                return 2
            opts[a] = argv[i + 1]
            i += 2
            continue
        if a in ("--in-place", "--check"):
            opts[a] = True
        elif a in ("-h", "--help"):
            print(__doc__)
            return 2
        else:
            pos.append(a)
        i += 1
    if len(pos) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        skip = {int(x) for x in opts.get("--skip", "").replace(" ", "").split(",") if x}
    except ValueError:
        print("--skip ждет номера через запятую: 3,7", file=sys.stderr)
        return 2
    try:
        with open(pos[0], encoding="utf-8", newline="") as fh:
            text = fh.read()
        with open(pos[1], encoding="utf-8") as fh:
            edits, errors = parse(fh.read())
    except (OSError, UnicodeDecodeError) as exc:
        print("Не читается файл: %s" % exc, file=sys.stderr)
        return 2

    new, applied, apply_errors = apply(text, edits, skip)
    errors += apply_errors
    if errors:
        print("Правки не применены:\n" + "\n".join("  - " + x for x in errors), file=sys.stderr)
        return 2
    if opts.get("--check"):
        print("Все %d цитат найдены, пересечений нет." % len(applied), file=sys.stderr)
        return 0

    is_html = Path(pos[0]).suffix.lower() in (".html", ".htm")
    budget = edit_budget.measure(visible(text) if is_html else text, visible(new) if is_html else new)
    if "--review" in opts:
        Path(opts["--review"]).write_text(
            review_html(text, applied, budget, Path(pos[0]).name), encoding="utf-8")
    if opts.get("--in-place"):
        shutil.copyfile(pos[0], pos[0] + ".bak")
        with open(pos[0], "w", encoding="utf-8", newline="") as fh:
            fh.write(new)
    elif "-o" in opts:
        with open(opts["-o"], "w", encoding="utf-8", newline="") as fh:
            fh.write(new)
    else:
        sys.stdout.write(new)
    print(_report(applied, budget, len(skip & {e.n for e in edits})), file=sys.stderr)
    return 1 if edit_budget.over_budget(budget) else 0


if __name__ == "__main__":
    raise SystemExit(main())

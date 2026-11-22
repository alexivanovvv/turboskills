#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# START_MODULE_CONTRACT
# PURPOSE: Measure how far an edit drifted from the original (Russian or English) text: share of words kept,
#          paragraphs rewritten beyond a threshold, paragraphs deleted or added.
#          Guards the "edit, don't rewrite" rule of the skill.
# SCOPE: heuristic, offline, stdlib only. Word-level diff, paragraphs split by blank lines
#        (or by lines for one-line-per-paragraph input). Says nothing about meaning itself.
#        Language-independent: a word is letters/digits joined by hyphens or apostrophes
#        ("well-known", "don't" = "don\u2019t"); case and ё/е are ignored.
# DEPENDS: Python 3.8+ standard library.
# LINKS: M-EDIT-BUDGET; V-M-EDIT-BUDGET.
# END_MODULE_CONTRACT
# START_MODULE_MAP
# paragraphs: text -> list of paragraphs.
# measure: (before, after, limit) -> {"kept": float, "rewritten": [...], "deleted": [...], "added": [...]}.
# main: CLI `edit_budget.py before.txt after.txt [--limit 0.5] [--json]`;
#       exit 0 within budget, 1 over budget, 2 bad input.
# END_MODULE_MAP
"""Бюджет правки: насколько чистовик ушел от исходника.

    python edit_budget.py до.txt после.txt               # отчет по-русски
    python edit_budget.py до.txt после.txt --limit 0.4   # порог переписанности абзаца
    python edit_budget.py до.txt после.txt --json

Абзац считается переписанным, если в нем изменено больше `limit` слов (по умолчанию 0.5).
Код выхода: 0 — в бюджете, 1 — есть удаленные или переписанные абзацы либо сохранено
меньше 60% слов, 2 — файл не читается.
"""
from __future__ import annotations

import difflib
import json
import re
import sys
from typing import Dict, List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

MIN_KEPT = 0.6
# Apostrophes inside a word keep it whole: "don't" and "don\u2019t" are one word, the same word.
WORD = re.compile(r"[\w%$€₽£]+(?:[-'\u2019][\w]+)*", re.UNICODE)


def _norm(w: str) -> str:
    return w.lower().replace("ё", "е").replace("\u2019", "'")


def words(text: str) -> List[str]:
    return [_norm(w) for w in WORD.findall(text)]


def paragraphs(text: str) -> List[str]:
    text = text.replace("\r\n", "\n").strip()
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(parts) == 1 and "\n" in parts[0]:
        parts = [p.strip() for p in parts[0].split("\n") if p.strip()]
    return parts


def _similarity(a: str, b: str) -> float:
    wa, wb = words(a), words(b)
    if not wa and not wb:
        return 1.0
    return difflib.SequenceMatcher(None, wa, wb, autojunk=False).ratio()


def _short(p: str, n: int = 90) -> str:
    p = " ".join(p.split())
    return p if len(p) <= n else p[: n - 1] + "…"


def measure(before: str, after: str, limit: float = 0.5) -> Dict:
    wa, wb = words(before), words(after)
    sm = difflib.SequenceMatcher(None, wa, wb, autojunk=False)
    same = sum(b.size for b in sm.get_matching_blocks())
    kept = same / len(wa) if wa else 1.0

    pa, pb = paragraphs(before), paragraphs(after)
    used = set()
    rewritten, deleted = [], []
    for i, p in enumerate(pa):
        best, best_j = 0.0, None
        lo, hi = max(0, i - 6), min(len(pb), i + 7)  # paragraphs stay roughly in place
        for j in list(range(lo, hi)) + [j for j in range(len(pb)) if j < lo or j >= hi]:
            if j in used:
                continue
            s = _similarity(p, pb[j])
            if s > best:
                best, best_j = s, j
            if s == 1.0:
                break
        if best_j is None or best < 0.25:
            deleted.append(_short(p))
            continue
        used.add(best_j)
        if 1 - best > limit:
            rewritten.append({"before": _short(p), "after": _short(pb[best_j]), "changed": round(1 - best, 2)})
    added = [_short(pb[j]) for j in range(len(pb)) if j not in used]
    return {"kept": round(kept, 2), "words_before": len(wa), "words_after": len(wb),
            "rewritten": rewritten, "deleted": deleted, "added": added}


def over_budget(r: Dict) -> bool:
    return bool(r["rewritten"] or r["deleted"]) or r["kept"] < MIN_KEPT


def render(r: Dict) -> str:
    out = ["Сохранено слов исходника: %d%% (было %d слов, стало %d)" % (round(r["kept"] * 100), r["words_before"], r["words_after"])]
    if r["deleted"]:
        out.append("\nУдалены абзацы (верни или объясни автору):")
        out += ["  - " + p for p in r["deleted"]]
    if r["rewritten"]:
        out.append("\nПереписаны сильнее порога (оставь исходник и правь только признаки):")
        for x in r["rewritten"]:
            out.append("  - изменено %d%%: «%s»\n    → «%s»" % (round(x["changed"] * 100), x["before"], x["after"]))
    if r["added"]:
        out.append("\nНовые абзацы (проверь, что в них нет нового смысла):")
        out += ["  - " + p for p in r["added"]]
    out.append("\nИтог: " + ("правка вышла за бюджет" if over_budget(r) else "в бюджете"))
    return "\n".join(out)


def main(argv: List[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    limit = 0.5
    if "--limit" in argv:
        i = argv.index("--limit")
        try:
            limit = float(argv[i + 1])
            args.remove(argv[i + 1])
        except (IndexError, ValueError):
            print("--limit ждет число от 0 до 1", file=sys.stderr)
            return 2
    if len(args) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        before = sys.stdin.read() if args[0] == "-" else open(args[0], encoding="utf-8").read()
        after = open(args[1], encoding="utf-8").read()
    except OSError as e:
        print("Не читается файл: %s" % e, file=sys.stderr)
        return 2
    r = measure(before, after, limit)
    print(json.dumps(r, ensure_ascii=False, indent=2) if "--json" in argv else render(r))
    return 1 if over_budget(r) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

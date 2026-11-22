#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# START_MODULE_CONTRACT
# PURPOSE: Offline fidelity check of edits on regression cases taken from real over-rewrites:
#          required phrases kept, forbidden additions absent, no new numbers, no invented first person
#          (Russian я/мне/мой... and English I/I'm/I've/me/my/we're/we've..., each language on its own),
#          share of source words kept and no deleted paragraphs (via edit_budget). Cases are Russian
#          and English.
# SCOPE: stdlib only, no API calls. Judges only what can be checked by text; meaning is for people
#        or the meaning check in SKILL.md.
# DEPENDS: Python 3.8+ standard library; skills/ochelovech/scripts/edit_budget.py.
# LINKS: M-EVAL-FIDELITY; V-M-EVAL-FIDELITY.
# END_MODULE_CONTRACT
# START_MODULE_MAP
# load: path -> list of cases from cases.json.
# check: (case, output) -> list of problems (empty = passed).
# self_test: cases -> problems where the recorded bad output passes or the good one fails.
# main: CLI `check.py --export DIR | check.py DIR | check.py --self-test`.
# END_MODULE_MAP
"""Проверка верности правки на кейсах из реальных ошибок переписывания.

    python eval/fidelity/check.py --export /tmp/fid      # исходники: /tmp/fid/<id>.src.txt
    python eval/fidelity/check.py /tmp/fid               # проверить ответы /tmp/fid/<id>.txt
    python eval/fidelity/check.py --self-test            # плохие ответы ловятся, хорошие проходят

Код выхода: 0 — все кейсы прошли, 1 — есть провалы, 2 — нет файлов или кейсов.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Dict, List

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "skills" / "ochelovech" / "scripts"))
import edit_budget  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
FIRST_PERSON = re.compile(r"\b(?:я|мне|меня|мной|мой|моя|мое|мои|моих|моим|моей|моего|моему|моем)\b")
# English, checked on its own so a Latin "my" in a Russian source does not hide an invented "я".
# norm() makes the straight apostrophe a '"'; the typographic one stays. Bare "we/our" is not
# counted (generic "we" is normal in English prose), only its contractions: "we've tried".
FIRST_PERSON_EN = re.compile(r"\b(?:i(?![.\w]|[\"\u2019](?!m\b|ve\b|d\b|ll\b))|me|my|mine|myself|"
                             r"we[\"\u2019](?:re|ve|d|ll))\b")


def norm(text: str) -> str:
    text = text.lower().replace("ё", "е")
    text = re.sub(r"[—–‒]", "-", text)
    text = re.sub(r"[«»„“”\"']", '"', text)
    return " ".join(text.split())


def load(path: Path = HERE / "cases.json") -> List[Dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def check(case: Dict, output: str) -> List[str]:
    src, out = norm(case["source"]), norm(output)
    problems = []
    for item in case["must_keep"]:
        variants = item if isinstance(item, list) else [item]
        if not any(norm(v) in out for v in variants):
            problems.append("пропало: «%s»" % " / ".join(variants))
    for pattern in case.get("must_not_add", []):
        if re.search(pattern, out) and not re.search(pattern, src):
            problems.append("добавлено: /%s/" % pattern)
    new_numbers = sorted(set(NUMBER.findall(out)) - set(NUMBER.findall(src)))
    if new_numbers:
        problems.append("новые числа: " + ", ".join(new_numbers))
    for first_person in (FIRST_PERSON, FIRST_PERSON_EN):
        if first_person.search(out) and not first_person.search(src):
            problems.append("первое лицо, которого не было: «%s»" % first_person.search(out).group(0))
    budget = edit_budget.measure(case["source"], output)
    if budget["kept"] < case.get("min_kept", 0.6):
        problems.append("сохранено слов %d%% (нужно от %d%%)" % (budget["kept"] * 100, case.get("min_kept", 0.6) * 100))
    for paragraph in budget["deleted"]:
        problems.append("удален абзац: «%s»" % paragraph)
    return problems


def self_test(cases: List[Dict]) -> List[str]:
    errors = []
    for case in cases:
        if not check(case, case["bad"]):
            errors.append("%s: плохой ответ прошел проверку" % case["id"])
        for problem in check(case, case["good"]):
            errors.append("%s: хороший ответ не прошел: %s" % (case["id"], problem))
    return errors


def main(argv: List[str]) -> int:
    cases = load()
    if not cases:
        print("Нет кейсов в cases.json", file=sys.stderr)
        return 2
    if argv[:1] == ["--self-test"]:
        errors = self_test(cases)
        print("\n".join(errors) if errors else "Самопроверка: %d кейсов, плохие ответы ловятся, хорошие проходят" % len(cases))
        return 1 if errors else 0
    if len(argv) == 2 and argv[0] == "--export":
        folder = Path(argv[1])
        folder.mkdir(parents=True, exist_ok=True)
        for case in cases:
            (folder / (case["id"] + ".src.txt")).write_text(case["source"] + "\n", encoding="utf-8")
        print("Исходники: %d файлов в %s" % (len(cases), folder))
        return 0
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    folder = Path(argv[0])
    failed = missing = 0
    for case in cases:
        answer = folder / (case["id"] + ".txt")
        if not answer.exists():
            missing += 1
            print("%s: нет ответа" % case["id"])
            continue
        problems = check(case, answer.read_text(encoding="utf-8"))
        failed += bool(problems)
        print("%s: %s" % (case["id"], "ok" if not problems else "провал"))
        for problem in problems:
            print("  - " + problem)
    print("\nИтог: прошли %d из %d%s" % (len(cases) - failed - missing, len(cases),
                                        ", без ответа %d" % missing if missing else ""))
    if missing == len(cases):
        return 2
    return 1 if failed or missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

# -*- coding: utf-8 -*-
# START_MODULE_CONTRACT
# PURPOSE: Unit tests for the fidelity regression set: every recorded over-rewrite is caught,
#          every careful edit passes, and the generic checks fire on their own.
# SCOPE: eval/fidelity/check.py and cases.json, offline.
# DEPENDS: unittest; eval/fidelity/check.py loaded by path.
# LINKS: V-M-EVAL-FIDELITY.
# END_MODULE_CONTRACT
import importlib.util
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "fidelity_check", Path(__file__).resolve().parents[1] / "eval" / "fidelity" / "check.py")
fc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fc)

CASE = {"id": "t", "source": "Модели нужен контекст: роль, проекты и ограничения.",
        "must_keep": ["роль", ["ограничения", "рамки"]], "must_not_add": [r"один раз"]}


class FidelityTest(unittest.TestCase):
    def test_recorded_cases(self):
        cases = fc.load()
        self.assertGreaterEqual(len(cases), 10)
        self.assertEqual(fc.self_test(cases), [])

    def test_careful_edit_passes(self):
        self.assertEqual(fc.check(CASE, "Модели нужен контекст: роль, проекты и рамки."), [])

    def test_lost_phrase_and_forbidden_addition(self):
        problems = fc.check(CASE, "Модели нужен контекст: роль и проекты. Расскажите это один раз.")
        self.assertTrue(any(p.startswith("пропало") for p in problems))
        self.assertTrue(any(p.startswith("добавлено") for p in problems))

    def test_new_number_and_first_person(self):
        problems = fc.check(CASE, "Я даю модели контекст: роль, проекты и ограничения, 80% успеха.")
        self.assertIn("новые числа: 80", problems)
        self.assertTrue(any(p.startswith("первое лицо") for p in problems))

    def test_english_first_person(self):
        case = {"id": "e", "source": "Batch cooking saves time. Cook on Sunday.", "must_keep": [],
                "must_not_add": []}
        for out in ("I've tried batch cooking. Cook on Sunday.", "I\u2019m sure it saves time. Cook on Sunday.",
                    "Batch cooking saves my time. Cook on Sunday.", "We've seen it save time. Cook on Sunday."):
            self.assertTrue(any(p.startswith("первое лицо") for p in fc.check(case, out)), out)
        for out in ("Batch cooking saves time, i.e. hours. Cook on Sunday.", "We cook on Sunday to save time."):
            self.assertFalse(any(p.startswith("первое лицо") for p in fc.check(case, out)), out)
        # A source that already speaks in the first person may keep it.
        own = dict(case, source="I cook on Sunday. It saves time.")
        self.assertEqual(fc.check(own, "I cook on Sunday, and it saves time."), [])

    def test_yo_dash_and_quotes_are_tolerated(self):
        case = dict(CASE, source="Это и есть принцип \"own your data\" — всё у вас.",
                    must_keep=["own your data", "все у вас"], must_not_add=[])
        self.assertEqual(fc.check(case, "Это и есть принцип «own your data» - все у вас."), [])


if __name__ == "__main__":
    unittest.main()

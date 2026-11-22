# -*- coding: utf-8 -*-
# START_MODULE_CONTRACT
# PURPOSE: Unit tests for the skill helpers: check_facts, clean_paste, edit_budget, apply_edits.
# SCOPE: positive and negative cases for each kind of fact and artifact.
# DEPENDS: unittest; scripts loaded by path from skills/ochelovech/scripts.
# LINKS: V-M-CHECK-FACTS; V-M-CLEAN-PASTE; V-M-EDIT-BUDGET; V-M-APPLY-EDITS.
# English cases: CheckFactsEnglishTest, EnglishHelpersTest.
# END_MODULE_CONTRACT
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "ochelovech" / "scripts"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # dataclasses look the module up while the class is built
    spec.loader.exec_module(mod)
    return mod


cf = _load("check_facts")
cp = _load("clean_paste")
eb = _load("edit_budget")
ae = _load("apply_edits")


def kinds(result):
    return sorted({e["kind"] for e in result["errors"]})


class CheckFactsTest(unittest.TestCase):
    def test_identical_text_is_clean(self):
        text = "Анна получила 30 000 рублей 5 марта. Переводы на карту не принимаем."
        self.assertEqual(cf.compare(text, text)["errors"], [])

    def test_swapped_amounts_between_people(self):
        a = "Анна получила 30 000 рублей. Борис получил 50 000 рублей."
        b = "Анна получила 50 000 рублей. Борис получил 30 000 рублей."
        self.assertIn("swap", kinds(cf.compare(a, b)))

    def test_repeated_card_numbers_are_not_swaps(self):
        text = ("01 Анна ведет план. 02 Борис ведет бюджет. "
                "Шаги: 01 Анна и Борис собирают задачи. 02 Анна и Борис делят их.")
        self.assertNotIn("swap", kinds(cf.compare(text, text)))

    def test_word_after_block_tag_is_not_a_name(self):
        a = "<h3>Шаг</h3> <p>Разбиение задач на микрошаги.</p> <p>Пишет <b>Анна</b> Смирнова.</p>"
        b = "<h3>Шаг</h3> <p>Разбивать задачи на микрошаги.</p> <p>Пишет <b>Анна</b> Смирнова.</p>"
        self.assertEqual(cf.compare(a, b)["errors"], [])
        lost = cf.compare(a, b.replace("Анна", "она"))["errors"]
        self.assertTrue(any("Анна" in e["detail"] for e in lost))

    def test_lost_and_added_numbers(self):
        r = cf.compare("Ссылка действует 30 дней.", "Ссылка действует 45 дней.")
        self.assertIn("lost", kinds(r))
        self.assertIn("added", kinds(r))

    def test_units_and_number_words_are_normalised(self):
        a = "Капучино стоит 240 рублей, доплата 50 руб."
        b = "Капучино теперь 240 ₽. Доплата за овсяное молоко 50 ₽."
        self.assertEqual(cf.compare(a, b)["errors"], [])
        self.assertEqual(cf.compare("Приехали двое.", "Приехали 2 человека.")["errors"], [])

    def test_time_with_zero_minutes_equals_hour(self):
        self.assertEqual(cf.compare("Ждём с 11 до 16.", "Ждём с 11:00 до 16:00.")["errors"], [])

    def test_unit_change_is_an_error(self):
        self.assertIn("unit", kinds(cf.compare("Держит тепло 6 часов.", "Держит тепло 6 минут.")))

    def test_inverted_negation(self):
        r = cf.compare("Сервис не сохраняет исходный текст.", "Сервис сохраняет исходный текст.")
        self.assertIn("inverted", kinds(r))

    def test_negation_moved_inside_sentence_is_fine(self):
        a = "Довольны не все. Переводы на карту не принимаем."
        b = "Не все довольны. Переводы на карту мы не принимаем."
        self.assertEqual(cf.compare(a, b)["errors"], [])

    def test_lost_name(self):
        r = cf.compare("Согласует Марина Ковалёва из отдела кадров.", "Согласует отдел кадров.")
        self.assertIn("lost", kinds(r))

    def test_name_in_other_case_is_kept(self):
        r = cf.compare("Письмо для Олега Петровича.", "Олег Петрович, добрый день.")
        self.assertEqual(r["errors"], [])

    def test_utm_tail_removal_is_not_a_lost_link(self):
        a = "Сайт: https://example.ru/help?utm_source=chatgpt.com"
        b = "Сайт: https://example.ru/help"
        self.assertEqual(cf.compare(a, b)["errors"], [])

    def test_lost_link(self):
        self.assertIn("lost", kinds(cf.compare("Подробнее: https://example.ru/a", "Подробнее на сайте.")))

    def test_dates(self):
        self.assertIn("lost", kinds(cf.compare("Сдача 14 ноября.", "Сдача 28 ноября.")))
        self.assertEqual(cf.compare("Ярмарка 22–23 ноября.", "Ярмарка пройдёт 22 и 23 ноября.")["errors"], [])

    def test_hedge_loss_is_a_check(self):
        r = cf.compare("Процедура длится около 60 минут.", "Процедура длится 60 минут.")
        self.assertEqual(r["errors"], [])
        self.assertTrue(any(c["kind"] == "hedge" for c in r["checks"]))

    def test_year_of_numeric_date(self):
        self.assertIn("lost", kinds(cf.compare("Срок — 01.02.2026.", "Срок — 01.02.2027.")))
        self.assertEqual(cf.compare("Срок — 01.02.2026.", "Срок: 1 февраля 2026.")["errors"], [])

    def test_compound_number_words(self):
        self.assertEqual(cf.compare("В группе двадцать пять человек.", "В группе 25 человек.")["errors"], [])
        self.assertEqual(cf.compare("Привезли сто двадцать коробок.", "Привезли 120 коробок.")["errors"], [])
        self.assertIn("lost", kinds(cf.compare("В группе двадцать пять человек.", "В группе 20 человек.")))

    def test_utm_with_other_params_is_not_a_lost_link(self):
        a = "Сайт: https://example.org/?utm_source=chatgpt.com&id=42"
        b = "Сайт: https://example.org/?id=42"
        self.assertEqual(cf.compare(a, b)["errors"], [])

    def test_modality_shift_is_a_check(self):
        r = cf.compare("Пользователь может увидеть старые данные. Субботник запланирован на апрель.",
                       "Пользователь увидит старые данные. Субботник пройдёт в апреле.")
        details = " ".join(c["detail"] for c in r["checks"] if c["kind"] == "modality")
        self.assertIn("может", details)
        self.assertIn("план", details)
        same = "Иногда кэш отдаёт старые данные."
        self.assertFalse([c for c in cf.compare(same, same)["checks"] if c["kind"] == "modality"])

    def test_scope_attribution_and_intensifiers_are_checks(self):
        def details(a, b):
            return " ".join(c["detail"] for c in cf.compare(a, b)["checks"] if c["kind"] == "modality")
        self.assertIn("риск", details("Есть риск переделок.", "Работу придётся переделывать."))
        self.assertIn("один из", details("Это один из лучших курсов.", "Это лучший курс."))
        self.assertIn("по данным", details("По словам врача, это безопасно.", "Это безопасно."))
        self.assertIn("главный", details("Температура — ключевой фактор.", "Температура — главный фактор."))
        self.assertEqual(details("Это самый тёплый месяц.", "Это самый тёплый месяц года."), "")

    def test_lost_html_tags_are_errors(self):
        before = "<ul>\n<li><strong>Диагностика</strong> бесплатно</li>\n<li>Запчасти клиента</li>\n</ul>"
        after = "<p>Диагностика бесплатно, запчасти клиента принимаем.</p>"
        res = cf.compare(before, after)
        lost = [e["detail"] for e in res["errors"] if e["what"] == "разметка"]
        self.assertIn("<li> 2 → 0", lost)
        self.assertNotIn("<strong> 1 → 0", lost)  # emphasis may be removed on purpose: a check
        self.assertIn("<strong> 1 → 0", [c["detail"] for c in res["checks"] if c["what"] == "разметка"])
        same = cf.compare(before, before.replace("бесплатно", "бесплатна"))
        self.assertFalse([e for e in same["errors"] if e["what"] == "разметка"])
        # Autolinks are not tags; tag names are case-insensitive.
        links = "Пишите <hr@lapka.ru> или <https://lapka.ru/a>, <https://lapka.ru/b>."
        self.assertFalse([e for e in cf.compare(links, "Пишите hr@lapka.ru.")["errors"] if e["what"] == "разметка"])
        upper = cf.compare("<UL><LI>Раз</LI><LI>Два</LI></UL>", "<p>Раз, два</p>")
        self.assertIn("<li> 2 → 0", [e["detail"] for e in upper["errors"] if e["what"] == "разметка"])
        # Angle brackets in prose and a single tag are not markup to protect.
        self.assertFalse([e for e in cf.compare("Тег <b> жирный", "Тег жирный")["errors"] if e["what"] == "разметка"])

    def test_polite_pronoun_and_line_break_are_not_facts(self):
        self.assertEqual(cf.compare("Поздравляем Вас и желаем Вашего успеха.", "Поздравляем и желаем успеха.")["errors"], [])
        self.assertEqual(cf.compare("Вариант 3\n\nНоябрь — время книг.", "Ноябрь — время книг.")["errors"], [])
        self.assertIn("lost", kinds(cf.compare("Сдача 3 ноября.", "Сдача в ноябре.")))
        self.assertIn("lost", kinds(cf.compare("Офис в Вашингтоне закрыт.", "Офис закрыт.")))

    def test_cli_exit_codes(self):
        tmp = ROOT / "tests" / "_tmp_cf"
        tmp.mkdir(exist_ok=True)
        try:
            (tmp / "a.txt").write_text("Цена 240 рублей.", encoding="utf-8")
            (tmp / "b.txt").write_text("Цена 260 рублей.", encoding="utf-8")
            run = lambda x, y: subprocess.run([sys.executable, str(SCRIPTS / "check_facts.py"), str(x), str(y)],
                                              capture_output=True).returncode
            self.assertEqual(run(tmp / "a.txt", tmp / "a.txt"), 0)
            self.assertEqual(run(tmp / "a.txt", tmp / "b.txt"), 1)
            self.assertEqual(run(tmp / "a.txt", tmp / "nope.txt"), 2)
        finally:
            for p in tmp.glob("*"):
                p.unlink()
            tmp.rmdir()


class CleanPasteTest(unittest.TestCase):
    def test_content_reference(self):
        text, counts = cp.clean("Рост заявок :contentReference[oaicite:3]{index=3}. Дальше.")
        self.assertEqual(text, "Рост заявок. Дальше.")
        self.assertEqual(counts, {"contentReference": 1})

    def test_source_tokens_and_cite(self):
        text, _ = cp.clean("Факт【4:2†source】 и ещё [cite: 1, 2] факт.")
        self.assertEqual(text, "Факт и ещё факт.")

    def test_utm_tail_keeps_link(self):
        text, _ = cp.clean("См. https://a.ru/p?utm_source=chatgpt.com и https://b.ru/q?id=1&utm_source=x.")
        self.assertEqual(text, "См. https://a.ru/p и https://b.ru/q?id=1.")
        text, _ = cp.clean("https://a.ru/p?utm_source=x&id=1")
        self.assertEqual(text, "https://a.ru/p?id=1")

    def test_several_utm_params_in_one_pass(self):
        text, counts = cp.clean("https://example.org/?utm_source=a&utm_medium=b&id=42#top")
        self.assertEqual(text, "https://example.org/?id=42#top")
        self.assertEqual(counts["utm"], 2)
        self.assertEqual(cp.clean(text), (text, {}))

    def test_invisible_characters(self):
        text, counts = cp.clean("при\u200bвет\u00ad мир\ufeff")
        self.assertEqual(text, "привет мир")
        self.assertEqual(counts["invisible"], 3)

    def test_emoji_joiner_and_nbsp_survive(self):
        family = "\U0001F468\u200d\U0001F469\u200d\U0001F467"
        src = "Семья " + family + " и 240\u00a0₽"
        text, counts = cp.clean(src)
        self.assertEqual(text, src)
        self.assertEqual(counts, {})

    def test_clean_text_untouched(self):
        src = "Обычный текст — с тире, «ёлочками» и ссылкой https://a.ru/x?id=2."
        self.assertEqual(cp.clean(src), (src, {}))



class HouseStyleTest(unittest.TestCase):
    def test_dashes_become_hyphen(self):
        out, n = cp.house("Personal OS — это среда. Годы 1941–1945. Конец —\nдальше")
        self.assertEqual(out, "Personal OS - это среда. Годы 1941-1945. Конец -\nдальше")
        self.assertEqual(n["тире"], 3)

    def test_dialogue_and_html_entities(self):
        self.assertEqual(cp.house("— Привет, — сказал он.")[0], "- Привет, - сказал он.")
        self.assertEqual(cp.house("<p>A&nbsp;&mdash; B</p>")[0], "<p>A - B</p>")

    def test_yo(self):
        self.assertEqual(cp.house("Ёлки, всё ещё", hyphen=False)[0], "Елки, все еще")
        self.assertEqual(cp.house("всё — ок", yo=False)[0], "всё - ок")

    def test_code_links_and_tags_are_protected(self):
        src = 'Код `a — b`, https://x.com/a—ё и <a title="x — ё">текст — тут</a>'
        out, _ = cp.house(src)
        self.assertEqual(out, 'Код `a — b`, https://x.com/a—ё и <a title="x — ё">текст - тут</a>')

    def test_html_head_and_pre_are_protected(self):
        src = ("<head><title>AI — всё</title></head><body><p>Тут — всё</p>"
               "<pre>Промпт — ещё</pre><code>a — ё</code></body>")
        out, _ = cp.house(src)
        self.assertEqual(out, "<head><title>AI — всё</title></head><body><p>Тут - все</p>"
                              "<pre>Промпт — ещё</pre><code>a — ё</code></body>")

    def test_cli_flag(self):
        r = subprocess.run([sys.executable, str(SCRIPTS / "clean_paste.py"), "-", "--alexey"],
                           input="Всё — просто.", capture_output=True, text=True)
        self.assertEqual((r.returncode, r.stdout), (1, "Все - просто."))


class ApplyEditsTest(unittest.TestCase):
    SRC = ("Personal AI OS — это рабочая среда, которая даёт AI постоянный контекст.\n\n"
           "Соберите контекст, который обычно приходится объяснять вручную. "
           "Это и есть реальное топливо системы.\n\n"
           "Курс идёт шесть недель. Новичкам подходит интенсив, интенсив простой.")

    def run_edits(self, edits, skip=frozenset()):
        parsed, errors = ae.parse(edits)
        self.assertEqual(errors, [])
        return ae.apply(self.SRC, parsed, skip)

    def test_untouched_text_stays_identical(self):
        new, applied, errors = self.run_edits(
            "@@ 9 концовка-мораль\n- Это и есть реальное топливо системы.\n+ С него система и работает.\n")
        self.assertEqual(errors, [])
        self.assertEqual(new, self.SRC.replace("Это и есть реальное топливо системы.", "С него система и работает."))

    def test_reason_is_required(self):
        _, errors = ae.parse("@@\n- Курс\n+ Курс!\n")
        self.assertTrue(any("без причины" in e for e in errors))

    def test_missing_and_ambiguous_quotes_write_nothing(self):
        new, applied, errors = self.run_edits("@@ 1\n- нет такой фразы\n+ x\n@@ 2\n- нтенсив\n+ x\n")
        self.assertEqual(new, self.SRC)
        self.assertEqual(applied, [])
        self.assertTrue(any("не найдена" in e for e in errors))
        self.assertTrue(any("встречается 2 раз" in e for e in errors))

    def test_replace_all_and_skip(self):
        new, applied, _ = self.run_edits("@@* термин\n- интенсив\n+ курс\n@@ 9\n- Курс идёт\n+ Курс длится\n",
                                         skip={2})
        self.assertIn("подходит курс, курс простой.", new)
        self.assertIn("Курс идёт", new)
        self.assertEqual([e.n for e in applied], [1])

    def test_tolerant_match_for_dash_yo_and_spaces(self):
        new, applied, errors = self.run_edits("@@ механика\n- Personal AI OS - это рабочая   среда, которая дает\n"
                                              "+ Personal OS - это рабочая среда, которая дает\n")
        self.assertEqual(errors, [])
        self.assertTrue(new.startswith("Personal OS - это рабочая среда, которая дает AI"))

    def test_overlap_is_refused(self):
        _, _, errors = self.run_edits("@@ 1\n- Курс идёт шесть\n+ Курс шесть\n@@ 2\n- идёт шесть недель\n+ идёт\n")
        self.assertTrue(any("задевают один фрагмент" in e for e in errors))

    def test_multiline_quote_and_deletion(self):
        new, _, errors = self.run_edits("@@ 11 метатекст\n- вручную. Это и есть реальное топливо системы.\n-\n- Курс\n"
                                        "+ вручную.\n+\n+ Курс\n")
        self.assertEqual(errors, [])
        self.assertNotIn("топливо", new)

    def test_cli_review_and_exit_codes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            src, ed, rv = Path(d) / "a.txt", Path(d) / "e.txt", Path(d) / "r.html"
            src.write_text(self.SRC, encoding="utf-8")
            ed.write_text("@@ 9 концовка\n- Это и есть реальное топливо системы.\n+ С него и работает.\n",
                          encoding="utf-8")
            run = lambda *x: subprocess.run([sys.executable, str(SCRIPTS / "apply_edits.py"), *x],
                                            capture_output=True, text=True)
            r = run(str(src), str(ed), "--review", str(rv))
            self.assertEqual(r.returncode, 0)
            self.assertIn("С него и работает.", r.stdout)
            self.assertIn("<del>", rv.read_text(encoding="utf-8"))
            ed.write_text("@@ 1 переписал все\n- " + self.SRC.replace("\n\n", "\n- \n- ").replace("- \n", "-\n")
                          + "\n+ Совсем другой текст про другое.\n", encoding="utf-8")
            self.assertEqual(run(str(src), str(ed)).returncode, 1)
            ed.write_text("@@ 1\n- нет такой\n+ x\n", encoding="utf-8")
            self.assertEqual(run(str(src), str(ed), "-o", str(Path(d) / "out.txt")).returncode, 2)
            self.assertFalse((Path(d) / "out.txt").exists())


class EditBudgetTest(unittest.TestCase):
    SRC = ("Модели нужен контекст: кто вы и над чем работаете.\n\n"
           "Соберите файл о себе и держите его рядом с промптами.\n\n"
           "Не автоматизируйте всё сразу, начните с одной задачи.")

    def test_identical_text_is_in_budget(self):
        r = eb.measure(self.SRC, self.SRC)
        self.assertEqual(r["kept"], 1.0)
        self.assertFalse(eb.over_budget(r))

    def test_mechanical_edit_is_in_budget(self):
        after = self.SRC.replace("всё", "все").replace(": кто", " - кто")
        self.assertFalse(eb.over_budget(eb.measure(self.SRC, after)))

    def test_deleted_paragraph_is_caught(self):
        after = "\n\n".join(self.SRC.split("\n\n")[:2])
        r = eb.measure(self.SRC, after)
        self.assertEqual(len(r["deleted"]), 1)
        self.assertTrue(eb.over_budget(r))

    def test_rewritten_paragraph_is_caught(self):
        parts = self.SRC.split("\n\n")
        parts[2] = "Я пробовал внедрять все автоматизации разом, это путь к выгоранию."
        r = eb.measure(self.SRC, "\n\n".join(parts))
        self.assertTrue(r["rewritten"] or r["deleted"])
        self.assertTrue(eb.over_budget(r))

    def test_cli_exit_codes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / "a.txt", Path(d) / "b.txt"
            a.write_text(self.SRC, encoding="utf-8")
            b.write_text(self.SRC, encoding="utf-8")
            run = lambda *x: subprocess.run([sys.executable, str(SCRIPTS / "edit_budget.py"), *x],
                                            capture_output=True, text=True).returncode
            self.assertEqual(run(str(a), str(b)), 0)
            b.write_text("Совсем другой текст.", encoding="utf-8")
            self.assertEqual(run(str(a), str(b)), 1)
            self.assertEqual(run(str(a), str(Path(d) / "nope.txt")), 2)


class CheckFactsEnglishTest(unittest.TestCase):
    SRC = ("Our app does not store your data. The trial lasts 30 days and costs $49 per month.\n\n"
           "We may launch the beta on March 5, 2026: about 30,000 users signed up.")

    def test_identical_text_is_clean(self):
        r = cf.compare(self.SRC, self.SRC)
        self.assertEqual((r["errors"], r["checks"], r["lang"]), ([], [], "en"))

    def test_language_detection(self):
        self.assertEqual(cf.detect_lang(self.SRC), "en")
        self.assertEqual(cf.detect_lang("Анна получила 30 000 рублей через Google Pay."), "ru")
        self.assertEqual(cf.detect_lang("Материалы курса AI Native и следующие потоки: ivanov.coach/ai, "
                                        "канал @ppprompt"), "ru")
        self.assertEqual(cf.detect_lang("Встреча в Zoom во вторник. Agenda: review the budget."), "ru+en")
        self.assertNotIn("lang", cf.compare("Цена 240 рублей.", "Цена 240 рублей."))

    def test_lost_number_with_unit(self):
        r = cf.compare(self.SRC, self.SRC.replace("30 days", "45 days"))
        self.assertEqual(kinds(r), ["added", "lost"])
        self.assertIn("30 days", [e["detail"] for e in r["errors"]])

    def test_unit_change_is_an_error(self):
        self.assertIn("unit", kinds(cf.compare("The route is 12 km long.", "The route is 12 miles long.")))
        self.assertIn("unit", kinds(cf.compare("It costs $30.", "It costs \u20ac30.")))

    def test_number_forms_are_normalised(self):
        same = [("30,000 users", "30k users"), ("30,000 users", "30 thousand users"),
                ("$3.5M in revenue", "$3.5 million in revenue"), ("twenty-five teams", "25 teams"),
                ("a dozen eggs", "12 eggs"), ("at 5 pm", "at 17:00"), ("50 percent", "50%")]
        for a, b in same:
            self.assertEqual(cf.compare(a, b)["errors"], [], (a, b))
        # "one" and "a" are not numbers on their own; "may" is a verb, not a month.
        self.assertEqual(cf.extract("One of us may go. A plan.", "en").of("number"), [])
        self.assertEqual(cf.extract("One of us may go. A plan.", "en").of("date"), [])

    def test_modality_may_to_will_is_a_check(self):
        r = cf.compare(self.SRC, self.SRC.replace("We may launch", "We will launch"))
        self.assertEqual(r["errors"], [])
        self.assertTrue(any(c["kind"] == "modality" and "may" in c["detail"] for c in r["checks"]))
        r = cf.compare("You should back up weekly.", "You must back up weekly.")
        self.assertTrue(any("should" in c["detail"] for c in r["checks"]))

    def test_lost_not_is_an_inverted_negation(self):
        r = cf.compare(self.SRC, self.SRC.replace("does not store", "stores"))
        self.assertIn("inverted", kinds(r))
        r = cf.compare("It isn\u2019t safe to share passwords.", "It is safe to share passwords.")
        self.assertIn("inverted", kinds(r))
        self.assertEqual(cf.compare("We never send spam.", "We don't send spam.")["errors"], [])

    def test_dates(self):
        r = cf.compare(self.SRC, self.SRC.replace("March 5", "March 12"))
        self.assertEqual(kinds(r), ["added", "lost"])
        self.assertEqual(cf.compare("We met on 5 March 2026.", "We met on March 5th, 2026.")["errors"], [])
        self.assertEqual(cf.compare("Due Mar. 5.", "Due on March 5.")["errors"], [])

    def test_hedge_and_names(self):
        r = cf.compare(self.SRC, self.SRC.replace("about 30,000", "30,000"))
        self.assertTrue(any(c["kind"] == "hedge" and "about" in c["detail"] for c in r["checks"]))
        self.assertIn("lost", kinds(cf.compare("Sarah joined Acme in 2024.", "She joined Acme in 2024.")))
        # Sentence starts, contractions and Title Case headings are not names.
        heading = "## Why This Matters For Teams\n\nThe tool doesn\u2019t sync. Teams lose time."
        self.assertEqual(cf.extract(heading, "en").of("name"), [])

    def test_lang_flag(self):
        tmp = ROOT / "tests" / "_tmp_cf_en"
        tmp.mkdir(exist_ok=True)
        try:
            (tmp / "a.txt").write_text("The trial lasts 30 days.", encoding="utf-8")
            (tmp / "b.txt").write_text("The trial lasts 45 days.", encoding="utf-8")
            run = lambda *x: subprocess.run([sys.executable, str(SCRIPTS / "check_facts.py"), *map(str, x)],
                                            capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(run(tmp / "a.txt", tmp / "b.txt").returncode, 1)
            self.assertIn("Язык сверки: английский.", run(tmp / "a.txt", tmp / "b.txt").stdout)
            self.assertEqual(run(tmp / "a.txt", tmp / "b.txt", "--lang", "en").returncode, 1)
            self.assertEqual(run(tmp / "a.txt", tmp / "a.txt", "--lang=ru").returncode, 0)
            self.assertEqual(run(tmp / "a.txt", tmp / "b.txt", "--lang", "de").returncode, 2)
        finally:
            for p in tmp.glob("*"):
                p.unlink()
            tmp.rmdir()


class EnglishHelpersTest(unittest.TestCase):
    def test_clean_paste_on_english_chat(self):
        src = ("Sure! Here is the post:\n\nTeams grow 20\u201330%.:contentReference[oaicite:0]{index=0} "
               "See https://ex.com/a?utm_source=chatgpt.com.\u200b\n\nI hope this helps!")
        text, counts = cp.clean(src)
        # Leftovers go, wording stays: assistant chatter is removed by the agent, not the script.
        self.assertEqual(text, "Sure! Here is the post:\n\nTeams grow 20\u201330%. See https://ex.com/a.\n\n"
                               "I hope this helps!")
        self.assertEqual(counts, {"contentReference": 1, "utm": 1, "invisible": 1})
        plain = "It\u2019s a \"well-known\" fact \u2014 don't panic."
        self.assertEqual(cp.clean(plain), (plain, {}))

    def test_house_style_on_english(self):
        out, _ = cp.house("In today\u2019s world\u2014a fast one\u2014we grow 20\u201330%.")
        self.assertEqual(out, "In today\u2019s world - a fast one - we grow 20-30%.")

    def test_edit_budget_counts_apostrophes_as_one_word(self):
        a = "We don't store data. It's safe and well-known."
        b = a.replace("'", "\u2019")
        self.assertEqual(eb.words(a), eb.words(b))
        self.assertEqual(len(eb.words(a)), 8)
        self.assertEqual(eb.measure(a, b)["kept"], 1.0)

    def test_apply_edits_tolerates_apostrophes(self):
        src = "We don\u2019t store your data \u2014 ever.\n\nIt\u2019s a fact."
        parsed, errors = ae.parse("@@ dash\n- don't store your data - ever\n+ don't store your data, ever\n")
        self.assertEqual(errors, [])
        new, applied, errors = ae.apply(src, parsed)
        self.assertEqual(errors, [])
        self.assertEqual(new, "We don't store your data, ever.\n\nIt\u2019s a fact.")


if __name__ == "__main__":
    unittest.main()

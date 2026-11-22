#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# START_MODULE_CONTRACT
# PURPOSE: Compare an original Russian or English text with its edited version and report facts
#          that were lost, invented or rebound: numbers, dates, times, names, URLs, quotes,
#          negations, hedges and "who got which number" pairs; flags certainty, scope,
#          condition and attribution words that got rarer and intensifiers that got more frequent;
#          HTML tags of the original that were lost (emphasis tags only as checks).
# SCOPE: heuristic, offline, stdlib only. Errors are likely real; "check" items need a human look.
#        An empty report does not prove the meaning is intact. Language of the lexicons comes from
#        the original: share of Cyrillic among letters >= 0.6 -> Russian, <= 0.2 -> English,
#        in between -> both (URLs, bare domains, @handles, e-mails, tags and code are not
#        counted). A Russian original gets exactly the Russian-only checks of the earlier
#        versions. The report is always in Russian. English rules: month names count only
#        capitalised ("may" is a verb, "May 5" a date); "one" and "a" are numbers only before
#        hundred/thousand/dozen; 30,000 = 30k = 30 thousand; $5M = 5 million dollars; 5 pm = 17:00;
#        "5.30" is a decimal, not a time; Title Case headings do not produce names.
# DEPENDS: Python 3.8+ standard library.
# LINKS: M-CHECK-FACTS; DF-SKILL-CHECK; V-M-CHECK-FACTS.
# END_MODULE_CONTRACT
# START_MODULE_MAP
# detect_lang: text -> "ru" | "en" | "ru+en".
# extract: (text, lang="auto") -> Facts (numbers with units, dates, urls, names, quotes, negations, hedges, sentences).
# compare: (before, after, lang="auto") -> {"errors": [...], "checks": [...]}; markup block counts HTML tags.
# _en_number_words: text -> [(start, end, value)] for "twenty-five", "a dozen", "three thousand".
# render: human-readable Russian report; adds "Язык сверки" when the language is not Russian.
# main: CLI `check_facts.py before.txt after.txt [--json] [--lang ru|en|auto]`;
#       exit 0 clean, 1 errors, 2 bad input.
# END_MODULE_MAP
"""Сверка фактов до и после правки.

    python check_facts.py до.txt после.txt            # отчёт по-русски
    python check_facts.py до.txt после.txt --json     # то же в JSON
    python check_facts.py - после.txt                 # исходник из stdin
    python check_facts.py до.txt после.txt --lang en  # язык словарей: ru, en или auto (по умолчанию)

auto: язык определяется по доле кириллицы среди букв исходника; смешанный текст
сверяется по обоим словарям. Отчёт всегда по-русски.
Код выхода: 0 — ошибок нет, 1 — есть ошибки, 2 — файл не читается или неверный флаг.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlsplit, urlunsplit

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

# START_BLOCK_LEXICON
SEP = " \u00a0\u202f"
UNIT_SYNONYMS = [
    (("%", "процент", "процента", "процентов", "процентам", "процентами"), "%"),
    (("₽", "р.", "руб.", "руб", "рубль", "рубля", "рублей", "рублю", "рублями", "рублях"), "₽"),
    (("$", "доллар", "доллара", "долларов"), "$"),
    (("€", "евро"), "€"),
    (("кг", "килограмм", "килограмма", "килограммов"), "кг"),
    (("г", "грамм", "грамма", "граммов"), "г"),
    (("км", "километр", "километра", "километров"), "км"),
    (("м", "метр", "метра", "метров"), "м"),
    (("кв. м", "кв.м", "м²", "квадратных метров", "квадратных метра"), "м²"),
    (("см", "сантиметр", "сантиметра", "сантиметров"), "см"),
    (("мм", "миллиметр", "миллиметра", "миллиметров"), "мм"),
    (("л", "литр", "литра", "литров"), "л"),
    (("мл", "миллилитр", "миллилитра", "миллилитров"), "мл"),
    (("шт", "штука", "штуки", "штук"), "шт"),
    (("ч", "час", "часа", "часов"), "ч"),
    (("мин", "минута", "минуты", "минут"), "мин"),
    (("мс", "миллисекунда", "миллисекунды", "миллисекунд"), "мс"),
    (("сек", "с", "секунда", "секунды", "секунд"), "с"),
    (("день", "дня", "дней", "дн"), "дн"),
    (("неделя", "недели", "недель", "нед"), "нед"),
    (("месяц", "месяца", "месяцев", "мес"), "мес"),
    (("год", "года", "лет"), "год"),
    (("человек", "человека", "чел"), "чел"),
    (("ГБ", "гигабайт", "гигабайта", "гигабайтов"), "ГБ"),
    (("МБ", "мегабайт", "мегабайта"), "МБ"),
    (("°C", "°С", "градус", "градуса", "градусов"), "°C"),
]
UNIT_CANON = {s.lower(): c for syns, c in UNIT_SYNONYMS for s in syns}
UNIT_RX = re.compile(r"[ \u00a0\u202f]?(%s)(?![0-9A-Za-zА-Яа-яЁё])" % "|".join(
    sorted((re.escape(u) for u in UNIT_CANON), key=len, reverse=True)), re.I)

WORD_NUM = {
    # "один/одна/одного" are left out on purpose: "одна из причин" is not a number.
    "ноль": 0, "два": 2, "две": 2, "двух": 2, "трое": 3, "двое": 2, "три": 3, "трех": 3,
    "четыре": 4, "четырех": 4, "четверо": 4, "пять": 5, "пяти": 5, "пятеро": 5, "шесть": 6,
    "шести": 6, "семь": 7, "семи": 7, "восемь": 8, "восьми": 8, "девять": 9, "девяти": 9,
    "десять": 10, "десяти": 10, "одиннадцать": 11, "двенадцать": 12, "пятнадцать": 15,
    "двадцать": 20, "двадцати": 20, "тридцать": 30, "тридцати": 30, "сорок": 40,
    "пятьдесят": 50, "шестьдесят": 60, "сто": 100, "двести": 200, "триста": 300,
    "полтора": 1.5, "полторы": 1.5, "половина": 0.5, "половину": 0.5,
}
SCALE = {"тыс": 1000, "тыс.": 1000, "тысяча": 1000, "тысячи": 1000, "тысяч": 1000,
         "млн": 10 ** 6, "млн.": 10 ** 6, "миллион": 10 ** 6, "миллиона": 10 ** 6,
         "миллионов": 10 ** 6, "млрд": 10 ** 9, "миллиард": 10 ** 9, "миллиарда": 10 ** 9,
         "миллиардов": 10 ** 9}
MONTHS = ("января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря|"
          "январе|феврале|марте|апреле|мае|июне|июле|августе|сентябре|октябре|ноябре|декабре|"
          "январь|февраль|март|апрель|май|июнь|июль|август|сентябрь|октябрь|ноябрь|декабрь")
MONTH_STEM = {m[:3]: i for i, m in enumerate(
    "янв фев мар апр мая июн июл авг сен окт ноя дек".split(), 1)}
MONTH_STEM["май"] = 5
WEEKDAYS = ("понедельник|вторник|сред|четверг|пятниц|суббот|воскресень")
HEDGES = ("около", "примерно", "приблизительно", "почти", "порядка", "до", "не более",
          "не менее", "более", "свыше", "менее", "больше", "меньше", "минимум", "максимум",
          "от", "не больше", "не меньше", "не позже", "не позднее", "не раньше", "после",
          "только", "лишь", "кроме", "без")
NEG_WORDS = ("не", "ни", "нет", "нельзя", "без")
# Words of certainty and scope: losing one turns "may" into "will", "some" into "sometimes".
MODALITY = [
    ("может", r"мо(?:жет|гут|жем|жете|гу|г|гла|гли|жно)"),
    ("возможно", r"возможн[оа]"),
    ("наверное", r"наверн(?:ое|яка)|вероятно|видимо|скорее всего|кажется"),
    ("план", r"(?:за)?планир\w*"),
    ("обычно", r"обычно"),
    ("иногда", r"иногда"),
    ("часто", r"часто"),
    ("редко", r"редко"),
    ("всегда", r"всегда"),
    ("никогда", r"никогда"),
    ("некоторые", r"некотор\w*"),
    ("многие", r"многи[ехм]\w*"),
    ("каждый", r"кажд\w+"),
    ("почти", r"почти"),
    ("риск", r"риск\w*|вероятност\w*"),
    ("один из", r"(?:один|одна|одно|одного|одной|одним|одну|одном) из"),
    ("только", r"только|лишь"),
    ("если", r"если|в случае|при условии"),
    ("по данным / по словам", r"по (?:данным|словам|оценк\w+|мнению)|согласно"),
]
# Words that make a claim stronger: a check when the edit has more of them than the original
# ("ключевой фактор" -> "главный фактор", "один из лучших" -> "лучший").
INTENSIFIERS = r"сам(?:ый|ая|ое|ые|ого|ой|ым|ых|ую|ом)|главн\w*|наиболее|лучш\w*|важнейш\w*|гарантирован\w*"
SENT_START_STOP = {"В", "На", "С", "И", "А", "Но", "Это", "Мы", "Вы", "Я", "Он", "Она",
                   "Они", "Если", "Когда", "Для", "По", "При", "От", "До", "За", "Из", "К",
                   "О", "У", "Как", "Что", "Так", "Все", "Всё", "Наш", "Наша", "Наши", "Ваш",
                   "Ваша", "Ваши", "Также", "Кроме", "Еще", "Ещё", "Уже", "Теперь", "Сейчас",
                   "Здравствуйте", "Привет", "Добрый", "Уважаемый", "Уважаемая", "Спасибо",
                   "С уважением"}
# "Вы" and "Ваш" written with a capital out of politeness are not names.
POLITE_PRONOUN = re.compile(r"Вы|Вас|Вам|Вами|Ваш(?:а|е|и|его|ему|ем|ей|у|ую|их|им|ими)?|"
                            r"Ты|Тебе|Тебя|Тобой|Твой|Тво(?:я|е|ё|и|его|ему|ем|ём|ей|ю|их|им|ими)")
# Tags inside a line of text; any other tag before a word starts a new block (<p>, <li>, </h3>).
INLINE_TAGS = {"a", "b", "strong", "i", "em", "mark", "u", "span", "code", "sup", "sub", "small", "s"}
# Frequent first names: a capitalised word at the start of a sentence is a name when it
# matches one of these (case endings allowed), otherwise only when it is capitalised elsewhere.
FIRST_NAMES = set("""Александр Александра Алексей Алина Алиса Алла Анастасия Анатолий Андрей Анна
Антон Арина Аркадий Арсений Артём Артем Борис Вадим Валентин Валентина Валерий Валерия Варвара
Василий Вера Вероника Виктор Виктория Виталий Владимир Владислав Вячеслав Галина Георгий Глеб
Григорий Дарья Денис Диана Дмитрий Евгений Евгения Егор Екатерина Елена Елизавета Иван Игорь
Илья Инна Ирина Карина Кирилл Константин Кристина Ксения Лариса Леонид Лидия Любовь Людмила
Максим Маргарита Марина Мария Марк Матвей Михаил Надежда Наталья Наталия Никита Николай Нина
Олег Ольга Павел Пётр Петр Полина Роман Руслан Светлана Семён Семен Сергей Софья Станислав
Степан Тамара Татьяна Тимофей Тимур Фёдор Федор Эдуард Юлия Юрий Яна Ярослав""".split())
# END_BLOCK_LEXICON

# START_BLOCK_LEXICON_EN
# Used only when the original is English or mixed; canonical units are shared with Russian.
UNIT_SYNONYMS_EN = [
    (("percent", "per cent", "pct"), "%"),
    (("dollar", "dollars", "usd", "bucks"), "$"),
    (("euro", "euros", "eur"), "€"),
    (("£", "gbp"), "£"),
    (("ruble", "rubles", "rouble", "roubles", "rub"), "₽"),
    (("kg", "kgs", "kilogram", "kilograms", "kilo", "kilos"), "кг"),
    (("gram", "grams"), "г"),
    (("lb", "lbs"), "lb"),
    (("km", "kilometer", "kilometers", "kilometre", "kilometres"), "км"),
    (("mi", "mile", "miles"), "mi"),
    (("m", "meter", "meters", "metre", "metres"), "м"),
    (("sq m", "square meters", "square metres"), "м²"),
    (("ft", "foot", "feet"), "ft"),
    (("cm", "centimeter", "centimeters", "centimetre", "centimetres"), "см"),
    (("mm", "millimeter", "millimeters", "millimetre", "millimetres"), "мм"),
    (("liter", "liters", "litre", "litres"), "л"),
    (("ml", "milliliter", "milliliters", "millilitre", "millilitres"), "мл"),
    (("pcs", "pieces"), "шт"),
    (("h", "hr", "hrs", "hour", "hours"), "ч"),
    (("min", "mins", "minute", "minutes"), "мин"),
    (("ms", "millisecond", "milliseconds"), "мс"),
    (("sec", "secs", "second", "seconds"), "с"),
    (("day", "days"), "дн"),
    (("wk", "wks", "week", "weeks"), "нед"),
    (("month", "months"), "мес"),
    (("yr", "yrs", "year", "years"), "год"),
    (("people", "person", "persons"), "чел"),
    (("gb", "gigabyte", "gigabytes"), "ГБ"),
    (("mb", "megabyte", "megabytes"), "МБ"),
    (("tb", "terabyte", "terabytes"), "ТБ"),
    (("kb", "kilobyte", "kilobytes"), "КБ"),
    (("°f", "fahrenheit"), "°F"),
    (("degree", "degrees"), "°C"),
    (("x", "times"), "×"),
]
UNIT_CANON_ALL = dict(UNIT_CANON)
UNIT_CANON_ALL.update({s.lower(): c for syns, c in UNIT_SYNONYMS_EN for s in syns})
UNIT_RX_ALL = re.compile(r"[   ]?(%s)(?![0-9A-Za-zА-Яа-яЁё])" % "|".join(
    sorted((re.escape(u) for u in UNIT_CANON_ALL), key=len, reverse=True)), re.I)
CURRENCY_PREFIX = {"$": "$", "€": "€", "£": "£", "₽": "₽"}
# Glued to the digits ("5k", "10GB", "3x", "5th", "1990s"): without this list "5k" is no number.
EN_ATTACHED = ("k|K|M|m|mn|bn|B|kg|km|cm|mm|ml|mi|ft|lb|lbs|h|hr|hrs|min|ms|sec|GB|MB|TB|KB|gb|mb|"
               "x|st|nd|rd|th|s")
# "5k", "$2M", "3bn" glued; words after a space. Bare "m" glued is a million ("5m users"),
# "5 m" with a space is metres.
EN_SCALE = {"k": 1e3, "K": 1e3, "M": 1e6, "m": 1e6, "mn": 1e6, "mln": 1e6, "bn": 1e9, "B": 1e9,
            "hundred": 100, "thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12}
EN_SCALE_RX = re.compile(r"(?:(k|K|M|m|mn|bn|B)|[   ]+(hundred|thousand|million|billion|"
                         r"trillion|mln|mn|bn))(?![A-Za-z])")
# "one" and "a" are numbers only before hundred/thousand/dozen: "one of the reasons" is not a number.
EN_SMALL = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
            "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
            "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
            "nineteen": 19}
EN_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
           "eighty": 80, "ninety": 90}
EN_BIG = {"thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12}
EN_MONTHS = ("January|February|March|April|May|June|July|August|September|October|November|"
             "December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec")
EN_MONTH_NUM = {m: i for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}
EN_WEEKDAYS = "Monday Tuesday Wednesday Thursday Friday Saturday Sunday".split()
HEDGES_EN = ("about", "around", "approximately", "roughly", "nearly", "almost", "up to",
             "at least", "at most", "more than", "less than", "fewer than", "no more than",
             "no less than", "over", "under", "only", "just", "except", "without",
             "no later than", "no earlier than", "before", "after", "within", "until", "from")
NEG_WORDS_EN = ("not", "no", "never", "nor", "without", "cannot", "none", "nobody", "nothing",
                "nowhere", "neither")
NEG_ALONE_EN = ("none", "nobody", "nothing", "nowhere", "neither")
NEG_RX_EN = re.compile(r"(?<![a-z'])(not|never|no|nor|without|cannot|[a-z]+n't)\s+"
                       r"(?:(?:a|an|the|be|been|to|any)\s+)?([a-z]{3,})|"
                       r"(?<![a-z'])(none|nobody|nothing|nowhere|neither)(?![a-z'])")
NEG_AFTER_RX_EN = re.compile(r"(?<![a-z'])(?:not|never|no|nor|without|cannot|[a-z]+n't|none|nobody|"
                             r"nothing)\s+(?:[a-z']+\s+){0,2}([a-z]{3,})")
# "not just X, but Y", "no longer", "no later than": the word after the negation is not the fact.
NEG_SKIP_EN = ("only", "just", "merely", "simply", "less", "more", "later", "earlier", "longer",
               "very", "too", "quite", "really", "even", "always", "necessarily")
MODALITY_EN = [
    ("may / might", r"(?-i:may)|might"),
    ("can / could", r"can(?:not|'t)?|could(?:n't)?"),
    ("possibly / perhaps", r"possibl[ey]|perhaps|maybe"),
    ("probably / likely", r"probabl[ey]|(?:un)?likely|apparently|presumably|seems?|seemed"),
    ("plan / planned", r"plan(?:s|ned)? to|planned|planning to|scheduled|expected to|intend(?:s|ed)? to"),
    ("usually", r"usually|typically|generally|normally"),
    ("often", r"often|frequently"),
    ("sometimes", r"sometimes|occasionally"),
    ("rarely", r"rarely|seldom"),
    ("always", r"always"),
    ("never", r"never"),
    ("some", r"some|several"),
    ("many", r"many"),
    ("each / every", r"each|every"),
    ("almost", r"almost|nearly"),
    ("risk", r"risks?|risky|chance|likelihood"),
    ("one of", r"one of"),
    ("only", r"only|just|merely"),
    ("if", r"if|unless|in case|provided that|as long as"),
    ("should", r"should(?:n't)?|ought to"),
    ("according to", r"according to|reportedly|estimated|estimates?"),
]
INTENSIFIERS_EN = (r"most|best|key|main|primary|biggest|greatest|crucial|critical|essential|vital|"
                   r"guarantee[ds]?|always|must|definitely|certainly|undoubtedly|proven|ultimate|perfect")
SENT_START_STOP_EN = set("""The A An This That These Those It Its We You Your Our They Their He She His
Her In On At For With By From To Of And But Or So If When While As How What Why Where Who Here There
Hello Hi Dear Thanks Thank Regards Also Now Today Yes No Not Just Then Once After Before Every Each
All Some Many Most Let Please Note Certainly Sure Absolutely""".split())
FIRST_NAMES_EN = set("""James John Robert Michael William David Richard Joseph Thomas Charles Daniel
Matthew Anthony Andrew Joshua Kevin Brian George Edward Ronald Timothy Jason Jeffrey Ryan Jacob Gary
Nicholas Eric Jonathan Stephen Steven Larry Justin Scott Brandon Benjamin Samuel Gregory Alexander
Patrick Jack Dennis Tyler Aaron Adam Nathan Henry Peter Zachary Kyle Noah Ethan Liam Lucas Oliver
Mary Patricia Jennifer Linda Elizabeth Barbara Susan Jessica Sarah Karen Lisa Nancy Betty Sandra
Ashley Kimberly Emily Donna Michelle Carol Amanda Melissa Deborah Stephanie Rebecca Sharon Laura
Cynthia Kathleen Amy Angela Anna Helen Emma Olivia Sophia Mia Isabella Charlotte Amelia Hannah Megan
Rachel Julia Alice Kate Katherine Catherine Victoria Natalie Alex Chris Mike Tom Tim Nick Ben Dan
Sam Max Paul Mark Maria Elena Anne""".split()) | set(EN_WEEKDAYS) | set(
    "January February March April June July August September October November December".split())
# END_BLOCK_LEXICON_EN


def _norm(s: str) -> str:
    return s.replace("ё", "е").replace("Ё", "Е")


def _low_en(s: str) -> str:
    """Lower case with typographic apostrophes made straight (don’t -> don't), same length."""
    return s.lower().replace("’", "'").replace("‘", "'")


LANGS = {"ru": ("ru",), "en": ("en",), "ru+en": ("ru", "en")}


# START_CONTRACT: detect_lang
# PURPOSE: Pick the lexicons for a text by the share of Cyrillic among its letters.
# INPUTS: text (str).
# OUTPUTS: "ru" (share >= 0.6 or no letters), "en" (share <= 0.2) or "ru+en".
# SIDE_EFFECTS: none.
# END_CONTRACT: detect_lang
def detect_lang(text: str) -> str:
    # Links, bare domains, @handles, tags, code and entities say nothing about the language of the prose.
    t = re.sub(r"(?:https?://|www\.)\S+|[\w.+-]+@[\w.-]+\.\w+|<[^<>\n]*>|`[^`\n]*`|^```.*$|&#?\w+;"
               r"|:contentReference\[[^\]]*\]\{[^}]*\}|\b[\w-]+(?:\.[\w-]+)*\.[a-z]{2,}/\S*|@\w+",
               " ", text, flags=re.M)
    cyr = len(re.findall(r"[А-Яа-яЁё]", t))
    lat = len(re.findall(r"[A-Za-z]", t))
    if not cyr + lat:
        return "ru"
    share = cyr / (cyr + lat)
    return "ru" if share >= 0.6 else ("en" if share <= 0.2 else "ru+en")


def _resolve_lang(lang, source: str) -> Tuple[str, ...]:
    if isinstance(lang, (tuple, list)):
        return tuple(lang)
    if lang in (None, "auto"):
        lang = detect_lang(source)
    return LANGS[lang]


def stem_match(a: str, b: str, strict: bool = False) -> bool:
    """Russian case endings: words match when they share all but the last 2 letters (>= 3).
    strict (for verbs and common words): the shared part is also >= 4 letters and >= 60%
    of the longer word, so "перегружал" does not match "перед"."""
    a, b = _norm(a.lower()), _norm(b.lower())
    if a == b:
        return True
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    if strict:
        return n >= max(4, min(len(a), len(b)) - 2) and n >= 0.6 * max(len(a), len(b))
    return n >= 3 and n >= min(len(a), len(b)) - 2


@dataclass
class Fact:
    kind: str
    value: str
    raw: str
    sent: int
    pos: int
    hedge: str = ""
    unit: str = ""


@dataclass
class Facts:
    items: List[Fact] = field(default_factory=list)
    sentences: List[str] = field(default_factory=list)

    def of(self, kind: str) -> List[Fact]:
        return [f for f in self.items if f.kind == kind]


def split_sentences(text: str) -> List[Tuple[int, str]]:
    out, start = [], 0
    for m in re.finditer(r"(?<=[.!?…])\s+(?=[«\"(A-ZА-ЯЁ0-9])|\n+", text):
        out.append((start, text[start:m.start()]))
        start = m.end()
    out.append((start, text[start:]))
    return [(s, t) for s, t in out if t.strip()]


def _canon_num(raw: str, en: bool = False) -> Optional[float]:
    s = re.sub("[%s]" % SEP, "", raw)
    if en and re.search(r"\d,\d{3}(?!\d)", s):
        s = s.replace(",", "")  # English thousands: 30,000 and 1,234.5
    s = s.replace(",", ".").lstrip("+")
    s = s.replace("−", "-")
    try:
        return float(s)
    except ValueError:
        return None


def _fmt(v: float) -> str:
    return str(int(v)) if v == int(v) else ("%g" % v)


# START_CONTRACT: extract
# PURPOSE: Pull checkable facts out of one text.
# INPUTS: text (str); lang ("auto" by the text itself, "ru", "en", "ru+en" or a tuple of codes).
# OUTPUTS: Facts with numbers (value, unit, hedge), dates, times, urls, emails, names,
#          quotes, negations; plus the sentence list used for bindings.
# SIDE_EFFECTS: none.
# END_CONTRACT: extract
def extract(text: str, lang="auto") -> Facts:
    langs = _resolve_lang(lang, text)
    ru, en = "ru" in langs, "en" in langs
    text = _strip_tracking(text)
    facts = Facts()
    sents = split_sentences(text)
    facts.sentences = [t for _, t in sents]
    taken: List[Tuple[int, int]] = []
    hedges = sorted((HEDGES if ru else ()) + (HEDGES_EN if en else ()), key=len, reverse=True)

    def sent_of(pos: int) -> int:
        idx = 0
        for i, (s, _) in enumerate(sents):
            if s <= pos:
                idx = i
        return idx

    def free(a: int, b: int) -> bool:
        return all(b <= s or a >= e for s, e in taken)

    def hedge_before(pos: int) -> str:
        left = _norm(text[max(0, pos - 24):pos].lower())
        for h in hedges:
            if re.search(r"(?:^|[^а-яa-z])%s[   ]*$" % re.escape(_norm(h)), left):
                return h
        return ""

    # START_BLOCK_URLS
    for m in re.finditer(r"(?:https?://|www\.)[^\s<>«»\"')\]]+", text):
        url = m.group().rstrip(".,;:!?")
        facts.items.append(Fact("url", url.lower(), url, sent_of(m.start()), m.start()))
        taken.append((m.start(), m.start() + len(url)))
    for m in re.finditer(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text):
        if free(m.start(), m.end()):
            facts.items.append(Fact("email", m.group().lower(), m.group(), sent_of(m.start()), m.start()))
            taken.append((m.start(), m.end()))
    # END_BLOCK_URLS

    # START_BLOCK_DATES_TIMES
    def add_date(m: "re.Match", days, month: int, year: Optional[str]) -> None:
        for day in days:
            facts.items.append(Fact("date", "%02d.%02d" % (int(day), month), m.group(),
                                    sent_of(m.start()), m.start(), hedge_before(m.start())))
        if year:
            facts.items.append(Fact("number", year, year, sent_of(m.start()), m.start()))
        taken.append((m.start(), m.end()))

    # Day and month stand on one line: "Вариант 3\n\nНоябрь — ..." is not the 3rd of November.
    if ru:
        date_rx = re.compile(r"\b(\d{1,2})(?:[ \t ]*(?:[–—-]|,|и)[ \t ]*(\d{1,2}))?[ \t ]+(%s)(?:[ \t ]+(\d{4}))?" % MONTHS, re.I)
        for m in date_rx.finditer(text):
            add_date(m, filter(None, (m.group(1), m.group(2))),
                     MONTH_STEM.get(m.group(3).lower()[:3], 0), m.group(4))
    if en:
        # "March 5", "March 5th, 2026", "Mar. 5-6", "5 March 2026", "5th of March". Month names are
        # matched with a capital only, so the verb "may" and "march" are not months.
        day = r"(\d{1,2})(?:st|nd|rd|th)?(?![\d:.,]\d)"
        rng = r"(?:[ \t]*(?:[–—-]|and|&)[ \t]*(\d{1,2})(?:st|nd|rd|th)?(?![\d:]))?"
        year = r"(?:,?[ \t]+(\d{4}))?(?!\d)"
        md_rx = re.compile(r"\b(%s)(?![a-z])\.?[ \t ]+%s%s%s" % (EN_MONTHS, day, rng, year))
        dm_rx = re.compile(r"\b%s%s[ \t ]+(?:of[ \t]+)?(%s)(?![a-z])\.?%s" % (day, rng, EN_MONTHS, year))
        for rx, mi, di in ((md_rx, 1, (2, 3)), (dm_rx, 3, (1, 2))):
            for m in rx.finditer(text):
                days = [d for d in (m.group(di[0]), m.group(di[1])) if d]
                if not free(m.start(), m.end()) or not all(1 <= int(d) <= 31 for d in days):
                    continue
                add_date(m, days, EN_MONTH_NUM[m.group(mi)[:3].lower()], m.group(4))
    for m in re.finditer(r"\b(\d{1,2})\.(\d{1,2})\.(\d{2,4})\b", text):
        if free(m.start(), m.end()):
            facts.items.append(Fact("date", "%02d.%02d" % (int(m.group(1)), int(m.group(2))),
                                    m.group(), sent_of(m.start()), m.start()))
            # The year is kept as a number, the same way as in "1 февраля 2026".
            year = m.group(3) if len(m.group(3)) == 4 else "20" + m.group(3)
            facts.items.append(Fact("number", year, m.group(3), sent_of(m.start()), m.start()))
            taken.append((m.start(), m.end()))

    def add_time(m: "re.Match", hh: int, mm: str) -> None:
        value = str(hh) if mm == "00" else "%d:%s" % (hh, mm)
        facts.items.append(Fact("number", value, m.group(), sent_of(m.start()), m.start(),
                                hedge_before(m.start()), "время"))
        taken.append((m.start(), m.end()))

    if en:
        # "5 pm" and "5:30 p.m." are 17 and 17:30, the same as "17:00" and "17:30".
        for m in re.finditer(r"\b(1[0-2]|0?[1-9])(?::([0-5]\d))?[ \t ]?([AaPp])(?:\.[Mm]\.|[Mm])(?![A-Za-z])", text):
            if free(m.start(), m.end()):
                hh = int(m.group(1)) % 12 + (12 if m.group(3) in "Pp" else 0)
                add_time(m, hh, m.group(2) or "00")
    # "5.30" is a time in Russian and a decimal in English.
    time_rx = r"\b([01]?\d|2[0-3])%s([0-5]\d)\b(?![.,]\d)" % ("[:.]" if ru else ":")
    for m in re.finditer(time_rx, text):
        if free(m.start(), m.end()):
            add_time(m, int(m.group(1)), m.group(2))
    # END_BLOCK_DATES_TIMES

    # START_BLOCK_NUMBERS
    # Counters in headings ("Вариант 1", "Шаг 2", "Step 3") are structure, not facts.
    for m in re.finditer(r"(?i)(?:вариант|шаг|этап|пункт|раздел|часть|глава)\s+(\d+)", text):
        taken.append((m.start(1), m.end(1)))
    if en:
        for m in re.finditer(r"(?i)\b(?:step|option|part|chapter|section|phase|stage|tip|lesson|module|"
                             r"variant)\s+(\d+)\b", text):
            taken.append((m.start(1), m.end(1)))
    if en:
        num_rx = re.compile(r"(?<![\w.,])[+\-−]?\d+(?:,\d{3}(?!\d))*(?:[%s]\d{3})*(?:[.,]\d+)?"
                            r"(?:(?![\w])|(?=(?:%s)(?![\w])))" % (SEP, EN_ATTACHED))
    else:
        num_rx = re.compile(r"(?<![\w.,])[+\-−]?\d+(?:[%s]\d{3})*(?:[.,]\d+)?(?![\w])" % SEP)
    ru_scale = r"[   ]+(%s)(?![а-я])" % "|".join(re.escape(k) for k in SCALE)
    unit_rx, unit_canon = (UNIT_RX_ALL, UNIT_CANON_ALL) if en else (UNIT_RX, UNIT_CANON)
    for m in num_rx.finditer(text):
        if not free(m.start(), m.end()):
            continue
        v = _canon_num(m.group(), en)
        if v is None:
            continue
        start, end, unit = m.start(), m.end(), ""
        if en and start and text[start - 1] in CURRENCY_PREFIX:  # "$30", "€5M"
            start -= 1
            unit = CURRENCY_PREFIX[text[start]]
        ordinal = en and re.match(r"(?:st|nd|rd|th|s)(?![\w])", text[end:end + 3])
        if ordinal:  # "5th", "1990s"
            end += ordinal.end()
        else:
            sc = re.match(ru_scale, text[end:end + 12], re.I) if ru else None
            if sc:
                v *= SCALE[sc.group(1).lower()]
                end += sc.end()
            elif en:
                sc = EN_SCALE_RX.match(text, end)
                if sc:
                    v *= EN_SCALE[sc.group(1) or sc.group(2)]
                    end = sc.end()
            um = unit_rx.match(text, end)
            if um:
                unit = unit or unit_canon.get(um.group(1).lower(), "")
                end = um.end()
        facts.items.append(Fact("number", _fmt(v), text[start:end], sent_of(start),
                                start, hedge_before(start), unit))
        taken.append((start, end))
    word_rx = re.compile(r"(?<![а-яё])(%s)(?![а-яё])" % "|".join(
        sorted(WORD_NUM, key=len, reverse=True)), re.I)
    norm_text = _norm(text)
    for m in (word_rx.finditer(norm_text) if ru else ()):
        if not free(m.start(), m.end()):
            continue
        v = float(WORD_NUM[m.group(1).lower()])
        end = m.end()
        # "двадцать пять", "сто двадцать" are one number: each next word is a smaller order.
        while True:
            nxt = re.match(r"[  ]+(%s)(?![а-яё])" % "|".join(sorted(WORD_NUM, key=len, reverse=True)),
                           norm_text[end:end + 20], re.I)
            if not nxt:
                break
            w = float(WORD_NUM[nxt.group(1).lower()])
            last_order = 100 if v % 100 == 0 and v >= 100 else (10 if v % 10 == 0 and v >= 20 else 1)
            if last_order == 1 or w >= last_order or w != int(w):
                break
            v += w
            end += nxt.end()
        sc = re.match(r"[   ]+(%s)(?![а-я])" % "|".join(re.escape(k) for k in SCALE), text[end:end + 12], re.I)
        if sc:
            v *= SCALE[sc.group(1).lower()]
            end += sc.end()
        facts.items.append(Fact("number", _fmt(v), text[m.start():end], sent_of(m.start()),
                                m.start(), hedge_before(m.start())))
        taken.append((m.start(), end))
    if en:
        for start, end, v in _en_number_words(text):
            if free(start, end):
                facts.items.append(Fact("number", _fmt(v), text[start:end], sent_of(start),
                                        start, hedge_before(start)))
                taken.append((start, end))
    # END_BLOCK_NUMBERS

    # START_BLOCK_NAMES_QUOTES
    for m in re.finditer(r"«([^»\n]{1,80})»|\"([^\"\n]{1,80})\"", text):
        q = (m.group(1) or m.group(2)).strip()
        facts.items.append(Fact("quote", q.lower(), q, sent_of(m.start()), m.start()))
    for s_start, sent in sents:
        for m in re.finditer(r"(?<![\w-])([A-ZА-ЯЁ][\w-]*[a-zа-яё][\w-]*|[A-Z]{2,}[\w-]*)", sent):
            word = m.group(1)
            pos = s_start + m.start()
            latin = en and word[0] in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            if latin and (word in SENT_START_STOP_EN or
                          re.match(r"['’](?:t|re|ve|ll|m|d)\b", text[pos + len(word):pos + len(word) + 3])):
                continue  # "The", "Don't", "Isn't" are not names
            first = _is_initial(text, s_start + m.start())
            if word in SENT_START_STOP or POLITE_PRONOUN.fullmatch(word):
                continue
            # A Title Case heading ("Why This Matters") capitalises every word: like a sentence start.
            first = first or (latin and _title_line(text, pos))
            known = (word in FIRST_NAMES_EN) if latin else \
                any(len(word) <= len(n) + 3 and stem_match(word, n) for n in FIRST_NAMES)
            if first and not (_capitalized_elsewhere(word, text, pos, latin) or known):
                # Sentence subject in capitals ("Капучино дорожает"): kept only as an anchor
                # for "who got which number", not as a name that must survive.
                facts.items.append(Fact("subject", word, word, sent_of(pos), pos))
                continue
            facts.items.append(Fact("name", word, word, sent_of(pos), pos))
    # END_BLOCK_NAMES_QUOTES

    # START_BLOCK_NEGATIONS
    for m in (re.finditer(r"(?<![а-яё])(не|ни|без)\s+([а-яё]{3,})|(?<![а-яё])(нет|нельзя)(?![а-яё])", _norm(text.lower()))
              if ru else ()):
        if m.group(1):
            facts.items.append(Fact("negation", m.group(2), m.group(), sent_of(m.start()), m.start(),
                                    hedge=m.group(1)))
        else:
            facts.items.append(Fact("negation", m.group(3), m.group(), sent_of(m.start()), m.start(),
                                    hedge=m.group(3)))
    if en:
        for m in NEG_RX_EN.finditer(_low_en(text)):
            if m.group(1):
                facts.items.append(Fact("negation", m.group(2), m.group(), sent_of(m.start()), m.start(),
                                        hedge=m.group(1)))
            else:
                facts.items.append(Fact("negation", m.group(3), m.group(), sent_of(m.start()), m.start(),
                                        hedge=m.group(3)))
    # END_BLOCK_NEGATIONS
    return facts


def _en_number_words(text: str) -> List[Tuple[int, int, float]]:
    """English number words: "twenty-five", "two hundred and five", "three thousand", "a dozen",
    "half". "one" and "a" count only before hundred/thousand/dozen ("one of us" is no number)."""
    toks = [(m.start(), m.end(), m.group().lower()) for m in re.finditer(r"[A-Za-z]+", text)]
    out: List[Tuple[int, int, float]] = []

    def joined(i: int) -> bool:  # the next token follows after spaces or one hyphen only
        return i + 1 < len(toks) and re.fullmatch(r"[  ]+|-", text[toks[i][1]:toks[i + 1][0]]) is not None

    def starts_ok(i: int) -> bool:  # not the tail of "o'clock" or "well-two"
        s = toks[i][0]
        return not (s and text[s - 1] in "'\u2019-")

    def ends_ok(i: int) -> bool:  # not the head of "twenty-something" or "two's"
        return not re.match(r"['\u2019-]?[A-Za-z]", text[toks[i][1]:toks[i][1] + 2])

    mult = ("hundred", "dozen") + tuple(EN_BIG)
    i = 0
    while i < len(toks):
        s, e, w = toks[i]
        nxt = toks[i + 1][2] if joined(i) else ""
        if not starts_ok(i) or not (w in EN_SMALL or w in EN_TENS or w == "half" or
                                  (w in ("a", "an") and nxt in mult)):
            i += 1
            continue
        if w == "one" and nxt not in mult:
            i += 1
            continue
        if w == "half" and ends_ok(i):
            out.append((s, e, 0.5))
            i += 1
            continue
        total, cur, j = 0.0, float(EN_SMALL.get(w, EN_TENS.get(w, 1))), i
        while joined(j):
            t = toks[j + 1][2]
            prev = toks[j][2]
            if prev in EN_TENS and t in EN_SMALL and 0 < EN_SMALL[t] < 10:
                cur += EN_SMALL[t]
            elif t == "hundred" and cur < 100:
                cur *= 100
            elif t == "dozen" and cur < 100:
                cur *= 12
            elif t in EN_BIG and cur:
                total += cur * EN_BIG[t]
                cur = 0.0
            elif t == "and" and prev in mult and j + 2 < len(toks) and joined(j + 1) and \
                    (toks[j + 2][2] in EN_SMALL or toks[j + 2][2] in EN_TENS):
                j += 1
                continue
            elif (prev in mult or prev == "and") and (t in EN_TENS or (t in EN_SMALL and t != "zero")):
                cur += EN_SMALL.get(t, EN_TENS.get(t, 0))
            else:
                break
            j += 1
        if ends_ok(j):
            out.append((s, toks[j][1], total + cur))
        i = j + 1
    return out


def _title_line(text: str, pos: int) -> bool:
    """A short line without a final period whose long words are almost all capitalised."""
    a = text.rfind("\n", 0, pos) + 1
    b = text.find("\n", pos)
    line = re.sub(r"<[^<>]*>", " ", text[a:b if b != -1 else len(text)]).strip()
    if len(line) > 90 or line.endswith((".", "!", "?")):
        return False
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'’-]*", line) if len(w) >= 4]
    return len(words) >= 2 and sum(w[0].isupper() for w in words) >= 0.8 * len(words)


def _occurrences(text: str, word: str, en: bool = False) -> List[Tuple[int, int]]:
    if en:
        return [(m.start(), m.end()) for m in re.finditer(r"(?<![a-z'])[a-z]{3,}(?![a-z'])", text)
                if _en_same(m.group(), word)]
    return [(m.start(), m.end()) for m in re.finditer(r"[а-яё]{3,}", text) if stem_match(m.group(), word, strict=True)]


def _en_same(a: str, b: str) -> bool:
    """English word forms: store / stores / stored / storing are one word."""
    def stem(w: str) -> str:
        for suf in ("ing", "ed", "es", "s"):
            if w.endswith(suf) and len(w) - len(suf) >= 3:
                return w[:-len(suf)].rstrip("e")
        return w.rstrip("e")
    return a == b or stem(a) == stem(b)


def _negated_near(text: str, start: int, end: int, en: bool = False) -> bool:
    """A negation within 3 words before or 4 words after, inside the same sentence."""
    s_from = max(text.rfind(c, 0, start) for c in ".!?\n") + 1
    stops = [i for i in (text.find(c, end) for c in ".!?\n") if i != -1]
    s_to = min(stops) if stops else len(text)
    left = text[s_from:start].split()[-3:]
    right = text[end:s_to].split()[:4]
    if en:
        words = [re.sub(r"[^a-z']", "", w) for w in left + right]
        return any(w in NEG_WORDS_EN or w.endswith("n't") for w in words)
    return any(re.sub(r"[^а-яё]", "", w) in NEG_WORDS for w in left + right)


def _is_initial(text: str, pos: int) -> bool:
    """True when only markup, list markers, emoji or spaces stand between the word and the
    start of a line or the end of the previous sentence. A block tag (<p>, <li>, </h3>) starts
    a new line; an inline one (<b>, <a href>) is skipped."""
    i = pos - 1
    while i >= 0:
        ch = text[i]
        if ch == "\n" or ch in ".!?…:":
            return True
        if ch == ">":
            tag = re.match(r"</?([a-zA-Z][a-zA-Z0-9]*)[^<>]*>$", text[text.rfind("<", 0, i):i + 1])
            if tag:
                if tag.group(1).lower() not in INLINE_TAGS:
                    return True
                i = text.rfind("<", 0, i) - 1
                continue
        if ch.isalnum() and not (ch.isdigit() and re.match(r"\d+[.)]", text[i:pos].lstrip())):
            return False
        if ch.isalpha():
            return False
        i -= 1
    return True


def _capitalized_elsewhere(word: str, text: str, pos: int, title: bool = False) -> bool:
    """title: an English word; its capital in a Title Case heading does not count."""
    for m in re.finditer(r"(?<![\w-])" + re.escape(word[:max(3, len(word) - 2)]), text):
        if m.start() == pos:
            continue
        if text[m.start()].isupper() and not _is_initial(text, m.start()) and \
                not (title and _title_line(text, m.start())):
            return True
    return False


def strip_utm(url: str) -> Tuple[str, int]:
    """Drop utm_* query parameters, keep the others, the '?' and the fragment."""
    parts = urlsplit(url)
    if not parts.query:
        return url, 0
    params = parts.query.split("&")
    kept = [x for x in params if not x.lower().startswith("utm_")]
    if len(kept) == len(params):
        return url, 0
    return urlunsplit(parts._replace(query="&".join(kept))), len(params) - len(kept)


def _strip_tracking(text: str) -> str:
    def fix(m: "re.Match") -> str:
        url = m.group(0)
        tail = re.search(r"[.,;:!?]*$", url).group()
        return strip_utm(url[:len(url) - len(tail)])[0] + tail
    text = re.sub(r"https?://[^\s<>«»\"')\]]+", fix, text)
    return re.sub(r":contentReference\[oaicite:\d+\]\{index=\d+\}|【\d+(?::\d+)?†[^】]*】", "", text)



# START_CONTRACT: compare
# PURPOSE: Find lost, invented, re-bound or inverted facts between two versions.
# INPUTS: before, after (str); lang ("auto" picks it by the original, or "ru", "en", "ru+en").
# OUTPUTS: {"errors": [ {kind, what, detail} ], "checks": [...], "counts": {...}};
#          plus "lang" when it is not Russian only.
# SIDE_EFFECTS: none.
# END_CONTRACT: compare
def compare(before: str, after: str, lang="auto") -> Dict:
    langs = _resolve_lang(lang, before)
    ru, en = "ru" in langs, "en" in langs
    fb, fa = extract(before, langs), extract(after, langs)
    errors: List[Dict] = []
    checks: List[Dict] = []

    # START_BLOCK_NUMBERS_DIFF
    def bag(facts: Facts, kind: str) -> Dict[str, List[Fact]]:
        d: Dict[str, List[Fact]] = {}
        for f in facts.of(kind):
            d.setdefault(f.value, []).append(f)
        return d

    for kind, label in (("number", "число"), ("date", "дата")):
        bb, ba = bag(fb, kind), bag(fa, kind)
        for value, items in bb.items():
            missing = len(items) - len(ba.get(value, []))
            if missing > 0 and value not in ba:
                errors.append({"kind": "lost", "what": label, "detail": items[0].raw})
            elif missing > 0:
                checks.append({"kind": "fewer", "what": label,
                               "detail": "%s встречается реже (%d → %d)" % (items[0].raw, len(items), len(ba[value]))})
        for value, items in ba.items():
            if value not in bb:
                errors.append({"kind": "added", "what": label, "detail": items[0].raw})
        # units and hedges for numbers present in both
        if kind == "number":
            for value, items in bb.items():
                if value not in ba:
                    continue
                units_b = {f.unit for f in items if f.unit}
                units_a = {f.unit for f in ba[value] if f.unit}
                if units_b and units_a and not (units_b & units_a):
                    errors.append({"kind": "unit", "what": "единица",
                                   "detail": "%s → %s" % (items[0].raw, ba[value][0].raw)})
                hedges_b = {f.hedge for f in items if f.hedge}
                hedges_a = {f.hedge for f in ba[value] if f.hedge}
                for h in hedges_b - hedges_a:
                    checks.append({"kind": "hedge", "what": "оговорка",
                                   "detail": "«%s» перед %s не найдено" % (h, items[0].raw)})
    # END_BLOCK_NUMBERS_DIFF

    # START_BLOCK_NAMES_DIFF
    after_words = re.findall(r"[\w-]+", after)
    seen = set()
    for f in fb.of("name"):
        key = _norm(f.value.lower())[:5]
        if key in seen:
            continue
        seen.add(key)
        if not any(stem_match(f.value, w) for w in after_words):
            errors.append({"kind": "lost", "what": "имя или название", "detail": f.raw})
    before_words = re.findall(r"[\w-]+", before)
    seen = set()
    for f in fa.of("name"):
        key = _norm(f.value.lower())[:5]
        if key in seen:
            continue
        seen.add(key)
        if not any(stem_match(f.value, w) for w in before_words):
            checks.append({"kind": "added", "what": "имя или название", "detail": f.raw})
    for kind, label in (("url", "ссылка"), ("email", "почта")):
        vb = {f.value for f in fb.of(kind)}
        va = {f.value for f in fa.of(kind)}
        for v in sorted(vb - va):
            errors.append({"kind": "lost", "what": label, "detail": v})
        for v in sorted(va - vb):
            errors.append({"kind": "added", "what": label, "detail": v})
    # END_BLOCK_NAMES_DIFF

    # START_BLOCK_NEGATIONS_DIFF
    after_norm = _norm(after.lower())
    before_norm = _norm(before.lower())
    after_low, before_low = _low_en(after), _low_en(before)
    for f in fb.of("negation"):
        if re.match(r"[a-z]", f.value):
            _negation_en(f, fb, fa, before_low, after_low, errors, checks)
            continue
        if f.hedge in ("нет", "нельзя"):
            if not re.search(r"(?<![а-яё])%s(?![а-яё])" % f.hedge, after_norm) and \
                    len(fa.of("negation")) < len(fb.of("negation")):
                checks.append({"kind": "negation", "what": "отрицание", "detail": "«%s» не найдено" % f.raw})
            continue
        word = f.value
        negated = [m for m in re.finditer(r"(?<![а-яё])(не|ни|без|нет|нельзя)\s+(?:[а-яё]+\s+){0,2}([а-яё]{3,})", after_norm)
                   if stem_match(m.group(2), word, strict=True)]
        if negated:
            continue
        if word in ("только", "менее", "более", "раньше", "позже", "позднее", "просто", "всегда", "совсем"):
            continue
        hits = _occurrences(after_norm, word)
        src_hits = _occurrences(before_norm, word)
        only_negated_in_source = all(_negated_near(before_norm, a, b) for a, b in src_hits)
        if hits:
            if only_negated_in_source and all(not _negated_near(after_norm, a, b) for a, b in hits):
                errors.append({"kind": "inverted", "what": "отрицание",
                               "detail": "«%s» в правке стоит без отрицания" % f.raw})
        else:
            checks.append({"kind": "negation", "what": "отрицание",
                           "detail": "«%s» не найдено, проверь, что смысл сохранён" % f.raw})
    # END_BLOCK_NEGATIONS_DIFF

    # START_BLOCK_MODALITY_DIFF
    specs = []
    if ru:
        specs.append((MODALITY, INTENSIFIERS, "а-яё", before_norm, after_norm, 0,
                      "«самый», «главный», «лучший»"))
    if en:
        # Case-insensitive except "may": the month "May" is not a modal verb.
        specs.append((MODALITY_EN, INTENSIFIERS_EN, "a-z", before.replace("\u2019", "'"),
                      after.replace("\u2019", "'"), re.I, "«most», «best», «key»"))
    for modality, intensifiers, letters, b_text, a_text, flags, examples in specs:
        for label, rx in modality:
            pat = r"(?<![%s])(?:%s)(?![%s])" % (letters, rx, letters)
            nb, na = len(re.findall(pat, b_text, flags)), len(re.findall(pat, a_text, flags))
            if nb > na:
                checks.append({"kind": "modality", "what": "уверенность и охват",
                               "detail": "«%s» встречается реже (%d → %d): не стало ли утверждение сильнее?" % (label, nb, na)})
            elif na > nb == 0:
                checks.append({"kind": "modality", "what": "уверенность и охват",
                               "detail": "появилось «%s», которого не было" % label})
        pat = r"(?<![%s])(?:%s)(?![%s])" % (letters, intensifiers, letters)
        nb, na = len(re.findall(pat, b_text, flags)), len(re.findall(pat, a_text, flags))
        if na > nb:
            checks.append({"kind": "modality", "what": "уверенность и охват",
                           "detail": "слов вроде %s стало больше (%d → %d): не усилено ли утверждение?" % (examples, nb, na)})
    # END_BLOCK_MODALITY_DIFF

    # START_BLOCK_MARKUP_DIFF
    # HTML in the original is part of the text: structural tags must survive the edit; lost
    # emphasis tags only need a look (decorative bold may be removed on purpose).
    # The name ends at a space, "/" or ">": autolinks <https://…> and <a@b.ru> are not tags.
    tag_rx = re.compile(r"<([a-z][a-z0-9]*)(?:\s[^<>]*)?/?>", re.I)
    emphasis = {"b", "strong", "i", "em", "mark", "u"}
    tags_b = [t.lower() for t in tag_rx.findall(before)]
    if len(tags_b) >= 2:
        tags_a = [t.lower() for t in tag_rx.findall(after)]
        for tag in sorted(set(tags_b)):
            nb, na = tags_b.count(tag), tags_a.count(tag)
            if na < nb:
                (checks if tag in emphasis else errors).append(
                    {"kind": "lost", "what": "разметка", "detail": "<%s> %d → %d" % (tag, nb, na)})
        for tag in sorted(set(tags_a) - set(tags_b)):
            checks.append({"kind": "added", "what": "разметка", "detail": "появился тег <%s>" % tag})
    # END_BLOCK_MARKUP_DIFF

    # START_BLOCK_BINDINGS
    # Who got which number: in the original sentence a name and a number stand together;
    # in the edit the number must not move to a sentence with another of those names only.
    pairs: Dict[str, set] = {}
    # Only real names anchor a number: sentence subjects ("Капучино", "Итог") were too noisy.
    names_b = [f for f in fb.of("name")]
    for n in fb.of("number"):
        owners = {_norm(x.value.lower())[:5] for x in names_b if x.sent == n.sent}
        if len(owners) == 1:
            pairs.setdefault(n.value, set()).update(owners)
    all_owners = set().union(*pairs.values()) if pairs else set()
    if len(all_owners) >= 2:
        def near(facts: Facts, n: Fact) -> set:
            words = re.findall(r"[\w-]+", facts.sentences[n.sent] if n.sent < len(facts.sentences) else "")
            return {o for o in all_owners if any(stem_match(o, w) for w in words)}
        # A number repeated in the original (card numbers 01, 02…) may stand by any name it stood by there.
        allowed: Dict[str, set] = {}
        for n in fb.of("number"):
            if n.value in pairs:
                allowed.setdefault(n.value, set()).update(near(fb, n))
        for n in fa.of("number"):
            want = pairs.get(n.value)
            if not want:
                continue
            here = near(fa, n)
            if here and not (here & allowed[n.value]):
                errors.append({"kind": "swap", "what": "привязка",
                               "detail": "%s в исходнике относится к «%s», в правке стоит рядом с «%s»" % (
                                   n.raw, "/".join(sorted(want)), "/".join(sorted(here)))})
    # END_BLOCK_BINDINGS

    counts = {k: len(fb.of(k)) for k in ("number", "date", "name", "url", "quote", "negation")}
    result = {"errors": _dedupe(errors), "checks": _dedupe(checks), "counts": counts}
    if langs != ("ru",):
        result["lang"] = "+".join(langs)
    return result


def _negation_en(f: Fact, fb: Facts, fa: Facts, before_low: str, after_low: str,
                 errors: List[Dict], checks: List[Dict]) -> None:
    """English branch of the negation diff: same rules as the Russian one."""
    if f.value in NEG_ALONE_EN:
        if not re.search(r"(?<![a-z'])%s(?![a-z'])" % f.value, after_low) and \
                len(fa.of("negation")) < len(fb.of("negation")):
            checks.append({"kind": "negation", "what": "отрицание", "detail": "«%s» не найдено" % f.raw})
        return
    word = f.value
    if word in NEG_SKIP_EN:
        return
    if any(_en_same(m.group(1), word) for m in NEG_AFTER_RX_EN.finditer(after_low)):
        return
    hits = _occurrences(after_low, word, True)
    src_hits = _occurrences(before_low, word, True)
    only_negated_in_source = all(_negated_near(before_low, a, b, True) for a, b in src_hits)
    if hits:
        if only_negated_in_source and all(not _negated_near(after_low, a, b, True) for a, b in hits):
            errors.append({"kind": "inverted", "what": "отрицание",
                           "detail": "«%s» в правке стоит без отрицания" % f.raw})
    else:
        checks.append({"kind": "negation", "what": "отрицание",
                       "detail": "«%s» не найдено, проверь, что смысл сохранён" % f.raw})


def _dedupe(items: List[Dict]) -> List[Dict]:
    seen, out = set(), []
    for it in items:
        key = (it["kind"], it["what"], it["detail"])
        if key not in seen:
            seen.add(key)
            out.append(it)
    return out


KIND_RU = {"lost": "потеряно", "added": "появилось", "unit": "изменилась", "swap": "перестановка",
           "inverted": "перевёрнуто",
           "fewer": "реже", "hedge": "потеряна", "negation": "проверь"}


LANG_RU = {"en": "английский", "ru+en": "русский и английский"}


def render(result: Dict) -> str:
    lines = ["Сверка фактов: исходник → правка"]
    c = result["counts"]
    lines.append("В исходнике: чисел %d, дат %d, имён и названий %d, ссылок %d, отрицаний %d." % (
        c["number"], c["date"], c["name"], c["url"], c["negation"]))
    if result.get("lang") in LANG_RU:
        lines.append("Язык сверки: %s." % LANG_RU[result["lang"]])
    if result["errors"]:
        lines.append("Ошибки (%d):" % len(result["errors"]))
        for e in result["errors"]:
            lines.append("  - %s %s: %s" % (KIND_RU.get(e["kind"], e["kind"]), e["what"], e["detail"]))
    if result["checks"]:
        lines.append("Проверь глазами (%d):" % len(result["checks"]))
        for e in result["checks"]:
            lines.append("  - %s: %s" % (e["what"], e["detail"]))
    lines.append("Итог: " + ("есть ошибки, верни факты в текст" if result["errors"] else
                             "ошибок не найдено (это не гарантия смысла: перечитай условия и связи)"))
    return "\n".join(lines)


def _read(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8-sig") as fh:
        return fh.read()


def main(argv: Optional[List[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in args
    args = [a for a in args if a != "--json"]
    lang = "auto"
    for i, a in enumerate(args):
        if a == "--lang" or a.startswith("--lang="):
            value = a.split("=", 1)[1] if "=" in a else (args[i + 1] if i + 1 < len(args) else "")
            del args[i:i + (1 if "=" in a else 2)]
            if value not in ("ru", "en", "auto"):
                print("--lang: ожидается ru, en или auto, получено %r" % value, file=sys.stderr)
                return 2
            lang = value
            break
    if len(args) != 2 or args[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    try:
        before, after = _read(args[0]), _read(args[1])
    except (OSError, UnicodeDecodeError) as exc:
        print("Не могу прочитать файл: %s" % exc, file=sys.stderr)
        return 2
    result = compare(before, after, lang)
    print(json.dumps(result, ensure_ascii=False, indent=2) if as_json else render(result))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

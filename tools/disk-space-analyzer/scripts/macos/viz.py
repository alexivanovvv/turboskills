#!/usr/bin/env python3
"""
Terminal visualizations for analyze_disk.py results.

Pure Unicode (block characters), no dependencies. Output is meant to be pasted
verbatim into a ```text block in the chat, so lines stay <= WIDTH columns.
ANSI colors are opt-in (--color) for running directly in a real terminal.
"""

import os
import shutil
from typing import Dict, List, Optional

WIDTH = 78
BAR = 22
BLOCKS = " ▏▎▍▌▋▊▉█"

USE_COLOR = False
COLORS = {
    "safe": "\033[32m", "check": "\033[33m", "admin": "\033[31m",
    "dim": "\033[2m", "bold": "\033[1m", "accent": "\033[36m", "reset": "\033[0m",
}
SAFETY_MARK = {"safe": "✓", "check": "!", "admin": "✗"}

# Chart language: English by default, Russian with --lang ru.
LANG = "en"
STRINGS = {
    "disk": ("DISK", "ДИСК"),
    "volume": ("volume {m}", "том {m}"),
    "used_pct": ("used", "занято"),
    "used_of": ("used {u} of {t}  ·  free {f}", "занято {u} из {t}  ·  свободно {f}"),
    "scan": ("SCAN", "СКАН"),
    "scan_line": ("{s} on disk  ·  {n:,} files  ·  {d:,} folders",
                  "{s} на диске  ·  {n:,} файлов  ·  {d:,} папок"),
    "cloud": (" ☁ +{s} ({n:,} files) cloud-only — use no disk space, not counted",
              " ☁ ещё {s} ({n:,} файлов) только в облаке — место не занимают, не считаются"),
    "types": ("FILE TYPES", "ТИПЫ ФАЙЛОВ"),
    "pcs": ("pcs", "шт"),
    "largest": ("LARGEST FILES", "САМЫЕ БОЛЬШИЕ ФАЙЛЫ"),
    "folders_lvl": ("FOLDERS · level {d}", "ПАПКИ · уровень {d}"),
    "folder": ("FOLDER", "ПАПКА"),
    "cleanable": ("CLEANABLE", "МОЖНО ПОЧИСТИТЬ"),
    "nothing": (" nothing found", " ничего не найдено"),
    "safe": ("safe", "безопасно"),
    "check": ("review", "проверить"),
    "share": (" {p:.0f}% of the scanned size", " это {p:.0f}% от просканированного объёма"),
    "search": ("SEARCH · {q}", "ПОИСК · {q}"),
    "plan": ("CLEANUP PLAN", "ПЛАН ЧИСТКИ"),
    "plan_right": ("{n} {w} · up to {s}", "{n} {w} · до {s}"),
    "plan_legend": ("    ✓ safe   ! review   ✗ needs sudo   Σ — cumulative space freed",
                    "    ✓ безопасно   ! проверить   ✗ нужен sudo   Σ — освобождено нарастающим итогом"),
    "now": ("now", "сейчас"),
    "plus_safe": ("+ safe only", "+ безопасное"),
    "plus_all": ("+ whole plan", "+ весь план"),
    "now_after": ("DISK: NOW → AFTER", "ДИСК: СЕЙЧАС → ПОСЛЕ"),
    "free": ("free", "свободно"),
    "map": ("DISK MAP", "КАРТА ДИСКА"),
    "map_legend": (" area = disk space · ═ top level · ─ nested · ░ small items",
                   " площадь = место на диске · ═ верхний уровень · ─ вложенные · ░ мелочь"),
    "files_node": ("· files", "· файлы"),
    "other": ("other", "прочее"),
    "more": ("more", "ещё"),
    "result": ("RESULT: BEFORE → AFTER", "РЕЗУЛЬТАТ: ДО → ПОСЛЕ"),
    "freed_right": ("freed {s}", "освобождено {s}"),
    "grew_right": ("grew {s}", "выросло {s}"),
    "before": ("before", "до"),
    "after": ("after", "после"),
    "est": ("  (est. from scans)", "  (оценка по сканам)"),
    "changes": ("WHAT CHANGED · level {d}", "ЧТО ИЗМЕНИЛОСЬ · уровень {d}"),
    "changes_legend": (" ▼ freed   ▲ grew   before → after",
                       " ▼ освобождено   ▲ выросло   до → после"),
    "no_changes": (" no changes above {s}", " изменений больше {s} нет"),
}


def t(key: str, **kw) -> str:
    en, ru = STRINGS[key]
    s = ru if LANG == "ru" else en
    return s.format(**kw) if kw else s


def plural_actions(n: int) -> str:
    if LANG != "ru":
        return "action" if n == 1 else "actions"
    return ("действие" if n % 10 == 1 and n % 100 != 11 else
            "действия" if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else "действий")


# Chat colors (--chat-color): output goes into a ```diff block in the chat, where the
# CLI highlights whole lines. Only green is used: "+" = effect of the cleanup
# (space freed, disk after). Other lines get a neutral " " prefix.
CHAT = False


def tag(line: str, green: bool) -> str:
    if not CHAT or not green:
        return line
    return "\x00+" + line


def join(lines: List[str]) -> str:
    """Final output: in chat mode every line gets its diff prefix."""
    if CHAT:
        lines = [l[1:] if l.startswith("\x00") else " " + l for l in lines]
    return "\n".join(lines)


def c(text: str, color: str) -> str:
    if not USE_COLOR:
        return text
    return f"{COLORS[color]}{text}{COLORS['reset']}"


def fmt(size_bytes: float) -> str:
    size_bytes = abs(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def bar(value: float, total: float, width: int = BAR, fill_empty: str = " ") -> str:
    """Horizontal bar with 1/8-character precision."""
    if total <= 0:
        return fill_empty * width
    frac = max(0.0, min(1.0, value / total))
    eighths = int(round(frac * width * 8))
    full, rem = divmod(eighths, 8)
    s = "█" * full + (BLOCKS[rem] if rem and full < width else "")
    return s + fill_empty * (width - len(s))


def gauge(used: float, total: float, width: int = 40) -> str:
    """Fill gauge, colored by how full it is."""
    pct = used / total if total else 0
    color = "safe" if pct < 0.7 else "check" if pct < 0.9 else "admin"
    return c(bar(used, total, width, "░"), color)


def short(path: str, width: int, root: Optional[str] = None) -> str:
    """Shorten a path: strip scan root / home, then cut the middle."""
    if root and path != root and path.startswith(root.rstrip("/") + "/"):
        path = path[len(root.rstrip("/")) + 1:]
    home = os.path.expanduser("~")
    if path.startswith(home):
        path = "~" + path[len(home):]
    if len(path) <= width:
        return path.ljust(width)
    keep = width - 1
    head = keep // 3
    return (path[:head] + "…" + path[-(keep - head):]).ljust(width)


def header(title: str, right: str = "") -> str:
    line = f"── {title} "
    tail = f" {right} ──" if right else ""
    return c(line + "─" * max(2, WIDTH - len(line) - len(tail)) + tail, "bold")


def bar_rows(rows: List[Dict], total: float, root: Optional[str] = None,
             label_w: int = 32, extra=None) -> List[str]:
    """rows: [{label, bytes}] → aligned bar lines with size and percent."""
    out = []
    peak = max((r["bytes"] for r in rows), default=0)
    for r in rows:
        pct = r["bytes"] / total * 100 if total else 0
        line = (f" {short(r['label'], label_w, root)} {c(bar(r['bytes'], peak), 'accent')}"
                f" {fmt(r['bytes']):>9} {pct:4.0f}%")
        if extra:
            line += " " + extra(r)
        out.append(line)
    return out


# ── Renderers per command ────────────────────────────────────────────────


def disk_gauge(path: str) -> List[str]:
    try:
        du = shutil.disk_usage(path)
    except OSError:
        return []
    mount = os.path.realpath(path)
    while not os.path.ismount(mount):
        mount = os.path.dirname(mount)
    pct = du.used / du.total * 100
    return [
        header(t("disk"), t("volume", m=mount)),
        f" {gauge(du.used, du.total)} {pct:3.0f}% {t('used_pct')}",
        " " + t("used_of", u=fmt(du.used), t=fmt(du.total), f=c(fmt(du.free), "bold")),
    ]


def render_summary(r: Dict, root: Optional[str] = None) -> List[str]:
    total = r["total_size_bytes"]
    out = [header(t("scan"), root or ""),
           " " + t("scan_line", s=fmt(total), n=r["total_files"], d=r["total_directories"])]
    if r.get("cloud_only_bytes"):
        out.append(c(t("cloud", s=fmt(r["cloud_only_bytes"]), n=r["cloud_only_files"]), "dim"))
    out += ["", header(t("types"))]
    rows = [{"label": e["ext"], "bytes": e["size_bytes"]} for e in r["top_extensions"]]
    out += bar_rows(rows, total, label_w=12)
    return out


def render_by_type(r: List[Dict], total: Optional[float] = None) -> List[str]:
    total = total or sum(e["size_bytes"] for e in r)
    rows = [{"label": e["extension"], "bytes": e["size_bytes"], "n": e["count"]} for e in r]
    return [header(t("types"))] + bar_rows(
        rows, total, label_w=14, extra=lambda x: c(f"{x['n']:>7,} {t('pcs')}", "dim"))


def render_largest(r: List[Dict], root: Optional[str] = None) -> List[str]:
    total = sum(e["size_bytes"] for e in r)
    rows = [{"label": e["path"], "bytes": e["size_bytes"]} for e in r]
    return [header(t("largest"), f"{len(r)} {t('pcs')} · {fmt(total)}")] + bar_rows(rows, total, root)


def render_top_folders(r: Dict, root: Optional[str] = None, total: Optional[float] = None) -> List[str]:
    out = []
    for depth, dirs in r["depths"].items():
        tot = total or sum(d["size_bytes"] for d in dirs)
        rows = [{"label": d["path"], "bytes": d["size_bytes"]} for d in dirs]
        out += [header(t("folders_lvl", d=depth))] + bar_rows(rows, tot, root) + [""]
    return out[:-1]


def render_folder(r: Dict) -> List[str]:
    root = r["path"]
    items = r["directories"] + r["files"]
    items.sort(key=lambda x: x["size_bytes"], reverse=True)
    total = sum(i["size_bytes"] for i in items if i["depth"] == 1) or 1
    rows = [{"label": i["path"] + ("/" if i["is_dir"] else ""), "bytes": i["size_bytes"]}
            for i in items[:25]]
    return [header(t("folder"), short(root, 40).strip())] + bar_rows(rows, total, root)


def render_cleanable(r: Dict, scanned: Optional[float] = None) -> List[str]:
    cats = r["categories"]
    total = r["total_cleanable_bytes"]
    if not cats:
        return [header(t("cleanable")), t("nothing")]
    safe = sum(d["total_size_bytes"] for d in cats.values() if d["safety"] == "safe")
    check = total - safe
    out = [header(t("cleanable"), fmt(total))]
    # stacked bar: safe vs needs-review
    w = 50
    ws = int(round(safe / total * w)) if total else 0
    out.append(" " + c("█" * ws, "safe") + c("▒" * (w - ws), "check"))
    out.append(f" {c('█', 'safe')} {t('safe'):<9} {fmt(safe):>9}   {c('▒', 'check')} {t('check'):<9} {fmt(check):>9}")
    if scanned:
        out.append(c(t("share", p=total / scanned * 100), "dim"))
    out.append("")
    rows = [{"label": cat, "bytes": d["total_size_bytes"], "safety": d["safety"],
             "n": d["file_count"]} for cat, d in cats.items()]
    out += bar_rows(rows, total, label_w=10, extra=lambda x: c(
        f"{SAFETY_MARK.get(x['safety'], '?')} {x['safety']:<5} {x['n']:>6,} {t('pcs')}", x["safety"]))
    return out


def render_search(r: Dict, root: Optional[str] = None) -> List[str]:
    m = r["matches"][:25]
    total = sum(x["size_bytes"] for x in m)
    title = r.get("pattern") or r.get("conditions")
    rows = [{"label": x["path"], "bytes": x["size_bytes"]} for x in m]
    return [header(t("search", q=title), f"{r['count']} {t('pcs')} · {fmt(total)}")] + bar_rows(rows, total, root)


def render_plan(items: List[Dict], disk_path: str = "/") -> List[str]:
    """Cleanup proposal: ranked actions with cumulative freed space, then disk before → after.

    items: [{label, bytes, safety}] in the order they are proposed.
    """
    total = sum(i["bytes"] for i in items)
    n_items = len(items)
    out = [header(t("plan"), t("plan_right", n=n_items, w=plural_actions(n_items), s=fmt(total)))]
    peak = max((i["bytes"] for i in items), default=0)
    acc = 0
    for n, it in enumerate(items, 1):
        acc += it["bytes"]
        safety = it.get("safety", "check")
        mark = c(SAFETY_MARK.get(safety, "?"), safety)
        label = it["label"] if len(it["label"]) <= 30 else it["label"][:29] + "…"
        out.append(f" {n:>2} {mark} {label:<30} {c(bar(it['bytes'], peak, 15), safety)}"
                   f" {fmt(it['bytes']):>9}  Σ {fmt(acc):>9}")
    out.append(c(t("plan_legend"), "dim"))

    try:
        du = shutil.disk_usage(disk_path)
    except OSError:
        return out
    safe = sum(i["bytes"] for i in items if i.get("safety", "check") == "safe")
    scenarios = [(t("now"), 0)]
    if 0 < safe < total:
        scenarios.append((t("plus_safe"), safe))
    scenarios.append((t("plus_all"), total))
    out += ["", header(t("now_after"))]
    for name, freed in scenarios:
        used = max(0, du.used - freed)
        pct = used / du.total * 100
        out.append(tag(f" {name:<13}{gauge(used, du.total, 36)} {pct:3.0f}%"
                       f"  {t('free')} {fmt(du.free + freed):>9}", freed > 0))
    return out


def render_dashboard(root: str, summary: Dict, folders: Dict, cleanable: Dict,
                     largest: List[Dict], tree: Optional[List[Dict]] = None) -> List[str]:
    scanned = summary["total_size_bytes"]
    out = disk_gauge(root)
    if tree:
        out += [""] + render_treemap(tree, root, WIDTH - 1, 20)
    out += [""] + render_summary(summary, root)
    out += [""] + render_top_folders(folders, root, scanned)
    out += [""] + render_cleanable(cleanable, scanned)
    out += [""] + render_largest(largest, root)
    return out


# ── Treemap ──────────────────────────────────────────────────────────────
# Squarified treemap drawn with box-drawing characters. Top-level folders get
# double borders (titled on the frame), their subfolders light borders inside.

def _squarify(sizes: List[float], x: float, y: float, w: float, h: float) -> List[tuple]:
    """Bruls et al. squarified layout. sizes sorted desc, sum == w*h."""
    rects = []
    sizes = list(sizes)

    def worst(row, side):
        s = sum(row)
        return max(max(side * side * r / (s * s), s * s / (side * side * r)) for r in row)

    while sizes:
        side = min(w, h)
        row = [sizes[0]]
        i = 1
        while i < len(sizes) and worst(row + [sizes[i]], side) <= worst(row, side):
            row.append(sizes[i])
            i += 1
        s = sum(row)
        if w >= h:  # column on the left
            cw = s / h if h else 0
            cy = y
            for r in row:
                rh = r / cw if cw else 0
                rects.append((x, cy, cw, rh))
                cy += rh
            x, w = x + cw, w - cw
        else:  # row on top
            rh = s / w if w else 0
            cx = x
            for r in row:
                rw = r / rh if rh else 0
                rects.append((cx, y, rw, rh))
                cx += rw
            y, h = y + rh, h - rh
        sizes = sizes[i:]
    return rects


# (up, down, left, right) weights: 0 none, 1 light, 2 double
_BOX = {
    (0, 0, 1, 1): "─", (1, 1, 0, 0): "│", (0, 1, 0, 1): "┌", (0, 1, 1, 0): "┐",
    (1, 0, 0, 1): "└", (1, 0, 1, 0): "┘", (1, 1, 0, 1): "├", (1, 1, 1, 0): "┤",
    (0, 1, 1, 1): "┬", (1, 0, 1, 1): "┴", (1, 1, 1, 1): "┼",
    (0, 0, 2, 2): "═", (2, 2, 0, 0): "║", (0, 2, 0, 2): "╔", (0, 2, 2, 0): "╗",
    (2, 0, 0, 2): "╚", (2, 0, 2, 0): "╝", (2, 2, 0, 2): "╠", (2, 2, 2, 0): "╣",
    (0, 2, 2, 2): "╦", (2, 0, 2, 2): "╩", (2, 2, 2, 2): "╬",
    (0, 1, 2, 2): "╤", (1, 0, 2, 2): "╧", (2, 2, 0, 1): "╟", (2, 2, 1, 0): "╢",
    (1, 1, 2, 2): "╪", (2, 2, 1, 1): "╫",
}


class _Canvas:
    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        self.edges = [[[0, 0, 0, 0] for _ in range(w)] for _ in range(h)]
        self.text = [[None] * w for _ in range(h)]

    def _mark(self, x, y, d, wt):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.edges[y][x][d] = max(self.edges[y][x][d], wt)

    def rect(self, x0, y0, x1, y1, wt):
        for x in range(x0, x1 + 1):
            for y in (y0, y1):
                if x > x0:
                    self._mark(x, y, 2, wt)
                if x < x1:
                    self._mark(x, y, 3, wt)
        for y in range(y0, y1 + 1):
            for x in (x0, x1):
                if y > y0:
                    self._mark(x, y, 0, wt)
                if y < y1:
                    self._mark(x, y, 1, wt)

    def put(self, x, y, s, max_len):
        for i, ch in enumerate(s[:max(0, max_len)]):
            if 0 <= x + i < self.w and 0 <= y < self.h:
                self.text[y][x + i] = ch

    def fill(self, x0, y0, x1, y1, pattern):
        """Fill the interior with a repeating pattern anchored to the canvas grid."""
        for y in range(y0 + 1, y1):
            for x in range(x0 + 1, x1):
                if self.text[y][x] is None:
                    self.text[y][x] = pattern[(x + y) % len(pattern)]

    def render(self) -> List[str]:
        out = []
        for y in range(self.h):
            line = ""
            for x in range(self.w):
                if self.text[y][x] is not None:
                    line += self.text[y][x]
                    continue
                k = tuple(self.edges[y][x])
                if k == (0, 0, 0, 0):
                    line += " "
                    continue
                ch = _BOX.get(k) or _BOX.get(tuple(min(v, 1) for v in k))
                if ch is None:  # dangling stub
                    ch = "─" if k[2] or k[3] else "│"
                line += ch
            out.append(line)
        return out


def _layout(items: List[Dict], x0: int, y0: int, x1: int, y1: int) -> List[tuple]:
    """Integer rects sharing borders; y is doubled during layout for char aspect."""
    total = sum(i["bytes"] for i in items)
    w, h = x1 - x0, (y1 - y0) * 2
    if total <= 0 or w <= 0 or h <= 0:
        return []
    areas = [i["bytes"] / total * w * h for i in items]
    out = []
    for it, (fx, fy, fw, fh) in zip(items, _squarify(areas, 0, 0, w, h)):
        rx0, rx1 = x0 + round(fx), x0 + round(fx + fw)
        ry0, ry1 = y0 + round(fy / 2), y0 + round((fy + fh) / 2)
        out.append((it, rx0, ry0, rx1, ry1))
    return out


HATCH = ["╱ ", "·  ", "╲ ", "░ ", "┄┄ ", "∙ ", "▚ ", "˙ ", "╳ "]


def _label(cv: _Canvas, it: Dict, total: float, x0, y0, x1, y1, hatch: str = "░"):
    """Centered name / size / % on a clean pad, rest of the cell hatched."""
    iw, ih = x1 - x0 - 1, y1 - y0 - 1
    if iw < 3 or ih < 1:
        cv.fill(x0, y0, x1, y1, "░")
        return
    lines = [it["label"], fmt(it["bytes"]), f"{it['bytes'] / total * 100:.0f}%"]
    if iw >= len(lines[1]) + len(lines[2]) + 3 and ih < 3:
        lines = [it["label"], f"{lines[1]} · {lines[2]}"]
    lines = [s if len(s) <= iw else s[:max(1, iw - 1)] + "…" for s in lines[:ih]]
    pad = min(iw, max(len(s) for s in lines) + 2)
    top = y0 + 1 + (ih - len(lines)) // 2
    for n, s in enumerate(lines):
        cv.put(x0 + 1 + (iw - pad) // 2, top + n, s.center(pad), iw)
    cv.fill(x0, y0, x1, y1, "░" if it.get("other") else hatch)


def render_treemap(tree: List[Dict], root: str, width: int = WIDTH, height: int = 24) -> List[str]:
    """tree: [{label, bytes, children: [{label, bytes}], other?}] sorted desc."""
    total = sum(t["bytes"] for t in tree) or 1
    cv = _Canvas(width, height)
    for idx, (it, x0, y0, x1, y1) in enumerate(_layout(tree, 0, 0, width - 1, height - 1)):
        if x1 - x0 < 1 or y1 - y0 < 1:
            continue
        hatch = HATCH[idx % len(HATCH)]
        kids = it.get("children") or []
        roomy = (x1 - x0) >= 16 and (y1 - y0) >= 6 and len(kids) > 1
        if roomy:
            for kid, kx0, ky0, kx1, ky1 in _layout(kids, x0, y0, x1, y1):
                if kx1 - kx0 >= 1 and ky1 - ky0 >= 1:
                    cv.rect(kx0, ky0, kx1, ky1, 1)
                    _label(cv, kid, total, kx0, ky0, kx1, ky1, hatch)
        cv.rect(x0, y0, x1, y1, 2)
        if roomy:
            title = f" {it['label']} {fmt(it['bytes'])} "
            cv.put(x0 + 2, y0, title, x1 - x0 - 3)
        else:
            _label(cv, it, total, x0, y0, x1, y1, hatch)
    return [header(t("map"), f"{short(root, 30).strip()} · {fmt(total)}")] + [
        " " + l for l in cv.render()[:]] + [c(t("map_legend"), "dim")]


# ── Before → after ───────────────────────────────────────────────────────


def render_compare(before: Dict, after: Dict, changes: List[Dict], depth: int,
                   estimated: bool = False, root: Optional[str] = None) -> List[str]:
    """Result of a cleanup: disk gauges before → after, freed space, per-folder deltas.

    before/after: {"total", "used", "free"} in bytes (disk snapshots at scan time).
    changes: [{label, before, after}] sorted by |after - before| desc.
    """
    freed = after["free"] - before["free"]
    right = t("freed_right", s=fmt(freed)) if freed >= 0 else t("grew_right", s=fmt(freed))
    out = [header(t("result"), right)]
    for name, d, is_after in ((t("before"), before, False), (t("after"), after, True)):
        pct = d["used"] / d["total"] * 100
        out.append(tag(f" {name:<8}{gauge(d['used'], d['total'], 40)} {pct:3.0f}%"
                       f"  {t('free')} {c(fmt(d['free']), 'bold'):>9}", is_after and freed > 0))
    sign = "+" if freed >= 0 else "−"
    out.append(tag(f" {'Δ':<8}{c(bar(abs(freed), before['total'], 40, ' '), 'safe' if freed >= 0 else 'admin')}"
               f"      {sign}{fmt(freed)}", freed > 0))
    if estimated:
        out.append(c(t("est"), "dim"))

    out += ["", header(t("changes", d=depth))]
    if not changes:
        return out + [t("no_changes", s="1 MB")]
    peak = max(abs(x["after"] - x["before"]) for x in changes)
    for x in changes:
        delta = x["after"] - x["before"]
        kind = "safe" if delta < 0 else "admin"
        arrow = c("▼" if delta < 0 else "▲", kind)
        out.append(tag(f" {arrow} {short(x['label'], 28, root)} {c(bar(abs(delta), peak, 14), kind)}"
                       f" {fmt(x['before']):>8} → {fmt(x['after']):>8}  {'−' if delta < 0 else '+'}{fmt(delta)}",
                       delta < 0))
    out.append(c(t("changes_legend"), "dim"))
    return out

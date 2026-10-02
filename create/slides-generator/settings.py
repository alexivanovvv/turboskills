#!/usr/bin/env python3
"""Settings page for slides-generator: serves settings.html and reads/writes config.json.

Usage: python3 settings.py [port] [--no-open]   (default 7361; --no-open — for the LaunchAgent)

POST /rebuild {"path": "/abs/Deck.html"} — rebuild a deck on the current template + config
(rebuild.py); called from the deck's ⋯ menu → «Обновить интерфейс».
GET/POST /comments — правки «на слайде» из ⋯ → Комментарий, хранятся в <деск>.comments.json рядом с деском.
GET /decks — все дески в vault PROJECTS/ (вкладка «Дески»); GET /deck?path= — сам деск для превью;
POST /open | /export | /lint {"path"} — открыть в браузере, PDF (export.sh), проверка (lint.py).
"""
import json
import os
import subprocess
import sys
import time
import uuid
from urllib.parse import parse_qs, urlparse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import rebuild as rebuilder

DIR = Path(__file__).resolve().parent
CONFIG = DIR / "config.json"
PAGE = DIR / "settings.html"
VAULT = Path.home() / "Library/CloudStorage/Dropbox/_Obsidian/Alex Ivanov MAIN Vault"
DECK_SUFFIX = "Slides Content.html"
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
PORT = int(ARGS[0]) if ARGS else 7361
OPEN = "--no-open" not in sys.argv


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="text/plain; charset=utf-8"):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    def _cors(self):
        # decks open as file:// (origin "null") and call /rebuild from the ⋯ menu
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Private-Network", "true")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _rebuild(self, raw):
        try:
            path = Path(json.loads(raw)["path"]).expanduser().resolve()
        except (ValueError, KeyError, TypeError):
            return self._send(400, "bad json: need {path}")
        if path.suffix != ".html" or not path.is_file() or Path.home() not in path.parents:
            return self._send(400, f"не найден деск: {path}")
        try:
            r = rebuilder.rebuild(path)
        except Exception as e:  # report to the deck's toast
            return self._send(500, str(e))
        self._send(200, json.dumps(r, ensure_ascii=False), "application/json")

    def _deck(self, path):
        """Путь к деску из запроса — только .html внутри домашней папки."""
        p = Path(path or "").expanduser().resolve()
        if p.suffix != ".html" or not p.is_file() or Path.home() not in p.parents:
            raise ValueError(f"не найден деск: {p}")
        return p

    def _json(self, obj):
        self._send(200, json.dumps(obj, ensure_ascii=False), "application/json")

    def _comments(self, body=None, query=None):
        try:
            deck = self._deck((body or {}).get("path") or (query or {}).get("path", [""])[0])
        except ValueError as e:
            return self._send(400, str(e))
        side = deck.with_name(deck.stem + ".comments.json")
        items = json.loads(side.read_text(encoding="utf-8")) if side.exists() else []
        if body and body.get("add"):
            a = body["add"]
            items.append({"id": uuid.uuid4().hex[:8], "slide": int(a["slide"]), "x": a.get("x"), "y": a.get("y"),
                          "text": str(a["text"])[:2000], "target": a.get("target", ""), "heading": a.get("heading", ""),
                          "at": time.strftime("%Y-%m-%d %H:%M")})
        elif body and body.get("remove"):
            items = [c for c in items if c["id"] != body["remove"]]
        if body:
            items.sort(key=lambda c: c["slide"])
            if items:
                side.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            elif side.exists():
                side.unlink()
        self._json(items)

    def _decks(self):
        out = []
        for root, dirs, files in os.walk(VAULT / "PROJECTS"):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "node_modules"]
            for f in files:
                if not f.endswith(DECK_SUFFIX):
                    continue
                p = Path(root) / f
                try:
                    info = rebuilder.rebuild(p, dry=True)
                except Exception:
                    info = {"outdated": None, "slides": 0}
                side = p.with_name(p.stem + ".comments.json")
                out.append({"path": str(p), "title": f[: -len(DECK_SUFFIX)].rstrip(" —"),
                            "folder": str(p.parent.relative_to(VAULT / "PROJECTS")), "mtime": p.stat().st_mtime,
                            "archived": "_ARCHIVE" in p.parts, "comments": len(json.loads(side.read_text())) if side.exists() else 0,
                            "pdf": p.with_suffix(".pdf").exists(), **info})
        out.sort(key=lambda d: (d["archived"], -d["mtime"]))
        self._json(out)

    def _action(self, name, raw):
        try:
            deck = self._deck(json.loads(raw).get("path"))
        except (ValueError, TypeError) as e:
            return self._send(400, str(e))
        if name == "/open":
            subprocess.Popen(["open", str(deck)])
            return self._json({"ok": True})
        cmd = {"/export": ["bash", str(DIR / "export.sh"), str(deck), "pdf"],
               "/lint": [sys.executable, str(DIR / "lint.py"), str(deck)]}[name]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            return self._send(500, "не уложилось в 5 минут")
        if name == "/export" and r.returncode == 0:
            subprocess.Popen(["open", "-R", str(deck.with_suffix(".pdf"))])
        self._json({"ok": r.returncode == 0, "out": (r.stdout + r.stderr).strip()[-6000:]})

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/comments":
            return self._comments(query=parse_qs(url.query))
        if url.path == "/decks":
            return self._decks()
        if url.path == "/deck":
            try:
                return self._send(200, self._deck(parse_qs(url.query).get("path", [""])[0]).read_bytes(), "text/html; charset=utf-8")
            except ValueError as e:
                return self._send(404, str(e))
        if self.path in ("/", "/settings.html"):
            self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/template":
            self._send(200, (DIR / "template.html").read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/config":
            if CONFIG.exists():
                self._send(200, CONFIG.read_bytes(), "application/json")
            else:
                self._send(404, "no config.json")
        else:
            self._send(404, "not found")

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.path == "/rebuild":
            return self._rebuild(raw)
        if self.path == "/comments":
            try:
                return self._comments(body=json.loads(raw))
            except (ValueError, KeyError, TypeError) as e:
                return self._send(400, f"bad json: {e}")
        if self.path in ("/open", "/export", "/lint"):
            return self._action(self.path, raw)
        if self.path != "/config":
            return self._send(404, "not found")
        try:
            cfg = json.loads(raw)
            if not isinstance(cfg, dict):
                raise ValueError("config must be an object")
        except ValueError as e:
            return self._send(400, f"bad json: {e}")
        CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self._send(200, "ok")

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    url = f"http://127.0.0.1:{PORT}/"
    try:
        server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError:
        # Already running — just open the tab
        print(f"slides-generator settings: уже запущено — {url}")
        if OPEN:
            webbrowser.open(url)
        sys.exit(0)
    print(f"slides-generator settings: {url}  (Ctrl+C — остановить)")
    if OPEN:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

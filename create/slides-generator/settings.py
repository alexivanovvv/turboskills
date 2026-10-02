#!/usr/bin/env python3
"""Settings page for slides-generator: serves settings.html and reads/writes config.json.

Usage: python3 settings.py [port] [--no-open]   (default 7361; --no-open — for the LaunchAgent)

POST /rebuild {"path": "/abs/Deck.html"} — rebuild a deck on the current template + config
(rebuild.py); called from the deck's ⋯ menu → «Обновить интерфейс».
"""
import json
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import rebuild as rebuilder

DIR = Path(__file__).resolve().parent
CONFIG = DIR / "config.json"
PAGE = DIR / "settings.html"
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

    def do_GET(self):
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

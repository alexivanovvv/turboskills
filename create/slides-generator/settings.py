#!/usr/bin/env python3
"""Settings page for slides-generator: serves settings.html and reads/writes config.json.

Usage: python3 settings.py [port]   (default 7361, opens the browser)
"""
import json
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DIR = Path(__file__).resolve().parent
CONFIG = DIR / "config.json"
PAGE = DIR / "settings.html"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 7361


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="text/plain; charset=utf-8"):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/settings.html"):
            self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/config":
            if CONFIG.exists():
                self._send(200, CONFIG.read_bytes(), "application/json")
            else:
                self._send(404, "no config.json")
        else:
            self._send(404, "not found")

    def do_POST(self):
        if self.path != "/config":
            return self._send(404, "not found")
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
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
        print(f"slides-generator settings: уже запущено, открываю {url}")
        webbrowser.open(url)
        sys.exit(0)
    print(f"slides-generator settings: {url}  (Ctrl+C — остановить)")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

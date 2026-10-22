#!/usr/bin/env python3
"""麦麦去留小程序。本机打开即可看裁决。

    python3 miniapp/server.py
    浏览器打开 http://127.0.0.1:8765
"""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "miniapp"))

from engine import list_scenarios, run_verdict  # noqa: E402

STATIC = Path(__file__).resolve().parent / "static"
HOST = "127.0.0.1"
PORT = 8765


class App(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/scenarios":
            self._json(200, {"scenarios": list_scenarios()})
            return
        if path == "/":
            path = "/index.html"
        file_path = (STATIC / path.lstrip("/")).resolve()
        if not str(file_path).startswith(str(STATIC.resolve())) or not file_path.is_file():
            self._send(404, "找不到页面".encode("utf-8"), "text/plain; charset=utf-8")
            return
        types = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8"}
        self._send(200, file_path.read_bytes(), types.get(file_path.suffix, "application/octet-stream"))

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/verdict":
            self._json(404, {"error": "没有这个接口"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            raw = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            wage = raw.get("wage")
            max_minutes = raw.get("max_minutes")
            result = run_verdict(
                str(raw.get("scenario") or "banshao"),
                minutes_to_spot=float(raw.get("minutes_to_spot") or 0),
                wage=None if wage in (None, "") else float(wage),
                driving=bool(raw.get("driving")),
                max_minutes=None if max_minutes in (None, "") else float(max_minutes),
            )
        except KeyError:
            self._json(404, {"error": "没有这顿饭的快照"})
            return
        except (TypeError, ValueError) as exc:
            self._json(400, {"error": str(exc)})
            return
        except RuntimeError as exc:
            self._json(422, {"error": str(exc)})
            return
        self._json(200, result)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), App)
    print(f"麦麦去留小程序 http://{HOST}:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

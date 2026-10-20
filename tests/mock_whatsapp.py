"""Local stand-in for the WhatsApp Cloud API send endpoint (Q-123 tests only).

The WhatsApp adapter workflow sends replies to this server instead of Meta,
so tests can check what would have been sent. Nothing leaves the machine.

  POST /<version>/<phone_number_id>/messages   record the body, answer like the Cloud API
  GET  /_sends                                 all recorded sends (JSON list)
  POST /_reset                                 forget all sends

Run: python tests/mock_whatsapp.py [--port 8122]   (binds 127.0.0.1 only)
"""

import argparse
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SENDS = []
LOCK = threading.Lock()
SEND_PATH = re.compile(r"^/v\d+\.\d+/([\w-]+)/messages$")


class Handler(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/_sends":
            with LOCK:
                return self._json(200, list(SENDS))
        return self._json(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        if self.path == "/_reset":
            with LOCK:
                SENDS.clear()
            return self._json(200, {"ok": True})
        m = SEND_PATH.match(self.path)
        if not m:
            return self._json(404, {"error": "not found"})
        if not (self.headers.get("Authorization") or "").startswith("Bearer "):
            return self._json(401, {"error": {"message": "missing bearer token", "code": 190}})
        try:
            body = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return self._json(400, {"error": {"message": "invalid JSON", "code": 100}})
        with LOCK:
            n = len(SENDS) + 1
            SENDS.append({"n": n, "phone_number_id": m.group(1), "body": body})
        to = body.get("to", "")
        return self._json(200, {"messaging_product": "whatsapp", "contacts": [{"input": to, "wa_id": to}],
                                "messages": [{"id": f"wamid.MOCK.{n:05d}"}]})

    def log_message(self, *args):  # quiet
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8122)
    a = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print(f"mock WhatsApp API on http://127.0.0.1:{a.port}")
    srv.serve_forever()


if __name__ == "__main__":
    main()

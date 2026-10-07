"""In-process fake of the Upstash Redis REST API (threading HTTPServer) for tests and manual runs.

Implements POST / (one command) and POST /pipeline for: SET (EX), GET, DEL, INCR, EXPIRE,
HSET, HSETNX, HGET, HGETALL, HDEL, KEYS, SCAN. Optional bearer-token check.
"""
from __future__ import annotations

import fnmatch
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeUpstash:
    def __init__(self, token: str = "test-token"):
        self.token = token
        self.data: dict[str, object] = {}
        self.ttls: dict[str, int] = {}
        self.commands: list[list[str]] = []
        self.scan_page = 50  # cap on keys per SCAN call so clients must follow the cursor
        self._lock = threading.Lock()
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):  # silence
                pass

            def _send(self, code, body):
                raw = json.dumps(body).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_POST(self):
                if self.headers.get("Authorization") != f"Bearer {fake.token}":
                    return self._send(401, {"error": "WRONGPASS invalid or missing auth token"})
                payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
                if self.path.rstrip("/") == "/pipeline":
                    return self._send(200, [fake._run_safe(c) for c in payload])
                if self.path.rstrip("/") == "":
                    out = fake._run_safe(payload)
                    return self._send(400 if "error" in out else 200, out)
                self._send(404, {"error": "not found"})

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self):
        self._thread.start()
        return self

    def stop(self):
        self.server.shutdown()
        self.server.server_close()

    # ---- command execution ---------------------------------------------------
    def _run_safe(self, cmd):
        try:
            return {"result": self._run(cmd)}
        except Exception as e:  # mimic Redis error replies
            return {"error": f"ERR {e}"}

    def _run(self, cmd):
        assert all(isinstance(a, str) for a in cmd), "args must be strings"
        name, a = cmd[0].upper(), cmd[1:]
        with self._lock:
            self.commands.append(list(cmd))
            d = self.data
            if name == "SET":
                d[a[0]] = a[1]
                if len(a) >= 4 and a[2].upper() == "EX":
                    self.ttls[a[0]] = int(a[3])
                return "OK"
            if name == "GET":
                return d.get(a[0])
            if name == "DEL":
                n = 0
                for k in a:
                    n += d.pop(k, None) is not None
                    self.ttls.pop(k, None)
                return n
            if name == "INCR":
                d[a[0]] = str(int(d.get(a[0], "0")) + 1)
                return int(d[a[0]])
            if name == "EXPIRE":
                if a[0] in d:
                    self.ttls[a[0]] = int(a[1])
                    return 1
                return 0
            if name in ("HSET", "HSETNX"):
                h = d.setdefault(a[0], {})
                assert isinstance(h, dict)
                if name == "HSETNX":
                    if a[1] in h:
                        return 0
                    h[a[1]] = a[2]
                    return 1
                new = 0
                for i in range(1, len(a), 2):
                    new += a[i] not in h
                    h[a[i]] = a[i + 1]
                return new
            if name == "HGET":
                return (d.get(a[0]) or {}).get(a[1])
            if name == "HGETALL":
                return [x for kv in (d.get(a[0]) or {}).items() for x in kv]
            if name == "HDEL":
                h = d.get(a[0]) or {}
                n = sum(h.pop(f, None) is not None for f in a[1:])
                if a[0] in d and not h:
                    del d[a[0]]
                return n
            if name == "KEYS":
                return sorted(k for k in d if fnmatch.fnmatchcase(k, a[0]))
            if name == "SCAN":
                # Single-page-per-call fake: cursor "0" -> first `count` matches, else next page.
                pattern, count = "*", 10
                for i in range(1, len(a) - 1, 2):
                    if a[i].upper() == "MATCH":
                        pattern = a[i + 1]
                    if a[i].upper() == "COUNT":
                        count = int(a[i + 1])
                count = min(count, self.scan_page)
                keys = sorted(k for k in d if fnmatch.fnmatchcase(k, pattern))
                start = int(a[0])
                page = keys[start:start + count]
                nxt = start + count
                return ["0" if nxt >= len(keys) else str(nxt), page]
        raise ValueError(f"unknown command '{name}'")

"""Loopback-only, offline trace review UI."""

import hashlib
import json
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files

from . import __version__
from .core import MAX_BYTES, InputError, dump, evaluate, normalize, parse, policy_from


def audit(payload):
    if not isinstance(payload, dict) or set(payload) != {"traces", "allowed_tools"}:
        raise InputError("Invalid request")
    records = payload["traces"]
    allowed = payload["allowed_tools"]
    if not isinstance(records, list) or not 1 <= len(records) <= 1000:
        raise InputError("Provide 1 to 1000 traces")
    if not isinstance(allowed, list) or any(not isinstance(x, str) or not x for x in allowed):
        raise InputError("Invalid tool allowlist")
    traces = [normalize(record) for record in records]
    policy = {**policy_from(), "allowed_tools": allowed}
    results = [evaluate(trace, policy) for trace in traces]
    return {"schema_version": 1, "evaluator_version": __version__, "rubric_version": 1,
            "judge": "offline", "model": None, "threshold": policy["threshold"],
            "policy_sha256": hashlib.sha256(dump(policy).encode()).hexdigest(),
            "summary": {s: sum(r["status"] == s for r in results) for s in ("pass", "fail", "review")},
            "results": results}


def make_server(port=8765):
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def send(self, code, body, content_type="application/json"):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

        def valid_host(self):
            return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

        def do_GET(self):
            if not self.valid_host():
                return self.send(403, b'{"error":"Invalid host"}')
            assets = {"/": ("index.html", "text/html; charset=utf-8"),
                      "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                      "/style.css": ("style.css", "text/css; charset=utf-8")}
            if self.path not in assets:
                return self.send(404, b'{"error":"Not found"}')
            name, mime = assets[self.path]
            body = files("jev_eval").joinpath("static", name).read_text().replace("__TOKEN__", token)
            self.send(200, body.encode(), mime)

        def do_POST(self):
            origin = f"http://127.0.0.1:{self.server.server_port}"
            if (not self.valid_host() or self.headers.get("Origin") != origin
                    or self.headers.get("X-JEV-Token") != token):
                return self.send(403, b'{"error":"Invalid request origin or token"}')
            if self.path != "/api/evaluate":
                return self.send(404, b'{"error":"Not found"}')
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= MAX_BYTES or self.headers.get("Content-Type") != "application/json":
                    raise InputError("Invalid body")
                self.connection.settimeout(10)
                result = audit(parse(self.rfile.read(length).decode("utf-8")))
                self.send(200, json.dumps(result).encode())
            except (ValueError, OSError, RecursionError):
                self.send(400, b'{"error":"Invalid trace data. Check schema, size, and tool names."}')

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def serve(port=8765):
    with make_server(port) as server:
        print(f"JEV local UI: http://127.0.0.1:{server.server_port} (offline; Ctrl-C to stop)", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass

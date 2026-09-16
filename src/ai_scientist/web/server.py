import hmac
import json
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .api import ReviewAPI


def handler(api: ReviewAPI, token: str):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # Do not log imported messages or authentication material.

        def respond(self, status, body: bytes, content_type="application/json"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'"
            )
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            hosts = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            if self.headers.get("Host") not in hosts:
                self.respond(403, b'{"error":"invalid host"}')
                return
            if self.path in {"/", "/app.js", "/style.css"}:
                name, mime = {
                    "/": ("index.html", "text/html; charset=utf-8"),
                    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                    "/style.css": ("style.css", "text/css; charset=utf-8"),
                }[self.path]
                self.respond(200, (Path(__file__).parent / "ui" / name).read_bytes(), mime)
                return
            authorization = self.headers.get("Authorization", "")
            if not hmac.compare_digest(authorization.encode(), f"Bearer {token}".encode()):
                self.respond(401, b'{"error":"authentication required"}')
                return
            try:
                result = api.get(self.path)
            except KeyError:
                self.respond(404, b'{"error":"not found"}')
                return
            self.respond(200, json.dumps(result).encode())

        def do_POST(self):
            self.respond(405, b'{"error":"read-only API; use CLI for approvals"}')

    return Handler


def serve(store, port: int = 8765):
    token = secrets.token_urlsafe(32)
    with ThreadingHTTPServer(("127.0.0.1", port), handler(ReviewAPI(store), token)) as server:
        print(f"Review workspace: http://127.0.0.1:{server.server_port}/#{token}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass

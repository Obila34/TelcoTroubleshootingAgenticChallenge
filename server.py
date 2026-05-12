"""
Local stub for API smoke tests.

Supports:
- Legacy: POST /tool/{name} with JSON body -> {"output": "..."}
- Track B README shape: POST /ip/api/agent/execute with
  {"device_name","command","question_number"} -> {"output": "..."}

Point telco-agent/.env at http://127.0.0.1:8000/ip/api/agent/execute via AGENT_EXECUTE_URL
when testing against this stub.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse


class ToolHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            params = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            params = {}

        if path.startswith("/tool/"):
            prefix = "/tool/"
            tool_name = path[len(prefix) :].strip("/")
            output = f"[stub-tool] {tool_name} {params}"
        elif "/agent/execute" in path or path.rstrip("/").endswith("execute"):
            output = f"[stub-execute] {params}"
        else:
            # Local smoke test: any other POST behaves like execute so URL typos still return JSON.
            output = f"[stub-execute] path={path!r} body={params}"

        body = json.dumps({"output": output}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        return


def main() -> None:
    host = "127.0.0.1"
    port = 8000
    httpd = HTTPServer((host, port), ToolHandler)
    print(f"Stub server: POST /tool/... or .../agent/execute on http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()

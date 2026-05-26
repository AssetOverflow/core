"""Stdlib HTTP server entrypoint for CORE Workbench W-026."""

from __future__ import annotations

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from workbench.api import WorkbenchApi


class WorkbenchRequestHandler(BaseHTTPRequestHandler):
    api = WorkbenchApi()

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        self._handle()

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        self._handle()

    def log_message(self, format: str, *args: object) -> None:
        if os.environ.get("CORE_WORKBENCH_QUIET") == "1":
            return
        sys.stderr.write(
            "%s - - [%s] %s\n"
            % (self.address_string(), self.log_date_time_string(), format % args)
        )

    def _handle(self) -> None:
        try:
            length = max(0, int(self.headers.get("Content-Length") or "0"))
        except ValueError:
            length = 0
        body = self.rfile.read(length) if length else b""
        response = self.api.handle(self.command, self.path, body)
        payload = json.dumps(response.payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.send_response(response.status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def serve(*, host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), WorkbenchRequestHandler)
    print(f"CORE Workbench API listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
        raise SystemExit(0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CORE Workbench local API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--allow-nonlocal-bind",
        action="store_true",
        help="allow binding to a host other than 127.0.0.1 or localhost",
    )
    args = parser.parse_args(argv)
    if args.host not in {"127.0.0.1", "localhost"} and not args.allow_nonlocal_bind:
        parser.error("non-local bind requires --allow-nonlocal-bind")
    serve(host=args.host, port=args.port)


if __name__ == "__main__":
    raise SystemExit(main())

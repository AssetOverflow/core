"""Small stdlib route layer for CORE Workbench W-026."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from workbench import readers
from workbench.schemas import error, ok


@dataclass(frozen=True, slots=True)
class ApiResponse:
    status: int
    payload: dict[str, Any]


class WorkbenchApi:
    def handle(self, method: str, raw_path: str, body: bytes = b"") -> ApiResponse:
        parsed = urlparse(raw_path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)
        try:
            return self._dispatch(method.upper(), path, query, body)
        except json.JSONDecodeError as exc:
            return ApiResponse(400, error("bad_request", "invalid JSON body", detail=str(exc)))
        except ValueError as exc:
            return ApiResponse(400, error("bad_request", str(exc)))
        except FileNotFoundError as exc:
            missing = str(exc) or "resource"
            return ApiResponse(404, error("not_found", f"not found: {missing}"))
        except OSError as exc:
            return ApiResponse(500, error("read_error", str(exc)))

    def _dispatch(
        self,
        method: str,
        path: str,
        query: dict[str, list[str]],
        body: bytes,
    ) -> ApiResponse:
        if method == "GET" and path == "/health":
            return ApiResponse(200, ok({"status": "ok"}))
        if method == "GET" and path == "/runtime/status":
            return ApiResponse(200, ok(readers.runtime_status()))
        if method == "GET" and path == "/artifacts":
            limit = int(query.get("limit", ["100"])[0])
            return ApiResponse(200, ok({"items": readers.list_artifacts(limit=limit)}))
        if method == "GET" and path.startswith("/artifacts/"):
            artifact_id = unquote(path.removeprefix("/artifacts/"))
            return ApiResponse(200, ok(readers.read_artifact(artifact_id)))
        if method == "GET" and path == "/proposals":
            return ApiResponse(200, ok({"items": readers.list_proposals()}))
        if method == "GET" and path.startswith("/proposals/"):
            proposal_id = unquote(path.removeprefix("/proposals/"))
            return ApiResponse(200, ok(readers.read_proposal(proposal_id)))
        if method == "GET" and path == "/evals":
            return ApiResponse(200, ok({"lanes": readers.list_eval_lanes()}))
        if method == "GET" and path.startswith("/evals/"):
            lane = unquote(path.removeprefix("/evals/"))
            return ApiResponse(200, ok(readers.read_eval_lane(lane)))
        if method == "POST" and path == "/evals/run":
            request = json.loads(body.decode("utf-8") or "{}")
            if not isinstance(request, dict):
                return ApiResponse(400, error("bad_request", "eval request must be an object"))
            try:
                result = readers.run_safe_eval_lane(
                    str(request.get("lane") or ""),
                    version=str(request.get("version") or "v1"),
                    split=str(request.get("split") or "public"),
                )
            except FileNotFoundError as exc:
                return ApiResponse(404, error("not_found", str(exc)))
            except ValueError as exc:
                return ApiResponse(400, error("bad_request", str(exc)))
            return ApiResponse(200, ok(result))
        if method == "GET" and path.startswith("/trace/"):
            return ApiResponse(404, error("not_found", "trace storage is not wired in W-026"))
        if (
            (method == "POST" and path == "/chat/turn")
            or (method == "GET" and path.startswith("/replay/"))
        ):
            return ApiResponse(501, error("unsupported", "route is deferred beyond W-026"))
        return ApiResponse(404, error("not_found", f"route not found: {method} {path}"))

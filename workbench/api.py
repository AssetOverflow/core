"""Small stdlib route layer for CORE Workbench W-026."""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from chat.runtime import ChatRuntime
from core.epistemic_state import (
    clearance_from_verdicts,
    coerce_normative_clearance,
    epistemic_state_for_grounding_source,
    normative_detail_from_verdicts,
)
from workbench import readers
from workbench.readers import ArtifactTooLargeError
from workbench.schemas import ChatTurnResult, ProposalRef, TurnVerdict, error, ok


MAX_CHAT_BODY_BYTES = 64 * 1024
MAX_CHAT_PROMPT_CHARS = 4096
_CHAT_TURN_LOCK = threading.Lock()


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
        except ArtifactTooLargeError as exc:
            return ApiResponse(413, error("read_error", str(exc)))
        except OSError as exc:
            return ApiResponse(500, error("read_error", str(exc)))
        except Exception as exc:  # noqa: BLE001 - API contract requires JSON errors.
            return ApiResponse(500, error("runtime_unavailable", f"internal error: {exc}"))

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
        if method == "POST" and path == "/chat/turn":
            return self._chat_turn(body)
        if method == "GET" and path.startswith("/trace/"):
            return ApiResponse(404, error("not_found", "trace storage is not wired in W-026"))
        if method == "GET" and path.startswith("/replay/"):
            return ApiResponse(501, error("unsupported", "route is deferred beyond W-026"))
        return ApiResponse(404, error("not_found", f"route not found: {method} {path}"))

    def _chat_turn(self, body: bytes) -> ApiResponse:
        """Execute one live runtime turn.

        ADR-0160 v1 is single-operator-local-only, so chat turns are serialized
        through the module-level ``_CHAT_TURN_LOCK``.
        """
        if len(body) > MAX_CHAT_BODY_BYTES:
            return ApiResponse(
                413,
                error("read_error", f"chat request exceeds {MAX_CHAT_BODY_BYTES} byte limit"),
            )
        request = json.loads(body.decode("utf-8") or "{}")
        if not isinstance(request, dict):
            return ApiResponse(400, error("bad_request", "chat request must be an object"))
        prompt = request.get("prompt")
        if not isinstance(prompt, str):
            return ApiResponse(400, error("bad_request", "prompt must be a string"))
        stripped = prompt.strip()
        if not stripped:
            return ApiResponse(400, error("bad_request", "prompt must be non-empty"))
        if len(prompt) > MAX_CHAT_PROMPT_CHARS:
            return ApiResponse(
                400,
                error("bad_request", f"prompt exceeds {MAX_CHAT_PROMPT_CHARS} character limit"),
            )
        with _CHAT_TURN_LOCK:
            started = time.perf_counter()
            result = _run_chat_turn(prompt)
            elapsed_ms = max(0, int(round((time.perf_counter() - started) * 1000)))
            return ApiResponse(200, ok(_with_turn_cost(result, elapsed_ms)))


def _with_turn_cost(result: ChatTurnResult, turn_cost_ms: int) -> ChatTurnResult:
    from dataclasses import replace

    return replace(result, turn_cost_ms=turn_cost_ms)


def _coerce_grounding_source(value: object) -> str:
    text = str(value or "none").strip().lower()
    return text if text in {"pack", "teaching", "vault", "partial", "oov", "none"} else "none"


def _identity_verdict(identity_score: object | None) -> TurnVerdict | None:
    if identity_score is None:
        return None
    flagged = bool(getattr(identity_score, "flagged", False))
    axes = tuple(getattr(identity_score, "deviation_axes", ()) or ())
    detail = ",".join(sorted(str(axis) for axis in axes))
    return TurnVerdict(
        outcome="violated" if flagged else "cleared",
        runtime_detail=detail,
    )


def _normative_verdict(verdict: object | None, *, ids_attr: str) -> TurnVerdict | None:
    if verdict is None:
        return None
    upheld = bool(getattr(verdict, "upheld", True))
    runtime_checkable_count = int(getattr(verdict, "runtime_checkable_count", 0) or 0)
    ids = tuple(getattr(verdict, ids_attr, ()) or ())
    if not upheld:
        return TurnVerdict(
            outcome="violated",
            runtime_detail=",".join(sorted(str(item) for item in ids)),
        )
    if runtime_checkable_count <= 0:
        return TurnVerdict(outcome="unassessable", runtime_detail="")
    return TurnVerdict(outcome="cleared", runtime_detail="")


def _proposal_refs(runtime: ChatRuntime, before_ids: set[str]) -> list[ProposalRef]:
    refs: list[ProposalRef] = []
    for candidate in getattr(runtime, "_pending_candidates", ()) or ():
        candidate_id = str(getattr(candidate, "candidate_id", "") or "")
        if not candidate_id or candidate_id in before_ids:
            continue
        refs.append(ProposalRef(candidate_id=candidate_id, source_kind="discovery"))
    return refs


def _run_chat_turn(prompt: str) -> ChatTurnResult:
    runtime = ChatRuntime()
    before_candidate_ids = {
        str(getattr(candidate, "candidate_id", "") or "")
        for candidate in getattr(runtime, "_pending_candidates", ()) or ()
    }
    checkpoint_emitted = False
    original_checkpoint = runtime.checkpoint_engine_state

    def tracked_checkpoint() -> None:
        nonlocal checkpoint_emitted
        checkpoint_emitted = True
        original_checkpoint()

    runtime.checkpoint_engine_state = tracked_checkpoint  # type: ignore[method-assign]
    response = runtime.chat(prompt)
    turn_event = runtime.turn_log[-1] if runtime.turn_log else None
    verdicts = getattr(response, "verdicts", None)
    grounding_source = _coerce_grounding_source(getattr(response, "grounding_source", "none"))
    normative_clearance = coerce_normative_clearance(
        getattr(response, "normative_clearance", None)
        or clearance_from_verdicts(verdicts)
    ).value
    normative_detail = str(
        getattr(response, "normative_detail", None)
        or normative_detail_from_verdicts(verdicts)
        or ""
    )
    refusal_emitted = bool(getattr(verdicts, "refusal_emitted", False))
    if (
        not refusal_emitted
        and normative_clearance == "violated"
        and response.surface.startswith("I don't know")
    ):
        refusal_emitted = True
        normative_clearance = "suppressed"
    trace_hash = str(getattr(turn_event, "trace_hash", "") or "") if turn_event else ""
    return ChatTurnResult(
        prompt=prompt,
        surface=response.surface,
        articulation_surface=response.articulation_surface or None,
        walk_surface=response.walk_surface or None,
        grounding_source=grounding_source,  # type: ignore[arg-type]
        epistemic_state=epistemic_state_for_grounding_source(grounding_source).value,  # type: ignore[arg-type]
        normative_clearance=normative_clearance,  # type: ignore[arg-type]
        normative_detail=normative_detail,
        trace_hash=trace_hash or None,
        refusal_emitted=refusal_emitted,
        hedge_injected=bool(getattr(verdicts, "hedge_injected", False)),
        mutation_mode="runtime_turn",
        identity_verdict=_identity_verdict(getattr(response, "identity_score", None)),
        safety_verdict=_normative_verdict(
            getattr(response, "safety_verdict", None),
            ids_attr="violated_boundaries",
        ),
        ethics_verdict=_normative_verdict(
            getattr(response, "ethics_verdict", None),
            ids_attr="violated_commitments",
        ),
        proposal_candidates=_proposal_refs(runtime, before_candidate_ids),
        turn_cost_ms=0,
        checkpoint_emitted=checkpoint_emitted,
    )

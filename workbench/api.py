"""Small stdlib route layer for CORE Workbench W-026."""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from core.epistemic_state import (
    clearance_from_verdicts,
    coerce_normative_clearance,
    epistemic_state_for_grounding_source,
    normative_detail_from_verdicts,
)
from workbench import readers
from workbench.journal import DEFAULT_JOURNAL_DIR, TurnJournal, TurnJournalEntry
from workbench.readers import ArtifactTooLargeError, EvidenceUnavailableError
from workbench.replay import replay_turn
from workbench.schemas import ChatTurnResult, MathRatifyResult, ProposalRef, TurnVerdict, error, ok


MAX_CHAT_BODY_BYTES = 64 * 1024
MAX_CHAT_PROMPT_CHARS = 4096
_CHAT_TURN_LOCK = threading.Lock()


def _pagination(
    query: dict[str, list[str]],
    *,
    default_limit: int = 100,
) -> tuple[int, int]:
    limit = int(query.get("limit", [str(default_limit)])[0])
    offset = int(query.get("offset", ["0"])[0])
    if limit < 0:
        raise ValueError("limit must be non-negative")
    if offset < 0:
        raise ValueError("offset must be non-negative")
    return limit, offset


@dataclass(frozen=True, slots=True)
class ApiResponse:
    status: int
    payload: dict[str, Any]


class WorkbenchApi:
    def __init__(
        self,
        telemetry_sink: Any | None = None,
        *,
        journal: TurnJournal | None = None,
        journal_dir: Any | None = None,
    ) -> None:
        self._telemetry_sink = telemetry_sink
        self._journal = journal or TurnJournal(
            DEFAULT_JOURNAL_DIR if journal_dir is None else Path(journal_dir)
        )

    def attach_telemetry_sink(self, sink: Any | None) -> None:
        self._telemetry_sink = sink

    def _emit_operator_telemetry(
        self,
        event_name: str,
        proposal_id: str,
        outcome: str | None = None,
        handler: str | None = None,
        note: str | None = None,
    ) -> None:
        if self._telemetry_sink is None:
            return
        payload: dict[str, Any] = {
            "event": event_name,
            "proposal_id": proposal_id,
            "ratifier_kind": "workbench",
        }
        if handler is not None:
            payload["handler"] = handler
        if outcome is not None:
            payload["outcome"] = outcome
        if note is not None:
            payload["note"] = note
        line = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        self._telemetry_sink.emit(line)

    def handle(self, method: str, raw_path: str, body: bytes = b"") -> ApiResponse:
        parsed = urlparse(raw_path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)
        try:
            return self._dispatch(method.upper(), path, query, body)
        except json.JSONDecodeError as exc:
            return ApiResponse(400, error("bad_request", "invalid JSON body", detail=str(exc)))
        except ValueError as exc:
            status = 400
            msg = str(exc)
            if "already ratified" in msg.lower():
                status = 409
            return ApiResponse(status, error("bad_request", msg))
        except FileNotFoundError as exc:
            missing = str(exc) or "resource"
            return ApiResponse(404, error("not_found", f"not found: {missing}"))
        except EvidenceUnavailableError as exc:
            return ApiResponse(501, error("evidence_unavailable", str(exc)))
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
        if method == "GET" and path == "/math-proposals":
            return ApiResponse(200, ok({"items": readers.list_math_proposals()}))
        if method == "POST" and path.endswith("/ratify") and path.startswith("/math-proposals/"):
            proposal_id = unquote(path.removeprefix("/math-proposals/").removesuffix("/ratify"))
            return self._math_ratify(proposal_id, body)
        if method == "POST" and path.endswith("/reject") and path.startswith("/math-proposals/"):
            proposal_id = unquote(path.removeprefix("/math-proposals/").removesuffix("/reject"))
            return self._math_reject(proposal_id, body)
        if method == "POST" and path.endswith("/defer") and path.startswith("/math-proposals/"):
            proposal_id = unquote(path.removeprefix("/math-proposals/").removesuffix("/defer"))
            return self._math_defer(proposal_id)
        if method == "GET" and path.startswith("/math-proposals/"):
            proposal_id = unquote(path.removeprefix("/math-proposals/"))
            return ApiResponse(200, ok(readers.read_math_proposal(proposal_id)))
        if method == "GET" and path == "/packs":
            limit, offset = _pagination(query)
            return ApiResponse(
                200,
                ok(
                    {
                        "items": readers.list_packs(limit=limit, offset=offset),
                        "limit": limit,
                        "offset": offset,
                    }
                ),
            )
        if method == "GET" and path.startswith("/packs/"):
            pack_id = unquote(path.removeprefix("/packs/"))
            return ApiResponse(200, ok(readers.read_pack(pack_id)))
        if method == "GET" and path == "/audit/events":
            limit, offset = _pagination(query)
            return ApiResponse(
                200,
                ok(
                    {
                        "items": readers.list_audit_events(limit=limit, offset=offset),
                        "limit": limit,
                        "offset": offset,
                    }
                ),
            )
        if method == "GET" and path == "/runs":
            limit, offset = _pagination(query)
            return ApiResponse(
                200,
                ok(
                    {
                        "items": readers.list_runs(self._journal, limit=limit, offset=offset),
                        "limit": limit,
                        "offset": offset,
                    }
                ),
            )
        if method == "GET" and path.startswith("/runs/"):
            session_id = unquote(path.removeprefix("/runs/"))
            turn_limit, turn_offset = _pagination(query)
            return ApiResponse(
                200,
                ok(
                    readers.read_run(
                        session_id,
                        self._journal,
                        turn_limit=turn_limit,
                        turn_offset=turn_offset,
                    )
                ),
            )
        if method == "GET" and path == "/vault/summary":
            return ApiResponse(200, ok(readers.read_vault_summary()))
        if method == "GET" and path == "/vault/entries":
            limit, offset = _pagination(query)
            return ApiResponse(
                200,
                ok(
                    {
                        "items": readers.list_vault_entries(limit=limit, offset=offset),
                        "limit": limit,
                        "offset": offset,
                    }
                ),
            )
        if method == "GET" and path == "/demos":
            return ApiResponse(200, ok({"items": readers.list_demos()}))
        if method == "POST" and path.endswith("/run") and path.startswith("/demos/"):
            demo_id = unquote(path.removeprefix("/demos/").removesuffix("/run"))
            try:
                return ApiResponse(200, ok(readers.run_demo(demo_id)))
            except FileNotFoundError as exc:
                return ApiResponse(404, error("not_found", str(exc) or demo_id))
            except ValueError as exc:
                return ApiResponse(400, error("bad_request", str(exc)))
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
        if method == "GET" and path == "/trace/turns":
            limit = int(query.get("limit", ["50"])[0])
            offset = int(query.get("offset", ["0"])[0])
            items = self._journal.list_summaries(limit=limit, offset=offset)
            return ApiResponse(200, ok({"items": items}))
        if method == "GET" and path.startswith("/trace/"):
            raw_turn_id = unquote(path.removeprefix("/trace/"))
            try:
                turn_id = int(raw_turn_id)
            except ValueError:
                return ApiResponse(404, error("not_found", f"trace turn not found: {raw_turn_id}"))
            try:
                return ApiResponse(200, ok(self._journal.get_entry(turn_id)))
            except FileNotFoundError:
                return ApiResponse(404, error("not_found", f"trace turn not found: {turn_id}"))
        if method == "GET" and path.startswith("/replay/"):
            raw_turn_id = unquote(path.removeprefix("/replay/"))
            try:
                turn_id = int(raw_turn_id)
            except ValueError:
                return ApiResponse(404, error("not_found", f"replay turn not found: {raw_turn_id}"))
            try:
                entry = self._journal.get_entry(turn_id)
            except FileNotFoundError:
                return ApiResponse(404, error("not_found", f"replay turn not found: {turn_id}"))
            if entry.trace_integrity != "pipeline_trace":
                return ApiResponse(
                    501,
                    error(
                        "evidence_unavailable",
                        "replay unavailable: turn has no canonical pipeline trace hash",
                    ),
                )
            # Replay executes a real runtime turn; serialize with live chat
            # turns the same way POST /chat/turn does.
            with _CHAT_TURN_LOCK:
                try:
                    comparison = replay_turn(entry, execute=_run_sealed_chat_turn)
                except Exception as exc:  # no comparison may be fabricated
                    return ApiResponse(
                        500, error("runtime_unavailable", f"replay failed: {exc}")
                    )
            return ApiResponse(200, ok(comparison))
        return ApiResponse(404, error("not_found", f"route not found: {method} {path}"))

    def _math_ratify(self, proposal_id: str, body: bytes) -> ApiResponse:
        """Route ratification by change_kind; in-process execution with allowlist checks."""
        category: str | None = None
        polarity: str | None = None
        dry_run: bool = False

        if body:
            try:
                req = json.loads(body.decode("utf-8") or "{}")
                if isinstance(req, dict):
                    category = req.get("category")
                    polarity = req.get("polarity")
                    dry_run = bool(req.get("dry_run", False))
            except Exception as exc:
                return ApiResponse(400, error("bad_request", "invalid JSON body", detail=str(exc)))

        import getpass
        reviewer = getpass.getuser()

        try:
            result: MathRatifyResult = readers.ratify_math_proposal(
                proposal_id,
                category=category,
                polarity=polarity,
                reviewer=reviewer,
                dry_run=dry_run,
            )
        except NotImplementedError as exc:
            return ApiResponse(501, error("unsupported", str(exc)))
        except (ValueError, FileNotFoundError) as exc:
            msg = str(exc)
            handler = "unknown"
            try:
                prop = readers.read_math_proposal(proposal_id)
                handler = prop.handler_name or "unknown"
            except Exception:
                pass
            status_code = 400
            exc_class_name = exc.__class__.__name__
            if exc_class_name == "AlreadyRatified" or "already ratified" in msg.lower():
                status_code = 409

            self._emit_operator_telemetry(
                event_name="operator_ratify",
                proposal_id=proposal_id,
                outcome="rejected_precondition",
                handler=handler,
            )
            return ApiResponse(status_code, error("bad_request", msg))
        except Exception as exc:
            return ApiResponse(500, error("runtime_unavailable", f"internal error: {exc}"))

        if result.applied:
            self._emit_operator_telemetry(
                event_name="operator_ratify",
                proposal_id=proposal_id,
                outcome="applied",
                handler=result.handler_name,
            )
        return ApiResponse(200, ok(result))

    def _math_reject(self, proposal_id: str, body: bytes) -> ApiResponse:
        note: str = ""
        if body:
            try:
                req = json.loads(body.decode("utf-8") or "{}")
                if isinstance(req, dict):
                    note = str(req.get("note", ""))
            except Exception as exc:
                return ApiResponse(400, error("bad_request", "invalid JSON body", detail=str(exc)))
        try:
            prop = readers.read_math_proposal(proposal_id)
            handler = prop.handler_name or "unknown"
        except FileNotFoundError as exc:
            return ApiResponse(404, error("not_found", str(exc)))

        self._emit_operator_telemetry(
            event_name="operator_reject",
            proposal_id=proposal_id,
            handler=handler,
            note=note,
        )
        return ApiResponse(200, ok({"proposal_id": proposal_id, "rejected": True}))

    def _math_defer(self, proposal_id: str) -> ApiResponse:
        try:
            prop = readers.read_math_proposal(proposal_id)
            handler = prop.handler_name or "unknown"
        except FileNotFoundError as exc:
            return ApiResponse(404, error("not_found", str(exc)))

        self._emit_operator_telemetry(
            event_name="operator_defer",
            proposal_id=proposal_id,
            handler=handler,
        )
        return ApiResponse(200, ok({"proposal_id": proposal_id, "deferred": True}))

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
            if not result.trace_hash:
                return ApiResponse(
                    500,
                    error(
                        "runtime_unavailable",
                        "chat turn did not produce a canonical pipeline trace hash",
                    ),
                )
            elapsed_ms = max(0, int(round((time.perf_counter() - started) * 1000)))
            turn_id = self._journal.next_turn_id()
            result_with_cost = _with_turn_cost_and_id(result, elapsed_ms, turn_id)
            entry = TurnJournalEntry.from_chat_turn(result_with_cost, turn_id=turn_id)
            self._journal.append(entry)
            return ApiResponse(200, ok(result_with_cost))


def _with_turn_cost_and_id(
    result: ChatTurnResult,
    turn_cost_ms: int,
    turn_id: int,
) -> ChatTurnResult:
    from dataclasses import replace

    return replace(result, turn_cost_ms=turn_cost_ms, turn_id=turn_id)


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


def _run_sealed_chat_turn(prompt: str) -> ChatTurnResult:
    """Replay executor: same envelope assembly, sealed runtime.

    ``no_load_state=True`` nulls the engine-state store by construction —
    no checkpoint load, ``checkpoint_engine_state`` no-ops, no proposal-log
    lineage — so a replay can neither read nor leave runtime state.
    """
    return _run_chat_turn(prompt, runtime=ChatRuntime(no_load_state=True))


def _run_chat_turn(prompt: str, runtime: ChatRuntime | None = None) -> ChatTurnResult:
    if runtime is None:
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
    try:
        result = CognitiveTurnPipeline(runtime).run(prompt)
    finally:
        runtime.checkpoint_engine_state = original_checkpoint  # type: ignore[method-assign]
    turn_event = runtime.turn_log[-1] if runtime.turn_log else None
    verdicts = getattr(turn_event, "verdicts", None)
    grounding_source = _coerce_grounding_source(getattr(turn_event, "grounding_source", "none"))
    normative_clearance = coerce_normative_clearance(
        getattr(turn_event, "normative_clearance", None)
        or clearance_from_verdicts(verdicts)
    ).value
    normative_detail = str(
        getattr(turn_event, "normative_detail", None)
        or normative_detail_from_verdicts(verdicts)
        or ""
    )
    refusal_emitted = bool(getattr(verdicts, "refusal_emitted", False))
    if (
        not refusal_emitted
        and normative_clearance == "violated"
        and result.surface.startswith("I don't know")
    ):
        refusal_emitted = True
        normative_clearance = "suppressed"
    trace_hash = result.trace_hash or (
        str(getattr(turn_event, "trace_hash", "") or "") if turn_event else ""
    )
    epistemic_state = str(
        getattr(turn_event, "epistemic_state", "")
        or epistemic_state_for_grounding_source(grounding_source).value
    )
    return ChatTurnResult(
        prompt=prompt,
        surface=result.surface,
        articulation_surface=result.articulation_surface or None,
        walk_surface=result.walk_surface or None,
        grounding_source=grounding_source,  # type: ignore[arg-type]
        epistemic_state=epistemic_state,  # type: ignore[arg-type]
        normative_clearance=normative_clearance,  # type: ignore[arg-type]
        normative_detail=normative_detail,
        trace_hash=trace_hash or None,
        refusal_emitted=refusal_emitted,
        hedge_injected=bool(getattr(verdicts, "hedge_injected", False)),
        mutation_mode="runtime_turn",
        identity_verdict=_identity_verdict(result.identity_score),
        safety_verdict=_normative_verdict(
            getattr(turn_event, "safety_verdict", None),
            ids_attr="violated_boundaries",
        ),
        ethics_verdict=_normative_verdict(
            getattr(turn_event, "ethics_verdict", None),
            ids_attr="violated_commitments",
        ),
        proposal_candidates=_proposal_refs(runtime, before_candidate_ids),
        turn_cost_ms=0,
        checkpoint_emitted=checkpoint_emitted,
    )

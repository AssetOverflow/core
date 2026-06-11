"""The System 2 side of the boundary: typed payload in, audited decision out.

This module is deliberately unable to commit an answer on its own:

* It imports **nothing from ``generate.*``** — the derivation lane is consulted
  exclusively through the ADR-0184 S4b audited trace facade
  (:mod:`evals.gsm8k_math.equivalence.trace`), whose ``problem_trace`` runs the
  real semantic-state worlds -> replay -> pool -> verifier pipeline and returns
  pure data.  The demo cannot construct a ``Resolution``, call the pool, or touch
  a composer; it can only read what the authorities decided.
* ``status == "verified"`` requires ALL of: the pool committed a resolution; the
  trace passes the commit-law audit (:func:`authority_violations`) and the
  world-faithfulness audit (:func:`replay_faithfulness_report`); the problem is in
  the committed, gold-audited **demo serving envelope** (``envelope.json``); and
  the live derivation trace byte-matches the envelope's pinned reference.  A pool
  commit outside that envelope is REFUSED — the off-serving derivation lane is
  not a wrong=0 oracle over arbitrary text (measured: 118 of its 231 commits on
  the 937-problem ADR-0184 corpus disagree with lane gold), and serving such a
  commit would be a false epistemic status.  Fail-closed beats impressive.
* The ASK leg never fabricates a question: a pool refusal (no committed
  resolution) is routed through the real organs (``route_setup`` ->
  ``assess_from_attempt``) and a question exists only
  if the Q1-D producer (:func:`emit_question`) renders one under its wrong=0
  grounding guards; it is then served only through the carried-handle seam
  (:mod:`core.epistemic_disclosure.ask_handle`), whose content-hash verification
  and artifact policy stay sole authority over the served text.

The ASK serving gate is dark by default repo-wide; this demo enables it ONLY via
its own local config object (:data:`DEMO_ASK_SERVING_CONFIG`), never by touching
``core.config``.  Trust boundary: ``problem_text`` is untrusted text and is
handed only to organs built for raw problem text; the question handle is
constructed here (demo-scoped plumbing) from the producer's own content-addressed
output, never parsed from caller input.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

from core.comprehension_attempt.router import route_setup
from core.epistemic_disclosure.ask_acquisition import acquire_served_ask_candidate
from core.epistemic_disclosure.ask_handle import (
    AskArtifactHandle,
    resolve_served_ask_handle,
)
from core.epistemic_disclosure.limitation import LimitationAssessment, assess_from_attempt
from core.epistemic_questions.delivery import emit_question
from core.epistemic_questions.serving_gate import ask_serving_enabled
from evals.gsm8k_math.equivalence.trace import (
    authority_violations,
    load_expected_traces,
    load_manifest,
    problem_trace,
    replay_faithfulness_report,
    trace_line,
)

from demos.claude_hybrid_verification.schema import load_tool_schema, validate_payload

_HERE: Final[Path] = Path(__file__).resolve().parent
ENVELOPE_PATH: Final[Path] = _HERE / "envelope.json"

TOOL_NAME: Final[str] = "core.semantic_derivation.verify"

#: Stable authority-path tokens — the module-qualified deciders, in consulted
#: order, listed ONLY when actually consulted (an unconsulted authority in this
#: list would itself be a false epistemic label).  The proposer appears nowhere
#: in this list; that absence is the demo's thesis.
_AUTHORITIES_DERIVATION: Final[tuple[str, ...]] = (
    "demos.claude_hybrid_verification.schema.validate_payload",
    "generate.derivation.state.source.semantic_state_candidates",
    "generate.derivation.pool.pooled_candidates",
    "generate.derivation.verify.classify_derivation",
    "generate.derivation.pool.resolve_pooled",
    "generate.derivation.state.provenance.faithfulness_violations",
    "evals.gsm8k_math.equivalence.trace.authority_violations",
    "adr0184_pinned_corpus(evals/gsm8k_math/equivalence/v1)",
    "demo_serving_envelope(envelope.json)",
)
#: The ASK pipeline in stage order; :func:`_attempt_ask` reports the prefix it
#: actually reached, so a gate-dark or no-ask refusal never names organs that
#: were not consulted.
_AUTHORITIES_ASK: Final[tuple[str, ...]] = (
    "core.comprehension_attempt.router.route_setup",
    "core.epistemic_disclosure.limitation.assess_from_attempt",
    "core.epistemic_questions.delivery.emit_question",
    "core.epistemic_disclosure.ask_handle.resolve_served_ask_handle",
    "core.epistemic_disclosure.ask_acquisition.acquire_served_ask_candidate",
    "core.epistemic_disclosure.ask_serving.evaluate_served_ask",
)


@dataclass(frozen=True, slots=True)
class DemoAskServingConfig:
    """Demo-local ASK gate config.  The runtime-wide default stays dark; enabling
    here affects only seam calls this demo makes with this object."""

    ask_serving_enabled: bool = True


DEMO_ASK_SERVING_CONFIG: Final[DemoAskServingConfig] = DemoAskServingConfig()


@dataclass(frozen=True, slots=True)
class AskOutcome:
    """What the ASK leg did, as inert trace data.  ``authorities`` is the prefix
    of :data:`_AUTHORITIES_ASK` that was actually consulted before the leg
    resolved — never the whole pipeline by default."""

    attempted: bool
    served: bool
    detail: str
    authorities: tuple[str, ...] = ()
    question: str | None = None
    blocking_reason: str | None = None
    owner_organ: str | None = None
    question_ref: str | None = None  # out_dir-relative, deterministic
    content_hash: str | None = None

    def to_trace_dict(self) -> dict[str, Any]:
        return {
            "attempted": self.attempted,
            "served": self.served,
            "detail": self.detail,
            "question": self.question,
            "blocking_reason": self.blocking_reason,
            "owner_organ": self.owner_organ,
            "question_ref": self.question_ref,
            "content_hash": self.content_hash,
        }


_ASK_NOT_ATTEMPTED: Final[AskOutcome] = AskOutcome(
    attempted=False, served=False, detail="not_attempted"
)


def _envelope() -> dict[str, Any]:
    """The committed serving envelope, re-read per call (a fresh object every
    time, so no shared-mutable cache can be poisoned in-process; the file is one
    entry and the cost is negligible)."""
    return json.loads(ENVELOPE_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _adr0184_pinned_by_sha() -> dict[str, dict[str, Any]]:
    """The 937-problem ADR-0184 pinned traces by sha.  Cached as immutable per
    the repo's caching doctrine: the mapping never escapes this module and is
    only ever compared against, never handed out or mutated."""
    return {str(t["problem_sha"]): t for t in load_expected_traces()}


def _adr0184_pin_status(trace: dict[str, Any]) -> str:
    pinned = _adr0184_pinned_by_sha().get(str(trace["problem_sha"]))
    if pinned is None:
        return "not_in_adr0184_corpus"
    return "equivalent_to_adr0184_pin" if pinned == trace else "drift_from_adr0184_pin"


def _derivation_trace_sha(trace: dict[str, Any]) -> str:
    return hashlib.sha256(trace_line(trace).encode("utf-8")).hexdigest()


def _format_quantity(value: float, unit: str) -> str:
    magnitude = str(int(value)) if float(value).is_integer() else str(value)
    return f"{magnitude} {unit}".strip()


def _refusal_reason(trace: dict[str, Any]) -> str:
    """A typed diagnostic label for a pool refusal, derived from trace data only.

    This mirrors the *documented* refusal order of ``resolve_pooled`` for display;
    it is never an authority — the demo asserts ``resolution is null`` before any
    refused status, so a mislabel here can rename a refusal but never mint a
    commit.  Reasons the pool enforces before pooling (e.g. the prior-state
    question-scope guard) land in the fail-closed catch-all.
    """
    pooled = trace["pooled"] or []
    classifications = trace["classifications"] or []
    classified = [
        (candidate, kind)
        for candidate, kind in zip(pooled, classifications)
        if kind is not None
    ]
    if not pooled:
        return "no_candidate_readings"
    if not classified:
        return "no_self_verifying_reading"
    answers = {round(float(candidate["answer"]), 9) for candidate, _ in classified}
    if len(answers) > 1:
        return "candidate_disagreement"
    if all(kind != "complete" for _, kind in classified):
        return "exempt_only_readings"
    return "pool_policy_refusal"


def _single_ask_assessment(problem_text: str) -> tuple[LimitationAssessment | None, str]:
    """The unique ask-mapped limitation for a refused problem, or why there is none.

    Fail-closed plumbing, not policy: zero ask-mapped organ attempts means the
    refusal stands; more than one means the demo refuses to pick (no 'best
    question' heuristic).  All question policy stays downstream in Q1-C/Q1-D and
    the serving adapter.
    """
    assessments = [
        assessment
        for attempt in route_setup(problem_text).attempts
        if (assessment := assess_from_attempt(attempt)) is not None
        and assessment.resolution_action == "ask_question"
    ]
    if not assessments:
        return None, "no_ask_mapped_attempt"
    if len(assessments) > 1:
        return None, "multiple_ask_mapped_attempts"
    return assessments[0], "single"


def _attempt_ask(
    problem_text: str,
    *,
    out_dir: Path,
    ask_config: Any,
    fallback_surface: str,
) -> AskOutcome:
    """Route a pool refusal through the real ASK stack.  Gate-first: while the
    config's gate is dark this performs no organ calls and no filesystem writes,
    mirroring the seam's side-effect-free dark-gate law.  ``authorities`` records
    exactly the pipeline prefix reached, so the response never names an
    unconsulted organ."""
    if not ask_serving_enabled(ask_config):
        return AskOutcome(attempted=True, served=False, detail="gate_disabled")

    assessment, why = _single_ask_assessment(problem_text)
    if assessment is None:
        return AskOutcome(
            attempted=True, served=False, detail=why, authorities=_AUTHORITIES_ASK[:2]
        )

    artifact_path = emit_question(assessment, root=out_dir / "questions")
    if artifact_path is None:
        # D2 guard: unrenderable asks fall back to the standing disposition —
        # never a contentless question.
        return AskOutcome(
            attempted=True,
            served=False,
            detail="question_unrenderable_fell_back",
            authorities=_AUTHORITIES_ASK[:3],
            blocking_reason=assessment.blocking_reason,
            owner_organ=assessment.owner_organ,
        )

    handle = AskArtifactHandle(
        question_path=str(artifact_path), content_hash=artifact_path.stem
    )
    resolution = resolve_served_ask_handle(ask_config, handle)
    if not resolution.resolved:
        return AskOutcome(
            attempted=True,
            served=False,
            detail=f"handle_not_resolved:{resolution.reason}",
            authorities=_AUTHORITIES_ASK[:4],
            blocking_reason=assessment.blocking_reason,
            owner_organ=assessment.owner_organ,
            question_ref=f"questions/{artifact_path.name}",
            content_hash=artifact_path.stem,
        )
    decision = acquire_served_ask_candidate(
        ask_config,
        fallback_surface=fallback_surface,
        contemplation_result=resolution.candidate,
    ).decision
    return AskOutcome(
        attempted=True,
        served=decision.served,
        detail="served" if decision.served else "not_served_by_adapter",
        authorities=_AUTHORITIES_ASK,
        question=decision.surface if decision.served else None,
        blocking_reason=assessment.blocking_reason,
        owner_organ=assessment.owner_organ,
        question_ref=f"questions/{artifact_path.name}",
        content_hash=artifact_path.stem,
    )


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _echoable_request_id(arguments: Any) -> str | None:
    """A request id is echoed only if it satisfies the schema pattern — the
    invalid path must not reflect arbitrary caller text into the response."""
    request_id = arguments.get("request_id") if isinstance(arguments, dict) else None
    if not isinstance(request_id, str):
        return None
    pattern = load_tool_schema()["inputSchema"]["properties"]["request_id"]["pattern"]
    return request_id if re.fullmatch(pattern, request_id) else None


def _invalid_response(arguments: Any, errors: tuple[str, ...]) -> dict[str, Any]:
    response: dict[str, Any] = {
        "tool": TOOL_NAME,
        "request_id": _echoable_request_id(arguments),
        "status": "invalid",
        "surface": "Invalid tool payload: " + "; ".join(errors),
        "answer": None,
        "answer_unit": None,
        "refusal_reason": None,
        "question": None,
        "authority_path": [_AUTHORITIES_DERIVATION[0]],
        "replay_equivalence_status": "not_evaluated",
        "trace_summary": {"validation_errors": list(errors)},
        "trace": None,
    }
    response["trace_hash"] = hashlib.sha256(_canonical(response).encode()).hexdigest()
    return response


@dataclass(frozen=True, slots=True)
class _Decision:
    """The decided outcome of one executed derivation, as inert data."""

    status: str
    surface: str
    answer: float | None = None
    answer_unit: str | None = None
    refusal_reason: str | None = None
    question: str | None = None
    ask: AskOutcome = _ASK_NOT_ATTEMPTED


def _refused(reason: str, ask: AskOutcome = _ASK_NOT_ATTEMPTED) -> _Decision:
    return _Decision(
        status="refused",
        surface=f"CORE refuses to serve an answer: {reason}.",
        refusal_reason=reason,
        ask=ask,
    )


def _decide(
    trace: dict[str, Any],
    *,
    envelope_entry: dict[str, Any] | None,
    derivation_sha: str,
    pin_status: str,
    commit_law_violations: list[str],
    faithfulness: list[str],
    problem_text: str,
    out_dir: Path,
    ask_config: Any,
) -> _Decision:
    """Map the audited trace to verified / refused / ask — fail-closed at every
    fork.  An internal audit trip refuses outright (never serve, never ask); a
    commit serves only under envelope authorization with no pinned-corpus drift;
    a pool refusal may upgrade to ASK only through the real Q1 stack."""
    if commit_law_violations or faithfulness:
        return _refused(
            "authority_violation_detected"
            if commit_law_violations
            else "provenance_violation_detected"
        )

    resolution = trace["resolution"]
    if resolution is not None:
        envelope_status = _envelope_status(envelope_entry, resolution, derivation_sha)
        if envelope_status == "authorized" and pin_status != "drift_from_adr0184_pin":
            answer = float(resolution["answer"])
            answer_unit = str(resolution["answer_unit"])
            return _Decision(
                status="verified",
                surface=_format_quantity(answer, answer_unit),
                answer=answer,
                answer_unit=answer_unit,
            )
        return _refused(
            "outside_demo_serving_envelope"
            if envelope_status == "absent"
            else "replay_drift_from_pinned_reference"
        )

    refusal = _refused(_refusal_reason(trace))
    ask = _attempt_ask(
        problem_text,
        out_dir=out_dir,
        ask_config=ask_config,
        fallback_surface=refusal.surface,
    )
    if ask.served and ask.question is not None:
        return _Decision(status="ask", surface=ask.question, question=ask.question, ask=ask)
    return _refused(refusal.refusal_reason or "pool_policy_refusal", ask=ask)


def run_tool(
    arguments: Any,
    *,
    out_dir: Path,
    ask_config: Any = DEMO_ASK_SERVING_CONFIG,
) -> dict[str, Any]:
    """Execute one ``core.semantic_derivation.verify`` call.  Deterministic: the
    same arguments always produce a byte-identical response (``out_dir`` is used
    only for the content-addressed question artifact of the ASK leg)."""
    errors = validate_payload(arguments)
    if errors:
        return _invalid_response(arguments, errors)

    problem_text: str = arguments["problem_text"]
    trace = problem_trace(problem_text)
    derivation_sha = _derivation_trace_sha(trace)
    commit_law_violations = list(authority_violations(trace))
    faithfulness = list(replay_faithfulness_report(problem_text))
    pin_status = _adr0184_pin_status(trace)
    resolution = trace["resolution"]
    envelope_entry = _envelope()["entries"].get(str(trace["problem_sha"]))

    decision = _decide(
        trace,
        envelope_entry=envelope_entry,
        derivation_sha=derivation_sha,
        pin_status=pin_status,
        commit_law_violations=commit_law_violations,
        faithfulness=faithfulness,
        problem_text=problem_text,
        out_dir=out_dir,
        ask_config=ask_config,
    )
    ask = decision.ask

    response: dict[str, Any] = {
        "tool": TOOL_NAME,
        "request_id": arguments.get("request_id"),
        "status": decision.status,
        "surface": decision.surface,
        "answer": decision.answer,
        "answer_unit": decision.answer_unit,
        "refusal_reason": decision.refusal_reason,
        "question": decision.question,
        "authority_path": [*_AUTHORITIES_DERIVATION, *ask.authorities],
        "replay_equivalence_status": pin_status,
        "trace_summary": {
            "problem_sha": trace["problem_sha"],
            "semantic_worlds": len(trace["worlds"]),
            "semantic_candidates": len(trace["semantic"]),
            "pooled_candidates": len(trace["pooled"]),
            "classifications": trace["classifications"],
            "pool_committed": resolution is not None,
            "commit_law_violations": len(commit_law_violations),
            "faithfulness_violations": len(faithfulness),
            "demo_envelope": _envelope_status(envelope_entry, resolution, derivation_sha),
            "ask": {"attempted": ask.attempted, "served": ask.served, "detail": ask.detail},
        },
        "trace": {
            "derivation": trace,
            "derivation_trace_sha": derivation_sha,
            "commit_law_violations": commit_law_violations,
            "faithfulness_violations": faithfulness,
            "adr0184_pin": {
                "status": pin_status,
                "corpus_sha": load_manifest()["corpus_sha"],
            },
            "ask": ask.to_trace_dict(),
        },
    }
    response["trace_hash"] = hashlib.sha256(_canonical(response).encode()).hexdigest()
    if arguments.get("return_trace", True) is False:
        response["trace"] = None
    return response


def _envelope_status(
    envelope_entry: dict[str, Any] | None,
    resolution: dict[str, Any] | None,
    derivation_sha: str,
) -> str:
    """Whether the committed demo envelope authorizes serving this commit."""
    if resolution is None:
        return "not_applicable"
    if envelope_entry is None:
        return "absent"
    if (
        envelope_entry["derivation_trace_sha"] == derivation_sha
        and round(float(envelope_entry["answer"]), 9) == round(float(resolution["answer"]), 9)
        and envelope_entry["answer_unit"] == resolution["answer_unit"]
    ):
        return "authorized"
    return "pinned_reference_mismatch"


__all__ = [
    "DEMO_ASK_SERVING_CONFIG",
    "DemoAskServingConfig",
    "ENVELOPE_PATH",
    "TOOL_NAME",
    "load_tool_schema",
    "run_tool",
]

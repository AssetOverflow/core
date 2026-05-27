"""ADR-0172 Tier 2 / W5 — MathReaderInferenceProposal schema.

Tier 2 intensional-contemplation proposal.  Records a proposed structural
equivalence (canonicalization bridge) derived from the refusal corpus.

Each proposal carries:

- ≥3 :class:`~teaching.math_evidence.MathReaderRefusalEvidence` pointers
  (tighter than Tier 1's ≥2);
- a ``structural_claim`` naming the proposed equivalence class;
- two :class:`ArmResult` records (arm1 = held-out, arm2 = known-good)
  from the two-arm self-test (W7);
- ``ratification_effect_kind`` pinned to ``"canonicalization_bridge"``;
- a ``wrong_zero_assertion`` (≥40 chars);
- a :class:`~teaching.math_reasoning_trace.ReasoningTrace` carrying ≥6
  steps including ``{abstraction, test_design, test_application, test_result}``.

Invariants enforced by :func:`build_inference_proposal`:

1. ``domain == "math"``.
2. ``len(evidence_pointers) >= 3``.
3. ``reasoning_trace`` carries ≥6 steps.
4. ``reasoning_trace`` steps include every kind in ``_REQUIRED_STEP_KINDS``.
5. Both arms cannot simultaneously be ``"REJECT"``.
6. Arm 2 ``"PASS"`` requires ``cases_changed_answer == 0``.
7. ``ratification_effect_kind == "canonicalization_bridge"``.
8. ``ratification_effect_payload`` is JSON-serializable.
9. ``wrong_zero_assertion`` ≥ 40 chars (stripped).

JSONL self-containment via :func:`to_jsonl_record` / :func:`from_jsonl_record`
mirrors the post-#386 pattern from ``math_contemplation_proposal.py``.

Trust boundary: schema-only module.  No filesystem I/O, no teaching-store
writes, no runtime pipeline hooks.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Literal

from generate.comprehension.audit import AuditRow
from teaching.math_evidence import MathReaderRefusalEvidence
from teaching.math_reasoning_trace import ReasoningStep, ReasoningTrace, build_trace

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ArmOutcome = Literal["PASS", "NEUTRAL", "REJECT"]
ArmName = Literal["arm1_held_out", "arm2_known_good"]

_ARM_OUTCOMES: frozenset[str] = frozenset({"PASS", "NEUTRAL", "REJECT"})
_ARM_NAMES: frozenset[str] = frozenset({"arm1_held_out", "arm2_known_good"})

_EVIDENCE_FLOOR: int = 3
_REQUIRED_STEP_KINDS: frozenset[str] = frozenset({
    "abstraction",
    "test_design",
    "test_application",
    "test_result",
})
_MIN_TRACE_STEPS: int = 6
_WRONG_ZERO_MIN_LEN: int = 40


# ---------------------------------------------------------------------------
# ArmResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArmResult:
    """Outcome record for one self-test arm.

    Fields
    ------
    arm:
        ``"arm1_held_out"`` — 30% held-out refusal subset, or
        ``"arm2_known_good"`` — prior admitted-with-correct-answer set.
    outcome:
        ``"PASS"`` | ``"NEUTRAL"`` | ``"REJECT"``.
    cases_tested:
        Total cases evaluated in this arm.
    cases_admitted:
        Cases where the bridge produced an admission result.
    cases_changed_answer:
        Cases where a previously-correct answer changed under the bridge.
        Must be 0 when arm is ``"arm2_known_good"`` and outcome is ``"PASS"``.
    """

    arm: ArmName
    outcome: ArmOutcome
    cases_tested: int
    cases_admitted: int
    cases_changed_answer: int


def build_arm_result(
    *,
    arm: str,
    outcome: str,
    cases_tested: int,
    cases_admitted: int,
    cases_changed_answer: int,
) -> ArmResult:
    """Build an :class:`ArmResult` with basic field validation."""
    if arm not in _ARM_NAMES:
        raise ValueError(
            f"arm must be one of {sorted(_ARM_NAMES)}; got {arm!r}"
        )
    if outcome not in _ARM_OUTCOMES:
        raise ValueError(
            f"outcome must be one of {sorted(_ARM_OUTCOMES)}; got {outcome!r}"
        )
    if cases_tested < 0:
        raise ValueError(f"cases_tested must be ≥0; got {cases_tested}")
    if cases_admitted < 0:
        raise ValueError(f"cases_admitted must be ≥0; got {cases_admitted}")
    if cases_changed_answer < 0:
        raise ValueError(f"cases_changed_answer must be ≥0; got {cases_changed_answer}")
    return ArmResult(
        arm=arm,  # type: ignore[arg-type]
        outcome=outcome,  # type: ignore[arg-type]
        cases_tested=cases_tested,
        cases_admitted=cases_admitted,
        cases_changed_answer=cases_changed_answer,
    )


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MathReaderInferenceProposal:
    """One proposed canonicalization bridge for the math domain (Tier 2).

    Construct via :func:`build_inference_proposal` — do not instantiate
    directly (``inference_id`` is content-derived).

    Fields
    ------
    inference_id:
        ``sha256(canonical_bytes(...)).hexdigest()`` over all other fields.
    domain:
        Always ``"math"``.
    structural_claim:
        Human-readable description of the proposed equivalence class.
    evidence_pointers:
        ≥3 :class:`MathReaderRefusalEvidence` records.
    arm1_result:
        Two-arm self-test result for the held-out subset.
    arm2_result:
        Two-arm self-test result for the known-good set.
    ratification_effect_kind:
        Always ``"canonicalization_bridge"`` for Tier 2 proposals.
    ratification_effect_payload:
        JSON-serializable payload describing the bridge implementation.
    wrong_zero_assertion:
        ≥40-char statement pinning the wrong=0 invariant.
    replay_equivalence_hash:
        ``sha256`` digest of the replay-equivalence gate output.
    reasoning_trace:
        :class:`~teaching.math_reasoning_trace.ReasoningTrace` carrying ≥6
        steps, including ``{abstraction, test_design, test_application,
        test_result}``.
    """

    inference_id: str
    domain: Literal["math"]
    structural_claim: str
    evidence_pointers: tuple[MathReaderRefusalEvidence, ...]
    arm1_result: ArmResult
    arm2_result: ArmResult
    ratification_effect_kind: Literal["canonicalization_bridge"]
    ratification_effect_payload: object
    wrong_zero_assertion: str
    replay_equivalence_hash: str
    reasoning_trace: ReasoningTrace


# ---------------------------------------------------------------------------
# Canonical-bytes serialization (content-hash; not round-trip)
# ---------------------------------------------------------------------------


def _arm_result_to_canonical(arm: ArmResult) -> dict[str, Any]:
    return {
        "arm": arm.arm,
        "cases_admitted": arm.cases_admitted,
        "cases_changed_answer": arm.cases_changed_answer,
        "cases_tested": arm.cases_tested,
        "outcome": arm.outcome,
    }


def canonical_bytes(proposal: MathReaderInferenceProposal) -> bytes:
    """Return deterministic canonical bytes over all fields except inference_id.

    Evidence pointers are reduced to their ``evidence_hash`` digests;
    ``reasoning_trace`` is reduced to its ``trace_id``.  Stable across
    processes and dict insertion order.
    """
    payload: dict[str, Any] = {
        "arm1_result": _arm_result_to_canonical(proposal.arm1_result),
        "arm2_result": _arm_result_to_canonical(proposal.arm2_result),
        "domain": proposal.domain,
        "evidence_pointers": sorted(
            ev.evidence_hash for ev in proposal.evidence_pointers
        ),
        "ratification_effect_kind": proposal.ratification_effect_kind,
        "ratification_effect_payload": proposal.ratification_effect_payload,
        "reasoning_trace_id": proposal.reasoning_trace.trace_id,
        "replay_equivalence_hash": proposal.replay_equivalence_hash,
        "structural_claim": proposal.structural_claim,
        "wrong_zero_assertion": proposal.wrong_zero_assertion,
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def compute_inference_id(
    *,
    domain: Literal["math"],
    structural_claim: str,
    evidence_pointers: tuple[MathReaderRefusalEvidence, ...],
    arm1_result: ArmResult,
    arm2_result: ArmResult,
    ratification_effect_kind: Literal["canonicalization_bridge"],
    ratification_effect_payload: object,
    wrong_zero_assertion: str,
    replay_equivalence_hash: str,
    reasoning_trace: ReasoningTrace,
) -> str:
    """Hash all content fields to produce a stable ``inference_id``."""
    placeholder = MathReaderInferenceProposal(
        inference_id="",
        domain=domain,
        structural_claim=structural_claim,
        evidence_pointers=evidence_pointers,
        arm1_result=arm1_result,
        arm2_result=arm2_result,
        ratification_effect_kind=ratification_effect_kind,
        ratification_effect_payload=ratification_effect_payload,
        wrong_zero_assertion=wrong_zero_assertion,
        replay_equivalence_hash=replay_equivalence_hash,
        reasoning_trace=reasoning_trace,
    )
    return hashlib.sha256(canonical_bytes(placeholder)).hexdigest()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def build_inference_proposal(
    *,
    domain: Literal["math"] = "math",
    structural_claim: str,
    evidence_pointers: tuple[MathReaderRefusalEvidence, ...],
    arm1_result: ArmResult,
    arm2_result: ArmResult,
    ratification_effect_kind: str,
    ratification_effect_payload: object,
    wrong_zero_assertion: str,
    replay_equivalence_hash: str,
    reasoning_trace: ReasoningTrace,
) -> MathReaderInferenceProposal:
    """Build a :class:`MathReaderInferenceProposal` with all invariants enforced.

    Raises ``ValueError`` on any violation; the caller must fix the inputs.
    """
    if domain != "math":
        raise ValueError(f"domain must be 'math'; got {domain!r}")

    if len(evidence_pointers) < _EVIDENCE_FLOOR:
        raise ValueError(
            f"evidence_pointers requires ≥{_EVIDENCE_FLOOR} entries; "
            f"got {len(evidence_pointers)}"
        )

    if not isinstance(reasoning_trace, ReasoningTrace):
        raise ValueError(
            f"reasoning_trace must be a ReasoningTrace instance; "
            f"got {type(reasoning_trace).__name__}"
        )

    if len(reasoning_trace.steps) < _MIN_TRACE_STEPS:
        raise ValueError(
            f"reasoning_trace must carry ≥{_MIN_TRACE_STEPS} steps; "
            f"got {len(reasoning_trace.steps)}"
        )

    present_kinds = {step.step_kind for step in reasoning_trace.steps}
    missing_kinds = _REQUIRED_STEP_KINDS - present_kinds
    if missing_kinds:
        raise ValueError(
            f"reasoning_trace is missing required step kind(s): "
            f"{sorted(missing_kinds)}; found kinds: {sorted(present_kinds)}"
        )

    if arm1_result.outcome == "REJECT" and arm2_result.outcome == "REJECT":
        raise ValueError(
            "both arms cannot simultaneously be REJECT at construction; "
            "proposals with two REJECT arms must not surface to the schema layer"
        )

    if arm2_result.outcome == "PASS" and arm2_result.cases_changed_answer != 0:
        raise ValueError(
            f"arm2 PASS requires cases_changed_answer == 0; "
            f"got {arm2_result.cases_changed_answer}"
        )

    if ratification_effect_kind != "canonicalization_bridge":
        raise ValueError(
            f"ratification_effect_kind must be 'canonicalization_bridge'; "
            f"got {ratification_effect_kind!r}"
        )

    try:
        json.dumps(
            ratification_effect_payload,
            ensure_ascii=False,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"ratification_effect_payload is not JSON-serializable: {exc}"
        ) from exc

    if not wrong_zero_assertion or len(wrong_zero_assertion.strip()) < _WRONG_ZERO_MIN_LEN:
        raise ValueError(
            f"wrong_zero_assertion must be ≥{_WRONG_ZERO_MIN_LEN} chars (non-empty); "
            f"got {len(wrong_zero_assertion)!r}"
        )

    iid = compute_inference_id(
        domain=domain,
        structural_claim=structural_claim,
        evidence_pointers=evidence_pointers,
        arm1_result=arm1_result,
        arm2_result=arm2_result,
        ratification_effect_kind="canonicalization_bridge",
        ratification_effect_payload=ratification_effect_payload,
        wrong_zero_assertion=wrong_zero_assertion,
        replay_equivalence_hash=replay_equivalence_hash,
        reasoning_trace=reasoning_trace,
    )

    return MathReaderInferenceProposal(
        inference_id=iid,
        domain=domain,
        structural_claim=structural_claim,
        evidence_pointers=tuple(evidence_pointers),
        arm1_result=arm1_result,
        arm2_result=arm2_result,
        ratification_effect_kind="canonicalization_bridge",
        ratification_effect_payload=ratification_effect_payload,
        wrong_zero_assertion=wrong_zero_assertion,
        replay_equivalence_hash=replay_equivalence_hash,
        reasoning_trace=reasoning_trace,
    )


# ---------------------------------------------------------------------------
# Self-contained JSONL persistence serializer
# ---------------------------------------------------------------------------
#
# canonical_bytes() is the content-hash function; it reduces evidence_pointers
# to evidence_hashes and reasoning_trace to its trace_id.  That is correct
# for inference_id derivation but not for round-tripping through disk.
#
# to_jsonl_record() / from_jsonl_record() emit a self-contained record so the
# workbench and HITL queue can read proposals.jsonl without re-running the
# two-arm loop (W7).
#
# Determinism contract: sort_keys=True, compact separators, no floats.


def _audit_row_to_dict(row: AuditRow) -> dict[str, Any]:
    return {
        "case_id": row.case_id,
        "sentence_index": row.sentence_index,
        "token_index": row.token_index,
        "token_text": row.token_text,
        "recognized_terms": list(row.recognized_terms),
        "skipped_frame": row.skipped_frame,
        "missing_operator": row.missing_operator,
        "refusal_reason": row.refusal_reason,
        "refusal_detail": row.refusal_detail,
    }


def _audit_row_from_dict(data: dict[str, Any]) -> AuditRow:
    return AuditRow(
        case_id=str(data["case_id"]),
        sentence_index=int(data["sentence_index"]),
        token_index=int(data["token_index"]),
        token_text=str(data["token_text"]),
        recognized_terms=tuple(data.get("recognized_terms") or ()),
        skipped_frame=data.get("skipped_frame"),
        missing_operator=data.get("missing_operator"),
        refusal_reason=str(data.get("refusal_reason", "")),
        refusal_detail=str(data.get("refusal_detail", "")),
    )


def _evidence_to_dict(ev: MathReaderRefusalEvidence) -> dict[str, Any]:
    return {
        "case_id": ev.case_id,
        "sentence_index": ev.sentence_index,
        "token_index": ev.token_index,
        "refusal_reason": ev.refusal_reason,
        "missing_operator": ev.missing_operator,
        "claim_signature": ev.claim_signature,
        "evidence_hash": ev.evidence_hash,
        "sub_type": ev.sub_type,
        "audit_row": _audit_row_to_dict(ev.audit_row),
    }


def _evidence_from_dict(data: dict[str, Any]) -> MathReaderRefusalEvidence:
    return MathReaderRefusalEvidence(
        case_id=str(data["case_id"]),
        sentence_index=int(data["sentence_index"]),
        token_index=int(data["token_index"]),
        refusal_reason=str(data["refusal_reason"]),
        missing_operator=data.get("missing_operator"),
        claim_signature=str(data.get("claim_signature", "")),
        evidence_hash=str(data["evidence_hash"]),
        audit_row=_audit_row_from_dict(data["audit_row"]),
        sub_type=data["sub_type"],
    )


def _arm_result_to_dict(arm: ArmResult) -> dict[str, Any]:
    return {
        "arm": arm.arm,
        "outcome": arm.outcome,
        "cases_tested": arm.cases_tested,
        "cases_admitted": arm.cases_admitted,
        "cases_changed_answer": arm.cases_changed_answer,
    }


def _arm_result_from_dict(data: dict[str, Any]) -> ArmResult:
    return ArmResult(
        arm=data["arm"],
        outcome=data["outcome"],
        cases_tested=int(data["cases_tested"]),
        cases_admitted=int(data["cases_admitted"]),
        cases_changed_answer=int(data["cases_changed_answer"]),
    )


def _step_to_dict(step: ReasoningStep) -> dict[str, Any]:
    return {
        "step_index": step.step_index,
        "step_kind": step.step_kind,
        "input_pointers": list(step.input_pointers),
        "claim": step.claim,
        "justification": step.justification,
        "output_payload": step.output_payload,
    }


def _step_from_dict(data: dict[str, Any]) -> ReasoningStep:
    return ReasoningStep(
        step_index=int(data["step_index"]),
        step_kind=data["step_kind"],
        input_pointers=tuple(str(p) for p in data.get("input_pointers", ())),
        claim=str(data.get("claim", "")),
        justification=str(data.get("justification", "")),
        output_payload=data.get("output_payload"),
    )


def to_jsonl_record(proposal: MathReaderInferenceProposal) -> dict[str, Any]:
    """Return a self-contained dict representation suitable for JSONL persistence.

    Unlike :func:`canonical_bytes`, this record includes:
    - ``inference_id`` (so consumers don't need to recompute it)
    - full ``evidence_pointers`` (nested dicts — not just hashes)
    - full ``arm1_result`` and ``arm2_result``
    - full ``reasoning_trace.steps`` (inline — not just trace_id)

    The output is JSON-serializable.  Encoding via
    ``json.dumps(record, sort_keys=True, separators=(",", ":"),
    ensure_ascii=False)`` produces deterministic byte-identical output.
    """
    return {
        "inference_id": proposal.inference_id,
        "domain": proposal.domain,
        "structural_claim": proposal.structural_claim,
        "evidence_pointers": [
            _evidence_to_dict(ev) for ev in proposal.evidence_pointers
        ],
        "arm1_result": _arm_result_to_dict(proposal.arm1_result),
        "arm2_result": _arm_result_to_dict(proposal.arm2_result),
        "ratification_effect_kind": proposal.ratification_effect_kind,
        "ratification_effect_payload": proposal.ratification_effect_payload,
        "wrong_zero_assertion": proposal.wrong_zero_assertion,
        "replay_equivalence_hash": proposal.replay_equivalence_hash,
        "reasoning_trace": {
            "trace_id": proposal.reasoning_trace.trace_id,
            "steps": [_step_to_dict(s) for s in proposal.reasoning_trace.steps],
        },
    }


def from_jsonl_record(record: dict[str, Any]) -> MathReaderInferenceProposal:
    """Reconstruct a proposal from a :func:`to_jsonl_record` dict.

    Goes through :func:`build_inference_proposal` so all invariants are
    re-validated.  The reconstructed ``inference_id`` must match the
    persisted one — mismatch indicates tampering or schema drift and
    raises :class:`ValueError`.
    """
    evidence_records = tuple(
        _evidence_from_dict(d) for d in record.get("evidence_pointers", ())
    )
    steps = tuple(_step_from_dict(d) for d in record["reasoning_trace"]["steps"])
    trace = build_trace(steps)

    arm1 = _arm_result_from_dict(record["arm1_result"])
    arm2 = _arm_result_from_dict(record["arm2_result"])

    proposal = build_inference_proposal(
        domain=record.get("domain", "math"),
        structural_claim=str(record["structural_claim"]),
        evidence_pointers=evidence_records,
        arm1_result=arm1,
        arm2_result=arm2,
        ratification_effect_kind=str(record["ratification_effect_kind"]),
        ratification_effect_payload=record.get("ratification_effect_payload"),
        wrong_zero_assertion=str(record["wrong_zero_assertion"]),
        replay_equivalence_hash=str(record["replay_equivalence_hash"]),
        reasoning_trace=trace,
    )

    persisted_id = str(record.get("inference_id", ""))
    if persisted_id and persisted_id != proposal.inference_id:
        raise ValueError(
            "inference_id mismatch on JSONL round-trip: persisted "
            f"{persisted_id!r} != recomputed {proposal.inference_id!r}"
        )
    return proposal


__all__ = [
    "ArmName",
    "ArmOutcome",
    "ArmResult",
    "MathReaderInferenceProposal",
    "build_arm_result",
    "build_inference_proposal",
    "canonical_bytes",
    "compute_inference_id",
    "from_jsonl_record",
    "to_jsonl_record",
]

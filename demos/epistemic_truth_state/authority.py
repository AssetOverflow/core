"""Local deterministic epistemic-state authority substrate for the demo.

A model-style proposer submits a claim, sealed evidence references, and
(optionally) a bounded-inference block.  The proposer contributes *references only*
for evidence; CORE resolves those references against a sealed local corpus. CORE
alone:

* validates a closed payload,
* resolves evidence references by committed content hash,
* derives support and provenance independence from the committed record bodies
  (never from proposer-supplied labels — the schema rejects them),
* decides the bounded-inference leg with the real propositional entailment
  engine (:func:`generate.proof_chain.entail.evaluate_entailment_with_trace`,
  the sound-and-complete ROBDD decision procedure) cross-checked against the
  independent truth-table oracle
  (:func:`evals.deductive_logic.oracle.oracle_entailment`),
* assigns the typed epistemic state drawn from the canonical taxonomy in
  :mod:`core.epistemic_state` (never a parallel enum),
* derives normative clearance,
* builds the evidence ledger, and
* regenerates a deterministic trace hash.

The proposer cannot set ``assigned_state``, ``status``, ``trace_hash``,
``authority_path``, the evidence ledger, or ``normative_clearance`` — and it
cannot mint them indirectly: ``inferred`` is assigned only when the cited,
resolved premises *propositionally entail* the claim's atom, so citing
unrelated records as premises yields ``undetermined``, not ``inferred``.  Any
proposer-supplied ``proposed_state`` / ``trace_hash`` is recorded as ignored
and never read by the decision path.  Nothing here executes a side effect.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

from core.epistemic_state import (
    EpistemicState,
    NormativeClearance,
    coerce_epistemic_state,
    coerce_normative_clearance,
)
from evals.deductive_logic.oracle import oracle_entailment
from generate.proof_chain.entail import Entailment, evaluate_entailment_with_trace

TOOL_NAME: Final[str] = "core.epistemic_truth_state.review"
_HERE: Final[Path] = Path(__file__).resolve().parent
SCHEMA_PATH: Final[Path] = _HERE / "schema.json"
EVIDENCE_CORPUS_PATH: Final[Path] = _HERE / "evidence_corpus.json"

# The local epistemic authority envelope: only claims declared inside these
# domains are evaluated.  Anything else is refused as outside scope rather than
# guessed at.
ENVELOPE_DOMAINS: Final[frozenset[str]] = frozenset({"demo.local_factual"})

_ROOT_AUTHORITY: Final[str] = "demos.epistemic_truth_state.authority.validate_payload"
_CORPUS_AUTHORITY: Final[str] = "demos.epistemic_truth_state.authority.resolve_evidence_refs"
_ASSIGN_AUTHORITY: Final[str] = "demos.epistemic_truth_state.authority.assign_epistemic_state"
_ENVELOPE_AUTHORITY: Final[str] = "demo_epistemic_truth_state_envelope(local-v1)"
_ENTAIL_AUTHORITY: Final[str] = "generate.proof_chain.entail.evaluate_entailment_with_trace"
_ORACLE_AUTHORITY: Final[str] = "evals.deductive_logic.oracle.oracle_entailment"
_TAXONOMY_AUTHORITY: Final[str] = "core.epistemic_state.coerce_epistemic_state"

_SUPPORTED_SCHEMA_KEYS: Final[frozenset[str]] = frozenset(
    {
        "type",
        "properties",
        "required",
        "additionalProperties",
        "enum",
        "pattern",
        "minLength",
        "maxLength",
        "items",
    }
)
_SCALAR_TYPES: Final[dict[str, type]] = {"string": str, "boolean": bool}


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_evidence_corpus() -> dict[str, dict[str, Any]]:
    raw = json.loads(EVIDENCE_CORPUS_PATH.read_text(encoding="utf-8"))
    records = raw.get("records")
    if not isinstance(records, list):
        raise ValueError("evidence corpus must contain a records array")
    by_id: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("evidence corpus records must be objects")
        evidence_id = record.get("evidence_id")
        if not isinstance(evidence_id, str):
            raise ValueError("evidence corpus record missing evidence_id")
        if evidence_id in by_id:
            raise ValueError(f"duplicate evidence_id {evidence_id!r}")
        by_id[evidence_id] = dict(record)
    return by_id


def _evidence_record_hash(record: dict[str, Any]) -> str:
    return _hash_text(_canonical(record))


@lru_cache(maxsize=1)
def corpus_file_sha256() -> str:
    """Hash of the committed corpus file bytes — the seal pinned into traces."""
    return _hash_text(EVIDENCE_CORPUS_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def corpus_identifier() -> str:
    return str(json.loads(EVIDENCE_CORPUS_PATH.read_text(encoding="utf-8"))["corpus_id"])


def _clip(value: object) -> str:
    rendered = repr(value)
    return rendered if len(rendered) <= 80 else rendered[:79] + "…"


def _ensure_supported_schema(spec: dict[str, Any], *, path: str) -> None:
    unsupported = set(spec) - _SUPPORTED_SCHEMA_KEYS
    if unsupported:
        raise ValueError(
            f"{path} uses unsupported schema keywords {sorted(unsupported)}; "
            "extend the validator before extending the schema"
        )
    schema_type = spec.get("type")
    if isinstance(schema_type, list):
        return
    if schema_type == "object":
        for name, child in spec.get("properties", {}).items():
            _ensure_supported_schema(child, path=f"{path}.{name}")
    elif schema_type == "array":
        _ensure_supported_schema(spec["items"], path=f"{path}[]")
    elif schema_type not in _SCALAR_TYPES:
        raise ValueError(f"{path} has unsupported schema type {schema_type!r}")


@lru_cache(maxsize=1)
def _input_schema() -> dict[str, Any]:
    schema = load_schema()["inputSchema"]
    _ensure_supported_schema(schema, path="inputSchema")
    if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
        raise ValueError("inputSchema must be a closed object")
    return schema


def _validate(spec: dict[str, Any], value: Any, *, path: str, errors: list[str]) -> None:
    schema_type = spec["type"]
    if isinstance(schema_type, list):
        for entry in schema_type:
            if entry == "null" and value is None:
                return
        if value is None:
            errors.append(f"{path} must be one of {schema_type}")
            return
        non_null = [entry for entry in schema_type if entry != "null"]
        if len(non_null) != 1:
            raise ValueError(f"{path} uses unsupported union type {schema_type!r}")
        schema_type = non_null[0]

    if schema_type == "object":
        if not isinstance(value, dict):
            errors.append(f"{path} must be object")
            return
        props = spec.get("properties", {})
        if spec.get("additionalProperties") is False:
            for unknown in sorted(set(value) - set(props)):
                errors.append(
                    f"{path} unexpected property {_clip(unknown)} "
                    "(additionalProperties is false)"
                )
        for required in spec.get("required", []):
            if required not in value:
                errors.append(f"{path} missing required property {required!r}")
        for name, child in props.items():
            if name in value:
                _validate(child, value[name], path=f"{path}.{name}", errors=errors)
        return

    if schema_type == "array":
        if not isinstance(value, list):
            errors.append(f"{path} must be array")
            return
        for index, item in enumerate(value):
            _validate(spec["items"], item, path=f"{path}[{index}]", errors=errors)
        return

    expected = _SCALAR_TYPES[schema_type]
    if type(value) is not expected:
        errors.append(f"{path} must be {schema_type}")
        return
    if isinstance(value, str):
        if "minLength" in spec and len(value) < spec["minLength"]:
            errors.append(f"{path} shorter than {spec['minLength']}")
        if "maxLength" in spec and len(value) > spec["maxLength"]:
            errors.append(f"{path} longer than {spec['maxLength']}")
        if "enum" in spec and value not in spec["enum"]:
            errors.append(f"{path} must be one of {spec['enum']}")
        if "pattern" in spec and re.fullmatch(spec["pattern"], value) is None:
            errors.append(f"{path} does not match {spec['pattern']!r}")
    elif "enum" in spec and value not in spec["enum"]:
        errors.append(f"{path} must be one of {spec['enum']}")


def validate_payload(payload: Any) -> tuple[str, ...]:
    errors: list[str] = []
    _validate(_input_schema(), payload, path="payload", errors=errors)
    return tuple(errors)


def _safe_field(payload: Any, field: str) -> str | None:
    value = payload.get(field) if isinstance(payload, dict) else None
    if not isinstance(value, str):
        return None
    pattern = _input_schema()["properties"][field]["pattern"]
    return value if re.fullmatch(pattern, value) else None


def _response_hash(response: dict[str, Any]) -> str:
    body = dict(response)
    body.pop("trace_hash", None)
    return _hash_text(_canonical(body))


def _finalize(response: dict[str, Any]) -> dict[str, Any]:
    response["trace_hash"] = _response_hash(response)
    return response


def _proposer_trace_hash_present(payload: Any) -> bool:
    return bool(
        isinstance(payload, dict)
        and isinstance(payload.get("proposer"), dict)
        and "trace_hash" in payload["proposer"]
    )


def _proposer_state_present(payload: Any) -> bool:
    return bool(
        isinstance(payload, dict)
        and isinstance(payload.get("proposer"), dict)
        and "proposed_state" in payload["proposer"]
    )


def _invalid_response(payload: Any, errors: tuple[str, ...]) -> dict[str, Any]:
    return _finalize(
        {
            "tool": TOOL_NAME,
            "status": "invalid",
            "request_id": _safe_field(payload, "request_id"),
            "scenario_id": _safe_field(payload, "scenario_id"),
            "authority_path": [_ROOT_AUTHORITY],
            "decision_reason": "invalid_payload",
            "assigned_state": None,
            "normative_clearance": None,
            "evidence_ledger": [],
            "trace_summary": {
                "authority_evaluated": False,
                "validation_errors": list(errors),
                "proposer_trace_hash_ignored": _proposer_trace_hash_present(payload),
                "proposer_state_ignored": _proposer_state_present(payload),
            },
            "invalid_reason": "; ".join(errors),
        }
    )


def _invalid_evidence_response(payload: dict[str, Any], errors: tuple[str, ...]) -> dict[str, Any]:
    return _finalize(
        {
            "tool": TOOL_NAME,
            "status": "invalid",
            "request_id": payload["request_id"],
            "scenario_id": payload["scenario_id"],
            "authority_path": [_ROOT_AUTHORITY, _CORPUS_AUTHORITY],
            "decision_reason": "invalid_evidence_reference",
            "assigned_state": None,
            "normative_clearance": None,
            "evidence_ledger": [],
            "trace_summary": {
                "authority_evaluated": False,
                "evidence_reference_errors": list(errors),
                "proposer_trace_hash_ignored": _proposer_trace_hash_present(payload),
                "proposer_state_ignored": _proposer_state_present(payload),
            },
            "invalid_reason": "; ".join(errors),
        }
    )


def _claim_fingerprint(payload: dict[str, Any]) -> str:
    proposer = payload["proposer"]
    digest_input = {
        "claim": payload["claim"],
        "proposer": {
            "lane": proposer["lane"],
            "model_family": proposer["model_family"],
            "proposal_id": proposer["proposal_id"],
        },
        "request_id": payload["request_id"],
        "scenario_id": payload["scenario_id"],
    }
    return _hash_text(_canonical(digest_input))


def resolve_evidence_refs(refs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
    """Resolve proposer-supplied refs against the sealed local evidence corpus."""
    corpus = load_evidence_corpus()
    resolved: list[dict[str, Any]] = []
    errors: list[str] = []
    seen: set[str] = set()
    for ref in refs:
        evidence_id = ref["evidence_id"]
        if evidence_id in seen:
            errors.append(f"duplicate evidence reference {evidence_id!r}")
            continue
        seen.add(evidence_id)
        record = corpus.get(evidence_id)
        if record is None:
            errors.append(f"unknown evidence reference {evidence_id!r}")
            continue
        expected_hash = _evidence_record_hash(record)
        if ref["content_sha256"] != expected_hash:
            errors.append(f"content hash mismatch for evidence reference {evidence_id!r}")
            continue
        # Hand out a copy: the corpus cache must stay immutable in-process.
        resolved.append(dict(record))
    return resolved, tuple(errors)


def _matching_evidence(claim: dict[str, Any], evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Corpus records that match the claim subject and predicate."""
    subject = claim["subject"]
    predicate = claim["predicate"]
    return [
        record
        for record in evidence
        if record.get("source_kind") != "premise"
        and record.get("subject") == subject
        and record.get("predicate") == predicate
    ]


def _independent_evidence(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_root: dict[str, dict[str, Any]] = {}
    for record in evidence:
        root = record["provenance_root"]
        by_root.setdefault(root, record)
    return list(by_root.values())


def _claim_atom(claim: dict[str, Any]) -> str:
    """The propositional atom the claim asserts (schema guarantees snake_case
    parts, so the derivation is total)."""
    return f"{claim['subject']}__{claim['predicate']}"


def _premise_formula(record: dict[str, Any]) -> str:
    """The propositional contribution of one resolved corpus record: a rule
    record contributes its committed formula, a fact record its atom."""
    formula = record.get("formula")
    if isinstance(formula, str) and formula:
        return formula
    return f"{record['subject']}__{record['predicate']}"


@dataclass(frozen=True, slots=True)
class _InferenceReport:
    """What the bounded-inference leg did, as inert trace data."""

    consulted: bool
    detail: str
    premise_ids: tuple[str, ...] = ()
    outcome: str | None = None
    reason: str | None = None
    oracle_verdict: str | None = None
    agreement: bool | None = None
    entailment: dict[str, Any] | None = None

    def to_trace_dict(self) -> dict[str, Any]:
        summary: dict[str, Any] = {"consulted": self.consulted, "detail": self.detail}
        if self.consulted:
            summary.update(
                {
                    "premise_ids": list(self.premise_ids),
                    "outcome": self.outcome,
                    "reason": self.reason,
                    "oracle_verdict": self.oracle_verdict,
                    "engine_oracle_agreement": self.agreement,
                    "entailment_trace": self.entailment,
                }
            )
        return summary


_INFERENCE_NOT_PRESENT: Final[_InferenceReport] = _InferenceReport(
    consulted=False, detail="no_inference_block"
)


def _evaluate_inference(
    payload: dict[str, Any], evidence: list[dict[str, Any]]
) -> _InferenceReport:
    """Decide the bounded-inference leg with the real entailment engine.

    Premises must be cited evidence references that resolved against the sealed
    corpus; a rule record contributes its committed formula, a fact record its
    atom.  The query is the claim's atom.  ``inferred`` is therefore an actual
    sound-and-complete entailment decision — citing records that merely *exist*
    proves nothing.  The engine verdict is cross-checked against the
    independent truth-table oracle; the caller treats disagreement as a
    defensive refusal.
    """
    inference = payload.get("inference")
    if not isinstance(inference, dict):
        return _INFERENCE_NOT_PRESENT
    premise_ids = tuple(inference.get("premise_ids") or ())
    if not premise_ids:
        return _InferenceReport(consulted=False, detail="no_premises")

    resolved_by_id = {record["evidence_id"]: record for record in evidence}
    premises: list[str] = []
    for premise_id in premise_ids:
        record = resolved_by_id.get(premise_id)
        if record is None:
            return _InferenceReport(consulted=False, detail="premise_unresolved")
        premises.append(_premise_formula(record))

    query = _claim_atom(payload["claim"])
    trace = evaluate_entailment_with_trace(tuple(premises), query)
    oracle_verdict = oracle_entailment(tuple(premises), query)
    return _InferenceReport(
        consulted=True,
        detail="evaluated",
        premise_ids=tuple(sorted(premise_ids)),
        outcome=trace.outcome.value,
        reason=trace.reason,
        oracle_verdict=oracle_verdict,
        agreement=trace.outcome.value == oracle_verdict,
        entailment=trace.as_dict(),
    )


def _base_trace_summary(
    payload: dict[str, Any],
    evidence: list[dict[str, Any]],
    independent: list[dict[str, Any]],
    inference: _InferenceReport,
) -> dict[str, Any]:
    return {
        "authority_evaluated": True,
        "envelope_version": "local-v1",
        "claim_fingerprint": _claim_fingerprint(payload),
        "corpus_id": corpus_identifier(),
        "corpus_sha256": corpus_file_sha256(),
        "evidence_considered": len(evidence),
        "independent_support_count": len(independent),
        "proposer_trace_hash_ignored": "trace_hash" in payload["proposer"],
        "proposer_state_ignored": "proposed_state" in payload["proposer"],
        "inference": inference.to_trace_dict(),
    }


def _authority_path(inference: _InferenceReport) -> list[str]:
    """Consulted authorities in order — the entailment engine and the oracle
    appear only when the inference leg actually ran."""
    path = [_ROOT_AUTHORITY, _ASSIGN_AUTHORITY, _ENVELOPE_AUTHORITY, _CORPUS_AUTHORITY]
    if inference.consulted:
        path.extend([_ENTAIL_AUTHORITY, _ORACLE_AUTHORITY])
    path.append(_TAXONOMY_AUTHORITY)
    return path


def _assigned(
    payload: dict[str, Any],
    *,
    state: EpistemicState,
    clearance: NormativeClearance,
    decision_reason: str,
    evidence_ledger: list[str],
    trace_summary: dict[str, Any],
    inference: _InferenceReport,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = {
        "tool": TOOL_NAME,
        "status": "assigned",
        "request_id": payload["request_id"],
        "scenario_id": payload["scenario_id"],
        "authority_path": _authority_path(inference),
        "decision_reason": decision_reason,
        "assigned_state": coerce_epistemic_state(state).value,
        "normative_clearance": coerce_normative_clearance(clearance).value,
        "evidence_ledger": evidence_ledger,
        "trace_summary": trace_summary,
    }
    if extra:
        response.update(extra)
    return _finalize(response)


def assign_epistemic_state(payload: dict[str, Any]) -> dict[str, Any]:
    """CORE's sole authority over the typed epistemic state.

    The proposer's ``proposed_state`` is never read here.  The state is derived
    only from the claim, sealed evidence references, and the bounded-inference
    block.
    """
    claim = payload["claim"]
    evidence_refs: list[dict[str, Any]] = payload.get("evidence", [])

    # Scope: refuse claims declared outside the local epistemic envelope before
    # consulting the corpus at all.
    if claim["domain"] not in ENVELOPE_DOMAINS:
        return _finalize(
            {
                "tool": TOOL_NAME,
                "status": "refused",
                "request_id": payload["request_id"],
                "scenario_id": payload["scenario_id"],
                "authority_path": [
                    _ROOT_AUTHORITY,
                    _ASSIGN_AUTHORITY,
                    _ENVELOPE_AUTHORITY,
                ],
                "decision_reason": "outside_epistemic_envelope",
                "assigned_state": coerce_epistemic_state(EpistemicState.SCOPE_BOUNDARY).value,
                "normative_clearance": coerce_normative_clearance(
                    NormativeClearance.UNASSESSABLE
                ).value,
                "evidence_ledger": [],
                "trace_summary": {
                    "authority_evaluated": True,
                    "envelope_version": "local-v1",
                    "claim_fingerprint": _claim_fingerprint(payload),
                    "evidence_considered": len(evidence_refs),
                    "evidence_resolution": "not_consulted",
                    "proposer_trace_hash_ignored": "trace_hash" in payload["proposer"],
                    "proposer_state_ignored": "proposed_state" in payload["proposer"],
                },
                "refusal_reason": "outside_epistemic_envelope",
            }
        )

    evidence, ref_errors = resolve_evidence_refs(evidence_refs)
    if ref_errors:
        return _invalid_evidence_response(payload, ref_errors)
    matching = _matching_evidence(claim, evidence)
    independent = _independent_evidence(matching)
    inference = _evaluate_inference(payload, evidence)
    trace_summary = _base_trace_summary(payload, evidence, independent, inference)

    # Defensive fail-closed: the engine and the independent oracle must agree
    # before any inference-derived state is assigned.  This path should never
    # fire (both procedures are sound and complete over the regime); if it
    # does, refusing is the only honest output.
    if inference.consulted and inference.agreement is False:
        return _finalize(
            {
                "tool": TOOL_NAME,
                "status": "refused",
                "request_id": payload["request_id"],
                "scenario_id": payload["scenario_id"],
                "authority_path": _authority_path(inference),
                "decision_reason": "entailment_oracle_disagreement",
                "assigned_state": None,
                "normative_clearance": coerce_normative_clearance(
                    NormativeClearance.UNASSESSABLE
                ).value,
                "evidence_ledger": [],
                "trace_summary": trace_summary,
                "refusal_reason": "entailment_oracle_disagreement",
            }
        )

    # Contradicted: the resolved premises propositionally refute the claim.
    # Conflict is surfaced, never averaged away.
    if inference.consulted and inference.outcome == Entailment.REFUTED.value:
        return _assigned(
            payload,
            state=EpistemicState.CONTRADICTED,
            clearance=NormativeClearance.UNASSESSABLE,
            decision_reason="claim_refuted_by_entailment",
            evidence_ledger=list(inference.premise_ids),
            trace_summary=trace_summary,
            inference=inference,
            extra={"inference_basis": list(inference.premise_ids)},
        )

    # Verified: two or more independent records that match subject and predicate.
    # Clearance stays UNASSESSABLE even here: this demo assigns epistemic
    # truth-state only and runs no normative/safety/ethics clearance pass, so it
    # has no basis to positively clear anything.
    if len(independent) >= 2:
        return _assigned(
            payload,
            state=EpistemicState.VERIFIED,
            clearance=NormativeClearance.UNASSESSABLE,
            decision_reason="verified_by_matching_evidence",
            evidence_ledger=sorted(record["evidence_id"] for record in independent),
            trace_summary=trace_summary,
            inference=inference,
        )

    # Inferred: the claim is not directly supported but its atom is PROVED from
    # the resolved premises by the sound-and-complete entailment decision, with
    # the independent oracle agreeing.  Premises that merely resolve do not
    # infer anything.
    if (
        inference.consulted
        and inference.outcome == Entailment.ENTAILED.value
        and inference.agreement is True
        and not matching
    ):
        return _assigned(
            payload,
            state=EpistemicState.INFERRED,
            clearance=NormativeClearance.UNASSESSABLE,
            decision_reason="entailed_from_resolved_premises",
            evidence_ledger=list(inference.premise_ids),
            trace_summary=trace_summary,
            inference=inference,
            extra={"inference_basis": list(inference.premise_ids)},
        )

    # Evidenced: at least one supporting record, but not enough to verify.
    if matching:
        return _assigned(
            payload,
            state=EpistemicState.EVIDENCED,
            clearance=NormativeClearance.UNASSESSABLE,
            decision_reason="evidence_present_but_not_verifying",
            evidence_ledger=sorted(record["evidence_id"] for record in matching),
            trace_summary=trace_summary,
            inference=inference,
        )

    # Undetermined: nothing grounds the claim.  CORE asks rather than guesses —
    # unrelated premises and unsupported claims land here, never in `inferred`.
    return _assigned(
        payload,
        state=EpistemicState.UNDETERMINED,
        clearance=NormativeClearance.UNASSESSABLE,
        decision_reason="insufficient_evidence",
        evidence_ledger=[],
        trace_summary=trace_summary,
        inference=inference,
        extra={
            "question": (
                "CORE has insufficient grounded evidence to assign a determined "
                "epistemic state to this claim. Provide supporting, refuting, or "
                "premise evidence."
            )
        },
    )


def run_authority(payload: Any) -> dict[str, Any]:
    errors = validate_payload(payload)
    if errors:
        return _invalid_response(payload, errors)
    assert isinstance(payload, dict)
    return assign_epistemic_state(payload)


__all__ = [
    "ENVELOPE_DOMAINS",
    "EVIDENCE_CORPUS_PATH",
    "SCHEMA_PATH",
    "TOOL_NAME",
    "assign_epistemic_state",
    "load_evidence_corpus",
    "load_schema",
    "resolve_evidence_refs",
    "run_authority",
    "validate_payload",
]

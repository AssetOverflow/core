"""Local deterministic epistemic-state authority substrate for the demo.

A model-style proposer submits a claim, an evidence bundle, and (optionally) a
bounded-inference block.  The proposer contributes *data only*.  CORE alone:

* validates a closed payload,
* assigns the typed epistemic state drawn from the canonical taxonomy in
  :mod:`core.epistemic_state` (never a parallel enum),
* derives normative clearance,
* builds the evidence ledger, and
* regenerates a deterministic trace hash.

The proposer cannot set ``assigned_state``, ``status``, ``trace_hash``,
``authority_path``, the evidence ledger, or ``normative_clearance``.  Any
proposer-supplied ``proposed_state`` / ``trace_hash`` is recorded as ignored
and never read by the decision path.  Nothing here executes a side effect.
"""

from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

from core.epistemic_state import (
    EpistemicState,
    NormativeClearance,
    coerce_epistemic_state,
    coerce_normative_clearance,
)

TOOL_NAME: Final[str] = "core.epistemic_truth_state.review"
_HERE: Final[Path] = Path(__file__).resolve().parent
SCHEMA_PATH: Final[Path] = _HERE / "schema.json"

# The local epistemic authority envelope: only claims declared inside these
# domains are evaluated.  Anything else is refused as outside scope rather than
# guessed at.
ENVELOPE_DOMAINS: Final[frozenset[str]] = frozenset({"demo.local_factual"})

_ROOT_AUTHORITY: Final[str] = "demos.epistemic_truth_state.authority.validate_payload"
_ASSIGN_AUTHORITY: Final[str] = "demos.epistemic_truth_state.authority.assign_epistemic_state"
_ENVELOPE_AUTHORITY: Final[str] = "demo_epistemic_truth_state_envelope(local-v1)"
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


def _matching_evidence(claim: dict[str, Any], evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Evidence records that explicitly support the claim subject and predicate."""
    subject = claim["subject"]
    predicate = claim["predicate"]
    return [
        record
        for record in evidence
        if bool(record.get("supports"))
        and record.get("subject") == subject
        and record.get("predicate") == predicate
    ]


def _resolved_inference_basis(payload: dict[str, Any]) -> list[str] | None:
    """Return sorted premise IDs iff an inference block resolves fully, else None."""
    inference = payload.get("inference")
    if not isinstance(inference, dict):
        return None
    premise_ids = inference.get("premise_ids") or []
    known_ids = {record["evidence_id"] for record in payload.get("evidence", [])}
    if not premise_ids or any(pid not in known_ids for pid in premise_ids):
        return None
    return sorted(premise_ids)


def _base_trace_summary(payload: dict[str, Any], evidence: list[dict[str, Any]], independent: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "authority_evaluated": True,
        "envelope_version": "local-v1",
        "claim_fingerprint": _claim_fingerprint(payload),
        "evidence_considered": len(evidence),
        "independent_support_count": len(independent),
        "proposer_trace_hash_ignored": "trace_hash" in payload["proposer"],
        "proposer_state_ignored": "proposed_state" in payload["proposer"],
    }


def _assigned(
    payload: dict[str, Any],
    *,
    state: EpistemicState,
    clearance: NormativeClearance,
    decision_reason: str,
    evidence_ledger: list[str],
    trace_summary: dict[str, Any],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = {
        "tool": TOOL_NAME,
        "status": "assigned",
        "request_id": payload["request_id"],
        "scenario_id": payload["scenario_id"],
        "authority_path": [
            _ROOT_AUTHORITY,
            _ASSIGN_AUTHORITY,
            _ENVELOPE_AUTHORITY,
            _TAXONOMY_AUTHORITY,
        ],
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
    only from the claim, the evidence bundle, and the bounded-inference block.
    """
    claim = payload["claim"]
    evidence: list[dict[str, Any]] = payload.get("evidence", [])
    matching = _matching_evidence(claim, evidence)
    independent = [record for record in matching if bool(record.get("independent"))]
    trace_summary = _base_trace_summary(payload, evidence, independent)

    # Scope: refuse claims declared outside the local epistemic envelope.
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
                "trace_summary": trace_summary,
                "refusal_reason": "outside_epistemic_envelope",
            }
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
        )

    # Inferred: claim follows from bounded premises and is not directly matched.
    inference_basis = _resolved_inference_basis(payload)
    if inference_basis is not None and not matching:
        return _assigned(
            payload,
            state=EpistemicState.INFERRED,
            clearance=NormativeClearance.UNASSESSABLE,
            decision_reason="bounded_inference_from_evidence",
            evidence_ledger=inference_basis,
            trace_summary=trace_summary,
            extra={"inference_basis": inference_basis},
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
        )

    # Undetermined: nothing grounds the claim.  CORE asks rather than guesses.
    return _assigned(
        payload,
        state=EpistemicState.UNDETERMINED,
        clearance=NormativeClearance.UNASSESSABLE,
        decision_reason="insufficient_evidence",
        evidence_ledger=[],
        trace_summary=trace_summary,
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
    "SCHEMA_PATH",
    "TOOL_NAME",
    "assign_epistemic_state",
    "load_schema",
    "run_authority",
    "validate_payload",
]

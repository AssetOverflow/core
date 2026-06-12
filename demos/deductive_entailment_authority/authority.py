"""Local deterministic deductive entailment authority for the demo.

A model-style proposer submits an entailment proposal: premises, a claim,
and (optionally) a verdict / confidence / proof / trace hash / engine pin.
The proposer contributes *data only*.  CORE alone:

* validates a closed payload,
* enforces the demo's explicit regime bound (a distinct-atom budget) so the
  brute-force oracle's enumeration stays inside the deductive lane's
  small-atom contract,
* recomputes formal propositional entailment through the pinned deductive
  engine — :func:`generate.proof_chain.entail.evaluate_entailment_with_trace`,
  the sound **and complete** ROBDD operator (no demo-local
  reimplementation) — and
* independently cross-checks the verdict with the deductive lane's gold
  oracle — :func:`evals.deductive_logic.oracle.oracle_entailment`, a second,
  code-disjoint decision procedure (own tokenizer, own parser, brute-force
  truth-table enumeration; it imports nothing from ``generate``).

A decision (``entailed`` / ``refuted`` / ``unknown``) is served only when
both independent procedures agree.  The engine's typed refusals —
``inconsistent_premises`` (no vacuous entailment from a contradiction) and
``out_of_regime_or_malformed`` — are served as ``status: refused`` with
``decision: null``.  An engine/oracle disagreement refuses defensively with
``oracle_disagreement``; inside the supported regime the two procedures
agree, so that branch is exercised by test-only fault injection (a
monkeypatched oracle), never by a committed fixture.

The proposer cannot set ``status``, ``decision``, ``trace_hash``,
``authority_path``, ``oracle_verdict``, ``oracle_agreement``,
``engine_pin``, ``entailment_trace``, or any other output field — the
closed schema rejects them before evaluation.  Proposer-attached
``verdict`` / ``confidence`` / ``proof`` / ``trace_hash`` / ``engine_pin``
are accepted inside ``proposer`` purely so the artifact can *prove* they
were ignored: this module reads only the field NAMES to build the
``proposer_ignored_fields`` ledger; no decision branch reads their values.

INV discipline (this file is scanned by INV-21/INV-24/INV-29): there is no
vault, no store call, no recall call, and no epistemic status anywhere —
the demo is a pure decision authority over the payload's formulas.

Nothing here touches the network, a model API, a subprocess, the clock, or
randomness.  It evaluates JSON and returns JSON.
"""

from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

from evals.deductive_logic.oracle import oracle_entailment
from generate.proof_chain.engine_pin import DEDUCTIVE_ENGINE_PIN
from generate.proof_chain.entail import (
    INCONSISTENT_PREMISES,
    OUT_OF_REGIME_OR_MALFORMED,
    Entailment,
    evaluate_entailment_with_trace,
)

TOOL_NAME: Final[str] = "deductive_entailment_authority"
_HERE: Final[Path] = Path(__file__).resolve().parent
SCHEMA_PATH: Final[Path] = _HERE / "schema.json"

_ROOT_AUTHORITY: Final[str] = (
    "demos.deductive_entailment_authority.authority.validate_payload"
)
_ATOM_BUDGET_AUTHORITY: Final[str] = (
    "demos.deductive_entailment_authority.authority.enforce_atom_budget"
)
_ENGINE_AUTHORITY: Final[str] = (
    "generate.proof_chain.entail.evaluate_entailment_with_trace"
)
_ORACLE_AUTHORITY: Final[str] = "evals.deductive_logic.oracle.oracle_entailment"

# Identity fields a proposer must supply; everything else inside ``proposer``
# is recorded as ignored and never read by the decision path.
_PROPOSER_IDENTITY_FIELDS: Final[frozenset[str]] = frozenset(
    {"lane", "model_family", "proposal_id"}
)

# Demo-local defensive refusal reason: the engine decided but the independent
# oracle did not confirm.  The engine's own refusal reasons pass through.
ORACLE_DISAGREEMENT: Final[str] = "oracle_disagreement"

REFUSAL_REASONS: Final[frozenset[str]] = frozenset(
    {INCONSISTENT_PREMISES, OUT_OF_REGIME_OR_MALFORMED, ORACLE_DISAGREEMENT}
)

# The demo's explicit regime bound.  The oracle is a deliberate O(2^atoms)
# brute-force enumerator ("the lane keeps atom counts small so enumeration
# stays cheap" — its own contract); the authority honors that contract at its
# boundary instead of letting a crafted payload churn the enumerator.
MAX_DISTINCT_ATOMS: Final[int] = 12

# Conservative OVER-estimate of distinct atoms: every atom is an identifier
# token, so counting identifier tokens (minus operator keywords) can never
# under-count.  Over-counting only refuses early — refusal-first is safe.
_IDENT_PATTERN: Final[str] = r"[A-Za-z_][A-Za-z0-9_]*"
_OPERATOR_WORDS: Final[frozenset[str]] = frozenset(
    {"and", "or", "not", "implies", "iff", "true", "false"}
)

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
        "minItems",
        "maxItems",
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
        if "minItems" in spec and len(value) < spec["minItems"]:
            errors.append(f"{path} has fewer than {spec['minItems']} items")
        if "maxItems" in spec and len(value) > spec["maxItems"]:
            errors.append(f"{path} has more than {spec['maxItems']} items")
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


def _proposer_ignored_fields(payload: Any) -> list[str]:
    """Field NAMES the proposer attached beyond identity — recorded, not read."""
    proposer = payload.get("proposer") if isinstance(payload, dict) else None
    if not isinstance(proposer, dict):
        return []
    return sorted(set(proposer) - _PROPOSER_IDENTITY_FIELDS)


def estimated_distinct_atoms(premises: tuple[str, ...], claim: str) -> int:
    """Conservative over-estimate of distinct atoms across all formulas."""
    idents: set[str] = set()
    for formula in (*premises, claim):
        for word in re.findall(_IDENT_PATTERN, formula):
            if word.lower() not in _OPERATOR_WORDS:
                idents.add(word)
    return len(idents)


def _invalid_response(payload: Any, errors: tuple[str, ...]) -> dict[str, Any]:
    return _finalize(
        {
            "tool": TOOL_NAME,
            "status": "invalid",
            "decision": None,
            "request_id": _safe_field(payload, "request_id"),
            "scenario_id": _safe_field(payload, "scenario_id"),
            "authority_path": [_ROOT_AUTHORITY],
            "decision_reason": "invalid_payload",
            "engine_pin": None,
            "entailment_trace": None,
            "oracle_verdict": None,
            "oracle_agreement": None,
            "proposer_ignored_fields": _proposer_ignored_fields(payload),
            "trace_summary": {
                "authority_evaluated": False,
                "validation_errors": list(errors),
                "proposer_fields_ignored": _proposer_ignored_fields(payload),
            },
            "refusal_reason": None,
            "invalid_reason": "; ".join(errors),
        }
    )


def _atom_budget_refusal(
    payload: dict[str, Any], premises: tuple[str, ...], atom_estimate: int
) -> dict[str, Any]:
    """Refuse BEFORE either procedure runs: neither the engine nor the oracle
    is invoked, so ``entailment_trace`` and ``oracle_verdict`` are honestly
    null — there is no evidence to show."""
    ignored = _proposer_ignored_fields(payload)
    return _finalize(
        {
            "tool": TOOL_NAME,
            "status": "refused",
            "decision": None,
            "request_id": payload["request_id"],
            "scenario_id": payload["scenario_id"],
            "authority_path": [_ROOT_AUTHORITY, _ATOM_BUDGET_AUTHORITY],
            "decision_reason": OUT_OF_REGIME_OR_MALFORMED,
            "engine_pin": DEDUCTIVE_ENGINE_PIN,
            "entailment_trace": None,
            "oracle_verdict": None,
            "oracle_agreement": None,
            "proposer_ignored_fields": ignored,
            "trace_summary": {
                "authority_evaluated": True,
                "regime_gate": "distinct_atom_budget",
                "distinct_atom_estimate": atom_estimate,
                "distinct_atom_budget": MAX_DISTINCT_ATOMS,
                "premise_count": len(premises),
                "engine_outcome": None,
                "engine_reason": None,
                "oracle_verdict": None,
                "oracle_agreement": None,
                "defensive_refusal": False,
                "proposer_fields_ignored": ignored,
            },
            "refusal_reason": OUT_OF_REGIME_OR_MALFORMED,
            "invalid_reason": None,
        }
    )


def evaluate_decision(payload: dict[str, Any]) -> dict[str, Any]:
    """CORE's sole authority over the entailment decision in this demo.

    The proposer's ``verdict`` / ``confidence`` / ``proof`` / ``trace_hash``
    / ``engine_pin`` are never read here — only their NAMES are echoed into
    the ignored-fields ledger.  The decision is the engine's recomputation,
    served only when the independent oracle agrees.
    """
    premises = tuple(payload["premises"])
    claim: str = payload["claim"]
    ignored = _proposer_ignored_fields(payload)

    atom_estimate = estimated_distinct_atoms(premises, claim)
    if atom_estimate > MAX_DISTINCT_ATOMS:
        return _atom_budget_refusal(payload, premises, atom_estimate)

    trace = evaluate_entailment_with_trace(premises, claim)
    oracle_verdict = oracle_entailment(premises, claim)
    oracle_agreement = trace.outcome.value == oracle_verdict
    defensive_refusal = (
        trace.outcome is not Entailment.REFUSED and not oracle_agreement
    )

    if trace.outcome is Entailment.REFUSED:
        # The engine's typed refusal is authoritative: refusing is always
        # safe, and the oracle verdict is still recorded alongside it.
        status, decision, reason = "refused", None, trace.reason
    elif defensive_refusal:
        # The engine decided but the independent oracle did not confirm —
        # never serve a decision only one procedure stands behind.
        status, decision, reason = "refused", None, ORACLE_DISAGREEMENT
    else:
        status, decision, reason = "decided", trace.outcome.value, trace.reason

    return _finalize(
        {
            "tool": TOOL_NAME,
            "status": status,
            "decision": decision,
            "request_id": payload["request_id"],
            "scenario_id": payload["scenario_id"],
            "authority_path": [
                _ROOT_AUTHORITY,
                _ATOM_BUDGET_AUTHORITY,
                _ENGINE_AUTHORITY,
                _ORACLE_AUTHORITY,
            ],
            "decision_reason": reason,
            "engine_pin": DEDUCTIVE_ENGINE_PIN,
            "entailment_trace": json.loads(trace.canonical_json()),
            "oracle_verdict": oracle_verdict,
            "oracle_agreement": oracle_agreement,
            "proposer_ignored_fields": ignored,
            "trace_summary": {
                "authority_evaluated": True,
                "regime_gate": None,
                "distinct_atom_estimate": atom_estimate,
                "distinct_atom_budget": MAX_DISTINCT_ATOMS,
                "premise_count": len(premises),
                "engine_outcome": trace.outcome.value,
                "engine_reason": trace.reason,
                "oracle_verdict": oracle_verdict,
                "oracle_agreement": oracle_agreement,
                "defensive_refusal": defensive_refusal,
                "proposer_fields_ignored": ignored,
            },
            "refusal_reason": reason if status == "refused" else None,
            "invalid_reason": None,
        }
    )


def run_authority(payload: Any) -> dict[str, Any]:
    errors = validate_payload(payload)
    if errors:
        return _invalid_response(payload, errors)
    assert isinstance(payload, dict)
    return evaluate_decision(payload)


__all__ = [
    "MAX_DISTINCT_ATOMS",
    "ORACLE_DISAGREEMENT",
    "REFUSAL_REASONS",
    "SCHEMA_PATH",
    "TOOL_NAME",
    "estimated_distinct_atoms",
    "evaluate_decision",
    "load_schema",
    "run_authority",
    "validate_payload",
]

"""Local deterministic proof-carrying promotion authority for the demo.

A model-style proposer submits a promotion request: a curator-declared local
store description, the claim and premise entry ids, and (optionally) proof /
status / confidence / certificate text.  The proposer contributes *data
only*.  CORE alone:

* validates a closed payload,
* builds a deterministic local store arena from the curator-declared entries,
* fresh-reads certified readings and epistemic statuses from that arena,
* recomputes the entailment proof under the pinned deductive engine via the
  REAL ratified promoter (:func:`teaching.proof_promotion.certify_promotion`
  — no demo-local reimplementation), and
* mutates only through the single transition owner
  (:meth:`vault.store.VaultStore.apply_certified_promotion`), which
  independently replay-verifies the certificate against live arena state.

The proposer cannot set ``status``, ``promoted``, ``certificate_digest``,
``trace_hash``, ``authority_path``, ``before_status``/``after_status``, or
any other output field — the closed schema rejects them before evaluation.
Proposer-attached ``proof`` / ``status`` / ``confidence`` / ``certificate`` /
``trace_hash`` are accepted inside ``proposer`` purely so the artifact can
*prove* they were ignored: the whole proposer block is handed to
``certify_promotion`` as ``proposer_payload``, which deletes it unread
(ADR-0218 §D3.5), and this module reads only the field NAMES to build the
``proposer_ignored_fields`` ledger.

INV discipline (this file is scanned by INV-21/INV-24/INV-29):

* the arena is constructed via ``VaultStore.from_dict`` over dict-literal
  metadata — no ``VaultStore.store`` call (INV-21) and no
  ``epistemic_status`` assignment anywhere (INV-29; dict-literal
  construction is the sanctioned serialization-builder shape);
* no ``vault.recall`` call (INV-24) — reads use ``iter_metadata`` only;
* the only status transition happens inside ``vault/store.py``.

Nothing here touches the network, a model API, a subprocess, the clock, or
randomness.  It evaluates JSON and returns JSON.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

import numpy as np

from algebra.cga import embed_point
from core.array_codec import encode_array
from generate.proof_chain.engine_pin import DEDUCTIVE_ENGINE_PIN
from teaching import proof_promotion
from teaching.epistemic import parse_status
from vault.store import VaultStore, epistemic_state_for_vault_status

TOOL_NAME: Final[str] = "proof_carrying_coherence_promotion"
_HERE: Final[Path] = Path(__file__).resolve().parent
SCHEMA_PATH: Final[Path] = _HERE / "schema.json"

_ROOT_AUTHORITY: Final[str] = (
    "demos.proof_carrying_promotion.authority.validate_payload"
)
_DECIDER_AUTHORITY: Final[str] = "teaching.proof_promotion.certify_promotion"
_OWNER_AUTHORITY: Final[str] = "vault.store.VaultStore.apply_certified_promotion"
_REPLAY_AUTHORITY: Final[str] = (
    "generate.proof_chain.certificate.verify_certificate(expected_engine_pin)"
)

# Identity fields a proposer must supply; everything else inside ``proposer``
# is recorded as ignored and never read by the decision path.
_PROPOSER_IDENTITY_FIELDS: Final[frozenset[str]] = frozenset(
    {"lane", "model_family", "proposal_id"}
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


def _proposer_ignored_fields(payload: Any) -> list[str]:
    """Field NAMES the proposer attached beyond identity — recorded, not read."""
    proposer = payload.get("proposer") if isinstance(payload, dict) else None
    if not isinstance(proposer, dict):
        return []
    return sorted(set(proposer) - _PROPOSER_IDENTITY_FIELDS)


def _invalid_response(payload: Any, errors: tuple[str, ...]) -> dict[str, Any]:
    return _finalize(
        {
            "tool": TOOL_NAME,
            "status": "invalid",
            "request_id": _safe_field(payload, "request_id"),
            "scenario_id": _safe_field(payload, "scenario_id"),
            "authority_path": [_ROOT_AUTHORITY],
            "decision_reason": "invalid_payload",
            "promoted": False,
            "claim_entry_id": None,
            "claim_entry_index": None,
            "before_status": None,
            "after_status": None,
            "premise_entry_ids": [],
            "premise_entry_indices": [],
            "certificate_digest": None,
            "engine_pin": None,
            "trace_summary": {
                "authority_evaluated": False,
                "validation_errors": list(errors),
                "proposer_fields_ignored": _proposer_ignored_fields(payload),
            },
            "proposer_ignored_fields": _proposer_ignored_fields(payload),
            "invalid_reason": "; ".join(errors),
        }
    )


# ---------------------------------------------------------------------------
# Deterministic local arena construction (no VaultStore.store call; INV-21)
# ---------------------------------------------------------------------------

def _versor_for(index: int) -> np.ndarray:
    """Deterministic per-entry versor from fixed coordinates — no randomness."""
    coords = np.array(
        [0.05 * (index + 1), 0.11 * (index + 2), 0.17 * (index + 3)],
        dtype=np.float32,
    )
    return embed_point(coords)


def _arena_metadata(entry: dict[str, Any], status: str) -> dict[str, Any]:
    # Dict-literal construction only (the INV-29 serialization-builder shape);
    # this module never ASSIGNS an epistemic_status key anywhere.
    return {
        "demo_entry_id": entry["entry_id"],
        "propositional_form": entry["propositional_form"],
        "reading_certified": entry["reading_certified"],
        "epistemic_status": status,
        "epistemic_state": epistemic_state_for_vault_status(
            parse_status(status)
        ).value,
    }


def _build_arena(
    entries: list[dict[str, Any]],
    status_overrides: dict[str, str],
) -> VaultStore:
    """Reconstruct a throwaway local arena via the persistence path.

    ``from_dict`` restores serialized state without any ``store()`` call, so
    the demo introduces no new vault writer; the entries' statuses are
    curator-declared fixture DATA, exactly the "already-reviewed store state"
    the promotion predicate fresh-reads.
    """
    payload = {
        "versors": [
            encode_array(_versor_for(index)) for index in range(len(entries))
        ],
        "metadata": [
            _arena_metadata(
                entry,
                status_overrides[entry["entry_id"]]
                if entry["entry_id"] in status_overrides
                else entry["epistemic_status"],
            )
            for entry in entries
        ],
        "store_count": len(entries),
        "reproject_interval": 0,
        "max_entries": None,
    }
    return VaultStore.from_dict(payload)


def _entry_status(arena: VaultStore, index: int) -> str | None:
    for i, meta in arena.iter_metadata():
        if i == index:
            status = meta.get("epistemic_status")
            return status if isinstance(status, str) else None
    return None


# ---------------------------------------------------------------------------
# The promotion flow — real decider, real owner, demo envelope
# ---------------------------------------------------------------------------

def _refused_structural(
    payload: dict[str, Any], reason: str, trace_summary: dict[str, Any]
) -> dict[str, Any]:
    return _finalize(
        {
            "tool": TOOL_NAME,
            "status": "refused",
            "request_id": payload["request_id"],
            "scenario_id": payload["scenario_id"],
            "authority_path": [_ROOT_AUTHORITY],
            "decision_reason": reason,
            "promoted": False,
            "claim_entry_id": None,
            "claim_entry_index": None,
            "before_status": None,
            "after_status": None,
            "premise_entry_ids": [],
            "premise_entry_indices": [],
            "certificate_digest": None,
            "engine_pin": DEDUCTIVE_ENGINE_PIN,
            "trace_summary": trace_summary,
            "proposer_ignored_fields": _proposer_ignored_fields(payload),
            "refusal_reason": reason,
        }
    )


def evaluate_promotion(payload: dict[str, Any]) -> dict[str, Any]:
    """CORE's sole authority over the promotion decision in this demo.

    The proposer's ``proof`` / ``status`` / ``confidence`` / ``certificate``
    are never read here — the whole proposer block goes to the real promoter
    as ``proposer_payload``, which deletes it unread.
    """
    store_spec = payload["store"]
    entries: list[dict[str, Any]] = store_spec["entries"]
    ignored = _proposer_ignored_fields(payload)
    base_trace: dict[str, Any] = {
        "authority_evaluated": True,
        "arena_entry_count": len(entries),
        "proposer_fields_ignored": ignored,
    }

    entry_ids = [entry["entry_id"] for entry in entries]
    if len(set(entry_ids)) != len(entry_ids):
        return _refused_structural(payload, "duplicate_store_entry_ids", base_trace)
    index_of = {entry_id: index for index, entry_id in enumerate(entry_ids)}

    claim_id = store_spec["claim_entry"]
    premise_ids: list[str] = store_spec["premise_entries"]
    unknown = [
        entry_id
        for entry_id in [claim_id, *premise_ids]
        if entry_id not in index_of
    ]
    if unknown:
        return _refused_structural(
            payload,
            "unknown_store_entry",
            {**base_trace, "unknown_entry_ids": sorted(set(unknown))},
        )

    claim_index = index_of[claim_id]
    premise_indices = tuple(index_of[entry_id] for entry_id in premise_ids)

    sabotage = payload.get("sabotage") or {}
    tamper_claim_form = sabotage.get("tamper_claim_form")
    restate = sabotage.get("restate")

    # The decision arena: the curator-declared state at certification time.
    certify_arena = _build_arena(entries, {})
    decision = proof_promotion.certify_promotion(
        claim_entry_index=claim_index,
        premise_entry_indices=premise_indices,
        vault=certify_arena,
        proposer_payload=payload["proposer"],
    )

    # The live arena the mutation owner sees.  ``restate`` models a curator
    # revision landing between certification and application (staleness);
    # without sabotage they are the same state.
    if restate is not None:
        live_arena = _build_arena(
            entries, {restate["entry_id"]: restate["epistemic_status"]}
        )
    else:
        live_arena = certify_arena

    certificate = decision.certificate
    if certificate is not None and tamper_claim_form is not None:
        certificate = dataclasses.replace(
            certificate, claim_form=tamper_claim_form
        )

    before_status = _entry_status(live_arena, claim_index)
    apply_attempted = certificate is not None
    if certificate is not None:
        result = live_arena.apply_certified_promotion(claim_index, certificate)
        applied, apply_reason = result.applied, result.reason
    else:
        applied, apply_reason = False, None
    after_status = _entry_status(live_arena, claim_index)

    if applied:
        decision_reason = decision.reason
    elif decision.promoted and apply_reason is not None:
        # The decider recommended, the owner's independent re-verification
        # refused (tamper or staleness) — the owner's reason is the decision.
        decision_reason = apply_reason
    else:
        decision_reason = decision.reason

    submitted_digest = (
        proof_promotion.certificate_digest(certificate)
        if certificate is not None
        else None
    )

    authority_path = [_ROOT_AUTHORITY, _DECIDER_AUTHORITY]
    if apply_attempted:
        authority_path += [_OWNER_AUTHORITY, _REPLAY_AUTHORITY]

    response: dict[str, Any] = {
        "tool": TOOL_NAME,
        "status": "promoted" if applied else "refused",
        "request_id": payload["request_id"],
        "scenario_id": payload["scenario_id"],
        "authority_path": authority_path,
        "decision_reason": decision_reason,
        "promoted": applied,
        "claim_entry_id": claim_id,
        "claim_entry_index": claim_index,
        "before_status": before_status,
        "after_status": after_status,
        "premise_entry_ids": list(premise_ids),
        "premise_entry_indices": list(premise_indices),
        "certificate_digest": submitted_digest,
        "engine_pin": DEDUCTIVE_ENGINE_PIN,
        "trace_summary": {
            **base_trace,
            "certify_promoted": decision.promoted,
            "certify_reason": decision.reason,
            "certify_certificate_digest": decision.certificate_digest,
            "apply_attempted": apply_attempted,
            "apply_reason": apply_reason,
            "engine_decision": (
                decision.certificate.decision
                if decision.certificate is not None
                else None
            ),
            "engine_reason": (
                decision.certificate.reason
                if decision.certificate is not None
                else None
            ),
            "sabotage_applied": sorted(sabotage),
        },
        "proposer_ignored_fields": ignored,
    }
    if not applied:
        response["refusal_reason"] = decision_reason
    return _finalize(response)


def run_authority(payload: Any) -> dict[str, Any]:
    errors = validate_payload(payload)
    if errors:
        return _invalid_response(payload, errors)
    assert isinstance(payload, dict)
    return evaluate_promotion(payload)


__all__ = [
    "SCHEMA_PATH",
    "TOOL_NAME",
    "evaluate_promotion",
    "load_schema",
    "run_authority",
    "validate_payload",
]

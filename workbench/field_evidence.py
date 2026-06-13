"""C3 field-substrate evidence — exact scalar invariants for a turn's field.

The engine owns the CL(4,1) field; this module surfaces, read-only, only the
EXACT scalars the engine computes over it — ``versor_condition`` (the
``< 1e-6`` validity invariant) and the ``cga_inner`` transition value — plus a
content-addressed ``field_digest``.  The raw multivector NEVER leaves this
module: only floats and a hash cross the boundary, so the workbench can show
"this is the geometry, it's exact, it can't fake coherence" without rendering a
decorative blob.

No engine math is re-implemented here: ``versor_condition`` and ``cga_inner``
are imported from :mod:`algebra` and the field bytes are encoded by the
engine-owned :func:`core.array_codec.encode_array`.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import numpy as np

from algebra import cga_inner, versor_condition
from core.array_codec import encode_array
from workbench.schemas import FieldEvidence

# The non-negotiable CORE invariant (CLAUDE.md; enforced at field/state.py:223
# as ``versor_condition(F) >= 1e-6`` -> raise).  Surfaced so the UI can render
# the measured value against the bound rather than asserting validity blindly.
VERSOR_CONDITION_CEILING: float = 1e-6


def _field_digest(field_array: Any) -> str:
    """Content-addressed digest of a field multivector — provenance, not the blob.

    Hashes the engine-canonical ``encode_array`` payload (dtype + shape + raw
    bytes), so the digest fully determines the array yet exposes none of it.
    """

    payload = encode_array(np.asarray(field_array))
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def missing_field_evidence(
    *,
    trace_hash: str | None,
    reason: str,
) -> FieldEvidence:
    """Honest absence — old journal rows have no persisted field evidence."""

    return FieldEvidence(
        schema_version="field_evidence_v1",
        status="missing_evidence",
        missing_reason=reason,
        trace_hash=trace_hash,
        versor_condition=None,
        versor_condition_ceiling=VERSOR_CONDITION_CEILING,
        field_valid=None,
        field_digest=None,
        parent_field_digest=None,
        transition_inner_product=None,
    )


def validate(record: FieldEvidence) -> None:
    """Fail-closed honesty gate.

    A recorded record must carry the scalars, and ``field_valid`` must agree
    with ``versor_condition < ceiling`` EXACTLY — the field card can never claim
    a valid field while the measured condition breaches the bound (the wrong=0
    analogue for the geometry surface).
    """

    if record.status != "recorded":
        return
    if record.versor_condition is None or record.field_valid is None:
        raise ValueError(
            "recorded field evidence missing versor_condition / field_valid"
        )
    if record.field_digest is None:
        raise ValueError("recorded field evidence missing field_digest")
    if record.field_valid != (record.versor_condition < record.versor_condition_ceiling):
        raise ValueError(
            "field_valid disagrees with versor_condition vs ceiling: "
            f"valid={record.field_valid} condition={record.versor_condition:.3e} "
            f"ceiling={record.versor_condition_ceiling:.3e}"
        )


def field_evidence_from_result(result: Any) -> FieldEvidence:
    """Build validated field evidence from a live engine turn result.

    Reads the engine's ``field_state_after`` / ``field_state_before`` and
    ``versor_condition``; emits only scalars + digests.  Returns an honest
    ``missing_evidence`` record when the result carries no field state.
    """

    trace_hash = str(getattr(result, "trace_hash", "") or "") or None
    after = getattr(result, "field_state_after", None)
    if after is None or getattr(after, "F", None) is None:
        return missing_field_evidence(
            trace_hash=trace_hash, reason="field_state_not_available"
        )

    measured = getattr(result, "versor_condition", None)
    condition = (
        float(measured) if measured is not None else float(versor_condition(after.F))
    )
    field_digest = _field_digest(after.F)

    before = getattr(result, "field_state_before", None)
    if before is not None and getattr(before, "F", None) is not None:
        parent_field_digest: str | None = _field_digest(before.F)
        transition_inner_product: float | None = float(cga_inner(before.F, after.F))
    else:
        parent_field_digest = None
        transition_inner_product = None

    record = FieldEvidence(
        schema_version="field_evidence_v1",
        status="recorded",
        missing_reason=None,
        trace_hash=trace_hash,
        versor_condition=condition,
        versor_condition_ceiling=VERSOR_CONDITION_CEILING,
        field_valid=condition < VERSOR_CONDITION_CEILING,
        field_digest=field_digest,
        parent_field_digest=parent_field_digest,
        transition_inner_product=transition_inner_product,
    )
    validate(record)
    return record


def _coerce(raw: Any) -> FieldEvidence:
    if isinstance(raw, FieldEvidence):
        return raw
    if not isinstance(raw, dict):
        raise ValueError("field_evidence must be an object")
    return FieldEvidence(
        schema_version=raw["schema_version"],
        status=raw["status"],
        missing_reason=raw.get("missing_reason"),
        trace_hash=raw.get("trace_hash"),
        versor_condition=raw.get("versor_condition"),
        versor_condition_ceiling=raw.get(
            "versor_condition_ceiling", VERSOR_CONDITION_CEILING
        ),
        field_valid=raw.get("field_valid"),
        field_digest=raw.get("field_digest"),
        parent_field_digest=raw.get("parent_field_digest"),
        transition_inner_product=raw.get("transition_inner_product"),
    )


def field_evidence_from_journal_entry(entry: Any) -> FieldEvidence:
    """Project a persisted journal row into the field-evidence read model."""

    raw = getattr(entry, "field_evidence", None)
    if raw is None:
        return missing_field_evidence(
            trace_hash=getattr(entry, "trace_hash", None),
            reason="field_evidence_not_persisted",
        )
    record = _coerce(raw)
    validate(record)
    return record

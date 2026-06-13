"""C3 field-substrate evidence — non-vacuous guards.

Each test fails under a specific violation of the honesty contract: a field
card that claimed ``field_valid`` while the measured ``versor_condition``
breaches the ``< 1e-6`` ceiling, a digest that leaked the raw multivector, or a
recorded record missing its scalars.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pytest

import workbench.field_evidence as fe
from field.state import FieldState
from workbench.schemas import FieldEvidence, to_data


def _versor_field() -> FieldState:
    """A valid Cl(4,1) versor field (scalar identity) — versor_condition == 0."""
    f = np.zeros(32, dtype=np.float64)
    f[0] = 1.0
    return FieldState(F=f)


def _non_versor_field() -> FieldState:
    """A field that breaches the versor manifold — versor_condition >= 1e-6."""
    f = np.zeros(32, dtype=np.float64)
    f[0] = 2.0
    return FieldState(F=f)


def _result(*, after: FieldState | None, before: FieldState | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        trace_hash="trace-abc",
        field_state_after=after,
        field_state_before=before,
        # versor_condition deliberately absent so the module computes it from F
        # via the real engine operator (the honest path).
    )


class TestFromResult:
    def test_valid_field_records_field_valid_true(self) -> None:
        record = fe.field_evidence_from_result(_result(after=_versor_field()))
        assert record.status == "recorded"
        assert record.field_valid is True
        assert record.versor_condition is not None
        assert record.versor_condition < fe.VERSOR_CONDITION_CEILING
        assert record.field_digest is not None and record.field_digest.startswith("sha256:")
        assert record.transition_inner_product is None  # no before on first turn

    def test_breaching_field_records_field_valid_false_not_a_lie(self) -> None:
        # The honest negative: a field off the versor manifold must report
        # field_valid False, never silently True.
        record = fe.field_evidence_from_result(_result(after=_non_versor_field()))
        assert record.status == "recorded"
        assert record.versor_condition is not None
        assert record.versor_condition >= fe.VERSOR_CONDITION_CEILING
        assert record.field_valid is False

    def test_transition_inner_product_present_when_before_exists(self) -> None:
        record = fe.field_evidence_from_result(
            _result(after=_versor_field(), before=_versor_field())
        )
        assert record.transition_inner_product is not None
        assert isinstance(record.transition_inner_product, float)
        assert record.parent_field_digest is not None

    def test_missing_field_state_is_honest_not_fabricated(self) -> None:
        record = fe.field_evidence_from_result(_result(after=None))
        assert record.status == "missing_evidence"
        assert record.missing_reason == "field_state_not_available"
        assert record.field_valid is None
        assert record.versor_condition is None

    def test_no_raw_multivector_crosses_the_boundary(self) -> None:
        record = fe.field_evidence_from_result(
            _result(after=_versor_field(), before=_non_versor_field())
        )
        serialized = json.dumps(to_data(record))
        # No base64 array payload, no array literal — only scalars + digests.
        assert "b64" not in serialized
        assert "2.0, 0.0" not in serialized
        assert "[1.0," not in serialized


class TestValidateHonestyGate:
    def test_field_valid_disagreeing_with_ceiling_raises(self) -> None:
        # The wrong=0 analogue: claiming a valid field above the ceiling.
        bad = FieldEvidence(
            schema_version="field_evidence_v1",
            status="recorded",
            missing_reason=None,
            trace_hash="x",
            versor_condition=1e-3,  # breaches the ceiling
            versor_condition_ceiling=fe.VERSOR_CONDITION_CEILING,
            field_valid=True,  # ...but claims valid
            field_digest="sha256:0",
            parent_field_digest=None,
            transition_inner_product=None,
        )
        with pytest.raises(ValueError, match="field_valid disagrees"):
            fe.validate(bad)

    def test_recorded_without_scalars_raises(self) -> None:
        bad = FieldEvidence(
            schema_version="field_evidence_v1",
            status="recorded",
            missing_reason=None,
            trace_hash="x",
            versor_condition=None,
            versor_condition_ceiling=fe.VERSOR_CONDITION_CEILING,
            field_valid=None,
            field_digest=None,
            parent_field_digest=None,
            transition_inner_product=None,
        )
        with pytest.raises(ValueError, match="missing versor_condition"):
            fe.validate(bad)

    def test_missing_evidence_is_not_validated(self) -> None:
        # Honest absence is allowed to carry null scalars.
        record = fe.missing_field_evidence(trace_hash="x", reason="not_persisted")
        fe.validate(record)  # must not raise


class TestDigest:
    def test_digest_is_content_addressed(self) -> None:
        a = _versor_field().F
        b = _non_versor_field().F
        assert fe._field_digest(a) == fe._field_digest(a.copy())
        assert fe._field_digest(a) != fe._field_digest(b)


class TestFromJournalEntry:
    def test_absent_field_evidence_reads_as_missing(self) -> None:
        entry = SimpleNamespace(trace_hash="t", field_evidence=None)
        record = fe.field_evidence_from_journal_entry(entry)
        assert record.status == "missing_evidence"
        assert record.missing_reason == "field_evidence_not_persisted"
        assert record.trace_hash == "t"

    def test_persisted_dict_is_coerced_and_validated(self) -> None:
        source = fe.field_evidence_from_result(_result(after=_versor_field()))
        entry = SimpleNamespace(trace_hash="t", field_evidence=to_data(source))
        record = fe.field_evidence_from_journal_entry(entry)
        assert record.status == "recorded"
        assert record.field_valid is True
        assert record.field_digest == source.field_digest

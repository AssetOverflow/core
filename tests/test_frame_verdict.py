"""FrameVerdict — the sealed closed-world type + isolated text-frame evaluator (B4 PR-1).

Covers the ADR-0222 §5.1 verdict mapping, the frame gating (OPEN / undeclared / non-TEXT
=> SCOPE_BOUNDARY), the admissibility invariant (entailed_false needs a NAMED positive
refutation), absence safety (no fact => UNDETERMINED, never entailed_false), and replay
determinism (order-invariant + repeat-stable trace_hash). INV-31 import/data-flow
containment lives in ``tests/test_architectural_invariants.py``.
"""

from __future__ import annotations

import dataclasses

import pytest

from generate.frame_verdict import (
    ClosedFrame,
    ClosedWorldProof,
    FrameKind,
    FrameVerdict,
    FrameVerdictKind,
    PositiveRefutationKind,
    WorldAssumption,
    evaluate_frame_verdict,
)


def _frame(
    propositions,
    *,
    closure: bool = True,
    kind: FrameKind = FrameKind.TEXT,
    wa: WorldAssumption = WorldAssumption.CLOSED,
) -> ClosedFrame:
    return ClosedFrame(
        frame_id="f1",
        frame_kind=kind,
        world_assumption=wa,
        propositions=tuple(propositions),
        closure_declared=closure,
        source="test",
        provenance=(),
    )


# --------------------------------------------------------------------------- #
# §5.1 verdict mapping
# --------------------------------------------------------------------------- #


def test_entailed_true_from_closed_text_frame() -> None:
    v = evaluate_frame_verdict(_frame(["a", "a -> b"]), "b")
    assert v.verdict is FrameVerdictKind.ENTAILED_TRUE
    assert v.proof.producer == "proof_chain.entail" and v.proof.outcome == "ENTAILED"
    assert v.proof.positive_refutation_kind is None
    assert v.basis == "as_told"


def test_entailed_false_from_refuted_carries_robdd_refutation() -> None:
    v = evaluate_frame_verdict(_frame(["a", "a -> ~b"]), "b")
    assert v.verdict is FrameVerdictKind.ENTAILED_FALSE
    assert v.proof.producer == "proof_chain.entail" and v.proof.outcome == "REFUTED"
    assert v.proof.positive_refutation_kind is PositiveRefutationKind.ROBDD_REFUTATION
    assert v.proof.proof_sha256  # non-empty positive proof


def test_unknown_maps_to_undetermined() -> None:
    v = evaluate_frame_verdict(_frame(["a"]), "b")
    assert v.verdict is FrameVerdictKind.UNDETERMINED


def test_inconsistent_premises_map_to_contradiction_not_false() -> None:
    v = evaluate_frame_verdict(_frame(["a", "~a"]), "b")
    assert v.verdict is FrameVerdictKind.CONTRADICTION
    assert v.verdict is not FrameVerdictKind.ENTAILED_FALSE


def test_malformed_maps_to_scope_boundary() -> None:
    v = evaluate_frame_verdict(_frame(["@@ not grammar ???"]), "b")
    assert v.verdict is FrameVerdictKind.SCOPE_BOUNDARY


# --------------------------------------------------------------------------- #
# Frame gating — a negation needs an explicit declared-complete TEXT frame
# --------------------------------------------------------------------------- #


def test_open_world_assumption_refuses() -> None:
    v = evaluate_frame_verdict(_frame(["a", "a -> ~b"], wa=WorldAssumption.OPEN), "b")
    assert v.verdict is FrameVerdictKind.SCOPE_BOUNDARY


def test_undeclared_closure_refuses() -> None:
    v = evaluate_frame_verdict(_frame(["a", "a -> ~b"], closure=False), "b")
    assert v.verdict is FrameVerdictKind.SCOPE_BOUNDARY


def test_perception_frame_is_scope_boundary_in_pr1() -> None:
    v = evaluate_frame_verdict(_frame(["a", "a -> ~b"], kind=FrameKind.PERCEPTION), "b")
    assert v.verdict is FrameVerdictKind.SCOPE_BOUNDARY


# --------------------------------------------------------------------------- #
# Admissibility invariant — entailed_false needs a NAMED positive refutation
# --------------------------------------------------------------------------- #


def _proof(producer, outcome, kind, sha="abc123") -> ClosedWorldProof:
    return ClosedWorldProof(
        producer=producer, outcome=outcome, proof_sha256=sha,
        proof_keys=("k",), positive_refutation_kind=kind,
    )


def _make(verdict, proof) -> FrameVerdict:
    return FrameVerdict(
        frame_id="f1", frame_kind=FrameKind.TEXT,
        world_assumption=WorldAssumption.CLOSED, query="b", verdict=verdict,
        proof=proof, basis="as_told", trace_hash="th", provenance=(),
    )


def test_entailed_false_with_generic_falsified_raises() -> None:
    # generic FALSIFIED (no positive_refutation_kind) cannot prove false.
    with pytest.raises(ValueError):
        _make(FrameVerdictKind.ENTAILED_FALSE, _proof("sensorium.falsification", "FALSIFIED", None))


def test_entailed_false_with_missing_proof_sha_raises() -> None:
    with pytest.raises(ValueError):
        _make(
            FrameVerdictKind.ENTAILED_FALSE,
            _proof("proof_chain.entail", "REFUTED", PositiveRefutationKind.ROBDD_REFUTATION, sha=""),
        )


def test_entailed_false_with_mismatched_kind_raises() -> None:
    # REFUTED text outcome but the PERCEPTION kind — mismatch must raise.
    with pytest.raises(ValueError):
        _make(
            FrameVerdictKind.ENTAILED_FALSE,
            _proof("proof_chain.entail", "REFUTED", PositiveRefutationKind.PERCEPTION_CHANGED_SLOT),
        )


def test_valid_text_entailed_false_constructs() -> None:
    v = _make(
        FrameVerdictKind.ENTAILED_FALSE,
        _proof("proof_chain.entail", "REFUTED", PositiveRefutationKind.ROBDD_REFUTATION),
    )
    assert v.verdict is FrameVerdictKind.ENTAILED_FALSE


def test_entailed_false_in_open_world_raises() -> None:
    # Structural backstop (types.py §(0)): OPEN + entailed_false is illegal even WITH a valid
    # ROBDD refutation proof — absence is never false. No producer may emit an OPEN negation.
    with pytest.raises(ValueError):
        FrameVerdict(
            frame_id="f1", frame_kind=FrameKind.TEXT, world_assumption=WorldAssumption.OPEN,
            query="b", verdict=FrameVerdictKind.ENTAILED_FALSE,
            proof=_proof("proof_chain.entail", "REFUTED", PositiveRefutationKind.ROBDD_REFUTATION),
            basis="as_told", trace_hash="th", provenance=(),
        )


@pytest.mark.parametrize(
    "kind",
    [
        FrameVerdictKind.UNDETERMINED,
        FrameVerdictKind.CONTRADICTION,
        FrameVerdictKind.SCOPE_BOUNDARY,
    ],
)
def test_refusal_verdicts_need_no_positive_proof(kind) -> None:
    # a proofless / None-kind proof is fine for every refusal/undetermined/contradiction verdict
    # (only the two COMMITTED verdicts — entailed_true / entailed_false — are proof-gated).
    v = _make(kind, _proof("proof_chain.entail", "UNKNOWN", None, sha=""))
    assert v.verdict is kind


# --------------------------------------------------------------------------- #
# Symmetric admissibility — entailed_true needs a positive entailment/support proof
# --------------------------------------------------------------------------- #


def test_valid_text_entailed_true_constructs() -> None:
    v = _make(FrameVerdictKind.ENTAILED_TRUE, _proof("proof_chain.entail", "ENTAILED", None))
    assert v.verdict is FrameVerdictKind.ENTAILED_TRUE


def test_valid_perception_entailed_true_constructs() -> None:
    v = _make(FrameVerdictKind.ENTAILED_TRUE, _proof("sensorium.falsification", "SUPPORTED", None))
    assert v.verdict is FrameVerdictKind.ENTAILED_TRUE


def test_entailed_true_with_wrong_outcome_raises() -> None:
    # an UNKNOWN/REFUTED outcome cannot back a committed "Yes." — symmetric with entailed_false.
    with pytest.raises(ValueError):
        _make(FrameVerdictKind.ENTAILED_TRUE, _proof("proof_chain.entail", "UNKNOWN", None))


def test_entailed_true_with_missing_proof_sha_raises() -> None:
    with pytest.raises(ValueError):
        _make(FrameVerdictKind.ENTAILED_TRUE, _proof("proof_chain.entail", "ENTAILED", None, sha=""))


def test_entailed_true_with_a_refutation_kind_raises() -> None:
    # a "true" carrying a positive_refutation_kind is malformed (refutation kinds prove FALSE).
    with pytest.raises(ValueError):
        _make(
            FrameVerdictKind.ENTAILED_TRUE,
            _proof("proof_chain.entail", "ENTAILED", PositiveRefutationKind.ROBDD_REFUTATION),
        )


# --------------------------------------------------------------------------- #
# Absence safety + determinism + distinctness
# --------------------------------------------------------------------------- #


def test_absence_never_yields_entailed_false() -> None:
    # a closed frame with no fact bearing on b: UNDETERMINED, never entailed_false.
    v = evaluate_frame_verdict(_frame(["a", "c -> d"]), "b")
    assert v.verdict is not FrameVerdictKind.ENTAILED_FALSE
    assert v.verdict is FrameVerdictKind.UNDETERMINED


def test_premise_reordering_keeps_trace_hash_stable() -> None:
    a = evaluate_frame_verdict(_frame(["a", "a -> b", "b -> c"]), "c")
    b = evaluate_frame_verdict(_frame(["b -> c", "a -> b", "a"]), "c")
    assert a.verdict is b.verdict is FrameVerdictKind.ENTAILED_TRUE
    assert a.trace_hash == b.trace_hash and a.proof.proof_sha256 == b.proof.proof_sha256


def test_repeated_evaluation_keeps_trace_hash_stable() -> None:
    a = evaluate_frame_verdict(_frame(["a", "a -> ~b"]), "b")
    b = evaluate_frame_verdict(_frame(["a", "a -> ~b"]), "b")
    assert a.trace_hash == b.trace_hash and a.proof.proof_sha256 == b.proof.proof_sha256


def test_frame_verdict_is_distinct_from_determined() -> None:
    # no `answer` field, a 5-way verdict enum — cannot be confused with an open-world answer.
    field_names = {f.name for f in dataclasses.fields(FrameVerdict)}
    assert "answer" not in field_names
    assert "verdict" in field_names
    assert FrameVerdict.__name__ == "FrameVerdict"  # distinct call-name from Determined

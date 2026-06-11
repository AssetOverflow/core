"""ADR-0218 PR B — PromotionCertificate + replay verifier (pure substrate).

PROMOTION IS STILL NOT LIVE.  These tests prove the *certificate* substrate:
build → freeze → replay-verify, fail-closed on every tamper.  The promoter
obligations (O1–O5, O7) remain strict-xfail in
tests/test_proof_carrying_promotion_obligations.py — every one of them binds
to `teaching.proof_promotion`, which must not exist before ADR-0218 is
ratified (P3).  What PR B retires is not a marker but a gap: the
certificate-shaped halves of O1/O7 (replay re-verification, byte-stable
determinism) are proven here for real instead of being asserted inside
promoter xfails.

Tamper tests use `dataclasses.replace` deliberately: the certificate's
authority comes from replay recomputation, never from trust in the frozen
object — a forged field must fail `verify_certificate`, not be unrepresentable.
"""

from __future__ import annotations

import ast
import dataclasses
import json
from pathlib import Path

import pytest

from generate.proof_chain import (
    CERTIFICATE_VERSION,
    ENGINE_PIN_MISMATCH,
    INCONSISTENT_PREMISES,
    MALFORMED_CERTIFICATE,
    OUT_OF_REGIME_OR_MALFORMED,
    PREMISE_STATUS_VOCAB,
    REPLAY_MATCH,
    REPLAY_MISMATCH,
    TAUTOLOGICAL_IMPLICATION,
    TAUTOLOGICAL_REFUTATION,
    UNDETERMINED,
    VERIFICATION_REASONS,
    Entailment,
    PremiseRecord,
    PromotionCertificate,
    build_certificate,
    evaluate_entailment_with_trace,
    verify_certificate,
)
import generate.proof_chain.certificate as certificate_module

# Opaque to the module under test; the real deductive-lane SHA is supplied by
# the P3 promoter from scripts/verify_lane_shas.py, never read from disk here.
_PIN = "deductive_logic_v1@pinned-for-test"

_CERTIFICATE_SOURCE = Path(certificate_module.__file__).read_text(encoding="utf-8")


def _coherent(*pairs: tuple[int, str]) -> tuple[PremiseRecord, ...]:
    return tuple(
        PremiseRecord(entry_id=entry_id, form=form, status="coherent")
        for entry_id, form in pairs
    )


def _build(claim: str, premises: tuple[PremiseRecord, ...]) -> PromotionCertificate:
    return build_certificate(claim_form=claim, premises=premises, engine_pin=_PIN)


# ---------------------------------------------------------------------------
# 1. The positive path: entailed certificate verifies
# ---------------------------------------------------------------------------

def test_entailed_certificate_verifies() -> None:
    cert = _build("q", _coherent((1, "p"), (2, "p -> q")))
    assert cert.certificate_version == CERTIFICATE_VERSION
    assert cert.decision == Entailment.ENTAILED.value
    assert cert.reason == TAUTOLOGICAL_IMPLICATION
    assert cert.promotion_positive is True

    verdict = verify_certificate(cert)
    assert verdict.verified is True
    assert verdict.reason == REPLAY_MATCH


def test_embedded_trace_matches_independent_recomputation() -> None:
    """The O1 substrate half, proven for real: recomputing from the embedded
    forms reproduces the embedded EntailmentTrace exactly (ADR-0218 §D3.4)."""
    cert = _build("q", _coherent((1, "p"), (2, "p -> q")))
    recomputed = evaluate_entailment_with_trace(("p", "p -> q"), "q")
    assert cert.entailment_trace == recomputed.as_dict()


# ---------------------------------------------------------------------------
# 2–4. Tampering fails replay
# ---------------------------------------------------------------------------

def test_tampered_premise_form_fails_verification() -> None:
    cert = _build("q", _coherent((1, "p"), (2, "p -> q")))
    tampered = dataclasses.replace(cert, premise_forms=("p", "p -> r"))
    verdict = verify_certificate(tampered)
    assert verdict.verified is False
    assert verdict.reason == REPLAY_MISMATCH


def test_tampered_claim_form_fails_verification() -> None:
    cert = _build("q", _coherent((1, "p"), (2, "p -> q")))
    tampered = dataclasses.replace(cert, claim_form="r")
    verdict = verify_certificate(tampered)
    assert verdict.verified is False
    assert verdict.reason == REPLAY_MISMATCH


def test_tampered_certificate_version_fails_verification() -> None:
    cert = _build("q", _coherent((1, "p"), (2, "p -> q")))
    tampered = dataclasses.replace(cert, certificate_version=CERTIFICATE_VERSION + 1)
    verdict = verify_certificate(tampered)
    assert verdict.verified is False
    assert verdict.reason == REPLAY_MISMATCH


def test_swapped_entailment_trace_fails_verification() -> None:
    """Strongest form: graft a *valid, also-ENTAILED* trace from a different
    proof — same decision and reason, different evidence keys.  Replay must
    reject the certificate on the evidence, not the verdict label."""
    cert = _build("q", _coherent((1, "p"), (2, "p -> q")))
    other = _build("b", _coherent((1, "a"), (2, "a -> b")))
    assert other.decision == Entailment.ENTAILED.value
    grafted = dataclasses.replace(cert, entailment_trace=other.entailment_trace)
    verdict = verify_certificate(grafted)
    assert verdict.verified is False
    assert verdict.reason == REPLAY_MISMATCH


# ---------------------------------------------------------------------------
# 5. Non sequitur: an unentailed claim cannot be certified entailed
# ---------------------------------------------------------------------------

def test_non_sequitur_does_not_verify_as_entailed() -> None:
    cert = _build("q", _coherent((1, "p")))  # consistent with {p}, not entailed
    assert cert.decision == Entailment.UNKNOWN.value
    assert cert.reason == UNDETERMINED
    assert cert.promotion_positive is False
    # It verifies as what it honestly is...
    assert verify_certificate(cert).verified is True

    # ...and forging the decision (or its reason) fails replay.
    forged = dataclasses.replace(cert, decision=Entailment.ENTAILED.value)
    assert verify_certificate(forged).verified is False
    forged_reason = dataclasses.replace(cert, reason=TAUTOLOGICAL_IMPLICATION)
    assert verify_certificate(forged_reason).verified is False


# ---------------------------------------------------------------------------
# 6–7. Refusal-first: inconsistency and malformed input never vacuously entail
# ---------------------------------------------------------------------------

def test_inconsistent_premises_refuse_not_vacuously_entail() -> None:
    cert = _build("q", _coherent((1, "p"), (2, "~p")))
    assert cert.decision == Entailment.REFUSED.value
    assert cert.reason == INCONSISTENT_PREMISES
    assert cert.decision != Entailment.ENTAILED.value
    assert cert.promotion_positive is False
    verdict = verify_certificate(cert)
    assert verdict.verified is True  # the refusal itself replays
    assert verdict.reason == REPLAY_MATCH


@pytest.mark.parametrize(
    "claim, premises",
    [
        ("q", _coherent((1, "p -> ("))),          # malformed premise
        ("q -> (", _coherent((1, "p"))),           # malformed claim
        ("q", _coherent((1, "forall x. p(x)"))),   # out-of-regime (quantified)
    ],
)
def test_malformed_or_out_of_regime_refuses(
    claim: str, premises: tuple[PremiseRecord, ...]
) -> None:
    cert = _build(claim, premises)
    assert cert.decision == Entailment.REFUSED.value
    assert cert.reason == OUT_OF_REGIME_OR_MALFORMED
    assert cert.promotion_positive is False
    assert verify_certificate(cert).verified is True


# ---------------------------------------------------------------------------
# 8–9. Determinism: canonical premise order, byte-stable canonical_json
# ---------------------------------------------------------------------------

def test_premise_order_is_canonical_and_deterministic() -> None:
    forward = _build("q", _coherent((1, "p"), (2, "p -> q")))
    reversed_input = _build("q", _coherent((2, "p -> q"), (1, "p")))
    assert forward.canonical_json() == reversed_input.canonical_json()
    assert forward.premise_entry_ids == (1, 2)
    assert forward.premise_forms == ("p", "p -> q")


def test_canonical_json_is_byte_stable_across_double_construction() -> None:
    first = _build("q", _coherent((1, "p"), (2, "p -> q")))
    second = _build("q", _coherent((1, "p"), (2, "p -> q")))
    assert first.canonical_json() == second.canonical_json()
    # Canonical form: sorted keys, compact separators — re-serializing the
    # parsed payload under the same policy must be a fixed point.
    payload = first.canonical_json()
    assert payload == json.dumps(
        json.loads(payload), sort_keys=True, separators=(",", ":")
    )


# ---------------------------------------------------------------------------
# 10. Only ENTAILED (non-empty, all-coherent) is promotion-positive
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "claim, premises, expected_decision, expected_reason",
    [
        ("q", _coherent((1, "p"), (2, "p -> ~q")),
         Entailment.REFUTED.value, TAUTOLOGICAL_REFUTATION),
        ("q", _coherent((1, "p")),
         Entailment.UNKNOWN.value, UNDETERMINED),
        ("q", _coherent((1, "p"), (2, "~p")),
         Entailment.REFUSED.value, INCONSISTENT_PREMISES),
        ("q", _coherent((1, "p -> (")),
         Entailment.REFUSED.value, OUT_OF_REGIME_OR_MALFORMED),
    ],
)
def test_non_entailed_outcomes_are_never_promotion_positive(
    claim: str,
    premises: tuple[PremiseRecord, ...],
    expected_decision: str,
    expected_reason: str,
) -> None:
    cert = _build(claim, premises)
    assert cert.decision == expected_decision
    assert cert.reason == expected_reason
    assert cert.promotion_positive is False
    # Each outcome verifies as itself — refusals and unknowns are replayable
    # evidence too, just never promotion-positive.
    assert verify_certificate(cert).verified is True


def test_entailed_over_non_coherent_recorded_status_is_not_positive() -> None:
    """Valid entailment over a speculative premise: the certificate is honest
    evidence (verifies) but never promotion-positive — the recorded status
    gate is part of positivity, before P3's fresh-read gate even runs."""
    premises = (
        PremiseRecord(entry_id=1, form="p", status="coherent"),
        PremiseRecord(entry_id=2, form="p -> q", status="speculative"),
    )
    cert = _build("q", premises)
    assert cert.decision == Entailment.ENTAILED.value
    assert cert.promotion_positive is False
    assert verify_certificate(cert).verified is True


def test_zero_premise_tautology_is_entailed_but_not_positive() -> None:
    """A tautology is entailed by the empty set — sound, but fail-closed out
    of v1 promotion scope (module docstring; ratification question)."""
    cert = _build("q | ~q", ())
    assert cert.decision == Entailment.ENTAILED.value
    assert cert.promotion_positive is False
    assert verify_certificate(cert).verified is True


# ---------------------------------------------------------------------------
# Engine pin: recorded provenance, checkable only against a supplied pin
# ---------------------------------------------------------------------------

def test_engine_pin_is_checked_when_expected_pin_is_supplied() -> None:
    cert = _build("q", _coherent((1, "p"), (2, "p -> q")))
    assert verify_certificate(cert, expected_engine_pin=_PIN).verified is True
    mismatch = verify_certificate(cert, expected_engine_pin="other-pin")
    assert mismatch.verified is False
    assert mismatch.reason == ENGINE_PIN_MISMATCH


def test_engine_pin_tamper_passes_pure_replay_documented_wrinkle() -> None:
    """HONEST LIMIT, pinned on purpose: the pin is carried verbatim through
    the rebuild, so pure replay cannot detect pin tampering — the module has
    no filesystem and nothing true to compare against.  P3 MUST pass
    expected_engine_pin (the deductive-lane SHA in force) to close this."""
    cert = _build("q", _coherent((1, "p"), (2, "p -> q")))
    tampered = dataclasses.replace(cert, engine_pin="forged-pin")
    assert verify_certificate(tampered).verified is True
    checked = verify_certificate(tampered, expected_engine_pin=_PIN)
    assert checked.verified is False
    assert checked.reason == ENGINE_PIN_MISMATCH


# ---------------------------------------------------------------------------
# Structural fail-closed: contract violations raise / verify malformed
# ---------------------------------------------------------------------------

def test_structural_contract_violations_raise() -> None:
    with pytest.raises(ValueError, match="duplicate premise entry_ids"):
        _build("q", _coherent((1, "p"), (1, "p -> q")))
    with pytest.raises(ValueError, match="closed vocabulary"):
        PremiseRecord(entry_id=1, form="p", status="definitely_legit")
    with pytest.raises(ValueError, match="entry_id must be an int"):
        PremiseRecord(entry_id=True, form="p", status="coherent")
    with pytest.raises(ValueError, match="premise form must be a str"):
        PremiseRecord(entry_id=1, form=None, status="coherent")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="engine_pin"):
        build_certificate(
            claim_form="q", premises=_coherent((1, "p")), engine_pin="   "
        )
    with pytest.raises(ValueError, match="claim_form"):
        build_certificate(
            claim_form=None,  # type: ignore[arg-type]
            premises=_coherent((1, "p")),
            engine_pin=_PIN,
        )


def test_structurally_broken_certificates_verify_malformed() -> None:
    cert = _build("q", _coherent((1, "p"), (2, "p -> q")))
    # Field-length mismatch (zip strict in the rebuild).
    short = dataclasses.replace(cert, premise_forms=("p",))
    assert verify_certificate(short).reason == MALFORMED_CERTIFICATE
    # Tampered status outside the closed vocabulary.
    bad_status = dataclasses.replace(cert, premise_statuses=("coherent", "trusted"))
    assert verify_certificate(bad_status).reason == MALFORMED_CERTIFICATE
    # Non-serializable trace payload.
    junk = dataclasses.replace(cert, entailment_trace={"outcome": object()})
    assert verify_certificate(junk).reason == MALFORMED_CERTIFICATE
    for broken in (short, bad_status, junk):
        assert verify_certificate(broken).verified is False


def test_verification_reasons_are_a_closed_vocabulary() -> None:
    assert VERIFICATION_REASONS == frozenset(
        {REPLAY_MATCH, REPLAY_MISMATCH, MALFORMED_CERTIFICATE, ENGINE_PIN_MISMATCH}
    )


# ---------------------------------------------------------------------------
# 11–12. Boundary hygiene: pure imports, no status-transition surface
# ---------------------------------------------------------------------------

def test_certificate_module_imports_are_pure() -> None:
    """No vault / teaching / session / runtime-shell import, no I/O or
    nondeterminism module — the certificate is evidence, not an actor."""
    tree = ast.parse(_CERTIFICATE_SOURCE)
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "use absolute imports in certificate.py"
            assert node.module is not None
            roots.add(node.module.split(".")[0])
    allowed = {"__future__", "json", "dataclasses", "typing", "generate"}
    assert roots <= allowed, f"impure imports in certificate.py: {roots - allowed}"

    forbidden_calls = {"eval", "exec", "open", "__import__", "compile"}
    offenders = [
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in forbidden_calls
    ]
    assert offenders == [], f"forbidden calls in certificate.py: {offenders}"


def test_certificate_module_has_no_status_transition_surface() -> None:
    """INV-29's own detector, applied directly: zero epistemic-status
    transition writes in certificate.py (the tree-wide INV-29 scan covers it
    too; this pins the file explicitly so a future edit fails loudly here)."""
    from tests.test_architectural_invariants import _status_transition_writes

    tree = ast.parse(_CERTIFICATE_SOURCE)
    assert _status_transition_writes(tree) == 0
    status_literals = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and node.value == "epistemic_status"
    ]
    assert status_literals == [], (
        "certificate.py must not handle the epistemic_status key at all — "
        "status strings arrive pre-read in PremiseRecord.status"
    )


def test_status_vocab_matches_teaching_enum() -> None:
    """The local closed vocab mirrors teaching.epistemic.EpistemicStatus
    values (generate/ must not import teaching/; this test owns the sync)."""
    from teaching.epistemic import EpistemicStatus

    assert PREMISE_STATUS_VOCAB == frozenset(s.value for s in EpistemicStatus)

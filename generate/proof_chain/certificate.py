"""ADR-0218 PR B — ``PromotionCertificate`` + pure replay verifier.

ADR-0218 is ratified (2026-06-11) and the P3 promoter exists
(``teaching/proof_promotion.py``; the transition owner is
``VaultStore.apply_certified_promotion``).  THE FEATURE HAS NO RUNTIME CALLER
YET — no chat/runtime turn path invokes promotion (the deterministic demo is
PR D).  This module remains the side-effect-free *evidence substrate*: it
decides nothing about the vault and mutates nothing anywhere:

- no vault / teaching / session import — premises arrive as already-read
  ``PremiseRecord`` values; binding them to real vault entries (fresh-read,
  ADR-0218 §D3.1) and checking reading certification (§D3.2) is the
  promoter's job, not this module's;
- no status transition — INV-29's allowlist (``vault/store.py``) is untouched;
- no clock, randomness, environment, or filesystem — a certificate is a pure
  function of ``(claim_form, premises, engine_pin)``, byte-stable under
  replay.

``build_certificate`` runs the sound+complete propositional engine
(:func:`generate.proof_chain.entail.evaluate_entailment_with_trace`, the
ADR-0201/0202 ROBDD keystone) and freezes the outcome plus its full
``EntailmentTrace`` into the certificate.  ``verify_certificate`` re-runs the
engine from the embedded forms and accepts iff the rebuilt certificate is
byte-identical under ``canonical_json()`` — any tamper with the claim form,
a premise form, the trace, the decision, the reason, the premise ordering,
or the version fails replay.

Honesty boundaries (load-bearing):

- ``promotion_positive`` is NECESSARY, never sufficient.  It checks the
  *recorded* decision and statuses; the P3 promoter must additionally
  fresh-read premise statuses and reading certification from the vault
  (§D3.1–D3.2) and call ``verify_certificate`` (§D3.4) before any
  transition.  ``entailed`` is the only positive decision; ``refuted`` /
  ``unknown`` / ``refused`` certificates verify as their own outcomes but
  are never positive.
- ``engine_pin`` is recorded provenance, carried verbatim through replay.
  It is independently checkable only against a caller-supplied
  ``expected_engine_pin`` (the deductive-lane SHA in force) — pure replay
  cannot know the true pin, because this module has no filesystem.
- Zero-premise certificates (tautology claims, entailed by the empty set)
  are never promotion-positive in v1; whether tautologies may promote is a
  ratification question, recorded fail-closed here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Final

from generate.proof_chain.entail import Entailment, evaluate_entailment_with_trace

CERTIFICATE_VERSION: Final[int] = 1

# Mirrors the *values* of teaching.epistemic.EpistemicStatus.  generate/ does
# not import teaching/ (layering: teaching consumes generate, never the
# reverse); the sync is pinned by
# tests/test_proof_chain_certificate.py::test_status_vocab_matches_teaching_enum.
PREMISE_STATUS_VOCAB: Final[frozenset[str]] = frozenset({
    "coherent",
    "contested",
    "speculative",
    "falsified",
})
_COHERENT: Final[str] = "coherent"

# Closed verification-reason vocabulary (the verifier makes exactly these
# distinctions).
REPLAY_MATCH: Final[str] = "replay_match"
REPLAY_MISMATCH: Final[str] = "replay_mismatch"
MALFORMED_CERTIFICATE: Final[str] = "malformed_certificate"
ENGINE_PIN_MISMATCH: Final[str] = "engine_pin_mismatch"

VERIFICATION_REASONS: Final[frozenset[str]] = frozenset({
    REPLAY_MATCH,
    REPLAY_MISMATCH,
    MALFORMED_CERTIFICATE,
    ENGINE_PIN_MISMATCH,
})


def _require_str(value: object, what: str) -> str:
    """Boundary type check for untyped callers; fail-closed replay needs
    tampered-type fields to raise ``ValueError``, never an arbitrary error."""
    if not isinstance(value, str):
        raise ValueError(
            f"certificate: {what} must be a str, got {type(value).__name__}"
        )
    return value


def _require_entry_id(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(
            f"certificate: premise entry_id must be an int, got "
            f"{type(value).__name__}"
        )
    return value


def _require_record(value: object) -> "PremiseRecord":
    if not isinstance(value, PremiseRecord):
        raise ValueError(
            f"certificate: premises must be PremiseRecord values, got "
            f"{type(value).__name__}"
        )
    return value


@dataclass(frozen=True, slots=True)
class PremiseRecord:
    """One already-read premise: vault identity + certified form + status.

    The record is a *claim about* a vault entry, not the entry itself — the
    P3 promoter is responsible for having fresh-read ``form`` and ``status``
    from the store (never from the proposer) before building a certificate.
    """

    entry_id: int
    form: str
    status: str

    def __post_init__(self) -> None:
        _require_entry_id(self.entry_id)
        _require_str(self.form, "premise form")
        if self.status not in PREMISE_STATUS_VOCAB:
            raise ValueError(
                f"certificate: premise status {self.status!r} is not in the "
                f"closed vocabulary {sorted(PREMISE_STATUS_VOCAB)}"
            )


@dataclass(frozen=True, slots=True)
class PromotionCertificate:
    """Frozen, deterministic audit artifact for one entailment decision.

    Premises are stored in canonical order (ascending ``entry_id``);
    ``decision``/``reason`` mirror the embedded ``entailment_trace`` and the
    closed vocabularies of :mod:`generate.proof_chain.entail`.  Tampering
    with any field is caught by :func:`verify_certificate`, not by interior
    immutability — the dataclass is frozen, but the certificate's authority
    comes from replay, never from trust in the object.
    """

    certificate_version: int
    claim_form: str
    premise_entry_ids: tuple[int, ...]
    premise_forms: tuple[str, ...]
    premise_statuses: tuple[str, ...]
    entailment_trace: dict[str, object]
    engine_pin: str
    decision: str
    reason: str

    @property
    def promotion_positive(self) -> bool:
        """Necessary-not-sufficient promotion precondition (module docstring).

        ``entailed`` over a non-empty, all-coherent *recorded* premise set.
        The P3 promoter must still fresh-read statuses, check reading
        certification, and replay-verify before any transition.
        """
        return (
            self.decision == Entailment.ENTAILED.value
            and len(self.premise_statuses) > 0
            and all(status == _COHERENT for status in self.premise_statuses)
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "certificate_version": self.certificate_version,
            "claim_form": self.claim_form,
            "premise_entry_ids": self.premise_entry_ids,
            "premise_forms": self.premise_forms,
            "premise_statuses": self.premise_statuses,
            "entailment_trace": dict(self.entailment_trace),
            "engine_pin": self.engine_pin,
            "decision": self.decision,
            "reason": self.reason,
        }

    def canonical_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class CertificateVerification:
    """Replay verdict: ``verified`` + a reason from ``VERIFICATION_REASONS``."""

    verified: bool
    reason: str


def build_certificate(
    *,
    claim_form: str,
    premises: tuple[PremiseRecord, ...],
    engine_pin: str,
) -> PromotionCertificate:
    """Run the entailment engine and freeze the decision into a certificate.

    Pure: same inputs → byte-identical certificate.  Premises are
    canonicalized to ascending ``entry_id`` order before the engine runs, so
    caller ordering cannot perturb the artifact.  Structural contract
    violations (duplicate entry ids, wrong types, empty engine pin) raise
    ``ValueError``; *content* problems — malformed / out-of-regime forms,
    inconsistent premises — are the engine's authority and surface as a
    ``refused`` decision, never as a vacuous entailment.
    """
    _require_str(claim_form, "claim_form")
    if not _require_str(engine_pin, "engine_pin").strip():
        raise ValueError("certificate: engine_pin must be a non-empty str")
    checked = tuple(_require_record(record) for record in premises)
    entry_ids = [record.entry_id for record in checked]
    if len(set(entry_ids)) != len(entry_ids):
        raise ValueError(
            f"certificate: duplicate premise entry_ids {sorted(entry_ids)}"
        )

    ordered = tuple(sorted(checked, key=lambda record: record.entry_id))
    forms = tuple(record.form for record in ordered)
    trace = evaluate_entailment_with_trace(forms, claim_form)
    return PromotionCertificate(
        certificate_version=CERTIFICATE_VERSION,
        claim_form=claim_form,
        premise_entry_ids=tuple(record.entry_id for record in ordered),
        premise_forms=forms,
        premise_statuses=tuple(record.status for record in ordered),
        entailment_trace=trace.as_dict(),
        engine_pin=engine_pin,
        decision=trace.outcome.value,
        reason=trace.reason,
    )


def verify_certificate(
    certificate: PromotionCertificate,
    *,
    expected_engine_pin: str | None = None,
) -> CertificateVerification:
    """Re-run the engine from the embedded forms; accept iff byte-identical.

    Rebuilds a certificate from ``(claim_form, premises, engine_pin)`` as
    embedded and compares ``canonical_json()`` byte-for-byte — a tampered
    premise form, claim form, swapped trace, forged decision/reason, broken
    ordering, or wrong version all fail replay.  ``engine_pin`` is carried
    verbatim through the rebuild, so pin provenance is only checked when the
    caller supplies ``expected_engine_pin`` (P3 must pass the deductive-lane
    SHA in force).  Structurally unusable certificates fail closed as
    ``malformed_certificate``.
    """
    if expected_engine_pin is not None and certificate.engine_pin != expected_engine_pin:
        return CertificateVerification(verified=False, reason=ENGINE_PIN_MISMATCH)
    try:
        records = tuple(
            PremiseRecord(entry_id=entry_id, form=form, status=status)
            for entry_id, form, status in zip(
                certificate.premise_entry_ids,
                certificate.premise_forms,
                certificate.premise_statuses,
                strict=True,
            )
        )
        rebuilt = build_certificate(
            claim_form=certificate.claim_form,
            premises=records,
            engine_pin=certificate.engine_pin,
        )
        replay_matches = rebuilt.canonical_json() == certificate.canonical_json()
    except (ValueError, TypeError):
        return CertificateVerification(verified=False, reason=MALFORMED_CERTIFICATE)
    if not replay_matches:
        return CertificateVerification(verified=False, reason=REPLAY_MISMATCH)
    return CertificateVerification(verified=True, reason=REPLAY_MATCH)

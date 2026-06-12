"""teaching/proof_promotion.py — ADR-0218 P3: the pure proof-carrying
promotion decider.

``certify_promotion`` decides whether a stored SPECULATIVE claim is
promotable to COHERENT because it is *deductively entailed* by an
all-COHERENT, curator-certified premise set (ADR-0218 §D3).  This module is
**pure decision logic**:

- it performs NO mutation and holds no vault write access — INV-21's and
  INV-29's allowlists are untouched (the structural proof lives in
  ``tests/test_adr_0218_proof_promotion.py``);
- the only mutation owner is ``VaultStore.apply_certified_promotion``
  (vault/store.py), which **independently re-verifies** the certificate and
  the live store state before flipping anything — a decision object from
  this module is a recommendation, never authority;
- it is not a parallel learning path: it produces a decision consumed by the
  single existing mutation owner, exactly the ADR-0148 policy/owner split.

Admissibility predicate (ADR-0218 §D3, exact):

1. Every premise ref resolves to a stored vault entry, fresh-read at
   decision time, with ``epistemic_status == "coherent"`` (strict string
   compare — no parse-defaulting anywhere in this module).
2. Every premise form AND the claim form are curator-certified readings
   (``reading_certified is True`` + a non-empty ``propositional_form``),
   taken from the store, never from the proposer.  The claim is itself a
   stored entry (``claim_entry_index``); a proposer cannot supply a form.
3. The engine outcome is ENTAILED.  REFUTED / UNKNOWN / REFUSED never
   promote; REFUTED also never demotes (no status is written here at all).
4. The built certificate replay-verifies under the pinned engine
   (``DEDUCTIVE_ENGINE_PIN``).
5. ``proposer_payload`` is data, never authority: it is accepted so
   proposers can attach proof candidates / statuses / confidences, and it
   is provably never read — the decision is byte-identical with and
   without it.

Any failure refuses with a typed reason from ``DECISION_REASONS``; the claim
stays SPECULATIVE.  Fail-closed is the only failure mode.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, Mapping

from generate.proof_chain.certificate import (
    PremiseRecord,
    PromotionCertificate,
    build_certificate,
    verify_certificate,
)
from generate.proof_chain.engine_pin import DEDUCTIVE_ENGINE_PIN
from teaching.epistemic import EpistemicStatus

if TYPE_CHECKING:
    from vault.store import VaultStore

# Closed decision-reason vocabulary.  O3/O4 obligation contract: the premise
# gates name "premise", the reading gates name "reading".
PROMOTED_ENTAILED: Final[str] = "promoted_entailed_from_coherent_premises"
REFUSED_NO_PREMISES: Final[str] = "refused_no_premises"
REFUSED_DUPLICATE_PREMISES: Final[str] = "refused_duplicate_premise_entries"
REFUSED_PREMISE_MISSING: Final[str] = "refused_premise_entry_missing"
REFUSED_PREMISE_NOT_COHERENT: Final[str] = "refused_premise_not_coherent"
REFUSED_PREMISE_READING: Final[str] = "refused_premise_reading_uncertified"
REFUSED_CLAIM_MISSING: Final[str] = "refused_claim_entry_missing"
REFUSED_CLAIM_NOT_SPECULATIVE: Final[str] = "refused_claim_not_speculative"
REFUSED_CLAIM_READING: Final[str] = "refused_claim_reading_uncertified"
REFUSED_NOT_ENTAILED: Final[str] = "refused_not_entailed"
REFUSED_MALFORMED_INPUT: Final[str] = "refused_malformed_input"
REFUSED_CERTIFICATE_REPLAY: Final[str] = "refused_certificate_replay_failed"

DECISION_REASONS: Final[frozenset[str]] = frozenset({
    PROMOTED_ENTAILED,
    REFUSED_NO_PREMISES,
    REFUSED_DUPLICATE_PREMISES,
    REFUSED_PREMISE_MISSING,
    REFUSED_PREMISE_NOT_COHERENT,
    REFUSED_PREMISE_READING,
    REFUSED_CLAIM_MISSING,
    REFUSED_CLAIM_NOT_SPECULATIVE,
    REFUSED_CLAIM_READING,
    REFUSED_NOT_ENTAILED,
    REFUSED_MALFORMED_INPUT,
    REFUSED_CERTIFICATE_REPLAY,
})


@dataclass(frozen=True, slots=True)
class PromotionDecision:
    """Outcome of one promotion certification.

    ``certificate`` is attached whenever the engine ran (including refused
    outcomes — the refusal is audit evidence too); it is ``None`` when a
    store-state gate refused before the engine could run.
    ``certificate_digest`` is the SHA-256 of ``certificate.canonical_json()``
    — the value ADR-0218 §D4 folds into the turn ``trace_hash`` once a
    runtime caller exists.
    """

    promoted: bool
    reason: str
    claim_entry_index: int
    certificate: PromotionCertificate | None
    certificate_digest: str | None


def certificate_digest(certificate: PromotionCertificate) -> str:
    """SHA-256 hex digest of the certificate's canonical JSON (D4 folding)."""
    return hashlib.sha256(certificate.canonical_json().encode("utf-8")).hexdigest()


def _is_index(value: object) -> bool:
    """Vault entry indices are non-negative ints; bool is not an index."""
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _fresh_read(vault: "VaultStore", index: object) -> Mapping[str, object] | None:
    """Fresh-read one entry's metadata from the store (read-only view).

    Uses the sanctioned ``iter_metadata`` read surface; returns None when the
    index does not resolve.  Decision-time freshness is the point: nothing
    cached, nothing proposer-supplied.
    """
    if not _is_index(index):
        return None
    for i, meta in vault.iter_metadata():
        if i == index:
            return meta
    return None


def _certified_form(meta: Mapping[str, object]) -> str | None:
    """The curator-certified reading, or None if certification is absent.

    ``reading_certified`` must be the boolean ``True`` — a truthy stand-in
    (``1``, ``"yes"``) is not a curator certification.  The form must be a
    non-empty string.  Fail-closed: any gap returns None.
    """
    if meta.get("reading_certified") is not True:
        return None
    form = meta.get("propositional_form")
    if not isinstance(form, str) or not form.strip():
        return None
    return form


def _refusal(reason: str, claim_entry_index: int) -> PromotionDecision:
    return PromotionDecision(
        promoted=False,
        reason=reason,
        claim_entry_index=claim_entry_index,
        certificate=None,
        certificate_digest=None,
    )


def certify_promotion(
    *,
    claim_entry_index: int,
    premise_entry_indices: tuple[int, ...],
    vault: "VaultStore",
    proposer_payload: object = None,
) -> PromotionDecision:
    """Decide promotability of one stored SPECULATIVE claim.  Pure: no
    mutation; the caller hands the decision's certificate to
    ``VaultStore.apply_certified_promotion``, which re-verifies independently.
    """
    # D3.5 — data, never authority.  Accepted so proposers can attach proof /
    # status / confidence; deleted unread, so the decision cannot depend on it.
    del proposer_payload

    safe_index = claim_entry_index if _is_index(claim_entry_index) else -1

    if not isinstance(premise_entry_indices, tuple) or not all(
        _is_index(i) for i in premise_entry_indices
    ):
        return _refusal(REFUSED_MALFORMED_INPUT, safe_index)
    if len(premise_entry_indices) == 0:
        # Zero-premise (tautology) certificates never promote in v1 — D3.1 is
        # vacuous over the empty set, so the empty set refuses (ratified D3.b).
        return _refusal(REFUSED_NO_PREMISES, safe_index)
    if len(set(premise_entry_indices)) != len(premise_entry_indices):
        return _refusal(REFUSED_DUPLICATE_PREMISES, safe_index)

    claim_meta = _fresh_read(vault, claim_entry_index)
    if claim_meta is None:
        return _refusal(REFUSED_CLAIM_MISSING, safe_index)
    if claim_meta.get("epistemic_status") != EpistemicStatus.SPECULATIVE.value:
        # Strict compare: a garbage status must not read as "speculative".
        return _refusal(REFUSED_CLAIM_NOT_SPECULATIVE, claim_entry_index)
    claim_form = _certified_form(claim_meta)
    if claim_form is None:
        return _refusal(REFUSED_CLAIM_READING, claim_entry_index)

    records: list[PremiseRecord] = []
    for index in premise_entry_indices:
        meta = _fresh_read(vault, index)
        if meta is None:
            return _refusal(REFUSED_PREMISE_MISSING, claim_entry_index)
        form = _certified_form(meta)
        if form is None:
            return _refusal(REFUSED_PREMISE_READING, claim_entry_index)
        if meta.get("epistemic_status") != EpistemicStatus.COHERENT.value:
            # Also structurally bars self-premising: the claim is required
            # SPECULATIVE above, so it can never pass this COHERENT gate.
            return _refusal(REFUSED_PREMISE_NOT_COHERENT, claim_entry_index)
        records.append(
            PremiseRecord(
                entry_id=index,
                form=form,
                status=EpistemicStatus.COHERENT.value,
            )
        )

    try:
        certificate = build_certificate(
            claim_form=claim_form,
            premises=tuple(records),
            engine_pin=DEDUCTIVE_ENGINE_PIN,
        )
    except ValueError:
        # Unreachable given the gates above; kept as a typed fail-closed
        # refusal rather than an escaping exception.
        return _refusal(REFUSED_MALFORMED_INPUT, claim_entry_index)

    digest = certificate_digest(certificate)
    verification = verify_certificate(
        certificate, expected_engine_pin=DEDUCTIVE_ENGINE_PIN
    )
    if not verification.verified:
        return PromotionDecision(
            promoted=False,
            reason=REFUSED_CERTIFICATE_REPLAY,
            claim_entry_index=claim_entry_index,
            certificate=certificate,
            certificate_digest=digest,
        )

    promoted = certificate.promotion_positive
    return PromotionDecision(
        promoted=promoted,
        reason=PROMOTED_ENTAILED if promoted else REFUSED_NOT_ENTAILED,
        claim_entry_index=claim_entry_index,
        certificate=certificate,
        certificate_digest=digest,
    )

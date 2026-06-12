"""ADR-0218 — executable proof obligations for proof-carrying coherence
promotion.  THE OBLIGATIONS ARE LIVE: ADR-0218 was ratified 2026-06-11 and
P3 landed (`teaching/proof_promotion.py` + `VaultStore.apply_certified_promotion`),
so every former strict-xfail marker in this file is retired and each
obligation now passes on its own.

Retirement record (PR C):

- `test_pin_promoter_module_does_not_exist_yet` is DELETED per its own
  docstring — the promoter module now exists, consciously.
- The remaining two honesty pins still pass and still guard what they always
  guarded: `review_correction` carries status as an input (promotion did NOT
  fork into a parallel path there), and the entailment substrate is
  replay-stable.
- O1–O5/O7 bodies were adjusted from the PR-A provisional API
  (`claim_form=...`) to the ratified surface (`claim_entry_index=...`),
  sanctioned by PR A's provisional-API note and ratified D3 note (a): the
  claim form is fresh-read from the claim's own stored entry — forms come
  from the store, never from the proposer.  Each obligation's semantics are
  preserved and O1/O2 are strengthened to prove the transition (or its
  absence) through the single mutation owner.

O6 (no new mutation path) is enforced continuously by INV-21 + INV-29 in
tests/test_architectural_invariants.py, not here.  O8 (wrong=0 lanes) is
enforced by the existing lane gates + scripts/verify_lane_shas.py.  The
exhaustive P3 suite (staleness, tamper, pin drift, structural purity) is
tests/test_adr_0218_proof_promotion.py.
"""

from __future__ import annotations

import numpy as np

from algebra.cga import embed_point
from generate.intent import DialogueIntent, IntentTag
from generate.proof_chain import Entailment, evaluate_entailment_with_trace
from teaching import proof_promotion
from teaching.correction import CorrectionCandidate
from teaching.epistemic import EpistemicStatus
from teaching.review import review_correction
from vault.store import VaultStore


def _versor(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return embed_point(rng.standard_normal(3).astype(np.float32))


def _store_entry(
    vault: VaultStore,
    seed: int,
    form: str,
    status: EpistemicStatus,
    *,
    certified: bool = True,
) -> int:
    """Store an entry carrying a curator-certified reading (ADR-0218 §D2)."""
    return vault.store(
        _versor(seed),
        {
            "propositional_form": form,
            "reading_certified": certified,
        },
        epistemic_status=status,
    )


def _status_of(vault: VaultStore, index: int) -> str:
    return dict(vault.iter_metadata())[index]["epistemic_status"]


# ---------------------------------------------------------------------------
# Honesty pins — still true, still load-bearing
# ---------------------------------------------------------------------------

def test_pin_review_correction_carries_status_it_does_not_compute() -> None:
    """Issue §1: `epistemic_status` is a passed-in parameter of
    review_correction, not a computed coherence judgment.  ADR-0218 routed
    computed promotion through the vault transition owner, NOT through
    review_correction — this pin proves the path did not fork."""
    candidate = CorrectionCandidate(
        correction_text="the sky is blue",
        intent=DialogueIntent(tag=IntentTag.CORRECTION, subject="sky"),
        prior_surface="the sky is green",
        prior_turn=1,
        candidate_id="pin-0001",
    )
    defaulted = review_correction(candidate)
    assert defaulted.epistemic_status is EpistemicStatus.SPECULATIVE

    # The curator-supplied input flows through verbatim — no computation runs.
    echoed = review_correction(candidate, epistemic_status=EpistemicStatus.COHERENT)
    assert echoed.epistemic_status is EpistemicStatus.COHERENT, (
        "review_correction no longer carries the curator-supplied status "
        "verbatim — a computation was added. Reconcile with ADR-0218 before "
        "merging: promotion logic must not fork into a parallel path here."
    )


def test_pin_entailment_trace_substrate_is_replay_stable() -> None:
    """O7's substrate half: the engine's proof evidence is deterministic and
    re-verifies by recomputation — the property the PromotionCertificate
    replay verifier relies on."""
    premises = ("p", "p -> q")
    first = evaluate_entailment_with_trace(premises, "q")
    second = evaluate_entailment_with_trace(premises, "q")
    assert first.outcome is Entailment.ENTAILED
    assert first.canonical_json() == second.canonical_json(), (
        "EntailmentTrace is not replay-stable — certificate re-verification "
        "has no substrate to stand on."
    )

    # A non-entailed query must be UNKNOWN, not promoted-shaped evidence.
    unknown = evaluate_entailment_with_trace(("p",), "q")
    assert unknown.outcome is Entailment.UNKNOWN


# ---------------------------------------------------------------------------
# Obligations — live since ADR-0218 ratification + P3
# ---------------------------------------------------------------------------

def test_O1_entailed_from_coherent_premises_promotes_with_reverifiable_proof() -> None:
    """Issue §7.1 — a claim deductively entailed by an all-COHERENT premise
    set promotes (through the single mutation owner), and the embedded proof
    re-verifies by recomputation."""
    vault = VaultStore(reproject_interval=0)
    idx_p = _store_entry(vault, 1, "p", EpistemicStatus.COHERENT)
    idx_pq = _store_entry(vault, 2, "p -> q", EpistemicStatus.COHERENT)
    idx_q = _store_entry(vault, 3, "q", EpistemicStatus.SPECULATIVE)

    decision = proof_promotion.certify_promotion(
        claim_entry_index=idx_q,
        premise_entry_indices=(idx_p, idx_pq),
        vault=vault,
    )
    assert decision.promoted is True
    assert decision.certificate is not None

    # Replay re-verification: recomputing from the stored forms must
    # reproduce the embedded trace byte-for-byte (ADR-0218 §D3.4).
    recomputed = evaluate_entailment_with_trace(("p", "p -> q"), "q")
    assert decision.certificate.entailment_trace == recomputed.as_dict()

    # The transition itself happens only inside the vault owner.
    result = vault.apply_certified_promotion(idx_q, decision.certificate)
    assert result.applied is True
    assert _status_of(vault, idx_q) == EpistemicStatus.COHERENT.value


def test_O2_consistent_but_not_entailed_stays_speculative() -> None:
    """Issue §7.2 — mere consistency with the field is not entailment;
    UNKNOWN never promotes, and the claim's stored status does not move."""
    vault = VaultStore(reproject_interval=0)
    idx_p = _store_entry(vault, 1, "p", EpistemicStatus.COHERENT)
    idx_q = _store_entry(vault, 3, "q", EpistemicStatus.SPECULATIVE)

    decision = proof_promotion.certify_promotion(
        claim_entry_index=idx_q,
        premise_entry_indices=(idx_p,),
        vault=vault,
    )
    assert decision.promoted is False
    assert decision.certificate is not None
    result = vault.apply_certified_promotion(idx_q, decision.certificate)
    assert result.applied is False
    assert _status_of(vault, idx_q) == EpistemicStatus.SPECULATIVE.value


def test_O3_any_non_coherent_premise_refuses() -> None:
    """Issue §7.3 — a SPECULATIVE premise poisons the proof for promotion
    purposes even when the entailment itself is valid."""
    vault = VaultStore(reproject_interval=0)
    idx_p = _store_entry(vault, 1, "p", EpistemicStatus.COHERENT)
    idx_pq = _store_entry(vault, 2, "p -> q", EpistemicStatus.SPECULATIVE)
    idx_q = _store_entry(vault, 3, "q", EpistemicStatus.SPECULATIVE)

    decision = proof_promotion.certify_promotion(
        claim_entry_index=idx_q,
        premise_entry_indices=(idx_p, idx_pq),
        vault=vault,
    )
    assert decision.promoted is False
    assert "premise" in decision.reason  # closed reason vocab names the gate


def test_O4_uncertified_reading_fails_closed() -> None:
    """Issue §7.4 — the reading is the hazard-bearing step. A premise whose
    propositional form lacks reading certification must refuse, never fall
    through to admission (ADR-0218 §D2)."""
    vault = VaultStore(reproject_interval=0)
    idx_p = _store_entry(vault, 1, "p", EpistemicStatus.COHERENT)
    idx_pq = _store_entry(
        vault, 2, "p -> q", EpistemicStatus.COHERENT, certified=False
    )
    idx_q = _store_entry(vault, 3, "q", EpistemicStatus.SPECULATIVE)

    decision = proof_promotion.certify_promotion(
        claim_entry_index=idx_q,
        premise_entry_indices=(idx_p, idx_pq),
        vault=vault,
    )
    assert decision.promoted is False
    assert "reading" in decision.reason


def test_O5_proposer_supplied_proof_status_confidence_are_ignored() -> None:
    """Issue §7.5 — proposer attachments are data, never authority. The
    decision must be byte-identical with and without them (echo-and-ignore,
    as demos/epistemic_truth_state does for proposed_state)."""
    vault = VaultStore(reproject_interval=0)
    idx_p = _store_entry(vault, 1, "p", EpistemicStatus.COHERENT)
    idx_q = _store_entry(vault, 3, "q", EpistemicStatus.SPECULATIVE)

    bare = proof_promotion.certify_promotion(
        claim_entry_index=idx_q,
        premise_entry_indices=(idx_p,),
        vault=vault,
    )
    adorned = proof_promotion.certify_promotion(
        claim_entry_index=idx_q,
        premise_entry_indices=(idx_p,),
        vault=vault,
        proposer_payload={
            "proof": "trust me, q follows",
            "status": "coherent",
            "confidence": 0.99,
        },
    )
    assert bare.promoted is adorned.promoted is False
    assert bare.certificate is not None and adorned.certificate is not None
    assert bare.certificate.canonical_json() == adorned.certificate.canonical_json()


def test_O7_promotion_decision_is_deterministic_and_replayable() -> None:
    """Issue §7.7 — double-run byte-identical; the certificate is the audit
    artifact replay re-verifies (its digest is emitted for trace-hash
    folding at the first runtime caller)."""

    def run() -> proof_promotion.PromotionDecision:
        vault = VaultStore(reproject_interval=0)
        idx_p = _store_entry(vault, 1, "p", EpistemicStatus.COHERENT)
        idx_pq = _store_entry(vault, 2, "p -> q", EpistemicStatus.COHERENT)
        idx_q = _store_entry(vault, 3, "q", EpistemicStatus.SPECULATIVE)
        return proof_promotion.certify_promotion(
            claim_entry_index=idx_q,
            premise_entry_indices=(idx_p, idx_pq),
            vault=vault,
        )

    first, second = run(), run()
    assert first.certificate is not None and second.certificate is not None
    assert first.certificate.canonical_json() == second.certificate.canonical_json()
    assert first.certificate_digest == second.certificate_digest

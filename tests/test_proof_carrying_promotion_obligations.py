"""ADR-0218 PR A — executable proof obligations for proof-carrying coherence
promotion.  THE FEATURE IS NOT LIVE.

Two kinds of tests, per the strict-xfail gate convention
(see tests/test_edge_budget_gate.py):

- HONESTY PINS (pass today).  They assert the *current* truth the governing
  issue documents: promotion is not computed, the promoter module does not
  exist, and the entailment substrate the future promoter will consume is
  replay-stable.  The moment someone wires promotion without consciously
  revisiting this file, a pin flips red.

- OBLIGATIONS O1–O5, O7 (xfail today, strict).  Executable spec for the
  ADR-0218 P3 promoter (`teaching/proof_promotion.py`).  Each body imports
  the not-yet-existing module, so today they xfail on ImportError.  When P3
  lands, strict=True turns any still-marked passing test into a loud XPASS
  failure — the P3 PR must retire the markers and make every obligation pass
  for real.  A test that passes under a broken implementation is decoration
  (CLAUDE.md §Schema-Defined Proof Obligations); these cannot pass at all
  until the implementation exists.

O6 (no new mutation path) is enforced continuously by INV-21 + INV-29 in
tests/test_architectural_invariants.py, not here.  O8 (wrong=0 lanes) is
enforced by the existing lane gates + scripts/verify_lane_shas.py.

PR B note: the certificate-substrate halves of O1/O7 (replay re-verification,
byte-stable determinism) are now proven for real in
tests/test_proof_chain_certificate.py against
generate/proof_chain/certificate.py.  NO xfail marker retires here — every
obligation below binds to the P3 promoter (`teaching.proof_promotion`), which
must not exist before ADR-0218 is ratified.

API surface used in the xfail bodies is PROVISIONAL per ADR-0218 §D3/§D4 —
P3 may adjust signatures, but must preserve each obligation's semantics.
"""

from __future__ import annotations

import importlib
import importlib.util

import numpy as np
import pytest

from algebra.cga import embed_point
from generate.intent import DialogueIntent, IntentTag
from generate.proof_chain import Entailment, evaluate_entailment_with_trace
from teaching.correction import CorrectionCandidate
from teaching.epistemic import EpistemicStatus
from teaching.review import review_correction
from vault.store import VaultStore

_PROMOTER_MODULE = "teaching.proof_promotion"

_XFAIL_REASON = (
    "ADR-0218 is Proposed, not ratified — the proof-carrying promoter "
    f"({_PROMOTER_MODULE}) does not exist. This test is the executable "
    "obligation; the P3 PR must retire this marker and make it pass."
)


def _promoter():
    """Import the future promoter. Raises ModuleNotFoundError today (→ xfail)."""
    return importlib.import_module(_PROMOTER_MODULE)


def _versor(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return embed_point(rng.standard_normal(3).astype(np.float32))


def _store_premise(
    vault: VaultStore,
    seed: int,
    form: str,
    status: EpistemicStatus,
    *,
    certified: bool = True,
) -> int:
    """Store a premise entry carrying a curator-certified reading (ADR-0218 §D2)."""
    return vault.store(
        _versor(seed),
        {
            "propositional_form": form,
            "reading_certified": certified,
        },
        epistemic_status=status,
    )


# ---------------------------------------------------------------------------
# Honesty pins — pass today, flip red when reality changes
# ---------------------------------------------------------------------------

def test_pin_promoter_module_does_not_exist_yet() -> None:
    """The feature is designed-but-unwired. This pin goes red in the same PR
    that creates the module, forcing the xfail markers below to be revisited
    (and this pin deleted) consciously rather than by drift."""
    assert importlib.util.find_spec(_PROMOTER_MODULE) is None, (
        f"{_PROMOTER_MODULE} now exists — ADR-0218 P3 is landing. Delete this "
        "pin AND retire every xfail marker in this file in the same PR; each "
        "obligation below must now pass on its own."
    )


def test_pin_review_correction_carries_status_it_does_not_compute() -> None:
    """Issue §1: `epistemic_status` is a passed-in parameter of
    review_correction, not a computed coherence judgment.  If a coherence
    computation is ever added there, this pin flips and the change must be
    reconciled with ADR-0218 (which routes computed promotion through the
    vault transition owner, NOT through review_correction)."""
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
    """O7's substrate half, testable today: the engine's proof evidence is
    deterministic and re-verifies by recomputation — the property the
    PromotionCertificate replay verifier (PR B,
    generate/proof_chain/certificate.py — landed) relies on."""
    premises = ("p", "p -> q")
    first = evaluate_entailment_with_trace(premises, "q")
    second = evaluate_entailment_with_trace(premises, "q")
    assert first.outcome is Entailment.ENTAILED
    assert first.canonical_json() == second.canonical_json(), (
        "EntailmentTrace is not replay-stable — PR B's certificate "
        "re-verification has no substrate to stand on."
    )

    # A non-entailed query must be UNKNOWN, not promoted-shaped evidence.
    unknown = evaluate_entailment_with_trace(("p",), "q")
    assert unknown.outcome is Entailment.UNKNOWN


# ---------------------------------------------------------------------------
# Obligations — xfail(strict) until ADR-0218 is ratified and P3 lands
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason=_XFAIL_REASON)
def test_O1_entailed_from_coherent_premises_promotes_with_reverifiable_proof() -> None:
    """Issue §7.1 — a claim deductively entailed by an all-COHERENT premise
    set promotes, and the embedded proof re-verifies by recomputation."""
    mod = _promoter()
    vault = VaultStore(reproject_interval=0)
    idx_p = _store_premise(vault, 1, "p", EpistemicStatus.COHERENT)
    idx_pq = _store_premise(vault, 2, "p -> q", EpistemicStatus.COHERENT)

    decision = mod.certify_promotion(
        claim_form="q",
        premise_entry_indices=(idx_p, idx_pq),
        vault=vault,
    )
    assert decision.promoted is True

    # Replay re-verification: recomputing from the stored forms must
    # reproduce the embedded trace byte-for-byte (ADR-0218 §D3.4).
    recomputed = evaluate_entailment_with_trace(("p", "p -> q"), "q")
    assert decision.certificate.entailment_trace == recomputed.as_dict()


@pytest.mark.xfail(strict=True, reason=_XFAIL_REASON)
def test_O2_consistent_but_not_entailed_stays_speculative() -> None:
    """Issue §7.2 — mere consistency with the field is not entailment;
    UNKNOWN never promotes."""
    mod = _promoter()
    vault = VaultStore(reproject_interval=0)
    idx_p = _store_premise(vault, 1, "p", EpistemicStatus.COHERENT)

    decision = mod.certify_promotion(
        claim_form="q",  # consistent with {p}, not entailed by it
        premise_entry_indices=(idx_p,),
        vault=vault,
    )
    assert decision.promoted is False


@pytest.mark.xfail(strict=True, reason=_XFAIL_REASON)
def test_O3_any_non_coherent_premise_refuses() -> None:
    """Issue §7.3 — a SPECULATIVE premise poisons the proof for promotion
    purposes even when the entailment itself is valid."""
    mod = _promoter()
    vault = VaultStore(reproject_interval=0)
    idx_p = _store_premise(vault, 1, "p", EpistemicStatus.COHERENT)
    idx_pq = _store_premise(vault, 2, "p -> q", EpistemicStatus.SPECULATIVE)

    decision = mod.certify_promotion(
        claim_form="q",
        premise_entry_indices=(idx_p, idx_pq),
        vault=vault,
    )
    assert decision.promoted is False
    assert "premise" in decision.reason  # closed reason vocab names the gate


@pytest.mark.xfail(strict=True, reason=_XFAIL_REASON)
def test_O4_uncertified_reading_fails_closed() -> None:
    """Issue §7.4 — the reading is the hazard-bearing step. A premise whose
    propositional form lacks reading certification must refuse, never fall
    through to admission (ADR-0218 §D2)."""
    mod = _promoter()
    vault = VaultStore(reproject_interval=0)
    idx_p = _store_premise(vault, 1, "p", EpistemicStatus.COHERENT)
    idx_pq = _store_premise(
        vault, 2, "p -> q", EpistemicStatus.COHERENT, certified=False
    )

    decision = mod.certify_promotion(
        claim_form="q",
        premise_entry_indices=(idx_p, idx_pq),
        vault=vault,
    )
    assert decision.promoted is False
    assert "reading" in decision.reason


@pytest.mark.xfail(strict=True, reason=_XFAIL_REASON)
def test_O5_proposer_supplied_proof_status_confidence_are_ignored() -> None:
    """Issue §7.5 — proposer attachments are data, never authority. The
    decision must be byte-identical with and without them (echo-and-ignore,
    as demos/epistemic_truth_state does for proposed_state)."""
    mod = _promoter()
    vault = VaultStore(reproject_interval=0)
    idx_p = _store_premise(vault, 1, "p", EpistemicStatus.COHERENT)

    bare = mod.certify_promotion(
        claim_form="q",
        premise_entry_indices=(idx_p,),
        vault=vault,
    )
    adorned = mod.certify_promotion(
        claim_form="q",
        premise_entry_indices=(idx_p,),
        vault=vault,
        proposer_payload={
            "proof": "trust me, q follows",
            "status": "coherent",
            "confidence": 0.99,
        },
    )
    assert bare.promoted is adorned.promoted is False
    assert bare.certificate.canonical_json() == adorned.certificate.canonical_json()


@pytest.mark.xfail(strict=True, reason=_XFAIL_REASON)
def test_O7_promotion_decision_is_deterministic_and_replayable() -> None:
    """Issue §7.7 — double-run byte-identical; the certificate is the audit
    artifact replay re-verifies (its hash folds into trace_hash at P3)."""
    mod = _promoter()

    def run():
        vault = VaultStore(reproject_interval=0)
        idx_p = _store_premise(vault, 1, "p", EpistemicStatus.COHERENT)
        idx_pq = _store_premise(vault, 2, "p -> q", EpistemicStatus.COHERENT)
        return mod.certify_promotion(
            claim_form="q",
            premise_entry_indices=(idx_p, idx_pq),
            vault=vault,
        )

    first, second = run(), run()
    assert first.certificate.canonical_json() == second.certificate.canonical_json()

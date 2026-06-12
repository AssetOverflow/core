"""ADR-0218 P3 — proof-carrying coherence promotion: decider + transition owner.

Covers the ratified admissibility predicate end-to-end:

- the pure decider (``teaching/proof_promotion.py``) — fresh-read premises,
  strict status/reading gates, engine certification, proposer payload
  provably unread, certificate digest emission, zero mutation;
- the single mutation owner (``VaultStore.apply_certified_promotion``) —
  independent re-verification (replay + pin + live store cross-checks),
  staleness refusals, tamper refusals, idempotency;
- the structural guarantees — no parallel learning path (the promoter has
  zero status-write sites and zero vault-store calls, proven with the
  INV-21/INV-29 detectors themselves), and the engine pin stays in sync
  with the deductive-lane registry.

Wrong=0 framing: every refusal path here is an input class that COULD have
admitted a bad promotion; each test pins the refusal so a later change that
weakens a gate fails loudly.
"""

from __future__ import annotations

import ast
import dataclasses
import hashlib
from pathlib import Path

import numpy as np
import pytest

from algebra.cga import embed_point
from generate.proof_chain import Entailment, evaluate_entailment_with_trace
from generate.proof_chain.certificate import (
    PremiseRecord,
    build_certificate,
)
from generate.proof_chain.engine_pin import DEDUCTIVE_ENGINE_PIN
from teaching import proof_promotion
from teaching.epistemic import EpistemicStatus
from vault.store import CERTIFIED_PROMOTION_REASONS, VaultStore

_REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _versor(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return embed_point(rng.standard_normal(3).astype(np.float32))


def _store(
    vault: VaultStore,
    seed: int,
    form: str,
    status: EpistemicStatus,
    *,
    certified: object = True,
    include_form: bool = True,
) -> int:
    metadata: dict = {"reading_certified": certified}
    if include_form:
        metadata["propositional_form"] = form
    return vault.store(_versor(seed), metadata, epistemic_status=status)


def _coherent_premises(vault: VaultStore, *forms: str) -> tuple[int, ...]:
    return tuple(
        _store(vault, 100 + i, form, EpistemicStatus.COHERENT)
        for i, form in enumerate(forms)
    )


def _speculative_claim(vault: VaultStore, form: str, **kwargs) -> int:
    return _store(vault, 7, form, EpistemicStatus.SPECULATIVE, **kwargs)


def _statuses(vault: VaultStore) -> list[str]:
    return [meta["epistemic_status"] for _, meta in vault.iter_metadata()]


class _PoisonedPayload(dict):
    """A proposer payload that detonates on ANY read — proves D3.5's
    "ignored completely" rather than merely "did not change the outcome"."""

    def _boom(self, *args, **kwargs):
        raise AssertionError(
            "certify_promotion read the proposer payload — D3.5 violated"
        )

    __getitem__ = _boom
    __iter__ = _boom
    __len__ = _boom
    __contains__ = _boom
    get = _boom
    keys = _boom
    values = _boom
    items = _boom


# ---------------------------------------------------------------------------
# The positive path
# ---------------------------------------------------------------------------

def test_entailed_from_coherent_promotes_end_to_end() -> None:
    vault = VaultStore(reproject_interval=0)
    idx_p, idx_pq = _coherent_premises(vault, "p", "p -> q")
    idx_q = _speculative_claim(vault, "q")

    decision = proof_promotion.certify_promotion(
        claim_entry_index=idx_q,
        premise_entry_indices=(idx_p, idx_pq),
        vault=vault,
    )
    assert decision.promoted is True
    assert decision.reason == proof_promotion.PROMOTED_ENTAILED
    assert decision.certificate is not None
    assert decision.certificate_digest == hashlib.sha256(
        decision.certificate.canonical_json().encode("utf-8")
    ).hexdigest()

    result = vault.apply_certified_promotion(idx_q, decision.certificate)
    assert result.applied is True and result.reason == "applied"

    claim_meta = dict(vault.iter_metadata())[idx_q]
    assert claim_meta["epistemic_status"] == EpistemicStatus.COHERENT.value
    assert claim_meta["epistemic_state"] == "decoded"
    assert claim_meta["promotion_certificate_digest"] == decision.certificate_digest

    # The promoted claim is now admissible as evidence on the read side.
    hits = vault.recall(
        vault._versors[idx_q], top_k=3, min_status=EpistemicStatus.COHERENT
    )
    assert any(hit["index"] == idx_q for hit in hits)


def test_certify_alone_never_mutates() -> None:
    """The decider is pure: a promoted=True decision changes no store state
    until the vault owner applies it — no parallel mutation path."""
    vault = VaultStore(reproject_interval=0)
    idx_p, idx_pq = _coherent_premises(vault, "p", "p -> q")
    idx_q = _speculative_claim(vault, "q")
    before = _statuses(vault)

    decision = proof_promotion.certify_promotion(
        claim_entry_index=idx_q,
        premise_entry_indices=(idx_p, idx_pq),
        vault=vault,
    )
    assert decision.promoted is True
    assert _statuses(vault) == before


def test_decision_is_deterministic_and_digest_stable() -> None:
    def run() -> proof_promotion.PromotionDecision:
        vault = VaultStore(reproject_interval=0)
        idx_p, idx_pq = _coherent_premises(vault, "p", "p -> q")
        idx_q = _speculative_claim(vault, "q")
        return proof_promotion.certify_promotion(
            claim_entry_index=idx_q,
            premise_entry_indices=(idx_p, idx_pq),
            vault=vault,
        )

    first, second = run(), run()
    assert first.certificate is not None and second.certificate is not None
    assert first.certificate.canonical_json() == second.certificate.canonical_json()
    assert first.certificate_digest == second.certificate_digest


# ---------------------------------------------------------------------------
# Engine outcomes that never promote
# ---------------------------------------------------------------------------

def test_consistent_but_not_entailed_stays_speculative() -> None:
    vault = VaultStore(reproject_interval=0)
    (idx_p,) = _coherent_premises(vault, "p")
    idx_q = _speculative_claim(vault, "q")

    decision = proof_promotion.certify_promotion(
        claim_entry_index=idx_q,
        premise_entry_indices=(idx_p,),
        vault=vault,
    )
    assert decision.promoted is False
    assert decision.reason == proof_promotion.REFUSED_NOT_ENTAILED
    assert decision.certificate is not None
    assert decision.certificate.decision == Entailment.UNKNOWN.value

    result = vault.apply_certified_promotion(idx_q, decision.certificate)
    assert result.applied is False
    assert result.reason == "certificate_not_promotion_positive"
    assert _statuses(vault)[idx_q] == EpistemicStatus.SPECULATIVE.value


def test_refuted_never_promotes_and_never_demotes() -> None:
    vault = VaultStore(reproject_interval=0)
    idx_p, idx_pnq = _coherent_premises(vault, "p", "p -> ~q")
    idx_q = _speculative_claim(vault, "q")
    before = _statuses(vault)

    decision = proof_promotion.certify_promotion(
        claim_entry_index=idx_q,
        premise_entry_indices=(idx_p, idx_pnq),
        vault=vault,
    )
    assert decision.promoted is False
    assert decision.certificate is not None
    assert decision.certificate.decision == Entailment.REFUTED.value

    result = vault.apply_certified_promotion(idx_q, decision.certificate)
    assert result.applied is False
    # No transition in EITHER direction: refutation is not demotion authority
    # (ADR-0218 open item) and certainly not promotion.
    assert _statuses(vault) == before


def test_inconsistent_coherent_premises_refuse_never_vacuously_entail() -> None:
    """Two individually-COHERENT entries can still be mutually inconsistent;
    the engine refuses (everything follows from ⊥) rather than promoting."""
    vault = VaultStore(reproject_interval=0)
    idx_p, idx_np = _coherent_premises(vault, "p", "~p")
    idx_q = _speculative_claim(vault, "q")

    decision = proof_promotion.certify_promotion(
        claim_entry_index=idx_q,
        premise_entry_indices=(idx_p, idx_np),
        vault=vault,
    )
    assert decision.promoted is False
    assert decision.certificate is not None
    assert decision.certificate.decision == Entailment.REFUSED.value
    assert vault.apply_certified_promotion(idx_q, decision.certificate).applied is False


# ---------------------------------------------------------------------------
# Store-state gates at certify time
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "bad_status",
    [EpistemicStatus.SPECULATIVE, EpistemicStatus.CONTESTED, EpistemicStatus.FALSIFIED],
)
def test_any_non_coherent_premise_refuses(bad_status: EpistemicStatus) -> None:
    vault = VaultStore(reproject_interval=0)
    (idx_p,) = _coherent_premises(vault, "p")
    idx_pq = _store(vault, 2, "p -> q", bad_status)
    idx_q = _speculative_claim(vault, "q")

    decision = proof_promotion.certify_promotion(
        claim_entry_index=idx_q,
        premise_entry_indices=(idx_p, idx_pq),
        vault=vault,
    )
    assert decision.promoted is False
    assert decision.reason == proof_promotion.REFUSED_PREMISE_NOT_COHERENT
    assert decision.certificate is None  # refused before the engine ran


@pytest.mark.parametrize("bad_index", [99, -1, True])
def test_missing_premise_entry_refuses(bad_index: object) -> None:
    vault = VaultStore(reproject_interval=0)
    (idx_p,) = _coherent_premises(vault, "p")
    idx_q = _speculative_claim(vault, "q")

    decision = proof_promotion.certify_promotion(
        claim_entry_index=idx_q,
        premise_entry_indices=(idx_p, bad_index),  # type: ignore[arg-type]
        vault=vault,
    )
    assert decision.promoted is False
    assert decision.reason in {
        proof_promotion.REFUSED_PREMISE_MISSING,
        proof_promotion.REFUSED_MALFORMED_INPUT,
    }


def test_missing_claim_entry_refuses() -> None:
    vault = VaultStore(reproject_interval=0)
    (idx_p,) = _coherent_premises(vault, "p")

    decision = proof_promotion.certify_promotion(
        claim_entry_index=42,
        premise_entry_indices=(idx_p,),
        vault=vault,
    )
    assert decision.promoted is False
    assert decision.reason == proof_promotion.REFUSED_CLAIM_MISSING


@pytest.mark.parametrize(
    "claim_status",
    [EpistemicStatus.COHERENT, EpistemicStatus.CONTESTED, EpistemicStatus.FALSIFIED],
)
def test_claim_not_speculative_refuses(claim_status: EpistemicStatus) -> None:
    """Only SPECULATIVE→COHERENT is authorized; an already-transitioned
    claim refuses (this is also the idempotency guard)."""
    vault = VaultStore(reproject_interval=0)
    idx_p, idx_pq = _coherent_premises(vault, "p", "p -> q")
    idx_q = _store(vault, 7, "q", claim_status)

    decision = proof_promotion.certify_promotion(
        claim_entry_index=idx_q,
        premise_entry_indices=(idx_p, idx_pq),
        vault=vault,
    )
    assert decision.promoted is False
    assert decision.reason == proof_promotion.REFUSED_CLAIM_NOT_SPECULATIVE


@pytest.mark.parametrize("bad_certified", [False, 1, "yes", None])
def test_uncertified_premise_reading_refuses(bad_certified: object) -> None:
    """reading_certified must be the boolean True — truthy stand-ins are not
    curator certifications (D2 fail-closed)."""
    vault = VaultStore(reproject_interval=0)
    (idx_p,) = _coherent_premises(vault, "p")
    idx_pq = _store(
        vault, 2, "p -> q", EpistemicStatus.COHERENT, certified=bad_certified
    )
    idx_q = _speculative_claim(vault, "q")

    decision = proof_promotion.certify_promotion(
        claim_entry_index=idx_q,
        premise_entry_indices=(idx_p, idx_pq),
        vault=vault,
    )
    assert decision.promoted is False
    assert decision.reason == proof_promotion.REFUSED_PREMISE_READING


def test_uncertified_or_formless_claim_refuses() -> None:
    vault = VaultStore(reproject_interval=0)
    idx_p, idx_pq = _coherent_premises(vault, "p", "p -> q")

    idx_uncertified = _store(
        vault, 7, "q", EpistemicStatus.SPECULATIVE, certified=False
    )
    idx_formless = _store(
        vault, 8, "q", EpistemicStatus.SPECULATIVE, include_form=False
    )
    for idx in (idx_uncertified, idx_formless):
        decision = proof_promotion.certify_promotion(
            claim_entry_index=idx,
            premise_entry_indices=(idx_p, idx_pq),
            vault=vault,
        )
        assert decision.promoted is False
        assert decision.reason == proof_promotion.REFUSED_CLAIM_READING


def test_zero_and_duplicate_premises_refuse() -> None:
    vault = VaultStore(reproject_interval=0)
    (idx_p,) = _coherent_premises(vault, "p")
    idx_q = _speculative_claim(vault, "q | ~q")  # a tautology claim

    empty = proof_promotion.certify_promotion(
        claim_entry_index=idx_q, premise_entry_indices=(), vault=vault
    )
    assert empty.promoted is False
    assert empty.reason == proof_promotion.REFUSED_NO_PREMISES

    dup = proof_promotion.certify_promotion(
        claim_entry_index=idx_q, premise_entry_indices=(idx_p, idx_p), vault=vault
    )
    assert dup.promoted is False
    assert dup.reason == proof_promotion.REFUSED_DUPLICATE_PREMISES


def test_claim_cannot_be_its_own_premise() -> None:
    """p ⊨ p, but the claim must be SPECULATIVE and every premise COHERENT —
    one entry cannot be both, so self-promotion is structurally refused."""
    vault = VaultStore(reproject_interval=0)
    idx_q = _speculative_claim(vault, "q")

    decision = proof_promotion.certify_promotion(
        claim_entry_index=idx_q,
        premise_entry_indices=(idx_q,),
        vault=vault,
    )
    assert decision.promoted is False
    assert decision.reason == proof_promotion.REFUSED_PREMISE_NOT_COHERENT


# ---------------------------------------------------------------------------
# Proposer attachments are data, never authority (D3.5)
# ---------------------------------------------------------------------------

def test_proposer_payload_is_never_read_and_never_changes_the_decision() -> None:
    vault = VaultStore(reproject_interval=0)
    idx_p, idx_pq = _coherent_premises(vault, "p", "p -> q")
    idx_q = _speculative_claim(vault, "q")

    bare = proof_promotion.certify_promotion(
        claim_entry_index=idx_q,
        premise_entry_indices=(idx_p, idx_pq),
        vault=vault,
    )
    adorned = proof_promotion.certify_promotion(
        claim_entry_index=idx_q,
        premise_entry_indices=(idx_p, idx_pq),
        vault=vault,
        proposer_payload=_PoisonedPayload(),  # raises on ANY read
    )
    assert bare.promoted is adorned.promoted is True
    assert bare.certificate is not None and adorned.certificate is not None
    assert bare.certificate.canonical_json() == adorned.certificate.canonical_json()


def test_no_source_trust_fast_path_for_refused_claims() -> None:
    """A proposer asserting proof/status/confidence cannot rescue a
    non-entailed claim — the refusal is byte-identical."""
    vault = VaultStore(reproject_interval=0)
    (idx_p,) = _coherent_premises(vault, "p")
    idx_q = _speculative_claim(vault, "q")

    bare = proof_promotion.certify_promotion(
        claim_entry_index=idx_q, premise_entry_indices=(idx_p,), vault=vault
    )
    adorned = proof_promotion.certify_promotion(
        claim_entry_index=idx_q,
        premise_entry_indices=(idx_p,),
        vault=vault,
        proposer_payload={
            "proof": "trust me, q follows",
            "status": "coherent",
            "confidence": 0.99,
            "propositional_form": "p",  # a lie about the claim form
        },
    )
    assert bare.promoted is adorned.promoted is False
    assert bare.certificate is not None and adorned.certificate is not None
    assert bare.certificate.canonical_json() == adorned.certificate.canonical_json()
    # The certificate's claim form is the STORED certified reading.
    assert bare.certificate.claim_form == "q"


# ---------------------------------------------------------------------------
# The mutation owner re-verifies independently
# ---------------------------------------------------------------------------

def _certified_decision(vault: VaultStore) -> proof_promotion.PromotionDecision:
    idx_p, idx_pq = _coherent_premises(vault, "p", "p -> q")
    idx_q = _speculative_claim(vault, "q")
    decision = proof_promotion.certify_promotion(
        claim_entry_index=idx_q,
        premise_entry_indices=(idx_p, idx_pq),
        vault=vault,
    )
    assert decision.promoted is True and decision.certificate is not None
    return decision


def test_tampered_certificate_refused_at_apply() -> None:
    vault = VaultStore(reproject_interval=0)
    decision = _certified_decision(vault)
    assert decision.certificate is not None
    before = _statuses(vault)

    forged_decision = dataclasses.replace(decision.certificate, claim_form="r")
    swapped_trace = dataclasses.replace(
        decision.certificate,
        entailment_trace=evaluate_entailment_with_trace(("p",), "p").as_dict(),
    )
    for tampered in (forged_decision, swapped_trace):
        result = vault.apply_certified_promotion(
            decision.claim_entry_index, tampered
        )
        assert result.applied is False
        assert result.reason == "certificate_replay_failed"

    # Statuses are caller-recorded data carried verbatim through rebuild, so
    # a status tamper yields an internally CONSISTENT certificate: it passes
    # replay and is refused by the promotion_positive gate instead.
    demoted_status = dataclasses.replace(
        decision.certificate, premise_statuses=("coherent", "speculative")
    )
    result = vault.apply_certified_promotion(
        decision.claim_entry_index, demoted_status
    )
    assert result.applied is False
    assert result.reason == "certificate_not_promotion_positive"
    assert _statuses(vault) == before


def test_statuses_forged_to_coherent_cannot_beat_the_live_check() -> None:
    """The dangerous tamper direction: recording 'coherent' for a premise
    that is actually SPECULATIVE.  The forged certificate is promotion-
    positive and passes replay — the vault's fresh-read of the LIVE premise
    status is what refuses it (live state is the authority, D3.1)."""
    vault = VaultStore(reproject_interval=0)
    (idx_p,) = _coherent_premises(vault, "p")
    idx_pq = _store(vault, 2, "p -> q", EpistemicStatus.SPECULATIVE)
    idx_q = _speculative_claim(vault, "q")

    forged = build_certificate(
        claim_form="q",
        premises=(
            PremiseRecord(entry_id=idx_p, form="p", status="coherent"),
            PremiseRecord(entry_id=idx_pq, form="p -> q", status="coherent"),
        ),
        engine_pin=DEDUCTIVE_ENGINE_PIN,
    )
    assert forged.promotion_positive is True  # the artifact LOOKS promotable
    result = vault.apply_certified_promotion(idx_q, forged)
    assert result.applied is False and result.reason == "premise_not_coherent"
    assert _statuses(vault)[idx_q] == EpistemicStatus.SPECULATIVE.value


def test_non_certificate_object_refused_at_apply() -> None:
    vault = VaultStore(reproject_interval=0)
    decision = _certified_decision(vault)
    result = vault.apply_certified_promotion(
        decision.claim_entry_index, {"decision": "entailed"}  # type: ignore[arg-type]
    )
    assert result.applied is False and result.reason == "not_a_certificate"


def test_wrong_engine_pin_refused_at_apply() -> None:
    """A certificate from a different engine build replays internally but
    fails the vault's pin demand — engine drift is an alarm, not a pass."""
    vault = VaultStore(reproject_interval=0)
    idx_p, idx_pq = _coherent_premises(vault, "p", "p -> q")
    idx_q = _speculative_claim(vault, "q")

    stale_pin_cert = build_certificate(
        claim_form="q",
        premises=(
            PremiseRecord(entry_id=idx_p, form="p", status="coherent"),
            PremiseRecord(entry_id=idx_pq, form="p -> q", status="coherent"),
        ),
        engine_pin="sha-of-some-other-engine-build",
    )
    result = vault.apply_certified_promotion(idx_q, stale_pin_cert)
    assert result.applied is False and result.reason == "certificate_replay_failed"
    assert _statuses(vault)[idx_q] == EpistemicStatus.SPECULATIVE.value


def test_fabricated_certificate_over_unstored_forms_cannot_flip() -> None:
    """A valid, replay-passing certificate whose premises the store does NOT
    hold as certified-COHERENT entries mutates nothing — authority is live
    store state, never the artifact."""
    vault = VaultStore(reproject_interval=0)
    idx_q = _speculative_claim(vault, "q")

    fabricated = build_certificate(
        claim_form="q",
        premises=(
            PremiseRecord(entry_id=5, form="q", status="coherent"),
        ),
        engine_pin=DEDUCTIVE_ENGINE_PIN,
    )
    assert fabricated.promotion_positive is True  # the artifact LOOKS perfect
    result = vault.apply_certified_promotion(idx_q, fabricated)
    assert result.applied is False and result.reason == "premise_entry_missing"
    assert _statuses(vault)[idx_q] == EpistemicStatus.SPECULATIVE.value


def test_stale_premise_status_refuses_at_apply() -> None:
    """A premise contested between certify and apply poisons the proof —
    fresh-read at the mutation boundary, not just at decision time."""
    vault = VaultStore(reproject_interval=0)
    decision = _certified_decision(vault)
    assert decision.certificate is not None

    premise_idx = decision.certificate.premise_entry_ids[0]
    vault._metadata[premise_idx]["epistemic_status"] = (
        EpistemicStatus.CONTESTED.value
    )

    result = vault.apply_certified_promotion(
        decision.claim_entry_index, decision.certificate
    )
    assert result.applied is False and result.reason == "premise_not_coherent"
    assert (
        _statuses(vault)[decision.claim_entry_index]
        == EpistemicStatus.SPECULATIVE.value
    )


def test_stale_premise_form_refuses_at_apply() -> None:
    vault = VaultStore(reproject_interval=0)
    decision = _certified_decision(vault)
    assert decision.certificate is not None

    premise_idx = decision.certificate.premise_entry_ids[0]
    vault._metadata[premise_idx]["propositional_form"] = "p & r"

    result = vault.apply_certified_promotion(
        decision.claim_entry_index, decision.certificate
    )
    assert result.applied is False and result.reason == "premise_form_mismatch"


def test_stale_claim_refuses_at_apply() -> None:
    vault = VaultStore(reproject_interval=0)
    decision = _certified_decision(vault)
    assert decision.certificate is not None
    claim_idx = decision.claim_entry_index

    # Re-applying after a successful promotion refuses (no double transition).
    assert vault.apply_certified_promotion(claim_idx, decision.certificate).applied
    second = vault.apply_certified_promotion(claim_idx, decision.certificate)
    assert second.applied is False and second.reason == "claim_not_speculative"


def test_claim_form_mismatch_refuses_at_apply() -> None:
    """Pointing a legitimate certificate at a different entry refuses — the
    stored certified reading must equal the certified claim form."""
    vault = VaultStore(reproject_interval=0)
    decision = _certified_decision(vault)
    assert decision.certificate is not None
    idx_other = _store(vault, 9, "r", EpistemicStatus.SPECULATIVE)

    result = vault.apply_certified_promotion(idx_other, decision.certificate)
    assert result.applied is False and result.reason == "claim_form_mismatch"
    assert _statuses(vault)[idx_other] == EpistemicStatus.SPECULATIVE.value


@pytest.mark.parametrize("bad_index", [99, -1, True])
def test_apply_with_bad_entry_index_refuses(bad_index: object) -> None:
    vault = VaultStore(reproject_interval=0)
    decision = _certified_decision(vault)
    assert decision.certificate is not None
    result = vault.apply_certified_promotion(
        bad_index, decision.certificate  # type: ignore[arg-type]
    )
    assert result.applied is False and result.reason == "claim_entry_missing"


# ---------------------------------------------------------------------------
# Structural guarantees — no parallel path, closed vocabs, pin sync
# ---------------------------------------------------------------------------

def test_promoter_module_is_pure_no_status_writes_no_vault_store_calls() -> None:
    """No parallel learning path: the INV-29 status-write detector and the
    INV-21 vault-store-call detector both report zero on the promoter."""
    from tests.test_architectural_invariants import (
        _file_has_vault_store_call,
        _status_transition_writes,
    )

    promoter_path = _REPO_ROOT / "teaching" / "proof_promotion.py"
    tree = ast.parse(promoter_path.read_text())
    assert _status_transition_writes(tree) == 0
    assert _file_has_vault_store_call(promoter_path) is False


def test_decision_reasons_are_closed_vocabularies() -> None:
    assert proof_promotion.PROMOTED_ENTAILED in proof_promotion.DECISION_REASONS
    assert len(proof_promotion.DECISION_REASONS) == 12
    assert "applied" in CERTIFIED_PROMOTION_REASONS
    assert len(CERTIFIED_PROMOTION_REASONS) == 12


def test_engine_pin_matches_lane_registry() -> None:
    """DEDUCTIVE_ENGINE_PIN mirrors scripts/verify_lane_shas.py — AST-parsed
    so the runtime never imports scripts/.  Drift between the lane registry
    and the promotion pin fails here, in the same suite that gates merges."""
    registry = _REPO_ROOT / "scripts" / "verify_lane_shas.py"
    tree = ast.parse(registry.read_text())
    pinned: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == "PINNED_SHAS" and isinstance(node.value, ast.Dict):
                for key, value in zip(node.value.keys, node.value.values):
                    if isinstance(key, ast.Constant) and isinstance(value, ast.Constant):
                        pinned[key.value] = value.value
    assert "deductive_logic_v1" in pinned, "lane registry shape changed"
    assert DEDUCTIVE_ENGINE_PIN == pinned["deductive_logic_v1"], (
        "generate/proof_chain/engine_pin.py is out of sync with "
        "scripts/verify_lane_shas.py — update the constant in the same commit "
        "as the lane re-pin."
    )


def test_adr_0148_promotion_keeps_epistemic_state_consistent() -> None:
    """Consistency fix shipped with PR C: BOTH promotion sites stamp
    epistemic_state alongside epistemic_status (the stored key must not go
    stale even though recall recomputes it)."""
    vault = VaultStore(reproject_interval=0)
    decision = _certified_decision(vault)
    assert decision.certificate is not None
    assert vault.apply_certified_promotion(
        decision.claim_entry_index, decision.certificate
    ).applied
    meta = vault._metadata[decision.claim_entry_index]
    assert meta["epistemic_state"] == "decoded"

"""ADR-0056 Phase C1 — contemplation loop tests.

Verification matrix mirrors the acceptance criteria in
``docs/decisions/ADR-0056-contemplation-loop-c1.md``:

  - Determinism across runs (byte-identical JSONL).
  - Empty corpus + empty pack → terminates with gap recorded.
  - Factual candidate with one reviewed line → polarity=affirms,
    claim_domain=factual.
  - Direct same-pack contradiction → polarity=falsifies.
  - Mixed evidence → polarity=undetermined + claim_domain upgraded.
  - Recursion overflow flips flag + emits subquestion outcome.
  - No corpus mutation (byte-identical before/after).
  - DiscoveryCandidate Phase B as_dict() unchanged when C1 fields
    are at default.
"""

from __future__ import annotations

import hashlib
import json

from chat.teaching_grounding import _CORPUS_PATH
from teaching.contemplation import contemplate
from teaching.discovery import (
    DiscoveryCandidate,
    EvidencePointer,
    format_candidate_jsonl,
)


CORPUS_BYTES_BEFORE = _CORPUS_PATH.read_bytes() if _CORPUS_PATH.exists() else b""


def _phase_b_candidate(
    *, subject: str = "wisdom", intent: str = "cause",
    candidate_id: str = "cand_abc", trace: str = "trace_xyz",
    domain: str = "cognition",
) -> DiscoveryCandidate:
    return DiscoveryCandidate(
        candidate_id=candidate_id,
        proposed_chain={
            "subject": subject,
            "intent": intent,
            "connective": None,
            "object": None,
        },
        trigger="would_have_grounded",
        source_turn_trace=trace,
        pack_consistent=True,
        boundary_clean=True,
        domain=domain,
    )


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_contemplate_is_deterministic_across_runs():
    """Same candidate input ⇒ byte-identical JSONL across runs."""
    cand = _phase_b_candidate()
    a = format_candidate_jsonl(contemplate(cand))
    b = format_candidate_jsonl(contemplate(cand))
    assert a == b
    # Hash equality, not just string equality.
    assert hashlib.sha256(a.encode()).digest() == hashlib.sha256(b.encode()).digest()


def test_contemplate_does_not_mutate_input():
    cand = _phase_b_candidate()
    before_chain = dict(cand.proposed_chain)
    _ = contemplate(cand)
    assert cand.proposed_chain == before_chain
    assert cand.polarity == "undetermined"
    assert cand.evidence == ()
    assert cand.sub_questions == ()


def test_contemplate_does_not_mutate_corpus_on_disk():
    """Trust boundary: contemplation NEVER writes to the corpus."""
    cand = _phase_b_candidate()
    _ = contemplate(cand)
    after = _CORPUS_PATH.read_bytes() if _CORPUS_PATH.exists() else b""
    assert after == CORPUS_BYTES_BEFORE


# ---------------------------------------------------------------------------
# Empty / cold-start
# ---------------------------------------------------------------------------


def test_empty_pack_and_corpus_terminates_with_gap(monkeypatch):
    """No pack, no corpus ⇒ every probe fails, parent gap-records."""
    from teaching import contemplation as contemp_mod

    monkeypatch.setattr(contemp_mod, "_pack_index_for_domain", lambda _domain: {})
    monkeypatch.setattr(contemp_mod, "_corpus_index_for_domain", lambda _domain: {})

    cand = _phase_b_candidate()
    out = contemplate(cand)

    assert out.polarity == "undetermined"
    assert out.evidence == ()
    assert out.sub_questions  # gap-recorded
    assert all(sq.outcome == "gap_recorded" for sq in out.sub_questions)
    assert out.recursion_overflow is False


# ---------------------------------------------------------------------------
# Domain-aware partition
# ---------------------------------------------------------------------------


def test_math_contemplation_does_not_borrow_cognition_corpus():
    """Math candidates fail closed instead of using cognition corpus evidence."""
    cand = DiscoveryCandidate(
        candidate_id="cand_math_no_cognition_leak",
        proposed_chain={
            "subject": "light",
            "intent": "cause",
            "connective": "reveals",
            "object": "truth",
        },
        trigger="would_have_grounded",
        source_turn_trace="t_math",
        pack_consistent=True,
        boundary_clean=True,
        domain="math",
    )
    out = contemplate(cand)
    assert out.domain == "math"
    assert out.polarity == "undetermined"
    assert not any(e.source == "corpus" for e in out.evidence)


def test_math_contemplation_uses_math_pack_residency():
    """Math candidates can receive math-pack evidence without corpus leakage."""
    cand = DiscoveryCandidate(
        candidate_id="cand_math_pack",
        proposed_chain={
            "subject": "does",
            "intent": "admissibility",
            "connective": "recognizes",
            "object": "does",
        },
        trigger="would_have_grounded",
        source_turn_trace="t_math_pack",
        pack_consistent=True,
        boundary_clean=True,
        domain="math",
    )
    out = contemplate(cand)
    assert out.domain == "math"
    assert any(e.source == "pack" and e.ref == "does" for e in out.evidence)
    assert not any(e.source == "corpus" for e in out.evidence)


# ---------------------------------------------------------------------------
# Factual affirming evidence
# ---------------------------------------------------------------------------


def test_factual_candidate_with_one_reviewed_line_affirms():
    """Concrete chain matching a reviewed corpus entry → affirms/factual."""
    # ``light reveals truth`` is in the production corpus (ADR-0052).
    cand = DiscoveryCandidate(
        candidate_id="cand_factual",
        proposed_chain={
            "subject": "light",
            "intent": "cause",
            "connective": "reveals",
            "object": "truth",
        },
        trigger="would_have_grounded",
        source_turn_trace="t1",
        pack_consistent=True,
        boundary_clean=True,
    )
    out = contemplate(cand)
    assert out.polarity == "affirms"
    assert out.claim_domain == "factual"
    assert any(
        e.source == "corpus" and e.polarity == "affirms" for e in out.evidence
    )


# ---------------------------------------------------------------------------
# Falsification: same-pack direct contradiction
# ---------------------------------------------------------------------------


def test_direct_same_pack_contradiction_falsifies():
    """Same subject+intent+object, different connective → falsifies."""
    # Corpus has ``light reveals truth``; propose ``light obscures truth``.
    cand = DiscoveryCandidate(
        candidate_id="cand_contradiction",
        proposed_chain={
            "subject": "light",
            "intent": "cause",
            "connective": "obscures",
            "object": "truth",
        },
        trigger="would_have_grounded",
        source_turn_trace="t2",
        pack_consistent=True,
        boundary_clean=True,
    )
    out = contemplate(cand)
    assert out.polarity == "falsifies"
    assert any(
        e.source == "corpus" and e.polarity == "falsifies" for e in out.evidence
    )


# ---------------------------------------------------------------------------
# Mixed evidence → undetermined + claim_domain upgrade
# ---------------------------------------------------------------------------


def test_mixed_evidence_upgrades_claim_domain(monkeypatch):
    """Mixed affirm + falsify ⇒ undetermined AND domain upgrades one tier."""
    from teaching import contemplation as contemp_mod

    def fake_corpus_probe(subject, intent, connective, obj, *, domain="cognition"):
        return (
            EvidencePointer(
                source="corpus", ref="chain_aff", polarity="affirms",
                epistemic_status="coherent",
            ),
        )

    def fake_vault(subject, obj):
        return (
            EvidencePointer(
                source="vault_coherent", ref="vault_42",
                polarity="falsifies", epistemic_status="coherent",
            ),
        )

    monkeypatch.setattr(contemp_mod, "_probe_corpus_direct", fake_corpus_probe)
    monkeypatch.setattr(contemp_mod, "_decompose", lambda _c: ())

    cand = DiscoveryCandidate(
        candidate_id="cand_mixed",
        proposed_chain={
            "subject": "wisdom", "intent": "cause",
            "connective": "informs", "object": "judgment",
        },
        trigger="would_have_grounded",
        source_turn_trace="t3",
        pack_consistent=True,
        boundary_clean=True,
    )
    out = contemplate(cand, vault_probe=fake_vault)
    assert out.polarity == "undetermined"
    # ``informs`` is in _FRAME_DEPENDENT_CONNECTIVES → start at relational.
    # Mixed evidence upgrades by one tier → evaluative.
    assert out.claim_domain == "evaluative"


# ---------------------------------------------------------------------------
# Recursion overflow
# ---------------------------------------------------------------------------


def test_recursion_overflow_sets_flag_and_emits_subquestion():
    cand = _phase_b_candidate()
    out = contemplate(cand, max_depth=0)  # depth 0 ⇒ immediate failsafe
    assert out.recursion_overflow is True
    assert out.sub_questions
    assert any(sq.outcome == "depth_failsafe" for sq in out.sub_questions)


def test_max_depth_one_terminates_without_overflow_at_root():
    """Depth 1 should let the root execute once; sub-candidates fire failsafe."""
    cand = _phase_b_candidate(subject="memory", intent="verification")
    out = contemplate(cand, max_depth=1)
    # Root processed; sub-candidates (depth=1) hit failsafe immediately.
    assert out.recursion_overflow is False
    # The sub-question outcomes will reflect depth_failsafe propagation.
    assert all(
        sq.outcome in ("grounded", "gap_recorded", "depth_failsafe")
        for sq in out.sub_questions
    )


# ---------------------------------------------------------------------------
# Frame-dependent classification
# ---------------------------------------------------------------------------


def test_frame_dependent_connective_classifies_as_relational():
    cand = DiscoveryCandidate(
        candidate_id="cand_relational",
        proposed_chain={
            "subject": "wisdom", "intent": "cause",
            "connective": "orders", "object": "judgment",
        },
        trigger="would_have_grounded",
        source_turn_trace="t4",
        pack_consistent=True,
        boundary_clean=True,
    )
    out = contemplate(cand)
    assert out.claim_domain == "relational"


# ---------------------------------------------------------------------------
# Phase B byte-equality preservation
# ---------------------------------------------------------------------------


def test_uncontemplated_candidate_jsonl_unchanged():
    """A Phase B candidate (defaults only) must serialise byte-identical
    to its pre-C1 encoding — no new keys leak into the line."""
    cand = _phase_b_candidate()
    line = format_candidate_jsonl(cand)
    parsed = json.loads(line)
    assert set(parsed.keys()) == {
        "candidate_id",
        "proposed_chain",
        "trigger",
        "source_turn_trace",
        "pack_consistent",
        "boundary_clean",
        "review_state",
    }


def test_contemplated_candidate_jsonl_carries_c1_fields():
    """An enriched candidate's JSONL line must include the C1 fields."""
    cand = DiscoveryCandidate(
        candidate_id="cand_enriched",
        proposed_chain={
            "subject": "light", "intent": "cause",
            "connective": "reveals", "object": "truth",
        },
        trigger="would_have_grounded",
        source_turn_trace="t5",
        pack_consistent=True,
        boundary_clean=True,
    )
    out = contemplate(cand)
    parsed = json.loads(format_candidate_jsonl(out))
    assert "polarity" in parsed
    assert "claim_domain" in parsed
    assert "evidence" in parsed
    assert "sub_questions" in parsed
    assert "contemplation_depth" in parsed
    assert "recursion_overflow" in parsed


# ---------------------------------------------------------------------------
# Determinism of sub_id derivation
# ---------------------------------------------------------------------------


def test_subquestion_ids_stable_across_runs():
    cand = _phase_b_candidate()
    a = contemplate(cand)
    b = contemplate(cand)
    assert [sq.sub_id for sq in a.sub_questions] == [
        sq.sub_id for sq in b.sub_questions
    ]


# ---------------------------------------------------------------------------
# Evidence pointer admissibility
# ---------------------------------------------------------------------------


def test_evidence_pointers_only_admit_three_sources():
    """No emitted pointer escapes the {corpus, pack, vault_coherent} set."""
    cand = _phase_b_candidate(subject="memory", intent="verification")
    out = contemplate(cand)
    all_ptrs = list(out.evidence) + [
        p for sq in out.sub_questions for p in sq.evidence
    ]
    for p in all_ptrs:
        assert p.source in ("corpus", "pack", "vault_coherent")
        assert p.polarity in ("affirms", "falsifies")


# ---------------------------------------------------------------------------
# Vault probe injection
# ---------------------------------------------------------------------------


def test_vault_probe_injection_contributes_evidence():
    cand = DiscoveryCandidate(
        candidate_id="cand_vault",
        proposed_chain={
            "subject": "memory", "intent": "verification",
            "connective": "requires", "object": "recall",
        },
        trigger="would_have_grounded",
        source_turn_trace="t6",
        pack_consistent=True,
        boundary_clean=True,
    )

    def probe(subj, obj):
        return (
            EvidencePointer(
                source="vault_coherent", ref="v_1",
                polarity="affirms", epistemic_status="coherent",
            ),
        )

    out = contemplate(cand, vault_probe=probe)
    assert any(e.source == "vault_coherent" for e in out.evidence)


def test_vault_probe_failure_does_not_poison_loop():
    cand = _phase_b_candidate()

    def bad_probe(subj, obj):
        raise RuntimeError("vault unreachable")

    # Loop must still terminate cleanly.
    out = contemplate(cand, vault_probe=bad_probe)
    assert out is not None

"""Tests for ``formation.forge`` — the trust boundary.

Every Forge rejection rule has at least one negative test, per the project's
TDD doctrine and the Phase 2 risk register entry.
"""

from __future__ import annotations

import pytest

from formation.allowlist import AllowedSource, SourceAllowlist
from formation.candidate import (
    CandidateState,
    ConceptCandidate,
    RelationCandidate,
    SourceRef,
)
from formation.forge import Forge, ValidatedTripleCache


# ---------- fixtures ----------


_PRIMARY_SHA = "1" * 64
_SECONDARY_SHA_A = "a" * 64
_SECONDARY_SHA_B = "b" * 64
_LLM_SHA = "c" * 64
_UNLISTED_SHA = "9" * 64


@pytest.fixture
def allowlist() -> SourceAllowlist:
    return SourceAllowlist((
        AllowedSource(_PRIMARY_SHA, "primary", "stanford-textbook"),
        AllowedSource(_SECONDARY_SHA_A, "secondary", "wikipedia"),
        AllowedSource(_SECONDARY_SHA_B, "secondary", "stackexchange"),
        AllowedSource(_LLM_SHA, "llm", "claude-opus-4-7"),
    ))


def _source(sha: str, adapter: str = "wikipedia") -> SourceRef:
    return SourceRef(
        source_sha=sha,
        span="...quoted excerpt...",
        adapter=adapter,
        retrieved_at="2026-05-16T00:00:00Z",
    )


def _rel(
    head: str = "wisdom",
    relation: str = "is",
    tail: str = "judgment",
    sources: tuple[SourceRef, ...] = (),
) -> RelationCandidate:
    return RelationCandidate(head=head, relation=relation, tail=tail, sources=sources)


@pytest.fixture
def forge(allowlist) -> Forge:
    return Forge(allowlist=allowlist)


# ---------- R1: well-typed ----------


class TestR1WellTyped:
    def test_malformed_no_relation_quarantined(self, forge) -> None:
        cand = _rel(head="wisdom", relation="orbits", tail="judgment",
                    sources=(_source(_PRIMARY_SHA),))
        vts = forge.validate("subject.x", relations=[cand])
        assert vts.relations == ()
        assert len(vts.quarantined) == 1
        assert vts.quarantined[0].rejection_reason == "malformed"

    def test_empty_sides_quarantined(self, forge) -> None:
        cand = _rel(head="", relation="is", tail="judgment",
                    sources=(_source(_PRIMARY_SHA),))
        vts = forge.validate("subject.x", relations=[cand])
        assert vts.quarantined[0].rejection_reason == "malformed"


# ---------- R2: identity-axis collision ----------


class TestR2IdentityAxis:
    def test_truth_in_head_rejected(self, forge) -> None:
        cand = _rel(head="truth", relation="is", tail="judgment",
                    sources=(_source(_PRIMARY_SHA),))
        vts = forge.validate("subject.x", relations=[cand])
        assert vts.quarantined[0].rejection_reason == "identity_axis_collision"

    def test_identity_in_tail_rejected(self, forge) -> None:
        cand = _rel(head="wisdom", relation="is", tail="identity",
                    sources=(_source(_PRIMARY_SHA),))
        vts = forge.validate("subject.x", relations=[cand])
        assert vts.quarantined[0].rejection_reason == "identity_axis_collision"

    def test_custom_axis_terms(self, allowlist) -> None:
        forge = Forge(allowlist=allowlist, identity_axis_terms=("forbidden",))
        cand = _rel(head="forbidden", relation="is", tail="judgment",
                    sources=(_source(_PRIMARY_SHA),))
        vts = forge.validate("subject.x", relations=[cand])
        assert vts.quarantined[0].rejection_reason == "identity_axis_collision"


# ---------- R3: source allow-list ----------


class TestR3SourceAllowlist:
    def test_no_sources_quarantined(self, forge) -> None:
        cand = _rel()
        vts = forge.validate("subject.x", relations=[cand])
        assert vts.quarantined[0].rejection_reason == "invalid_source:no_sources"

    def test_unlisted_source_quarantined(self, forge) -> None:
        cand = _rel(sources=(_source(_UNLISTED_SHA),))
        vts = forge.validate("subject.x", relations=[cand])
        assert vts.quarantined[0].rejection_reason.startswith("invalid_source:not_in_allowlist")

    def test_path_traversal_sha_quarantined(self, forge) -> None:
        cand = _rel(sources=(_source("../escape"),))
        vts = forge.validate("subject.x", relations=[cand])
        assert vts.quarantined[0].rejection_reason.startswith("invalid_source:path_traversal")


# ---------- R4: pack/teaching-store duplicate ----------


class TestR4Duplicate:
    def test_duplicate_in_pack_silently_dropped(self, allowlist) -> None:
        class _Pack:
            def triples(self):
                return (("wisdom", "is", "judgment"),)
        forge = Forge(allowlist=allowlist, pack_haystack=_Pack())
        cand = _rel(sources=(_source(_PRIMARY_SHA),))
        vts = forge.validate("subject.x", relations=[cand])
        assert vts.relations == ()
        assert vts.quarantined == ()

    def test_duplicate_in_teaching_store_silently_dropped(self, allowlist) -> None:
        class _Store:
            def triples(self):
                return (("wisdom", "is", "judgment"),)
        forge = Forge(allowlist=allowlist, teaching_store=_Store())
        cand = _rel(sources=(_source(_PRIMARY_SHA),))
        vts = forge.validate("subject.x", relations=[cand])
        assert vts.relations == ()


# ---------- R5: cross-reference ----------


class TestR5CrossReference:
    def test_single_primary_validates(self, forge) -> None:
        cand = _rel(sources=(_source(_PRIMARY_SHA),))
        vts = forge.validate("subject.x", relations=[cand])
        assert len(vts.relations) == 1
        assert vts.relations[0].state is CandidateState.VALIDATED

    def test_single_secondary_quarantined(self, forge) -> None:
        cand = _rel(sources=(_source(_SECONDARY_SHA_A),))
        vts = forge.validate("subject.x", relations=[cand])
        assert vts.quarantined[0].rejection_reason == "insufficient_corroboration"

    def test_two_independent_secondaries_validates(self, forge) -> None:
        cand = _rel(sources=(_source(_SECONDARY_SHA_A), _source(_SECONDARY_SHA_B)))
        vts = forge.validate("subject.x", relations=[cand])
        assert len(vts.relations) == 1

    def test_two_copies_of_same_secondary_quarantined(self, forge) -> None:
        # Two SourceRefs with the same SHA do not count as independent.
        cand = _rel(sources=(
            _source(_SECONDARY_SHA_A, "wikipedia"),
            _source(_SECONDARY_SHA_A, "wikipedia-mirror"),
        ))
        vts = forge.validate("subject.x", relations=[cand])
        assert vts.quarantined[0].rejection_reason == "insufficient_corroboration"

    def test_single_llm_source_never_validates(self, forge) -> None:
        cand = _rel(sources=(_source(_LLM_SHA, "llm_ideation"),))
        vts = forge.validate("subject.x", relations=[cand])
        assert vts.quarantined[0].rejection_reason == "insufficient_corroboration"

    def test_llm_plus_one_secondary_quarantined(self, forge) -> None:
        cand = _rel(sources=(
            _source(_LLM_SHA, "llm_ideation"),
            _source(_SECONDARY_SHA_A),
        ))
        vts = forge.validate("subject.x", relations=[cand])
        assert vts.quarantined[0].rejection_reason == "insufficient_corroboration"

    def test_llm_plus_two_secondaries_validates(self, forge) -> None:
        cand = _rel(sources=(
            _source(_LLM_SHA, "llm_ideation"),
            _source(_SECONDARY_SHA_A),
            _source(_SECONDARY_SHA_B),
        ))
        vts = forge.validate("subject.x", relations=[cand])
        assert len(vts.relations) == 1


# ---------- Cache ----------


class TestValidatedTripleCache:
    def test_cache_short_circuits_reverification(self, allowlist, tmp_path) -> None:
        cache = ValidatedTripleCache(tmp_path / "cache.jsonl")
        forge = Forge(allowlist=allowlist, cache=cache)
        cand = _rel(sources=(_source(_PRIMARY_SHA),))
        forge.validate("subject.x", relations=[cand])
        assert cache.contains("wisdom", "is", "judgment")
        # Same triple with a *single secondary* source would normally fail R5,
        # but the cache hit short-circuits to VALIDATED.
        again = _rel(sources=(_source(_SECONDARY_SHA_A),))
        vts2 = forge.validate("subject.x", relations=[again])
        assert len(vts2.relations) == 1

    def test_cache_persists_to_disk(self, allowlist, tmp_path) -> None:
        cache_path = tmp_path / "cache.jsonl"
        cache = ValidatedTripleCache(cache_path)
        forge = Forge(allowlist=allowlist, cache=cache)
        forge.validate("subject.x", relations=[_rel(sources=(_source(_PRIMARY_SHA),))])
        # Reload.
        cache2 = ValidatedTripleCache(cache_path)
        assert cache2.contains("wisdom", "is", "judgment")


# ---------- Concept candidates ----------


class TestConcepts:
    def test_concept_with_valid_source_passes(self, forge) -> None:
        cc = ConceptCandidate(
            canonical_term="wisdom",
            definition="judgment grounded in experience",
            sources=(_source(_PRIMARY_SHA),),
        )
        vts = forge.validate("subject.x", concepts=[cc])
        assert len(vts.concepts) == 1
        assert vts.concepts[0].state is CandidateState.VALIDATED

    def test_concept_identity_term_rejected(self, forge) -> None:
        cc = ConceptCandidate(
            canonical_term="truth",
            definition="ungrounded",
            sources=(_source(_PRIMARY_SHA),),
        )
        vts = forge.validate("subject.x", concepts=[cc])
        assert vts.concepts == ()

    def test_concept_unlisted_source_rejected(self, forge) -> None:
        cc = ConceptCandidate(
            canonical_term="wisdom",
            definition="x",
            sources=(_source(_UNLISTED_SHA),),
        )
        vts = forge.validate("subject.x", concepts=[cc])
        assert vts.concepts == ()


# ---------- Multi-candidate run ----------


class TestMixed:
    def test_partial_acceptance(self, forge) -> None:
        good = _rel(head="wisdom", relation="is", tail="judgment",
                    sources=(_source(_PRIMARY_SHA),))
        bad_identity = _rel(head="truth", relation="is", tail="judgment",
                            sources=(_source(_PRIMARY_SHA),))
        bad_source = _rel(head="number", relation="is", tail="quantity",
                          sources=(_source(_UNLISTED_SHA),))
        vts = forge.validate("subject.x", relations=[good, bad_identity, bad_source])
        assert len(vts.relations) == 1
        assert len(vts.quarantined) == 2
        reasons = {q.rejection_reason for q in vts.quarantined}
        assert any(r.startswith("identity_axis_collision") for r in reasons)
        assert any(r.startswith("invalid_source") for r in reasons)

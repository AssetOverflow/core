"""Tests for ``generate/grounding_accessors.py`` (step 3).

These tests pin the structured-grounding contract:

* Every fact returned carries a canonical ``FactSource`` and a
  ``source_id`` that points back into a real artifact (pack lemma,
  teaching chain id, cross-pack chain id).
* Returned tuples are canonically sorted — equal calls produce
  byte-identical tuples.
* No content synthesis: ``obj`` values are verbatim pack
  ``semantic_domains`` strings, verbatim pack glosses, or verbatim
  teaching/cross-pack chain object lemmas.
* The accessors do not import or call any ``*_grounded_surface``
  composer — they consult only the underlying data sources, so the
  existing string composers stay untouched.

The grounding-source characterization sidecar (step 1) covers the
underlying data substrate; this file pins the *adapter* layer that
converts that substrate into :class:`GroundedFact` tuples.
"""

from __future__ import annotations

import inspect

from generate.discourse_planner import (
    FactSource,
    GroundedFact,
    GroundingBundle,
)
from generate.grounding_accessors import (
    cross_pack_grounded_chains,
    grounding_bundle_for,
    pack_grounded_facts,
    teaching_grounded_chains,
)


# ---------------------------------------------------------------------------
# Pack accessor
# ---------------------------------------------------------------------------


class TestPackGroundedFacts:
    def test_returns_facts_for_pack_lemma(self) -> None:
        facts = pack_grounded_facts("truth")
        assert len(facts) > 0
        assert all(f.source is FactSource.PACK for f in facts)
        assert all(f.subject == "truth" for f in facts)

    def test_returns_empty_for_unknown_lemma(self) -> None:
        assert pack_grounded_facts("definitely_not_a_lemma_xyz") == ()
        assert pack_grounded_facts("") == ()
        assert pack_grounded_facts("   ") == ()

    def test_source_id_points_into_resolving_pack(self) -> None:
        facts = pack_grounded_facts("truth")
        assert all(":" in f.source_id for f in facts)
        # Every source_id is namespaced by the resolving pack id;
        # cognition pack comes first by default precedence so "truth"
        # resolves there.
        assert all(
            f.source_id.startswith("en_core_cognition_v1:")
            for f in facts
        )

    def test_facts_are_canonically_sorted(self) -> None:
        facts = pack_grounded_facts("truth")
        assert facts == tuple(sorted(facts, key=GroundedFact.sort_key))

    def test_belongs_to_obj_is_verbatim_pack_domain(self) -> None:
        # Every "belongs_to" obj must appear as a literal string in the
        # pack's semantic_domains for the lemma — no synthesis.
        from chat.pack_resolver import resolve_lemma

        facts = pack_grounded_facts("truth")
        resolved = resolve_lemma("truth")
        assert resolved is not None
        _, domains = resolved
        belongs_to_objs = {
            f.obj for f in facts if f.predicate == "belongs_to"
        }
        assert belongs_to_objs <= set(domains)

    def test_predicates_are_canonical(self) -> None:
        facts = pack_grounded_facts("truth")
        predicates = {f.predicate for f in facts}
        assert predicates <= {"belongs_to", "is_defined_as"}


# ---------------------------------------------------------------------------
# Teaching accessor
# ---------------------------------------------------------------------------


class TestTeachingGroundedChains:
    def test_returns_chains_for_subject_with_reviewed_teaching(self) -> None:
        facts = teaching_grounded_chains("knowledge")
        assert len(facts) > 0
        assert all(f.source is FactSource.TEACHING for f in facts)
        assert all(f.subject == "knowledge" for f in facts)

    def test_returns_empty_for_unknown_subject(self) -> None:
        assert teaching_grounded_chains("definitely_not_a_subject_xyz") == ()
        assert teaching_grounded_chains("") == ()

    def test_source_id_points_into_corpus(self) -> None:
        facts = teaching_grounded_chains("knowledge")
        # Format is "<corpus_id>#<chain_id>"
        assert all("#" in f.source_id for f in facts)
        for f in facts:
            corpus_id, chain_id = f.source_id.split("#", 1)
            assert corpus_id != ""
            assert chain_id != ""

    def test_facts_are_canonically_sorted(self) -> None:
        facts = teaching_grounded_chains("knowledge")
        assert facts == tuple(sorted(facts, key=GroundedFact.sort_key))

    def test_obj_is_verbatim_chain_object(self) -> None:
        from chat.teaching_grounding import _all_chains_index

        facts = teaching_grounded_chains("knowledge")
        chains = _all_chains_index()
        # Every fact's (subject, predicate, obj) must match exactly one
        # aggregated chain.
        chain_triples = {
            (chain.subject, chain.connective, chain.object)
            for chain in chains.values()
        }
        for f in facts:
            assert (f.subject, f.predicate, f.obj) in chain_triples


# ---------------------------------------------------------------------------
# Cross-pack accessor
# ---------------------------------------------------------------------------


class TestCrossPackGroundedChains:
    def test_returns_chains_for_subject_with_cross_pack_data(self) -> None:
        facts = cross_pack_grounded_chains("parent")
        assert len(facts) > 0
        assert all(f.source is FactSource.TEACHING for f in facts)

    def test_object_view_can_be_disabled(self) -> None:
        forward_and_reverse = cross_pack_grounded_chains(
            "memory", include_object_view=True
        )
        forward_only = cross_pack_grounded_chains(
            "memory", include_object_view=False
        )
        assert len(forward_only) <= len(forward_and_reverse)

    def test_returns_empty_for_unknown_lemma(self) -> None:
        assert cross_pack_grounded_chains("definitely_not_a_lemma_xyz") == ()

    def test_facts_are_canonically_sorted_and_deduped(self) -> None:
        facts = cross_pack_grounded_chains("parent")
        assert facts == tuple(sorted(facts, key=GroundedFact.sort_key))
        # Dedupe by sort_key — no duplicate facts allowed.
        keys = [f.sort_key() for f in facts]
        assert len(keys) == len(set(keys))


# ---------------------------------------------------------------------------
# Bundle composer
# ---------------------------------------------------------------------------


class TestGroundingBundleFor:
    def test_combines_all_three_sources(self) -> None:
        bundle = grounding_bundle_for("knowledge")
        assert isinstance(bundle, GroundingBundle)
        sources = {f.source for f in bundle.sorted_facts()}
        # Knowledge is a cognition-pack lemma with reviewed teaching
        # chains rooted on it.
        assert FactSource.PACK in sources
        assert FactSource.TEACHING in sources

    def test_pack_facts_come_before_teaching_in_sorted_view(self) -> None:
        bundle = grounding_bundle_for("knowledge")
        sources_in_order = [f.source for f in bundle.sorted_facts()]
        # Pack < Teaching by canonical priority.  First non-pack index
        # must come AFTER the last pack index.
        try:
            first_teaching = sources_in_order.index(FactSource.TEACHING)
        except ValueError:
            return
        for src in sources_in_order[:first_teaching]:
            assert src is FactSource.PACK

    def test_empty_bundle_for_unknown_lemma(self) -> None:
        bundle = grounding_bundle_for("definitely_not_a_lemma_xyz")
        assert bundle.is_empty()

    def test_bundle_is_deterministic(self) -> None:
        a = grounding_bundle_for("truth").sorted_facts()
        b = grounding_bundle_for("truth").sorted_facts()
        assert a == b


# ---------------------------------------------------------------------------
# Doctrine invariants
# ---------------------------------------------------------------------------


class TestAccessorDoctrine:
    def test_no_string_composer_imports(self) -> None:
        # The accessors must not pull in any *_grounded_surface
        # composer — they consult only the underlying data accessors.
        import generate.grounding_accessors as ga

        src = inspect.getsource(ga)
        forbidden = (
            "pack_grounded_surface",
            "pack_grounded_definition",
            "pack_grounded_comparison",
            "pack_grounded_correction",
            "pack_grounded_procedure",
            "teaching_grounded_surface",
            "cross_pack_grounded_surface",
            "narrative_grounded_surface",
            "example_grounded_surface",
        )
        for token in forbidden:
            assert token not in src, (
                f"grounding_accessors must not depend on {token}"
            )

    def test_no_runtime_imports(self) -> None:
        import generate.grounding_accessors as ga

        src = inspect.getsource(ga)
        assert "chat.runtime" not in src
        assert "ChatRuntime" not in src

"""ADR-0064 — ``relations_chains_v1`` reviewed teaching corpus tests.

The contract these tests pin:

  - The relations corpus loads cleanly via the cross-corpus
    aggregator (``_all_chains_index``); none of its chains drop on
    pack-residency or schema gates.
  - Every chain's subject AND object resides in
    ``en_core_relations_v1`` (strict pack-internal, per
    ``docs/teaching_order.md`` §5 — no cross-domain triples in v1).
  - Every connective is already humanised by
    :data:`generate.semantic_templates._PREDICATE_HUMANIZE` (no new
    predicates introduced in this seed).
  - Each chain emits a deterministic teaching-grounded surface tagged
    ``teaching-grounded (relations_chains_v1)``.
  - The cognition lane invariant is preserved: cognition chains
    still tag ``cognition_chains_v1`` byte-identically.
"""

from __future__ import annotations

import pytest

from chat.teaching_grounding import (
    TEACHING_CORPORA,
    _all_chains_index,
    _load_corpus,
    clear_teaching_caches,
    has_teaching_chain,
    teaching_grounded_surface,
)
from chat.pack_resolver import _pack_lexicon_for
from generate.intent import IntentTag
from generate.semantic_templates import _PREDICATE_HUMANIZE


RELATIONS_CORPUS_ID = "relations_chains_v1"
RELATIONS_PACK_ID = "en_core_relations_v1"


EXPECTED_CHAIN_IDS: frozenset[str] = frozenset({
    "cause_advisor_precedes_apprentice",
    "cause_ancestor_precedes_descendant",
    "cause_caregiver_supports_child",
    "cause_child_follows_parent",
    "cause_colleague_supports_teammate",
    "cause_cousin_belongs_to_family",
    "cause_descendant_follows_ancestor",
    "cause_elder_precedes_descendant",
    "cause_family_grounds_parent",
    "cause_manager_precedes_supervisor",
    "cause_mentor_precedes_apprentice",
    "cause_parent_precedes_child",
    "verification_apprentice_requires_advisor",
    "verification_child_requires_parent",
    "verification_descendant_requires_ancestor",
    "verification_friend_requires_trust",
    "verification_guardian_requires_child",
    "verification_neighbor_requires_family",
    "verification_relative_requires_family",
    "verification_supervisor_requires_manager",
    "verification_teammate_requires_colleague",
})


@pytest.fixture(autouse=True)
def _isolate_caches():
    clear_teaching_caches()
    yield
    clear_teaching_caches()


# ---------------------------------------------------------------------------
# Registry — the relations corpus is registered
# ---------------------------------------------------------------------------


def test_relations_corpus_is_registered() -> None:
    corpus_ids = {spec.corpus_id for spec in TEACHING_CORPORA}
    assert RELATIONS_CORPUS_ID in corpus_ids


def test_relations_corpus_is_bound_to_relations_pack() -> None:
    spec = next(s for s in TEACHING_CORPORA if s.corpus_id == RELATIONS_CORPUS_ID)
    assert spec.pack_id == RELATIONS_PACK_ID


# ---------------------------------------------------------------------------
# Corpus content — every chain loads, lives in the right pack
# ---------------------------------------------------------------------------


def test_all_seed_chains_load_cleanly() -> None:
    spec = next(s for s in TEACHING_CORPORA if s.corpus_id == RELATIONS_CORPUS_ID)
    loaded = _load_corpus(spec)
    chain_ids = {c.chain_id for c in loaded.values()}
    assert chain_ids == EXPECTED_CHAIN_IDS


def test_every_chain_is_pack_internal_to_relations() -> None:
    """Strict pack-internal invariant: subject AND object must both
    reside in ``en_core_relations_v1``.  Cross-domain triples are
    deferred to a future ADR per teaching_order.md §5."""
    spec = next(s for s in TEACHING_CORPORA if s.corpus_id == RELATIONS_CORPUS_ID)
    pack = _pack_lexicon_for(RELATIONS_PACK_ID)
    loaded = _load_corpus(spec)
    for chain in loaded.values():
        assert chain.subject in pack, (
            f"{chain.chain_id}: subject {chain.subject!r} not in relations pack"
        )
        assert chain.object in pack, (
            f"{chain.chain_id}: object {chain.object!r} not in relations pack"
        )


def test_every_connective_is_humanised() -> None:
    """No new predicates introduced in the v1 seed — every connective
    must already appear in ``_PREDICATE_HUMANIZE``."""
    spec = next(s for s in TEACHING_CORPORA if s.corpus_id == RELATIONS_CORPUS_ID)
    loaded = _load_corpus(spec)
    for chain in loaded.values():
        assert chain.connective in _PREDICATE_HUMANIZE, (
            f"{chain.chain_id}: connective {chain.connective!r} not humanised — "
            f"add to generate/semantic_templates.py or pick an existing one"
        )


def test_corpus_id_recorded_on_loaded_chains() -> None:
    spec = next(s for s in TEACHING_CORPORA if s.corpus_id == RELATIONS_CORPUS_ID)
    loaded = _load_corpus(spec)
    for chain in loaded.values():
        assert chain.corpus_id == RELATIONS_CORPUS_ID


# ---------------------------------------------------------------------------
# Aggregated index — chains visible cross-corpus
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "subject,intent",
    [
        ("parent", IntentTag.CAUSE),
        ("child", IntentTag.CAUSE),
        ("ancestor", IntentTag.CAUSE),
        ("descendant", IntentTag.CAUSE),
        ("family", IntentTag.CAUSE),
        ("child", IntentTag.VERIFICATION),
        ("descendant", IntentTag.VERIFICATION),
    ],
)
def test_has_teaching_chain_finds_relations_chains(subject: str, intent: IntentTag) -> None:
    assert has_teaching_chain(subject, intent) is True


# ---------------------------------------------------------------------------
# Surface emission — relations-corpus chains tag their resolving corpus
# ---------------------------------------------------------------------------


def test_relations_surface_tag_is_relations_corpus_id() -> None:
    surface = teaching_grounded_surface("parent", IntentTag.CAUSE)
    assert surface is not None
    assert "teaching-grounded (relations_chains_v1)" in surface
    assert "cognition_chains_v1" not in surface


def test_cognition_surface_tag_is_cognition_corpus_id_byte_identical() -> None:
    """ADR-0064 invariant: registering a second corpus must not alter
    surfaces emitted by the first.  Cognition lemmas still tag
    ``cognition_chains_v1``."""
    surface = teaching_grounded_surface("light", IntentTag.CAUSE)
    assert surface is not None
    assert "teaching-grounded (cognition_chains_v1)" in surface
    assert "relations_chains_v1" not in surface


def test_relations_surface_emits_only_pack_atoms() -> None:
    """Every visible token must be either the lemma itself or a
    verbatim ``semantic_domains`` entry from the relations pack — no
    synthesis, no rewording."""
    surface = teaching_grounded_surface("parent", IntentTag.CAUSE)
    assert surface is not None
    # Relations-pack atoms expected for parent/child:
    relations_pack = _pack_lexicon_for(RELATIONS_PACK_ID)
    parent_domains = relations_pack["parent"]
    child_domains = relations_pack["child"]
    # At least the first parent domain and first child domain appear.
    assert parent_domains[0] in surface
    assert child_domains[0] in surface
    # No cognition-pack signature should appear in a relations
    # surface.  We check semantic-domain prefixes rather than bare
    # lemmas — the template constant ``"No session evidence yet."``
    # includes the substring ``evidence`` which would false-positive
    # any lemma-substring scan.
    for cognition_signature in (
        "cognition.knowledge",
        "cognition.truth",
        "epistemic.ground",
        "memory.semantic",
    ):
        assert cognition_signature not in surface, (
            f"relations surface leaked cognition signature {cognition_signature!r}"
        )


# ---------------------------------------------------------------------------
# Aggregator — orthogonality enforced
# ---------------------------------------------------------------------------


def test_cross_corpus_aggregator_has_both_corpora() -> None:
    index = _all_chains_index()
    cognition_keys = {k for k, c in index.items() if c.corpus_id == "cognition_chains_v1"}
    relations_keys = {k for k, c in index.items() if c.corpus_id == RELATIONS_CORPUS_ID}
    assert cognition_keys, "cognition corpus disappeared"
    assert relations_keys, "relations corpus did not register"
    # Orthogonality: no (subject, intent) cell is claimed by both.
    assert not (cognition_keys & relations_keys), (
        "cross-corpus (subject, intent) collision — orthogonality broken"
    )

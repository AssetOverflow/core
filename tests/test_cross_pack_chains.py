"""Phase 4 / ADR-0067 — cross-pack teaching chain tests.

Contracts pinned here:

  Loader
  - Cross-pack corpus loads chains whose subject + object reside in
    DIFFERENT ratified packs (verified per-chain via the declared
    ``subject_pack_id`` / ``object_pack_id`` fields).
  - Same-pack entries are rejected as corpus-misfilings.
  - Chains whose declared packs do not actually contain the lemmas
    are dropped silently (pack-corpus skew defence).
  - Invalid intents / missing connective / missing pack ids are
    dropped.
  - Superseded chains are dropped from the active view.

  Single-chain surface
  - ``cross_pack_grounded_surface(subject, intent)`` returns a
    deterministic surface tagged with both pack ids.
  - Returns ``None`` for unknown subject / unsupported intent.

  Multi-chain access
  - ``cross_pack_chains_for_subject`` and
    ``cross_pack_chains_for_object`` enumerate every chain (including
    duplicates on ``(subject, intent)``) for NARRATIVE / EXAMPLE.

  Runtime integration
  - CAUSE/VERIFICATION on a cross-pack subject routes to the cross-
    pack composer when no in-pack chain resolves.
  - In-pack chains still take precedence (cognition lane byte-
    identity preserved).
  - NARRATIVE aggregates cross-pack + in-pack chains on the same
    subject.
  - EXAMPLE aggregates cross-pack + in-pack chains on the same object.
"""

from __future__ import annotations

import pytest

from chat.cross_pack_grounding import (
    CROSS_PACK_CORPUS_ID,
    CrossPackChain,
    _all_cross_pack_chains,
    _cross_pack_index,
    cross_pack_chains_for_object,
    cross_pack_chains_for_subject,
    cross_pack_grounded_surface,
)
from chat.runtime import ChatRuntime
from generate.intent import IntentTag


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def test_corpus_loads_five_seed_chains() -> None:
    chains = _all_cross_pack_chains()
    assert len(chains) == 5
    chain_ids = {c.chain_id for c in chains}
    assert chain_ids == {
        "cause_family_grounds_identity",
        "cause_parent_grounds_understanding",
        "cause_family_supports_memory",
        "verification_identity_requires_family",
        "verification_understanding_requires_parent",
    }


def test_every_chain_actually_crosses_packs() -> None:
    for chain in _all_cross_pack_chains():
        assert chain.subject_pack_id != chain.object_pack_id
        assert chain.subject_pack_id.startswith("en_core_")
        assert chain.object_pack_id.startswith("en_core_")


def test_index_first_occurrence_wins_on_collision() -> None:
    """Both ``cause_family_grounds_identity`` and
    ``cause_family_supports_memory`` share ``(family, cause)``;
    the index keeps the first."""
    chain = _cross_pack_index()[("family", "cause")]
    assert chain.chain_id == "cause_family_grounds_identity"


def test_loader_drops_unparseable_lines(tmp_path, monkeypatch) -> None:
    bad = tmp_path / "bad.jsonl"
    bad.write_text(
        '{"chain_id":"good","subject":"family","intent":"cause",'
        '"connective":"grounds","object":"identity",'
        '"subject_pack_id":"en_core_relations_v1",'
        '"object_pack_id":"en_core_cognition_v1"}\n'
        "{ not json }\n"
        '"a top-level string"\n',
        encoding="utf-8",
    )
    import chat.cross_pack_grounding as mod
    monkeypatch.setattr(mod, "_CORPUS_PATH", bad)
    mod.clear_cross_pack_cache()
    try:
        chains = _all_cross_pack_chains()
        assert len(chains) == 1
        assert chains[0].chain_id == "good"
    finally:
        mod.clear_cross_pack_cache()


def test_loader_drops_same_pack_entries(tmp_path, monkeypatch) -> None:
    same = tmp_path / "same.jsonl"
    same.write_text(
        '{"chain_id":"bad","subject":"knowledge","intent":"cause",'
        '"connective":"requires","object":"evidence",'
        '"subject_pack_id":"en_core_cognition_v1",'
        '"object_pack_id":"en_core_cognition_v1"}\n'
        '{"chain_id":"good","subject":"family","intent":"cause",'
        '"connective":"grounds","object":"identity",'
        '"subject_pack_id":"en_core_relations_v1",'
        '"object_pack_id":"en_core_cognition_v1"}\n',
        encoding="utf-8",
    )
    import chat.cross_pack_grounding as mod
    monkeypatch.setattr(mod, "_CORPUS_PATH", same)
    mod.clear_cross_pack_cache()
    try:
        ids = {c.chain_id for c in _all_cross_pack_chains()}
        assert ids == {"good"}
    finally:
        mod.clear_cross_pack_cache()


def test_loader_drops_lemma_outside_declared_pack(tmp_path, monkeypatch) -> None:
    skewed = tmp_path / "skewed.jsonl"
    skewed.write_text(
        '{"chain_id":"skewed","subject":"family","intent":"cause",'
        '"connective":"grounds","object":"identity",'
        '"subject_pack_id":"en_core_cognition_v1",'
        '"object_pack_id":"en_core_cognition_v1"}\n',
        encoding="utf-8",
    )
    import chat.cross_pack_grounding as mod
    monkeypatch.setattr(mod, "_CORPUS_PATH", skewed)
    mod.clear_cross_pack_cache()
    try:
        assert _all_cross_pack_chains() == ()
    finally:
        mod.clear_cross_pack_cache()


def test_loader_drops_invalid_intent(tmp_path, monkeypatch) -> None:
    bad = tmp_path / "bad.jsonl"
    bad.write_text(
        '{"chain_id":"x","subject":"family","intent":"definition",'
        '"connective":"grounds","object":"identity",'
        '"subject_pack_id":"en_core_relations_v1",'
        '"object_pack_id":"en_core_cognition_v1"}\n',
        encoding="utf-8",
    )
    import chat.cross_pack_grounding as mod
    monkeypatch.setattr(mod, "_CORPUS_PATH", bad)
    mod.clear_cross_pack_cache()
    try:
        assert _all_cross_pack_chains() == ()
    finally:
        mod.clear_cross_pack_cache()


def test_supersession_drops_retired_chain(tmp_path, monkeypatch) -> None:
    corpus = tmp_path / "c.jsonl"
    corpus.write_text(
        '{"chain_id":"old","subject":"family","intent":"cause",'
        '"connective":"grounds","object":"identity",'
        '"subject_pack_id":"en_core_relations_v1",'
        '"object_pack_id":"en_core_cognition_v1"}\n'
        '{"chain_id":"new","subject":"family","intent":"cause",'
        '"connective":"supports","object":"memory",'
        '"subject_pack_id":"en_core_relations_v1",'
        '"object_pack_id":"en_core_cognition_v1",'
        '"superseded_by":"old"}\n',
        encoding="utf-8",
    )
    import chat.cross_pack_grounding as mod
    monkeypatch.setattr(mod, "_CORPUS_PATH", corpus)
    mod.clear_cross_pack_cache()
    try:
        ids = {c.chain_id for c in _all_cross_pack_chains()}
        assert ids == {"new"}
    finally:
        mod.clear_cross_pack_cache()


# ---------------------------------------------------------------------------
# Single-chain surface
# ---------------------------------------------------------------------------


def test_surface_tag_exposes_both_pack_ids() -> None:
    s = cross_pack_grounded_surface("family", IntentTag.CAUSE)
    assert s is not None
    assert "cross-pack-grounded" in s
    assert "cross_pack_chains_v1" in s
    assert "en_core_relations_v1" in s
    assert "en_core_cognition_v1" in s


def test_surface_relations_to_cognition_direction() -> None:
    s = cross_pack_grounded_surface("family", IntentTag.CAUSE)
    assert s is not None
    assert "family grounds identity" in s
    assert "kinship.unit" in s
    assert "cognition.identity" in s


def test_surface_cognition_to_relations_direction() -> None:
    s = cross_pack_grounded_surface("identity", IntentTag.VERIFICATION)
    assert s is not None
    assert "identity requires family" in s
    assert "cognition.identity" in s
    assert "kinship.unit" in s


def test_surface_returns_none_for_unknown_subject() -> None:
    assert cross_pack_grounded_surface("photosynthesis", IntentTag.CAUSE) is None
    assert cross_pack_grounded_surface("xyz", IntentTag.VERIFICATION) is None


@pytest.mark.parametrize("tag", [
    IntentTag.DEFINITION,
    IntentTag.RECALL,
    IntentTag.COMPARISON,
    IntentTag.CORRECTION,
    IntentTag.PROCEDURE,
])
def test_surface_returns_none_for_unsupported_intent(tag: IntentTag) -> None:
    assert cross_pack_grounded_surface("family", tag) is None


def test_surface_is_deterministic() -> None:
    a = cross_pack_grounded_surface("family", IntentTag.CAUSE)
    b = cross_pack_grounded_surface("family", IntentTag.CAUSE)
    assert a == b


def test_surface_empty_input_returns_none() -> None:
    assert cross_pack_grounded_surface("", IntentTag.CAUSE) is None
    assert cross_pack_grounded_surface("   ", IntentTag.CAUSE) is None


# ---------------------------------------------------------------------------
# Multi-chain access
# ---------------------------------------------------------------------------


def test_chains_for_subject_returns_all_rooted_on_lemma() -> None:
    chains = cross_pack_chains_for_subject("family")
    ids = [c.chain_id for c in chains]
    assert "cause_family_grounds_identity" in ids
    assert "cause_family_supports_memory" in ids


def test_chains_for_object_returns_reverse_chains() -> None:
    chains = cross_pack_chains_for_object("family")
    ids = [c.chain_id for c in chains]
    assert "verification_identity_requires_family" in ids


def test_chains_for_subject_unknown_returns_empty() -> None:
    assert cross_pack_chains_for_subject("nonexistent") == ()
    assert cross_pack_chains_for_subject("") == ()


def test_chains_for_object_unknown_returns_empty() -> None:
    assert cross_pack_chains_for_object("nonexistent") == ()


# ---------------------------------------------------------------------------
# Runtime integration
# ---------------------------------------------------------------------------


def test_runtime_verification_on_cross_pack_only_subject() -> None:
    """``identity/verification`` has NO in-pack chain in any registered
    corpus — cross-pack composer must fire."""
    rt = ChatRuntime()
    resp = rt.chat("Does identity require family?")
    assert resp.grounding_source == "teaching"
    assert "cross-pack-grounded" in resp.surface
    assert "identity requires family" in resp.surface


def test_runtime_understanding_verification_routes_cross_pack() -> None:
    """``understanding/verification`` has no in-pack chain (only the
    ``understanding/cause`` chain exists in the cognition corpus)."""
    rt = ChatRuntime()
    resp = rt.chat("Does understanding require parent?")
    assert resp.grounding_source == "teaching"
    assert "cross-pack-grounded" in resp.surface
    assert "understanding requires parent" in resp.surface


def test_runtime_in_pack_chain_takes_precedence_over_cross_pack() -> None:
    """When BOTH an in-pack chain and a cross-pack chain match the
    same ``(subject, intent)``, the in-pack composer fires.  Cross-
    pack is the fall-through only — the cognition-lane byte-identity
    invariant depends on this rule."""
    rt = ChatRuntime()
    resp = rt.chat("Why does family exist?")
    assert resp.grounding_source == "teaching"
    # ``family/cause`` has both an in-pack chain (``family grounds
    # parent`` in relations_chains_v1) and a cross-pack chain
    # (``family grounds identity``).  The in-pack chain wins.
    assert "cross-pack-grounded" not in resp.surface
    assert "teaching-grounded" in resp.surface
    assert "family grounds parent" in resp.surface


def test_runtime_in_pack_cognition_chain_unaffected() -> None:
    """Sanity: ``knowledge/cause`` continues to ground via the
    cognition corpus."""
    rt = ChatRuntime()
    resp = rt.chat("Why does knowledge exist?")
    assert resp.grounding_source == "teaching"
    assert "cross-pack-grounded" not in resp.surface
    assert "teaching-grounded" in resp.surface


def test_runtime_narrative_aggregates_cross_pack_chains() -> None:
    rt = ChatRuntime()
    resp = rt.chat("Tell me about family.")
    assert resp.grounding_source == "teaching"
    # Anaphoric rendering: "family" is replaced by "it" in continued chain hops.
    assert "grounds identity" in resp.surface


def test_runtime_example_aggregates_cross_pack_reverse_chains() -> None:
    rt = ChatRuntime()
    resp = rt.chat("Give me an example of memory.")
    assert resp.grounding_source == "teaching"
    assert "memory" in resp.surface.lower()


def test_corpus_id_constant_matches_filename() -> None:
    from pathlib import Path
    expected = (
        Path(__file__).resolve().parent.parent
        / "teaching" / "cross_pack_chains"
        / f"{CROSS_PACK_CORPUS_ID}.jsonl"
    )
    assert expected.exists()


def test_cross_pack_chain_is_frozen() -> None:
    chain = _all_cross_pack_chains()[0]
    assert isinstance(chain, CrossPackChain)
    with pytest.raises(Exception):
        chain.subject = "mutated"  # type: ignore[misc]

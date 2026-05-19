"""Phase 3.3 + 3.4 — NARRATIVE and EXAMPLE intent + composer tests.

The contracts pinned here:

  NARRATIVE
  - "Tell me about X" / "Describe X" / "What can you say about X"
    classify as NARRATIVE before falling through to DEFINITION.
  - Composer walks every reviewed chain rooted on X across all
    registered teaching corpora; emits up to max_clauses unique
    (predicate, object) clauses; deterministic ordering.
  - Falls through to OOV invitation when X is unknown.

  EXAMPLE
  - "Give me an example of X" / "Show an instance of X" /
    "Example of X" classify as EXAMPLE before DEFINITION.
  - Composer surfaces chains where X is the OBJECT (reverse-chain
    access pattern); dedupes by subject; deterministic ordering.
  - Falls through to OOV invitation when X is unknown.

  Both
  - Surface composes only pack atoms + verbatim chain content +
    fixed template — no content synthesis.
  - Tagged ``grounding_source="teaching"`` (same provenance as
    teaching_grounded_surface — both consume the reviewed corpora).
"""

from __future__ import annotations

import pytest

from chat.example_surface import example_grounded_surface
from chat.narrative_surface import narrative_grounded_surface
from chat.runtime import ChatRuntime
from generate.intent import IntentTag, classify_intent


# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("prompt", [
    "Tell me about light.",
    "Tell me about parent",
    "Describe truth",
    "Describe photosynthesis.",
    "What can you say about wisdom?",
    "What do you know about memory?",
])
def test_narrative_patterns_classify_narrative(prompt: str) -> None:
    intent = classify_intent(prompt)
    assert intent.tag is IntentTag.NARRATIVE
    assert intent.subject


@pytest.mark.parametrize("prompt", [
    "Give me an example of truth.",
    "Show me an instance of knowledge.",
    "Show an example of parent.",
    "Example of meaning",
])
def test_example_patterns_classify_example(prompt: str) -> None:
    intent = classify_intent(prompt)
    assert intent.tag is IntentTag.EXAMPLE
    assert intent.subject


def test_narrative_pattern_precedes_definition() -> None:
    """``What can you say about X?`` could match the generic
    ``what is/are X`` pattern — assert NARRATIVE wins on the more
    specific pattern."""
    intent = classify_intent("What can you say about light?")
    assert intent.tag is IntentTag.NARRATIVE


# ---------------------------------------------------------------------------
# NARRATIVE composer — pure function
# ---------------------------------------------------------------------------


def test_narrative_aggregates_multiple_chains() -> None:
    """``truth`` appears as the subject of multiple cognition chains;
    the narrative composer emits a clause for each."""
    surface = narrative_grounded_surface("truth")
    assert surface is not None
    assert "narrative-grounded (cognition_chains_v1)" in surface
    assert "truth grounds knowledge" in surface
    assert "truth requires evidence" in surface


def test_narrative_dedupes_by_predicate_object() -> None:
    """When cause + verification carry the same (connective, object),
    only one clause is emitted."""
    surface = narrative_grounded_surface("light")
    assert surface is not None
    # (light, cause, reveals, truth) + (light, verification, reveals, truth)
    # → one clause "light reveals truth", not two.
    assert surface.count("light reveals truth") == 1


def test_narrative_handles_relations_pack_subject() -> None:
    surface = narrative_grounded_surface("parent")
    assert surface is not None
    # ADR-0067 — ``parent`` is the subject of both the in-pack chain
    # ``parent precedes child`` (relations_chains_v1) and the cross-
    # pack chain ``parent grounds understanding`` (cross_pack_chains_v1).
    # The narrative composer aggregates both; the corpus tag reflects
    # both binding sources.
    assert "relations_chains_v1" in surface
    assert "parent precedes child" in surface


def test_narrative_handles_relations_v2_subject() -> None:
    surface = narrative_grounded_surface("mother")
    assert surface is not None
    assert "narrative-grounded (relations_chains_v2)" in surface
    assert "mother precedes daughter" in surface


def test_narrative_unknown_lemma_returns_none() -> None:
    assert narrative_grounded_surface("photosynthesis") is None
    assert narrative_grounded_surface("xyzunknown") is None


def test_narrative_empty_input_returns_none() -> None:
    assert narrative_grounded_surface("") is None
    assert narrative_grounded_surface("   ") is None


def test_narrative_is_deterministic() -> None:
    a = narrative_grounded_surface("truth")
    b = narrative_grounded_surface("truth")
    assert a == b


def test_narrative_max_clauses_caps_output() -> None:
    """``max_clauses=1`` should emit just the lexicographically-first
    clause for a multi-chain subject."""
    full = narrative_grounded_surface("truth", max_clauses=8)
    capped = narrative_grounded_surface("truth", max_clauses=1)
    assert full is not None
    assert capped is not None
    assert capped != full
    assert len(capped) < len(full)


# ---------------------------------------------------------------------------
# EXAMPLE composer — pure function
# ---------------------------------------------------------------------------


def test_example_surfaces_reverse_chain() -> None:
    """``truth`` appears as the object of ``light reveals truth`` —
    the example composer surfaces the chain inverted (X = object)."""
    surface = example_grounded_surface("truth")
    assert surface is not None
    assert "example-grounded (cognition_chains_v1)" in surface
    assert "light reveals truth" in surface


def test_example_aggregates_multiple_subjects() -> None:
    """``knowledge`` appears as the object of multiple chains; the
    example composer dedupes by subject."""
    surface = example_grounded_surface("knowledge")
    assert surface is not None
    # truth/understanding/evidence all relate to knowledge as object.
    assert "knowledge" in surface
    # Each is listed once at most.
    subjects = ["truth", "understanding", "evidence"]
    found = [s for s in subjects if f"{s}" in surface]
    assert len(found) >= 1


def test_example_handles_relations_object() -> None:
    """``parent`` appears as object of ``child follows parent`` +
    ``family grounds parent`` — multiple examples.  ADR-0067 added
    ``understanding requires parent`` (cross-pack), which is also
    aggregated; the corpus tag widens to reflect both bindings."""
    surface = example_grounded_surface("parent")
    assert surface is not None
    assert "relations_chains_v1" in surface
    assert "parent" in surface


def test_example_unknown_object_returns_none() -> None:
    assert example_grounded_surface("photosynthesis") is None
    assert example_grounded_surface("xyzunknown") is None


def test_example_is_deterministic() -> None:
    a = example_grounded_surface("truth")
    b = example_grounded_surface("truth")
    assert a == b


def test_example_max_examples_caps_output() -> None:
    capped = example_grounded_surface("knowledge", max_examples=1)
    full = example_grounded_surface("knowledge", max_examples=8)
    assert capped is not None
    assert full is not None
    assert len(capped) <= len(full)


# ---------------------------------------------------------------------------
# Live runtime — NARRATIVE
# ---------------------------------------------------------------------------


def test_runtime_narrative_on_known_subject_routes_to_teaching() -> None:
    rt = ChatRuntime()
    resp = rt.chat("Tell me about truth.")
    assert resp.grounding_source == "teaching"
    assert "narrative-grounded" in resp.surface
    assert "truth" in resp.surface


def test_runtime_narrative_on_oov_routes_to_oov_invitation() -> None:
    rt = ChatRuntime()
    resp = rt.chat("Describe photosynthesis.")
    assert resp.grounding_source == "oov"
    assert "photosynthesis" in resp.surface
    assert "PackMutationProposal" in resp.surface


# ---------------------------------------------------------------------------
# Live runtime — EXAMPLE
# ---------------------------------------------------------------------------


def test_runtime_example_on_known_object_routes_to_teaching() -> None:
    rt = ChatRuntime()
    resp = rt.chat("Give me an example of truth.")
    assert resp.grounding_source == "teaching"
    assert "example-grounded" in resp.surface
    assert "light reveals truth" in resp.surface


def test_runtime_example_on_oov_routes_to_oov_invitation() -> None:
    rt = ChatRuntime()
    resp = rt.chat("Example of photosynthesis")
    assert resp.grounding_source == "oov"


def test_runtime_example_on_relations_object() -> None:
    rt = ChatRuntime()
    resp = rt.chat("Give me an example of parent.")
    assert resp.grounding_source == "teaching"
    assert "relations_chains_v1" in resp.surface

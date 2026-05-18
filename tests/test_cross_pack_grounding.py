"""ADR-0063 — cross-pack surface grounding integration tests.

These tests pin the live-path behaviour the cross-pack surface resolver
unlocks: with ``en_core_relations_v1`` joining the default mount, the
pack-grounded DEFINITION / RECALL / COMPARISON / CORRECTION / PROCEDURE
composers all engage on kinship lemmas the same way they already engage
on cognition lemmas.

The trust-boundary tag in the emitted surface follows the *resolving*
pack id — cognition lemmas still emit ``pack-grounded
(en_core_cognition_v1)`` byte-identically, kinship lemmas emit
``pack-grounded (en_core_relations_v1)``.

Cognition lane invariants (covered elsewhere) must remain unchanged:
the only surfaces that move are the ones whose subject lemma is a
kinship token.
"""

from __future__ import annotations

import pytest

from chat.pack_grounding import (
    pack_grounded_comparison_surface,
    pack_grounded_correction_surface,
    pack_grounded_procedure_surface,
    pack_grounded_surface,
)
from chat.runtime import ChatRuntime
from core.config import RuntimeConfig


# ---------------------------------------------------------------------------
# Pure-function surface composers — kinship lemmas now ground
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "lemma",
    ["parent", "child", "sibling", "family",
     "ancestor", "descendant", "spouse", "offspring"],
)
def test_pack_grounded_surface_resolves_kinship_lemmas(lemma: str) -> None:
    """Every kinship lemma now produces a deterministic pack-grounded
    surface tagged with the resolving pack id."""
    surface = pack_grounded_surface(lemma)
    assert surface is not None, f"{lemma!r} did not surface"
    assert lemma in surface
    assert "pack-grounded (en_core_relations_v1)" in surface
    assert "No session evidence yet." in surface


def test_cognition_surface_is_byte_identical_after_resolver() -> None:
    """ADR-0063 must not change the surface for cognition-pack lemmas
    — the resolver picks cognition first, the pack tag remains
    ``en_core_cognition_v1``."""
    surface = pack_grounded_surface("light")
    assert surface is not None
    assert "pack-grounded (en_core_cognition_v1)" in surface
    assert "en_core_relations_v1" not in surface


def test_comparison_cross_pack_renders_composite_tag() -> None:
    """A kinship × cognition comparison emits the composite pack tag
    ``(en_core_cognition_v1 × en_core_relations_v1)`` — first side's
    resolution first."""
    surface = pack_grounded_comparison_surface("knowledge", "parent")
    assert surface is not None
    assert "knowledge" in surface
    assert "parent" in surface
    assert "contrasts with" in surface
    assert "en_core_cognition_v1 × en_core_relations_v1" in surface


def test_comparison_cognition_only_is_byte_identical() -> None:
    """A cognition × cognition comparison must keep the single-pack
    tag — adding the resolver did not regress the existing surface."""
    surface = pack_grounded_comparison_surface("knowledge", "truth")
    assert surface is not None
    assert "pack-grounded (en_core_cognition_v1)" in surface
    assert "×" not in surface


def test_procedure_surface_resolves_kinship_topic() -> None:
    """A procedure verb-phrase whose topical lemma resolves only in
    the relations pack must tag the surface with the relations pack id."""
    surface = pack_grounded_procedure_surface("trace my ancestor")
    assert surface is not None
    assert "ancestor" in surface
    assert "procedure-grounded (en_core_relations_v1)" in surface
    assert "not yet ratified in this session" in surface


def test_correction_surface_threads_kinship_topic() -> None:
    """A CORRECTION whose first topic lemma is kinship-pack-resident
    weaves it into the acknowledgement.  Anchor pack stays cognition
    (the ``correction`` lemma lives there)."""
    surface = pack_grounded_correction_surface(
        "No, my parent disagrees with that."
    )
    assert surface is not None
    assert "pack-grounded (en_core_cognition_v1)" in surface
    assert "Noted topic: parent" in surface
    # Topic domains come from the relations pack, but render verbatim
    # as part of the topic clause — no separate tag emitted (the topic
    # pack is implied by the lemma).
    assert "kinship" in surface


# ---------------------------------------------------------------------------
# Live runtime — DEFINITION on a kinship lemma grounds
# ---------------------------------------------------------------------------


def test_runtime_definition_on_kinship_lemma_engages_pack_path() -> None:
    """``What is a parent?`` on a cold-start runtime now routes through
    the pack-grounded path — the relations pack is mounted, the
    resolver finds the lemma, the surface composer emits a
    deterministic surface tagged ``en_core_relations_v1``."""
    rt = ChatRuntime()
    resp = rt.chat("What is a parent?")
    assert resp.grounding_source == "pack"
    assert "parent" in resp.surface
    assert "en_core_relations_v1" in resp.surface


def test_runtime_recall_on_kinship_lemma_engages_pack_path() -> None:
    """``Remember family`` — RECALL intent — also surfaces via the
    cross-pack path."""
    rt = ChatRuntime()
    resp = rt.chat("Remember family")
    assert resp.grounding_source == "pack"
    assert "family" in resp.surface


def test_relations_pack_is_in_default_input_packs() -> None:
    """ADR-0063 — invariant: the relations pack joins the default
    mount once the resolver lands.  If this asserts false, the live
    path lost cross-pack grounding silently."""
    assert "en_core_relations_v1" in RuntimeConfig().input_packs


def test_resolver_default_pack_order_favors_cognition() -> None:
    """Cognition is resolved first.  When future packs introduce a
    name collision (today there is none), cognition wins — preserving
    cognition-lane byte-identity."""
    from chat.pack_resolver import DEFAULT_RESOLVABLE_PACK_IDS
    assert DEFAULT_RESOLVABLE_PACK_IDS[0] == "en_core_cognition_v1"

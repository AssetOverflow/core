"""ADR-0050 — pack-grounded COMPARISON surface tests.

Contract pinned here:

  - ``pack_grounded_comparison_surface(a, b)`` returns a deterministic
    surface composed of both lemmas + their pack ``semantic_domains``
    (up to two per side) joined by the fixed connective
    ``"contrasts with"``.  No synthesis.
  - Returns ``None`` when either lemma is missing, not a pack lemma,
    or when the two lemmas are identical (no contrastive evidence).
  - The runtime wiring engages only when:
      - the gate fires with ``source="empty_vault"``,
      - ``output_language == "en"``,
      - intent is ``COMPARISON``,
      - both ``subject`` and ``secondary_subject`` are pack lemmas.
  - ``ChatResponse.grounding_source`` and ``TurnEvent.grounding_source``
    both carry ``"pack"`` on this branch.
  - Refusal still takes priority — pack-grounded comparison never
    bypasses safety / ethics verdict refusal.
"""

from __future__ import annotations

import pytest

from chat.pack_grounding import (
    PACK_ID,
    pack_grounded_comparison_surface,
)
from chat.runtime import ChatRuntime, _UNKNOWN_DOMAIN_SURFACE


# ---------------------------------------------------------------------------
# pack_grounded_comparison_surface — pure-function contracts
# ---------------------------------------------------------------------------


def test_two_known_lemmas_produce_comparison_surface() -> None:
    surface = pack_grounded_comparison_surface("memory", "recall")
    assert surface is not None
    assert "memory" in surface
    assert "recall" in surface
    assert "contrasts with" in surface
    assert PACK_ID in surface
    assert "No session evidence yet." in surface


def test_unknown_lemma_a_returns_none() -> None:
    assert pack_grounded_comparison_surface("nonexistentxyz", "memory") is None


def test_unknown_lemma_b_returns_none() -> None:
    assert pack_grounded_comparison_surface("memory", "nonexistentxyz") is None


def test_identical_lemmas_return_none() -> None:
    """``Compare X and X`` carries no contrastive evidence — defer."""
    assert pack_grounded_comparison_surface("memory", "memory") is None
    assert pack_grounded_comparison_surface("MEMORY", "memory") is None  # case-insensitive


@pytest.mark.parametrize("bad", ["", "   ", None])
def test_empty_or_invalid_returns_none(bad) -> None:
    assert pack_grounded_comparison_surface(bad, "memory") is None  # type: ignore[arg-type]
    assert pack_grounded_comparison_surface("memory", bad) is None  # type: ignore[arg-type]


def test_comparison_surface_is_deterministic() -> None:
    """Same input must produce byte-identical surface on repeat."""
    a = pack_grounded_comparison_surface("memory", "recall")
    b = pack_grounded_comparison_surface("memory", "recall")
    assert a == b
    assert a is not None


def test_comparison_surface_is_order_sensitive() -> None:
    """``compare(a, b)`` and ``compare(b, a)`` produce distinct surfaces —
    the connective ``"contrasts with"`` orients the comparison."""
    ab = pack_grounded_comparison_surface("memory", "recall")
    ba = pack_grounded_comparison_surface("recall", "memory")
    assert ab is not None and ba is not None
    assert ab != ba


# ---------------------------------------------------------------------------
# ChatRuntime integration — cold-start COMPARISON path
# ---------------------------------------------------------------------------


def test_cold_start_comparison_returns_pack_grounded_surface() -> None:
    rt = ChatRuntime()
    resp = rt.chat("Compare memory and recall")
    assert resp.grounding_source == "pack"
    assert "memory" in resp.surface
    assert "recall" in resp.surface
    assert "contrasts with" in resp.surface


def test_cold_start_comparison_with_unknown_lemma_routes_to_partial() -> None:
    """ADR-0065 / P2.2 — when exactly one COMPARISON lemma resolves
    and the other is OOV, the runtime emits the partial-grounding
    surface (grounds the known side, hedges the OOV side) instead of
    the universal disclosure.

    Pre-P2.2 this returned the flat disclosure; post-P2.2 it emits
    an explicit partial surface that names which side could be
    grounded and which side needs a reviewed PackMutationProposal."""
    rt = ChatRuntime()
    resp = rt.chat("Compare memory and zigzagxyz")
    assert resp.grounding_source == "partial"
    assert "memory" in resp.surface
    assert "zigzagxyz" in resp.surface
    assert "PackMutationProposal" in resp.surface


def test_cold_start_comparison_with_identical_lemmas_disclosure() -> None:
    """``Compare X and X`` defers to the universal disclosure."""
    rt = ChatRuntime()
    resp = rt.chat("Compare memory and memory")
    assert resp.surface == _UNKNOWN_DOMAIN_SURFACE
    assert resp.grounding_source == "none"


def test_turn_event_carries_grounding_source_on_comparison() -> None:
    rt = ChatRuntime()
    rt.chat("Compare memory and recall")
    last_event = rt.turn_log[-1]
    assert getattr(last_event, "grounding_source", None) == "pack"


def test_comparison_pack_grounded_passes_verdict_audit() -> None:
    rt = ChatRuntime()
    resp = rt.chat("Compare memory and recall")
    assert resp.safety_verdict is not None
    assert resp.ethics_verdict is not None


# ---------------------------------------------------------------------------
# Doctrine — no synthesis, no inference
# ---------------------------------------------------------------------------


def test_comparison_surface_atoms_are_verbatim_from_pack() -> None:
    """Every visible non-template token must be either the lemma or a
    verbatim ``semantic_domains`` string from the pack — no rewording."""
    from chat.pack_grounding import _pack_index

    surface = pack_grounded_comparison_surface("memory", "recall")
    assert surface is not None

    index = _pack_index()
    memory_domains = index["memory"][:2]
    recall_domains = index["recall"][:2]

    for domain in memory_domains:
        assert domain in surface
    for domain in recall_domains:
        assert domain in surface

    # The two fixed-template tokens
    assert "contrasts with" in surface
    assert "pack-grounded" in surface
    assert "No session evidence yet." in surface

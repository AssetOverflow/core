"""Pin engagement for the en_collapse_anchors_v1 synthetic-anchor pack.

ADR-0073c: synthetic English anchors (``love`` / ``peace`` / ``justice``)
exist only so the Hebrew covenantal lenses (``he_chesed_v1`` /
``he_shalom_v1`` / ``he_tzedek_v1``) can resolve English prompts and
walk the alignment graph to their substrate atoms.  Without these
entries, the lenses ratify but stay dormant on English input.
"""

from __future__ import annotations

import pytest

from chat.pack_resolver import DEFAULT_RESOLVABLE_PACK_IDS, resolve_lemma
from chat.runtime import ChatRuntime, RuntimeConfig


@pytest.mark.parametrize(
    "lemma,expected_entry_id",
    [
        ("love", "en-collapse-love"),
        ("peace", "en-collapse-peace"),
        ("justice", "en-collapse-justice"),
    ],
)
def test_collapse_anchor_lemma_resolves(lemma: str, expected_entry_id: str):
    """Each anchor lemma resolves in the collapse pack to its synthetic
    entry_id — that entry_id is the engagement hook for the Hebrew
    covenantal lenses' alignment edges (he-021 → en-collapse-love, etc.)."""
    result = resolve_lemma(lemma)
    assert result is not None
    pack_id, _domains = result
    assert pack_id == "en_collapse_anchors_v1"


def test_collapse_pack_is_mounted_last():
    """First-match-wins precedence — collapse pack must be last so the
    cognition / relations / etc. content packs win on any lemma
    collision.  Currently no real content pack carries love/peace/justice,
    but the precedence guarantee should be maintained."""
    assert DEFAULT_RESOLVABLE_PACK_IDS[-1] == "en_collapse_anchors_v1"


@pytest.mark.parametrize(
    "lens_id,prompt,expected_mode",
    [
        ("he_chesed_v1", "What is love?", "covenant-love"),
        ("he_shalom_v1", "What is peace?", "wholeness-peace"),
        ("he_tzedek_v1", "What is justice?", "right-order"),
    ],
)
def test_hebrew_covenantal_lens_engages_via_collapse_anchor(
    lens_id: str, prompt: str, expected_mode: str,
):
    """End-to-end: the lens annotation appears on the surface, proving
    the engagement path resolved the English lemma through the collapse
    pack and walked the alignment graph to the Hebrew atom."""
    rt = ChatRuntime(config=RuntimeConfig(anchor_lens_id=lens_id))
    response = rt.chat(prompt)
    annotation = f"[lens({lens_id}):{expected_mode}]"
    assert annotation in response.surface


def test_collapse_anchor_baseline_surface_advertises_anchor_nature():
    """Without a lens engaged, the surface for ``What is love?`` should
    still be honest about being a collapse-anchor entry — the pack id
    and the ``collapse_anchor.*`` domain are the honesty signal."""
    rt = ChatRuntime()
    response = rt.chat("What is love?")
    assert response.grounding_source == "pack"
    assert "en_collapse_anchors_v1" in response.surface
    # Pack-grounded suffix format no longer inlines domain atoms in the surface.
    # And no lens annotation when no lens is selected.
    assert "[lens(" not in response.surface

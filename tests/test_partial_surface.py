"""Phase 2.2 — partial-grounding tier tests.

The contract these tests pin:

  - When exactly one of the two compared lemmas resolves in a
    mounted pack, the partial composer emits a hedged surface
    grounding the known side and disclaiming the OOV side.
  - When both resolve OR neither resolves, the composer returns
    ``None`` — the caller routes through the full pack-grounded
    composer or the OOV invitation respectively.
  - The OOV token is sanitised through ``safe_display``.
  - Live runtime: COMPARISON with mixed-residency lemmas tags
    ``grounding_source="partial"``.
  - Terminal punctuation on secondary_subject does not defeat
    resolution.
"""

from __future__ import annotations

import pytest

from chat.partial_surface import partial_comparison_surface
from chat.runtime import ChatRuntime


# ---------------------------------------------------------------------------
# Pure-function contract
# ---------------------------------------------------------------------------


def test_oov_first_known_second_emits_partial() -> None:
    result = partial_comparison_surface("photosynthesis", "knowledge")
    assert result is not None
    surface, known_side = result
    assert known_side == "b"
    assert "knowledge" in surface
    assert "photosynthesis" in surface
    assert "Whatever 'photosynthesis' is" in surface
    assert "pack-grounded (en_core_cognition_v1)" in surface
    assert "PackMutationProposal" in surface


def test_known_first_oov_second_emits_partial() -> None:
    result = partial_comparison_surface("knowledge", "photosynthesis")
    assert result is not None
    surface, known_side = result
    assert known_side == "a"
    assert "Whatever 'photosynthesis' is" in surface
    assert "I can ground 'knowledge'" in surface


def test_both_known_returns_none() -> None:
    """Both lemmas resolve — caller should route through the full
    pack-grounded comparison composer instead."""
    assert partial_comparison_surface("knowledge", "truth") is None
    assert partial_comparison_surface("parent", "child") is None


def test_both_oov_returns_none() -> None:
    """Neither lemma resolves — partial-grounding has nothing to
    anchor on.  Caller routes to the OOV invitation."""
    assert partial_comparison_surface("photosynthesis", "mitochondria") is None
    assert partial_comparison_surface("aaa", "bbb") is None


def test_identical_lemmas_return_none() -> None:
    """Same-lemma comparison has no contrastive evidence at any tier."""
    assert partial_comparison_surface("knowledge", "knowledge") is None


@pytest.mark.parametrize("bad", ["", "   ", None])
def test_empty_or_invalid_lemma_returns_none(bad) -> None:
    assert partial_comparison_surface(bad, "knowledge") is None  # type: ignore[arg-type]
    assert partial_comparison_surface("knowledge", bad) is None  # type: ignore[arg-type]


def test_surface_is_deterministic() -> None:
    a = partial_comparison_surface("photosynthesis", "knowledge")
    b = partial_comparison_surface("photosynthesis", "knowledge")
    assert a == b


def test_oov_side_is_safe_displayed() -> None:
    """The OOV token comes from user input and must pass through the
    safe-display sanitiser; control chars do not leak."""
    result = partial_comparison_surface("evil\x00token", "knowledge")
    assert result is not None
    surface, _ = result
    assert "\x00" not in surface


# ---------------------------------------------------------------------------
# Live runtime — COMPARISON with mixed-residency lemmas
# ---------------------------------------------------------------------------


def test_runtime_comparison_known_oov_routes_to_partial() -> None:
    rt = ChatRuntime()
    resp = rt.chat("Compare knowledge and photosynthesis.")
    assert resp.grounding_source == "partial"
    assert "photosynthesis" in resp.surface
    assert "knowledge" in resp.surface


def test_runtime_comparison_oov_known_routes_to_partial() -> None:
    rt = ChatRuntime()
    resp = rt.chat("Compare photosynthesis and knowledge.")
    assert resp.grounding_source == "partial"
    assert "knowledge" in resp.surface


def test_runtime_comparison_both_known_routes_to_pack() -> None:
    """Mixed residency triggers partial; both-known still hits the
    full pack-grounded comparison composer (ADR-0050)."""
    rt = ChatRuntime()
    resp = rt.chat("Compare knowledge and truth.")
    assert resp.grounding_source == "pack"
    assert "contrasts with" in resp.surface


def test_runtime_comparison_both_oov_routes_to_oov() -> None:
    rt = ChatRuntime()
    resp = rt.chat("Compare photosynthesis and mitochondria.")
    assert resp.grounding_source == "oov"


def test_runtime_comparison_cross_pack_known_routes_to_pack() -> None:
    """Cross-pack comparison (cognition × relations) still pack-grounds
    when both lemmas resolve — the partial tier is a fallback, not
    an interception."""
    rt = ChatRuntime()
    resp = rt.chat("Compare knowledge and parent.")
    assert resp.grounding_source == "pack"


def test_runtime_terminal_punctuation_does_not_defeat_resolution() -> None:
    """The intent classifier may leave a trailing period on
    secondary_subject ('Compare A and B.').  The runtime strips
    terminal sentence punctuation at the COMPARISON boundary so
    resolution finds the underlying lemma."""
    rt = ChatRuntime()
    resp = rt.chat("Compare knowledge and truth.")
    # Without normalization, "truth." was OOV → fired partial.
    # With normalization, "truth" resolves → pack.
    assert resp.grounding_source == "pack"

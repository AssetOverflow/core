"""ADR-0086 — UNKNOWN-intent pack-resident token surface.

Pins:

1. **Engagement** — the four cognition-eval UNKNOWN miss prompts each
   surface their pack-resident English tokens with semantic_domains.
2. **Null-lift invariant** — fully-OOV prompts that have zero
   pack-resident lemmas still emit the universal disclosure
   byte-identically.
3. **Composer determinism** — repeated invocation on the same prompt
   returns the byte-identical surface (ratified packs are immutable
   and the composer reads no session state).
4. **Provenance** — surfaces emitted by the new composer carry
   ``grounding_source == "pack"`` so the audit contract distinguishes
   them from vault- and teaching-grounded surfaces.
5. **Pre-ADR-0086 hand-off** — the runtime falls through to the
   bare ``_UNKNOWN_DOMAIN_SURFACE`` only when the composer returns
   ``None``; no other UNKNOWN-intent code path is disturbed.
6. **Stopword discipline** — pure dialogue-filler prompts (``be have``)
   return ``None`` because every resident token is stopworded.
"""
from __future__ import annotations

import pytest

from chat.pack_grounding import pack_grounded_unknown_surface
from chat.runtime import ChatRuntime, _UNKNOWN_DOMAIN_SURFACE


# ---------------------------------------------------------------------------
# Composer — direct calls
# ---------------------------------------------------------------------------


def test_composer_returns_none_on_empty() -> None:
    assert pack_grounded_unknown_surface("") is None
    assert pack_grounded_unknown_surface(None) is None  # type: ignore[arg-type]


def test_composer_returns_none_on_fully_oov_prompt() -> None:
    """Null-lift invariant — zero resident tokens → None."""
    assert pack_grounded_unknown_surface("xyzzy plugh frobnitz") is None


def test_composer_returns_none_on_stopwords_only() -> None:
    """``be`` and ``have`` are pack-resident but stopworded — a
    prompt of only stopwords yields no surface."""
    assert pack_grounded_unknown_surface("be have") is None


def test_composer_lifts_single_resident_token() -> None:
    """``light`` is in ``en_core_cognition_v1`` — composer surfaces it."""
    surface = pack_grounded_unknown_surface("light logos")
    assert surface is not None
    assert "light" in surface
    assert "pack-grounded (en_core_cognition_v1)" in surface
    assert "No session evidence yet." in surface


def test_composer_lifts_two_resident_tokens() -> None:
    surface = pack_grounded_unknown_surface("evidence reason")
    assert surface is not None
    assert "evidence" in surface
    assert "reason" in surface


def test_composer_caps_at_max_tokens() -> None:
    """Default ``max_tokens=3`` — four resident tokens surface
    only the first three, deterministically."""
    surface = pack_grounded_unknown_surface(
        "spirit wisdom truth knowledge",
    )
    assert surface is not None
    # First three lemmas in left-to-right order should appear; the
    # fourth (``knowledge``) is dropped under the default cap.
    assert "spirit" in surface
    assert "wisdom" in surface
    assert "truth" in surface
    assert "knowledge" not in surface


def test_composer_is_deterministic() -> None:
    """Repeated calls on the same prompt yield byte-identical surfaces."""
    a = pack_grounded_unknown_surface("spirit wisdom truth")
    b = pack_grounded_unknown_surface("spirit wisdom truth")
    assert a == b


def test_composer_strips_punctuation() -> None:
    surface = pack_grounded_unknown_surface("light, logos.")
    assert surface is not None
    assert "light" in surface


def test_composer_is_case_insensitive() -> None:
    surface = pack_grounded_unknown_surface("LIGHT LOGOS")
    assert surface is not None
    assert "light" in surface


# ---------------------------------------------------------------------------
# Runtime engagement — the four cognition-eval miss cases
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "prompt,expected_terms",
    [
        # public split — unknown_logos_019
        ("light logos", ("light",)),
        # dev split — unknown_evidence_042
        ("evidence reason", ("evidence", "reason")),
        # holdout split — unknown_spirit_041
        ("spirit wisdom truth", ("wisdom", "truth")),
        # holdout split — unknown_word_018
        ("word beginning truth", ("word", "truth")),
    ],
)
def test_runtime_unknown_lifts_pack_tokens(
    prompt: str, expected_terms: tuple[str, ...],
) -> None:
    """The four UNKNOWN-intent eval misses each lift to pack-grounded
    surfaces containing the expected English term(s)."""
    rt = ChatRuntime()
    resp = rt.chat(prompt)
    assert resp.grounding_source == "pack"
    surface_lower = resp.surface.lower()
    for term in expected_terms:
        assert term.lower() in surface_lower, (
            f"expected {term!r} in surface, got {resp.surface!r}"
        )


def test_runtime_null_lift_on_fully_oov_unknown() -> None:
    """Null-lift invariant at the runtime layer: prompts with zero
    pack-resident lemmas still emit the universal disclosure
    byte-identically."""
    rt = ChatRuntime()
    resp = rt.chat("xyzzy plugh frobnitz")
    assert resp.surface == _UNKNOWN_DOMAIN_SURFACE
    assert resp.grounding_source == "none"

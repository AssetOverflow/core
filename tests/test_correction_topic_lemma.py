"""ADR-0060 — CORRECTION acknowledgement carries the corrected-topic lemma.

ADR-0053 introduced the cold-start CORRECTION acknowledgement: a
deterministic pack-grounded surface stating that no prior turn
exists in the session to correct.  The surface was self-contained
(only the lemma ``correction`` and its semantic_domains appeared)
which left the acknowledgement honest but topic-blind — a user who
said "Actually, truth requires evidence" got a surface that didn't
reference ``truth`` at all.

ADR-0060 closes that gap by weaving the **first pack-resident
topical lemma** from the correction utterance into the surface
("Noted topic: <lemma> (<head_domains>)"), while preserving the
existing trust-boundary properties:

  - Every visible non-template token is still either the lemma
    ``correction``, the topical lemma, or a verbatim
    ``semantic_domains`` string from the ratified pack.
  - The surface is deterministic: same text → same bytes.
  - Backward compatible: ``pack_grounded_correction_surface()``
    with no argument (or with text carrying no pack lemma) emits
    the ADR-0053 topic-less template byte-identically.
  - The trailing "No prior turn in this session to correct yet."
    trust-boundary label is preserved.
"""

from __future__ import annotations

from chat.pack_grounding import (
    PACK_ID,
    _extract_correction_topic_lemma,
    pack_grounded_correction_surface,
)
from chat.runtime import ChatRuntime


# ---------------------------------------------------------------------------
# Topic lemma extraction
# ---------------------------------------------------------------------------


def test_extract_topic_lemma_picks_first_pack_lemma() -> None:
    """Left-to-right token order is the canonical selector."""
    assert _extract_correction_topic_lemma("Actually, truth requires evidence") == "truth"


def test_extract_topic_lemma_skips_meta_cognition_lemma() -> None:
    """``correction`` itself is excluded — it's already the subject of
    the acknowledgement template; echoing it would be circular."""
    assert _extract_correction_topic_lemma("That correction is wrong about wisdom") == "wisdom"


def test_extract_topic_lemma_skips_dialogue_fillers() -> None:
    """``be`` and ``have`` are pack lemmas but carry no topical signal
    in a correction utterance — filtered out as stopwords."""
    # "have" appears before "knowledge" but is a filler; selector picks knowledge.
    assert _extract_correction_topic_lemma("we have knowledge here") == "knowledge"


def test_extract_topic_lemma_returns_none_when_no_pack_lemma() -> None:
    assert _extract_correction_topic_lemma("Nope that is wrong") is None
    assert _extract_correction_topic_lemma("") is None
    assert _extract_correction_topic_lemma(None) is None  # type: ignore[arg-type]


def test_extract_topic_lemma_strips_common_punctuation() -> None:
    """Tokens with attached punctuation (``truth.``, ``"evidence"``)
    still match pack lemmas after normalization."""
    assert _extract_correction_topic_lemma('Actually, "truth" matters.') == "truth"


def test_extract_topic_lemma_is_case_insensitive() -> None:
    assert _extract_correction_topic_lemma("ACTUALLY TRUTH REQUIRES EVIDENCE") == "truth"


# ---------------------------------------------------------------------------
# Surface composition with topic
# ---------------------------------------------------------------------------


def test_surface_with_topic_contains_corrected_lemma() -> None:
    surface = pack_grounded_correction_surface("Actually, truth requires evidence")
    assert surface is not None
    assert "correction" in surface
    assert "truth" in surface
    assert "Noted topic: truth" in surface


def test_surface_with_topic_contains_topic_domains() -> None:
    """The corrected lemma's top semantic_domains are included
    verbatim — keeps the pack-grounded discipline (no rewording)."""
    from chat.pack_grounding import _pack_index
    truth_domains = _pack_index().get("truth", ())
    assert truth_domains, "test fixture: 'truth' must be a pack lemma"

    surface = pack_grounded_correction_surface("Actually, truth requires evidence")
    assert surface is not None
    # At least one of truth's top-2 domains appears in the surface.
    assert any(d in surface for d in truth_domains[:2])


def test_surface_with_no_topic_degrades_to_adr_0053_template() -> None:
    """Backward compatibility: ``pack_grounded_correction_surface()``
    with no argument emits the ADR-0053 topic-less template
    byte-identically."""
    legacy = pack_grounded_correction_surface()
    no_lemma = pack_grounded_correction_surface("Nope that is wrong")
    assert legacy is not None
    assert legacy == no_lemma
    assert "Noted topic" not in legacy
    assert "No prior turn in this session to correct yet." in legacy


def test_surface_preserves_trust_boundary_label() -> None:
    """The trailing 'No prior turn...' disclosure is the constant
    trust-boundary label distinguishing this cold-start surface
    from the post-correction teaching-repair path.  Must be present
    in both variants."""
    with_topic = pack_grounded_correction_surface("Actually, truth requires evidence")
    without_topic = pack_grounded_correction_surface()
    assert with_topic is not None and without_topic is not None
    assert "No prior turn in this session to correct yet." in with_topic
    assert "No prior turn in this session to correct yet." in without_topic


def test_surface_is_deterministic() -> None:
    a = pack_grounded_correction_surface("Actually, truth requires evidence")
    b = pack_grounded_correction_surface("Actually, truth requires evidence")
    assert a == b


def test_surface_pack_id_is_correct() -> None:
    surface = pack_grounded_correction_surface("Actually, truth requires evidence")
    assert surface is not None
    assert PACK_ID in surface


# ---------------------------------------------------------------------------
# End-to-end through ChatRuntime — the holdout test case
# ---------------------------------------------------------------------------


def test_correction_truth_040_now_emits_truth_in_surface() -> None:
    """The exact holdout case that this ADR targets:
    `correction_truth_040` expects `term=['truth']` and was missing it
    pre-ADR-0060.  Through the live ChatRuntime, the surface must now
    contain ``truth``."""
    rt = ChatRuntime()
    response = rt.chat("Actually, truth requires evidence")
    assert response.grounding_source == "pack"
    assert "truth" in response.surface.lower()
    assert "correction" in response.surface.lower()


def test_correction_with_no_pack_lemma_still_grounds() -> None:
    """A correction utterance with no pack-resident topical lemma
    still receives the acknowledgement surface (degrades to the
    topic-less template), not the universal disclosure."""
    rt = ChatRuntime()
    response = rt.chat("Nope that is wrong")
    assert response.grounding_source == "pack"
    assert "correction" in response.surface.lower()
    assert "Noted topic" not in response.surface

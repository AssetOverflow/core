"""ADR-0061 — PROCEDURE intent routes to pack-grounded surface.

Pre-ADR-0061, ``PROCEDURE`` intent had no pack-grounded composer:
every ``"How do I X?"`` question fell through to the universal
disclosure even when ``X`` was a pack-resident lemma.  This closed
``procedure_define_010`` ("How do I define a concept?") as a
surface-and-term holdout miss and ``procedure_verify_034``
("How do I verify a claim?") as a surface miss.

ADR-0061 adds ``pack_grounded_procedure_surface(subject_text)``:
extracts the **last** pack-resident lemma from the verb-phrase
subject (deliberately: procedure verb → topic, last is the topic)
and emits a deterministic acknowledgement surface that grounds
the topic in pack semantic_domains and notes explicitly that
step-by-step guidance is not yet ratified.

These tests pin:

  - Extraction picks the last pack-resident lemma (not the first).
  - Stopwords ``be`` / ``have`` are skipped.
  - Verbs (``define``, ``verify``, ``correct``, ``learn``) are NOT
    stopworded — when the verb is the only pack-resident lemma,
    the verb is the topic by elimination.
  - Surface is deterministic.
  - Surface preserves the trust-boundary clause about
    not-yet-ratified guidance.
  - Returns ``None`` when no pack lemma is found (so the universal
    disclosure still fires for fully-unknown procedure utterances).
  - Live ``ChatRuntime`` routes ``procedure_define_010`` through
    this composer and the surface contains ``concept``.
"""

from __future__ import annotations

from chat.pack_grounding import (
    PACK_ID,
    _extract_procedure_topic_lemma,
    pack_grounded_procedure_surface,
)
from chat.runtime import ChatRuntime


# ---------------------------------------------------------------------------
# Topic-lemma extraction (last-wins on procedure subjects)
# ---------------------------------------------------------------------------


def test_extract_picks_last_pack_lemma() -> None:
    """For verb-phrase subjects the topic is the object — last
    pack-resident lemma wins."""
    assert _extract_procedure_topic_lemma("define a concept") == "concept"


def test_extract_returns_verb_when_only_pack_lemma() -> None:
    """When the verb is the only pack-resident lemma (object is OOV
    or filler), the verb is the topic by elimination — preserves
    coverage on procedure utterances with non-pack objects."""
    # ``hypothesis`` is genuinely OOV across cognition/meta/relations.
    # Pre-en_core_meta_v1 the canonical example was "verify a claim",
    # but ``claim`` now resolves via the meta pack (meta.speech_act.claim),
    # so the object-first selector would correctly pick ``claim`` over
    # ``verify`` for that utterance.  Use ``hypothesis`` to keep the
    # verb-fallback contract isolated from pack-coverage changes.
    assert _extract_procedure_topic_lemma("verify a hypothesis") == "verify"
    assert _extract_procedure_topic_lemma("correct an error") == "correct"
    assert _extract_procedure_topic_lemma("learn this") == "learn"


def test_extract_skips_dialogue_fillers() -> None:
    """``be`` and ``have`` are pack-resident but stopworded."""
    assert _extract_procedure_topic_lemma("be a teacher") is None  # 'teacher' is OOV
    assert _extract_procedure_topic_lemma("have knowledge") == "knowledge"


def test_extract_none_when_no_pack_lemma() -> None:
    assert _extract_procedure_topic_lemma("") is None
    assert _extract_procedure_topic_lemma(None) is None  # type: ignore[arg-type]
    assert _extract_procedure_topic_lemma("do stuff") is None


def test_extract_strips_punctuation() -> None:
    assert _extract_procedure_topic_lemma("define, a concept.") == "concept"


def test_extract_is_case_insensitive() -> None:
    assert _extract_procedure_topic_lemma("DEFINE A CONCEPT") == "concept"


# ---------------------------------------------------------------------------
# Surface composition
# ---------------------------------------------------------------------------


def test_surface_contains_topic_lemma() -> None:
    surface = pack_grounded_procedure_surface("define a concept")
    assert surface is not None
    assert "concept" in surface


def test_surface_contains_topic_domains() -> None:
    """Pack-grounded: the topic lemma's top semantic_domains are
    surfaced verbatim — no rewording."""
    from chat.pack_grounding import _pack_index
    concept_domains = _pack_index().get("concept", ())
    assert concept_domains, "test fixture: 'concept' must be a pack lemma"

    surface = pack_grounded_procedure_surface("define a concept")
    assert surface is not None
    assert any(d in surface for d in concept_domains[:2])


def test_surface_contains_pack_id() -> None:
    surface = pack_grounded_procedure_surface("define a concept")
    assert surface is not None
    assert PACK_ID in surface


def test_surface_preserves_not_yet_ratified_clause() -> None:
    """Trust-boundary label: procedure guidance is not yet ratified.
    Must appear in every surface emitted by this composer."""
    surface = pack_grounded_procedure_surface("define a concept")
    assert surface is not None
    assert "not yet ratified" in surface


def test_surface_returns_none_for_no_pack_lemma() -> None:
    """A procedure subject with no pack-resident lemma falls
    through to the universal disclosure — preserves the honesty
    contract for fully-unknown procedures."""
    assert pack_grounded_procedure_surface("") is None
    assert pack_grounded_procedure_surface("do stuff") is None


def test_surface_is_deterministic() -> None:
    a = pack_grounded_procedure_surface("define a concept")
    b = pack_grounded_procedure_surface("define a concept")
    assert a == b


# ---------------------------------------------------------------------------
# End-to-end through ChatRuntime
# ---------------------------------------------------------------------------


def test_procedure_define_010_now_emits_concept() -> None:
    """The exact holdout case this ADR targets:
    `procedure_define_010` ("How do I define a concept?") expected
    ``term=['concept']`` and was missing it pre-ADR-0061.  Through
    the live runtime, the surface must now contain ``concept``."""
    rt = ChatRuntime()
    response = rt.chat("How do I define a concept?")
    assert response.grounding_source == "pack"
    assert "concept" in response.surface.lower()


def test_procedure_with_no_pack_lemma_routes_to_oov_invitation() -> None:
    """ADR-0065 / P2.1 — a procedure utterance with no pack-resident
    lemma now routes to the OOV invitation surface (names the unknown
    topic, points at PackMutationProposal path) instead of the flat
    universal disclosure.  No surface fabrication: the invitation
    only references the OOV token and the mounted-pack list."""
    rt = ChatRuntime()
    response = rt.chat("How do I do stuff?")
    # Either UNKNOWN-intent → "none", or PROCEDURE-intent on OOV
    # subject → "oov" invitation.  Both honour the no-fabrication
    # contract; the surface text differs by intent classification.
    assert response.grounding_source in {"oov", "none"}
    if response.grounding_source == "oov":
        assert "PackMutationProposal" in response.surface


def test_procedure_verify_an_oov_object_falls_back_to_verb() -> None:
    """When the object is OOV but the verb is pack-resident, the
    procedure composer surfaces the verb — keeps surface_groundedness
    coverage on utterances whose object is not yet packed.

    ``hypothesis`` is genuinely OOV across cognition/meta/relations.
    """
    rt = ChatRuntime()
    response = rt.chat("How do I verify a hypothesis?")
    assert response.grounding_source == "pack"
    assert "verify" in response.surface.lower()

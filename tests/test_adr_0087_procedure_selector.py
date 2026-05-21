"""ADR-0087 — PROCEDURE selector + trailing-clause subject echo.

Two coupled changes:

1. **Numeric-determiner downrank** in :func:`_extract_procedure_topic_lemma`
   — tokens whose primary semantic_domain starts with
   ``quantitative.numeric.`` are demoted; a non-numeric resident
   candidate always wins.  Only when the numeric is the sole
   resident does it become the topic.

2. **Subject-text echo in the trailing clause** of
   :func:`pack_grounded_procedure_surface` — the *"Step-by-step
   guidance for X is not yet ratified."* clause echoes the
   normalized full subject_text rather than just the lemma, so OOV
   head nouns (``terms``, ``mistake``) reach the surface even when
   only the procedure verb is pack-resident.

Closes ``procedure_compare_011`` (*"How do I compare two terms?"*)
where the pre-ADR-0087 selector picked the cardinal ``two`` over
``compare`` and the OOV head noun ``terms`` never reached the surface.

Pins both the engagement on the failing case and the regression
guard on the four existing PROCEDURE eval cases.
"""
from __future__ import annotations

import pytest

from chat.pack_grounding import (
    _extract_procedure_topic_lemma,
    pack_grounded_procedure_surface,
)
from chat.runtime import ChatRuntime


# ---------------------------------------------------------------------------
# Selector — numeric downrank
# ---------------------------------------------------------------------------


def test_numeric_determiner_is_downranked() -> None:
    """A non-numeric resident candidate (verb ``compare``) wins over
    a numeric-cardinal candidate (``two``)."""
    assert _extract_procedure_topic_lemma("compare two terms") == "compare"


def test_numeric_only_resident_still_wins_by_elimination() -> None:
    """If the numeric is the sole resident token, it remains the
    topic — preserves coverage on numeric-only prompts."""
    assert _extract_procedure_topic_lemma("count to two") == "two"


def test_non_numeric_resident_still_takes_last_wins_priority() -> None:
    """Existing last-wins behavior is preserved for non-numeric tokens.
    ``concept`` still wins over ``define`` in ``define a concept``."""
    assert _extract_procedure_topic_lemma("define a concept") == "concept"


# ---------------------------------------------------------------------------
# Surface — trailing clause echoes subject_text
# ---------------------------------------------------------------------------


def test_trailing_clause_echoes_full_subject_text() -> None:
    """OOV head noun ``terms`` reaches the surface via the trailing
    clause even though it doesn't resolve in any pack."""
    surface = pack_grounded_procedure_surface("compare two terms")
    assert surface is not None
    assert "terms" in surface
    assert "Step-by-step guidance for compare two terms" in surface


def test_trailing_clause_normalizes_punctuation_in_echo() -> None:
    surface = pack_grounded_procedure_surface("define, a concept.")
    assert surface is not None
    assert "Step-by-step guidance for define a concept" in surface


def test_displayed_lemma_is_compare_not_two() -> None:
    """The semantic anchor in the surface is the operation verb
    ``compare``, not the cardinal determiner ``two``."""
    surface = pack_grounded_procedure_surface("compare two terms")
    assert surface is not None
    assert "compare (operation.compare" in surface
    # The cardinal-determiner lemma should not appear as the displayed
    # pack-grounded anchor (it may still appear in the echoed subject).
    assert "two (quantitative.numeric" not in surface


# ---------------------------------------------------------------------------
# Regression guard — existing PROCEDURE eval cases still pass
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "prompt,expected_terms",
    [
        ("How do I define a concept?", ("concept",)),
        # ``verify a claim`` and ``correct a mistake`` carry no
        # expected_terms in the cognition eval, but the surfaces must
        # still ground deterministically and mention the user's topic.
        ("How do I verify a claim?", ("claim", "verify a claim")),
        ("How can I correct a mistake?", ("correct", "correct a mistake")),
        # The ADR-0087 target case.
        ("How do I compare two terms?", ("terms", "compare two terms")),
    ],
)
def test_runtime_procedure_surfaces_contain_expected_terms(
    prompt: str, expected_terms: tuple[str, ...],
) -> None:
    rt = ChatRuntime()
    resp = rt.chat(prompt)
    assert resp.grounding_source == "pack"
    surface_lower = resp.surface.lower()
    for term in expected_terms:
        assert term.lower() in surface_lower, (
            f"prompt={prompt!r} expected {term!r} in surface, got {resp.surface!r}"
        )


def test_procedure_surface_is_deterministic_after_adr_0087() -> None:
    a = pack_grounded_procedure_surface("compare two terms")
    b = pack_grounded_procedure_surface("compare two terms")
    assert a == b


def test_oov_only_procedure_still_falls_through_to_none() -> None:
    """ADR-0061 honesty contract holds: a verb+noun pair that is
    entirely OOV across mounted packs still returns ``None`` from
    the composer (runtime falls through to the OOV invitation)."""
    # ``fix bugs`` is the canonical fully-OOV PROCEDURE fixture used
    # by tests/test_procedure_surface.py.
    assert pack_grounded_procedure_surface("fix bugs") is None

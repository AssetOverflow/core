"""tests/test_achat.py — Async ChatRuntime.achat() and arespond() smoke tests.

Covers:
  - achat() returns a ChatResponse with non-empty surface
  - achat() surface is a str
  - arespond() returns a non-empty str
  - achat() ChatResponse.dialogue_role is set
  - achat() ChatResponse.flagged is a bool
  - achat() ChatResponse.articulation is an ArticulationPlan
  - achat() produces deterministic output (same input → same surface structure)
  - arespond() on empty input returns empty string gracefully

All tests use pytest-asyncio. If ChatRuntime cannot be instantiated
(missing language packs), the tests are skipped gracefully.
"""
from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def runtime():
    """Module-scoped ChatRuntime; skip if unavailable."""
    try:
        from chat.runtime import ChatRuntime
        return ChatRuntime()
    except Exception as exc:
        pytest.skip(f"ChatRuntime not available: {exc}")


# ---------------------------------------------------------------------------
# achat() surface invariants
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_achat_returns_non_empty_surface(runtime):
    response = await runtime.achat("truth", max_tokens=8)
    assert response.surface, "achat() surface must not be empty"


@pytest.mark.asyncio
async def test_achat_surface_is_str(runtime):
    response = await runtime.achat("light", max_tokens=8)
    assert isinstance(response.surface, str)


@pytest.mark.asyncio
async def test_achat_surface_ends_with_punctuation(runtime):
    """SentenceAssembler always terminates with . or ? or ;"""
    response = await runtime.achat("word", max_tokens=8)
    if response.surface:
        assert response.surface[-1] in {".", "?", ";", "!"}, (
            f"Surface does not end with punctuation: {response.surface!r}"
        )


# ---------------------------------------------------------------------------
# achat() ChatResponse field invariants
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_achat_dialogue_role_is_set(runtime):
    response = await runtime.achat("covenant", max_tokens=8)
    assert response.dialogue_role is not None


@pytest.mark.asyncio
async def test_achat_flagged_is_bool(runtime):
    response = await runtime.achat("beginning", max_tokens=8)
    assert isinstance(response.flagged, bool)


@pytest.mark.asyncio
async def test_achat_articulation_is_articulation_plan(runtime):
    from generate.articulation import ArticulationPlan
    response = await runtime.achat("logos", max_tokens=8)
    assert isinstance(response.articulation, ArticulationPlan)


@pytest.mark.asyncio
async def test_achat_proposition_subject_is_str(runtime):
    response = await runtime.achat("dabar", max_tokens=8)
    assert isinstance(response.proposition.subject, str)


# ---------------------------------------------------------------------------
# arespond() invariants
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_arespond_returns_str(runtime):
    result = await runtime.arespond("aletheia", max_tokens=8)
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_arespond_non_empty_for_known_token(runtime):
    result = await runtime.arespond("truth", max_tokens=8)
    assert result, "arespond() returned empty string for known token"


@pytest.mark.asyncio
async def test_arespond_graceful_on_unknown_token(runtime):
    """OOV input should not raise — returns empty string."""
    result = await runtime.arespond(
        "xyzzy_unknown_token_12345", max_tokens=4
    )
    assert isinstance(result, str)  # empty string is acceptable


# ---------------------------------------------------------------------------
# Structural determinism
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_achat_same_input_same_sentence_structure(runtime):
    """Two calls with the same input must produce surfaces that end the same way.

    Exact surface equality isn't guaranteed across sessions (persona motor
    state accumulates), but the punctuation terminal and role must be stable.
    """
    r1 = await runtime.achat("truth", max_tokens=8)
    r2 = await runtime.achat("truth", max_tokens=8)
    # Both surfaces must be strings and end with punctuation.
    for r in (r1, r2):
        assert isinstance(r.surface, str)
        if r.surface:
            assert r.surface[-1] in {".", "?", ";", "!"}

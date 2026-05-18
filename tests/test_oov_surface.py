"""Phase 2.1 — OOV "teach me" surface tests.

The contract these tests pin:

  - OOV tokens with a supported intent produce a deterministic
    learning-invitation surface tagged ``grounding_source="oov"``.
  - Known tokens still ground through the existing pack/teaching
    paths byte-identically.
  - The OOV surface names the unknown token, lists mounted packs,
    and points at the reviewed PackMutationProposal path — never
    invents meaning, never auto-mutates.
  - UNKNOWN-intent prompts still get the universal disclosure
    (the classifier itself failed to extract a confident subject).
  - User-text passes through the safe-display sanitiser; control
    chars do not leak into surfaces.
"""

from __future__ import annotations

import pytest

from chat.oov_surface import (
    is_oov_for_packs,
    oov_learning_invitation_surface,
)
from chat.runtime import ChatRuntime
from generate.intent import IntentTag


# ---------------------------------------------------------------------------
# Pure-function contract
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("intent_tag", [
    IntentTag.DEFINITION,
    IntentTag.RECALL,
    IntentTag.CAUSE,
    IntentTag.VERIFICATION,
    IntentTag.COMPARISON,
    IntentTag.PROCEDURE,
    IntentTag.CORRECTION,
])
def test_oov_token_with_supported_intent_emits_invitation(
    intent_tag: IntentTag,
) -> None:
    surface = oov_learning_invitation_surface("photosynthesis", intent_tag)
    assert surface is not None
    assert "photosynthesis" in surface
    assert "haven't learned" in surface
    assert "en_core_cognition_v1" in surface
    assert "en_core_relations_v1" in surface
    assert "PackMutationProposal" in surface
    assert intent_tag.name.lower() in surface


def test_known_token_returns_none() -> None:
    """If the token IS resolvable, the composer returns None so the
    caller routes through pack-grounded / teaching-grounded paths."""
    assert oov_learning_invitation_surface("light", IntentTag.DEFINITION) is None
    assert oov_learning_invitation_surface("parent", IntentTag.CAUSE) is None
    assert oov_learning_invitation_surface("knowledge", IntentTag.VERIFICATION) is None


@pytest.mark.parametrize("bad", ["", "   ", None])
def test_empty_or_invalid_token_returns_none(bad) -> None:
    assert oov_learning_invitation_surface(bad, IntentTag.DEFINITION) is None  # type: ignore[arg-type]


def test_unknown_intent_returns_none() -> None:
    """UNKNOWN intent means the classifier could not extract a
    confident subject; emitting an invitation for an unparsed prompt
    would be misleading."""
    assert oov_learning_invitation_surface("photosynthesis", IntentTag.UNKNOWN) is None


def test_empty_pack_list_returns_none() -> None:
    """With no mounted packs there is no learnable destination;
    the invitation has no targets to suggest."""
    surface = oov_learning_invitation_surface(
        "photosynthesis", IntentTag.DEFINITION, pack_ids=(),
    )
    assert surface is None


def test_surface_is_deterministic() -> None:
    a = oov_learning_invitation_surface("photosynthesis", IntentTag.DEFINITION)
    b = oov_learning_invitation_surface("photosynthesis", IntentTag.DEFINITION)
    assert a == b
    assert a is not None


def test_surface_includes_explicit_intent_name() -> None:
    for tag, expected_token in [
        (IntentTag.DEFINITION, "definition"),
        (IntentTag.CAUSE, "cause"),
        (IntentTag.VERIFICATION, "verification"),
        (IntentTag.PROCEDURE, "procedure"),
    ]:
        surface = oov_learning_invitation_surface("xyzunknown", tag)
        assert surface is not None
        assert f"(intent: {expected_token})" in surface


# ---------------------------------------------------------------------------
# Safety — user text is sanitised at the safe_display boundary
# ---------------------------------------------------------------------------


def test_control_characters_in_token_are_sanitised() -> None:
    surface = oov_learning_invitation_surface(
        "evil\x00\x07token", IntentTag.DEFINITION,
    )
    assert surface is not None
    # Control bytes must not survive — safe_display strips/escapes them.
    assert "\x00" not in surface
    assert "\x07" not in surface


# ---------------------------------------------------------------------------
# is_oov_for_packs predicate
# ---------------------------------------------------------------------------


def test_is_oov_for_packs_round_trips() -> None:
    assert is_oov_for_packs("photosynthesis") is True
    assert is_oov_for_packs("light") is False
    assert is_oov_for_packs("parent") is False
    assert is_oov_for_packs("") is False
    assert is_oov_for_packs("   ") is False


# ---------------------------------------------------------------------------
# Live runtime — OOV converts cliff into gradient
# ---------------------------------------------------------------------------


def test_runtime_definition_on_oov_emits_invitation() -> None:
    rt = ChatRuntime()
    resp = rt.chat("What is photosynthesis?")
    assert resp.grounding_source == "oov"
    assert "photosynthesis" in resp.surface
    assert "PackMutationProposal" in resp.surface


def test_runtime_cause_on_oov_emits_invitation() -> None:
    """A CAUSE prompt on an OOV subject must hit the OOV branch, not
    fall through to the universal disclosure.  Previously these went
    silent because the CAUSE/VERIFICATION branch early-returned None
    when no teaching chain existed."""
    rt = ChatRuntime()
    resp = rt.chat("Why does mitochondria exist?")
    assert resp.grounding_source == "oov"
    assert "mitochondria" in resp.surface


def test_runtime_known_subject_still_grounds_pack() -> None:
    """Known cognition lemmas still ground through the pack path —
    OOV branch is a fall-through only, not a replacement."""
    rt = ChatRuntime()
    resp = rt.chat("What is light?")
    assert resp.grounding_source == "pack"
    assert "light" in resp.surface


def test_runtime_known_subject_still_grounds_teaching() -> None:
    """Reviewed teaching chains still route through teaching-grounded."""
    rt = ChatRuntime()
    resp = rt.chat("Why does parent exist?")
    assert resp.grounding_source == "teaching"
    assert "parent" in resp.surface


def test_runtime_unknown_intent_still_emits_universal_disclosure() -> None:
    """If the classifier returns UNKNOWN intent, there is no clean
    subject to invite an operator to teach.  Universal disclosure
    remains the right fall-through."""
    rt = ChatRuntime()
    resp = rt.chat("Define mitochondria.")  # classifier returns UNKNOWN here
    # Either UNKNOWN intent → universal disclosure ("none"), OR if
    # the classifier improves to read "Define mitochondria." as
    # DEFINITION the prompt should switch to OOV invitation.  Both
    # are acceptable.
    assert resp.grounding_source in {"none", "oov"}

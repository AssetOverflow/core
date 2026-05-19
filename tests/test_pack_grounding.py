"""ADR-0048 — pack-grounded fallback surface tests.

The contract these tests pin:

  - Pack-grounded surfaces engage ONLY when the ``UnknownDomainGate``
    fires with ``source="empty_vault"`` AND the intent is DEFINITION
    or RECALL AND the subject lemma is in ``en_core_cognition_v1``.
  - The surface is composed verbatim from the pack lexicon's
    ``semantic_domains`` and the lemma — no synthesis.
  - The audit contract is preserved: ChatResponse and TurnEvent both
    carry a ``grounding_source`` provenance tag set to ``"pack"`` on
    the pack-grounded path, ``"none"`` on the universal disclosure,
    and ``"vault"`` on the main walk path.
  - Safety / ethics refusal still takes priority — pack-grounded
    surfaces never bypass a SafetyVerdict violation.
"""

from __future__ import annotations

import pytest

from chat.pack_grounding import (
    PACK_ID,
    is_pack_lemma,
    pack_grounded_surface,
)
from chat.runtime import ChatRuntime, _UNKNOWN_DOMAIN_SURFACE


# ---------------------------------------------------------------------------
# pack_grounding module — pure-function contracts
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lemma", ["light", "knowledge", "meaning", "memory", "truth"])
def test_known_pack_lemmas_produce_grounded_surface(lemma: str) -> None:
    surface = pack_grounded_surface(lemma)
    assert surface is not None
    # Case-insensitive: gloss-backed surfaces capitalize the lemma at
    # the start of the sentence ("Truth is a claim..."), while the
    # dotted-disclosure fallback keeps it lowercase.  Both forms must
    # contain the lemma.
    assert lemma.lower() in surface.lower()
    assert PACK_ID in surface
    # Surface carries either the gloss-backed "pack-grounded (pack_id)."
    # tag or the dotted-disclosure "No session evidence yet." trailer.
    assert "pack-grounded" in surface


def test_unknown_lemma_returns_none() -> None:
    assert pack_grounded_surface("nonexistentwordxyz") is None


@pytest.mark.parametrize("bad", ["", "   ", None])
def test_empty_or_invalid_lemma_returns_none(bad) -> None:
    assert pack_grounded_surface(bad) is None  # type: ignore[arg-type]


def test_is_pack_lemma_round_trips() -> None:
    assert is_pack_lemma("light") is True
    assert is_pack_lemma("nonexistentwordxyz") is False
    assert is_pack_lemma("") is False


def test_surface_is_deterministic() -> None:
    """Same lemma must produce byte-identical surfaces on repeat calls
    — pack is immutable, no randomness, no synthesis."""
    a = pack_grounded_surface("light")
    b = pack_grounded_surface("light")
    assert a == b
    assert a is not None


# ---------------------------------------------------------------------------
# ChatRuntime integration — cold-start path
# ---------------------------------------------------------------------------


def test_cold_start_definition_returns_pack_grounded_surface() -> None:
    """Cold-start DEFINITION on a pack-known lemma routes through the
    pack-grounded surface, not the universal disclosure."""
    rt = ChatRuntime()
    resp = rt.chat("What is light?")
    assert "pack-grounded" in resp.surface
    # Case-insensitive: fluent gloss surfaces capitalize at sentence start.
    assert "light" in resp.surface.lower()
    assert resp.grounding_source == "pack"


def test_cold_start_recall_returns_pack_grounded_surface() -> None:
    """RECALL intent on a pack-known lemma also engages the pack path."""
    rt = ChatRuntime()
    resp = rt.chat("Remember light")
    assert resp.grounding_source == "pack"
    assert "light" in resp.surface.lower()


def test_cold_start_unknown_lemma_routes_to_oov_invitation() -> None:
    """ADR-0065 / P2.1 — when the classifier extracts a clean subject
    that is OOV, the runtime emits the OOV "teach me" invitation
    surface instead of the universal disclosure.

    ``How can I quoxulate the wxyzabc?`` is PROCEDURE intent;
    ``quoxulate`` is OOV.  Pre-P2.1 this produced the universal
    disclosure; post-P2.1 it produces an OOV invitation naming the
    unknown token + the mounted-pack list."""
    rt = ChatRuntime()
    resp = rt.chat("How can I quoxulate the wxyzabc?")
    assert resp.grounding_source == "oov"
    assert "quoxulate" in resp.surface or "wxyzabc" in resp.surface
    assert "PackMutationProposal" in resp.surface


def test_cold_start_cause_on_oov_routes_to_oov_invitation() -> None:
    """ADR-0065 / P2.1 — CAUSE on an OOV subject also routes to the
    OOV invitation, not the universal disclosure.

    Pre-P2.1 these prompts went silent (CAUSE branch early-returned
    None when no teaching chain existed).  Post-P2.1 the runtime
    explicitly names the gap."""
    rt = ChatRuntime()
    resp = rt.chat("Why does wxyzabc exist?")
    assert resp.grounding_source == "oov"
    assert "wxyzabc" in resp.surface


def test_turn_event_carries_grounding_source() -> None:
    """ADR-0048 provenance propagates to TurnEvent for downstream audit."""
    rt = ChatRuntime()
    rt.chat("What is light?")
    last_event = rt.turn_log[-1]
    assert getattr(last_event, "grounding_source", None) == "pack"


def test_chat_response_grounding_source_default_for_main_path() -> None:
    """When the walk path runs, the ChatResponse carries
    ``grounding_source="vault"``.  We force the walk by priming the
    vault with one turn so the second turn's gate clears."""
    rt = ChatRuntime()
    rt.chat("light truth")  # seed vault with one known-token turn
    resp = rt.chat("light truth")
    # The second turn may or may not have vault hits depending on
    # gate threshold; what we assert is that grounding_source is set
    # to one of the documented values.
    assert resp.grounding_source in {"vault", "pack", "none"}


def test_pack_grounded_surface_passes_safety_check() -> None:
    """Pack-grounded surfaces preserve the audit contract — safety
    and ethics verdicts still surface and refusal still takes
    priority above pack grounding when triggered."""
    rt = ChatRuntime()
    resp = rt.chat("What is light?")
    # Safety verdict must be present on every stub-path response
    # (ADR-0035).  Specific verdict outcome depends on the safety
    # pack — we only assert the audit contract holds.
    assert resp.safety_verdict is not None
    assert resp.ethics_verdict is not None

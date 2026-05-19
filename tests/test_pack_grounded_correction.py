"""ADR-0053 — pack-grounded CORRECTION acknowledgement tests.

Contract pinned here:

  - ``pack_grounded_correction_surface()`` returns a deterministic
    surface composed entirely of: the literal token ``correction``,
    verbatim ``semantic_domains`` strings from the pack, and a fixed
    template (``"correction received — pack-grounded ({pack_id}): ...
    No prior turn in this session to correct yet."``).
  - The cold-start CORRECTION intent routes through this branch in
    ``_maybe_pack_grounded_surface`` and emits the acknowledgement
    surface with ``grounding_source="pack"``.
  - Distinct from DEFINITION-of-correction: the CORRECTION
    acknowledgement explicitly notes the missing prior turn.
  - Refusal still takes priority — CORRECTION acknowledgement never
    bypasses a SafetyVerdict violation.
"""

from __future__ import annotations

import pytest

from chat.pack_grounding import (
    PACK_ID,
    pack_grounded_correction_surface,
)
from chat.runtime import ChatRuntime, _UNKNOWN_DOMAIN_SURFACE


# ---------------------------------------------------------------------------
# pack_grounded_correction_surface — pure-function contract
# ---------------------------------------------------------------------------


def test_correction_surface_is_returned() -> None:
    surface = pack_grounded_correction_surface()
    assert surface is not None


def test_correction_surface_contains_literal_correction() -> None:
    surface = pack_grounded_correction_surface()
    assert surface is not None
    assert "correction" in surface


def test_correction_surface_names_pack_id() -> None:
    surface = pack_grounded_correction_surface()
    assert surface is not None
    assert PACK_ID in surface


def test_correction_surface_marks_missing_prior_turn() -> None:
    """The CORRECTION acknowledgement must be distinct from the
    DEFINITION-of-correction surface: it explicitly states there is no
    prior turn in this session to correct."""
    surface = pack_grounded_correction_surface()
    assert surface is not None
    assert "No prior turn in this session to correct yet." in surface
    # Must NOT use the DEFINITION-style trailing disclosure:
    assert "No session evidence yet." not in surface


def test_correction_surface_is_deterministic() -> None:
    a = pack_grounded_correction_surface()
    b = pack_grounded_correction_surface()
    assert a == b


def test_correction_surface_atoms_are_verbatim_from_pack() -> None:
    """Every visible non-template token must be either the literal
    ``"correction"`` or a verbatim ``semantic_domains`` string from
    the pack — no synthesis."""
    from chat.pack_grounding import _pack_index

    surface = pack_grounded_correction_surface()
    assert surface is not None

    index = _pack_index()
    domains = index["correction"][:3]
    for domain in domains:
        assert domain in surface


# ---------------------------------------------------------------------------
# ChatRuntime integration — cold-start CORRECTION path
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "prompt",
    [
        "No, that's wrong",
        "No, correction means reviewed repair",
        "Actually, truth requires evidence",
        "Incorrect",
        "correction: that needs review",
    ],
)
def test_cold_start_correction_routes_through_pack_grounded(prompt: str) -> None:
    rt = ChatRuntime()
    resp = rt.chat(prompt)
    assert resp.grounding_source == "pack"
    assert "correction" in resp.surface
    assert "No prior turn in this session to correct yet." in resp.surface


def test_correction_does_not_use_universal_disclosure() -> None:
    rt = ChatRuntime()
    resp = rt.chat("No, that's wrong")
    assert resp.surface != _UNKNOWN_DOMAIN_SURFACE


def test_turn_event_carries_grounding_source_on_correction() -> None:
    rt = ChatRuntime()
    rt.chat("No, that's wrong")
    last_event = rt.turn_log[-1]
    assert getattr(last_event, "grounding_source", None) == "pack"


def test_correction_pack_grounded_passes_verdict_audit() -> None:
    rt = ChatRuntime()
    resp = rt.chat("No, that's wrong")
    assert resp.safety_verdict is not None
    assert resp.ethics_verdict is not None


# ---------------------------------------------------------------------------
# Doctrine — distinct from DEFINITION-of-correction
# ---------------------------------------------------------------------------


def test_correction_surface_distinct_from_definition_of_correction() -> None:
    """Compare ``"What is correction?"`` (DEFINITION) vs ``"No, that's
    wrong"`` (CORRECTION).  Both go through the pack-grounded branch
    but emit different surfaces — the CORRECTION acknowledgement
    notes the missing prior turn; the DEFINITION does not."""
    rt_def = ChatRuntime()
    def_resp = rt_def.chat("What is correction?")

    rt_corr = ChatRuntime()
    corr_resp = rt_corr.chat("No, that's wrong")

    assert def_resp.surface != corr_resp.surface
    # The CORRECTION acknowledgement carries its own template trailer
    # (still dotted-disclosure form — the correction composer is not
    # yet gloss-backed).  The DEFINITION surface is gloss-backed for
    # ``correction`` (cognition_v1 ships a gloss); we assert the
    # two paths produce distinct outputs without pinning the exact
    # DEFINITION trailer, which now varies between gloss-backed and
    # dotted-disclosure fallback forms.
    assert def_resp.grounding_source == "pack"
    assert "correction" in def_resp.surface.lower()
    assert "pack-grounded" in def_resp.surface
    assert "No prior turn in this session to correct yet." in corr_resp.surface

"""Step B-2 — surface the determination: the engine answers from accrued knowledge.

When a question turn is Determined over realized knowledge, the user-facing ``surface``
IS that answer (rendered honestly: "as I was told", never "verified"). The realizer's
``articulation_surface`` is retained as evidence — the determination is a selection, not
a rewrite. Undetermined and flag-off keep the default surface. This is the contract test
for the selection policy in docs/runtime_contracts.md.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from chat.runtime import ChatRuntime
from core.config import RuntimeConfig
from generate.determine import Determined, render_determination


# --------------------------------------------------------------------------- #
# render_determination — deterministic, honest basis (unit, no runtime)
# --------------------------------------------------------------------------- #


def test_render_member_reads_naturally() -> None:
    d = Determined(answer=True, basis="as_told", predicate="member",
                   subject="truth", object="concept", grounds=())
    assert render_determination(d) == "Yes — as I was told, truth is a concept."


def test_render_relational_predicate_is_legible() -> None:
    d = Determined(answer=True, basis="as_told", predicate="parent_of",
                   subject="alice", object="bob", grounds=())
    assert render_determination(d) == "Yes — as I was told, alice parent of bob."


def test_render_basis_is_honest_never_overclaims() -> None:
    # SPECULATIVE grounds → "as I was told" (today's only case); COHERENT would be the
    # only thing that renders "verified". The render must never overclaim.
    as_told = Determined(True, "as_told", "member", "truth", "concept", ())
    assert "as I was told" in render_determination(as_told)
    assert "verified" not in render_determination(as_told)


# --------------------------------------------------------------------------- #
# Surface selection in the live turn (integration)
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def accrued_runtime() -> ChatRuntime:
    rt = ChatRuntime(
        config=replace(RuntimeConfig(), accrue_realized_knowledge=True),
        no_load_state=True,
    )
    rt.chat("Truth is a concept.")  # accrue the fact this module's questions probe
    return rt


def _default_surface(text: str) -> str:
    rt = ChatRuntime(config=RuntimeConfig(), no_load_state=True)
    rt.chat("Truth is a concept.")
    return rt.chat(text).surface


def test_determined_question_surfaces_the_answer(accrued_runtime) -> None:
    response = accrued_runtime.chat("Is truth a concept?")
    assert response.surface == "Yes — as I was told, truth is a concept."
    # the realizer surface is retained as evidence, distinct from the selection
    assert response.articulation_surface
    assert response.surface != response.articulation_surface


def test_determined_surface_does_not_rewrite_articulation(accrued_runtime) -> None:
    # The determination SELECTS the surface; the articulation_surface is the same
    # evidence the default (flag-off) turn produces.
    response = accrued_runtime.chat("Is truth a concept?")
    off = ChatRuntime(config=RuntimeConfig(), no_load_state=True)
    off.chat("Truth is a concept.")
    off_response = off.chat("Is truth a concept?")
    assert response.articulation_surface == off_response.articulation_surface


def test_undetermined_question_keeps_default_surface(accrued_runtime) -> None:
    response = accrued_runtime.chat("Is truth a virtue?")  # never told → Undetermined
    # not an affirmation; the honest default surface (== the flag-off surface)
    assert not response.surface.startswith("Yes — as I was told")
    assert response.surface == _default_surface("Is truth a virtue?")


def test_flag_off_never_surfaces_a_determination() -> None:
    surface = _default_surface("Is truth a concept?")
    assert not surface.startswith("Yes — as I was told")

from __future__ import annotations

from core.cognition.surface_resolution import resolve_surface


def test_runtime_canonical_surface_has_base_precedence() -> None:
    resolved = resolve_surface(
        canonical_surface="canonical",
        pre_decoration_surface="pre-decoration",
        response_surface="runtime",
        response_articulation_surface="articulation",
    )

    assert resolved.surface == "canonical"
    assert resolved.articulation_surface == "articulation"
    assert resolved.authority == "runtime_canonical"
    assert resolved.fold_sources == ()


def test_useful_realizer_replaces_prefix_when_gate_did_not_fire() -> None:
    resolved = resolve_surface(
        response_surface="runtime",
        response_articulation_surface="runtime articulation",
        realized_surface="realizer",
        realizer_useful=True,
        gate_fired=False,
    )

    assert resolved.surface == "realizer"
    assert resolved.articulation_surface == "realizer"
    assert resolved.authority == "realizer"


def test_gate_fired_keeps_runtime_surface_even_when_realizer_is_useful() -> None:
    resolved = resolve_surface(
        response_surface="runtime refusal",
        response_articulation_surface="runtime refusal articulation",
        realized_surface="realizer noise",
        realizer_useful=True,
        gate_fired=True,
    )

    assert resolved.surface == "runtime refusal"
    assert resolved.articulation_surface == "runtime refusal articulation"
    assert resolved.authority == "runtime"


def test_useless_realizer_keeps_runtime_surface() -> None:
    resolved = resolve_surface(
        response_surface="runtime",
        response_articulation_surface="runtime articulation",
        realized_surface="Truth is defined as ...",
        realizer_useful=False,
    )

    assert resolved.surface == "runtime"
    assert resolved.articulation_surface == "runtime articulation"
    assert resolved.authority == "runtime"


def test_walk_and_compose_fold_after_selected_authority() -> None:
    resolved = resolve_surface(
        response_surface="runtime",
        response_articulation_surface="runtime articulation",
        realized_surface="realizer",
        realizer_useful=True,
        walk_surface="walk chain",
        compose_surface="compose transfer",
    )

    assert resolved.surface == "realizer — walk chain — compose transfer"
    assert resolved.articulation_surface == "realizer — walk chain — compose transfer"
    assert resolved.authority == "realizer"
    assert resolved.fold_sources == ("walk", "compose")


def test_folds_stand_alone_when_base_surface_is_empty() -> None:
    resolved = resolve_surface(walk_surface="walk chain", compose_surface="compose transfer")

    assert resolved.surface == "walk chain — compose transfer"
    assert resolved.articulation_surface == "walk chain — compose transfer"
    assert resolved.authority == "runtime"
    assert resolved.fold_sources == ("walk", "compose")

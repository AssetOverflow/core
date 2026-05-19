"""``register_invariant_grounding`` — the load-bearing R3 invariant
(ADR-0070, Phase R3).

For every case in the cognition lane (public split), the following
must hold across ``register_pack_id`` ∈ {``None``,
``"default_neutral_v1"``, ``"terse_v1"``}:

* ``grounding_source`` is byte-identical
* ``trace_hash`` is byte-identical  (extends ADR-0069 invariant C)
* ``versor_closures`` (aggregate) is byte-identical

Surface text MAY differ between terse and the two null registers —
that is the entire point of R3.  Surface text MUST be byte-identical
between ``None`` and ``default_neutral_v1`` (ADR-0069 invariant B
re-asserted under R3 wiring).
"""

from __future__ import annotations

import pytest

from chat.runtime import ChatRuntime
from core.config import RuntimeConfig
from evals.run_cognition_eval import load_cases, run_eval


@pytest.fixture(scope="module")
def cases():
    return load_cases()


@pytest.fixture(scope="module")
def report_none(cases):
    return run_eval(cases, config=RuntimeConfig(register_pack_id=None))


@pytest.fixture(scope="module")
def report_neutral(cases):
    return run_eval(
        cases, config=RuntimeConfig(register_pack_id="default_neutral_v1"),
    )


@pytest.fixture(scope="module")
def report_terse(cases):
    return run_eval(
        cases, config=RuntimeConfig(register_pack_id="terse_v1"),
    )


@pytest.fixture(scope="module")
def report_convivial(cases):
    """register_pack_id='convivial_v1' — first marker-using register."""
    return run_eval(
        cases, config=RuntimeConfig(register_pack_id="convivial_v1"),
    )


def _by_id(report):
    return {c.case_id: c for c in report.cases}


@pytest.fixture(scope="module")
def grounding_by_register(cases):
    """Map ``register_pack_id → {prompt_index: (grounding_source, surface)}``.

    Built by calling ``ChatRuntime.chat()`` directly on every cognition
    case across all three registers.  ``grounding_source`` is a
    ChatResponse field, not an eval projection, so this fixture exists
    alongside ``report_*`` fixtures rather than replacing them.
    """
    register_configs = (
        ("none", RuntimeConfig(register_pack_id=None)),
        ("neutral", RuntimeConfig(register_pack_id="default_neutral_v1")),
        ("terse", RuntimeConfig(register_pack_id="terse_v1")),
        ("convivial", RuntimeConfig(register_pack_id="convivial_v1")),
    )
    out: dict[str, dict[int, tuple[str, str]]] = {}
    for label, cfg in register_configs:
        per_register: dict[int, tuple[str, str]] = {}
        for i, case in enumerate(cases):
            runtime = ChatRuntime(config=cfg)
            response = runtime.chat(case["prompt"])
            per_register[i] = (
                getattr(response, "grounding_source", "none"),
                response.surface,
            )
        out[label] = per_register
    return out


def test_grounding_source_invariant_across_registers(grounding_by_register):
    """grounding_source identical case-by-case across {None, neutral,
    terse, convivial}.

    This is the load-bearing R3/R4 invariant.  Register lives on the
    realizer side; grounding_source is decided before realizer is
    called; therefore it must not vary with register.
    """
    none_map = grounding_by_register["none"]
    neutral_map = grounding_by_register["neutral"]
    terse_map = grounding_by_register["terse"]
    convivial_map = grounding_by_register["convivial"]

    diffs: list[str] = []
    for idx in sorted(none_map):
        gs_none = none_map[idx][0]
        gs_neutral = neutral_map[idx][0]
        gs_terse = terse_map[idx][0]
        gs_convivial = convivial_map[idx][0]
        if not (gs_none == gs_neutral == gs_terse == gs_convivial):
            diffs.append(
                f"case[{idx}]: grounding_source diverged\n"
                f"  None      : {gs_none!r}\n"
                f"  neutral   : {gs_neutral!r}\n"
                f"  terse     : {gs_terse!r}\n"
                f"  convivial : {gs_convivial!r}"
            )
    assert not diffs, (
        "register_invariant_grounding violated — grounding_source "
        "diverged across registers. Register must not influence "
        "anything upstream of the realizer.\n\n" + "\n\n".join(diffs)
    )


def test_trace_hash_invariant_across_registers(
    report_none, report_neutral, report_terse, report_convivial,
):
    """trace_hash identical across all four registers (extends ADR-0069 inv C).

    Truth-path isolation: register lives on the realizer side and
    must not move a single bit of the trace hash.
    """
    none_by_id = _by_id(report_none)
    neutral_by_id = _by_id(report_neutral)
    terse_by_id = _by_id(report_terse)
    convivial_by_id = _by_id(report_convivial)

    diffs: list[str] = []
    for case_id in none_by_id:
        a = none_by_id[case_id].trace_hash
        b = neutral_by_id[case_id].trace_hash
        c = terse_by_id[case_id].trace_hash
        d = convivial_by_id[case_id].trace_hash
        if not (a == b == c == d):
            diffs.append(
                f"{case_id}: trace_hash diverged\n"
                f"  None      : {a}\n"
                f"  neutral   : {b}\n"
                f"  terse     : {c}\n"
                f"  convivial : {d}"
            )
    assert not diffs, (
        "TRUTH-PATH LEAK — trace_hash differs across registers.\n\n"
        + "\n\n".join(diffs)
    )


def test_surface_byte_identical_none_vs_neutral(report_none, report_neutral):
    """ADR-0069 invariant B re-asserted at R3 (no regression from R2)."""
    none_by_id = _by_id(report_none)
    neutral_by_id = _by_id(report_neutral)
    diffs: list[str] = []
    for case_id, a in none_by_id.items():
        b = neutral_by_id[case_id]
        if a.surface != b.surface:
            diffs.append(
                f"{case_id}: None vs neutral surface diverged\n"
                f"  None    : {a.surface!r}\n"
                f"  neutral : {b.surface!r}"
            )
    assert not diffs, (
        "Invariant B regression at R3 — None ≢ default_neutral_v1.\n\n"
        + "\n\n".join(diffs)
    )


def test_aggregate_metrics_invariant_none_neutral(
    report_none, report_neutral,
):
    """None ≡ neutral — every aggregate metric matches."""
    assert report_none.total == report_neutral.total
    assert report_none.intent_correct == report_neutral.intent_correct
    assert report_none.terms_captured == report_neutral.terms_captured
    assert report_none.terms_expected == report_neutral.terms_expected
    assert report_none.surface_grounded == report_neutral.surface_grounded
    assert report_none.versor_closures == report_neutral.versor_closures


def test_versor_closures_invariant_across_registers(
    report_none, report_neutral, report_terse, report_convivial,
):
    """Versor closure rate is a property of the truth path; register
    must not change it."""
    assert (
        report_none.versor_closures
        == report_neutral.versor_closures
        == report_terse.versor_closures
        == report_convivial.versor_closures
    )


def test_intent_correct_invariant_across_registers(
    report_none, report_neutral, report_terse, report_convivial,
):
    """Intent classification runs before realizer — register has no
    business changing it."""
    assert (
        report_none.intent_correct
        == report_neutral.intent_correct
        == report_terse.intent_correct
        == report_convivial.intent_correct
    )


def test_terse_diverges_somewhere_or_pack_content_warns(
    grounding_by_register,
):
    """Terse should produce at least one different surface vs neutral.

    If every surface is identical, the R3 knob is vacuous against the
    current cognition lane content (no without-gloss disclosure case
    reaches it).  Skip with a clear message rather than fail —
    content coverage is a separate concern from architectural seam.
    """
    neutral_map = grounding_by_register["neutral"]
    terse_map = grounding_by_register["terse"]
    divergences = [
        idx for idx in neutral_map
        if neutral_map[idx][1] != terse_map[idx][1]
    ]
    if not divergences:
        pytest.skip(
            "no terse-vs-neutral surface divergence detected — "
            "cognition lane does not currently exercise the "
            "without-gloss disclosure path on any case (R3 knob is "
            "vacuous against current content)."
        )

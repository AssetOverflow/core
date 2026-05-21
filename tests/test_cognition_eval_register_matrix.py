"""Full 7-register invariant matrix on the cognition lane (Option 3 CI gate).

Pins the ADR-0072 invariant across every ratified register pack
simultaneously. Strict superset of
``tests/test_register_invariant_grounding.py`` (which only covers
4 of the 7 ratified registers): each of the seven ratified packs is
treated as a parametrized variant, and every per-case projection the
eval reports is asserted byte-identical against the unregistered
(``None``) baseline.

Load-bearing claims pinned:

  cognition_eval_register_matrix:
    For every cognition case AND every ratified register pack:
      * ``trace_hash`` byte-identical to baseline
      * ``intent_correct`` byte-identical to baseline
      * ``terms_captured`` byte-identical to baseline
      * ``surface_contains_pass`` byte-identical to baseline
      * ``versor_closure`` byte-identical to baseline
      * ``versor_condition`` byte-identical to baseline
    Aggregate metrics on the eval report:
      * ``intent_correct`` (count) byte-identical to baseline
      * ``terms_captured`` (count) byte-identical to baseline
      * ``terms_expected`` (count) byte-identical to baseline
      * ``surface_grounded`` (count) byte-identical to baseline
      * ``versor_closures`` (count) byte-identical to baseline
      * ``total`` byte-identical to baseline

Why this gate exists.  We are about to materialise 93 drafted register
packs from ``packs/register/_catalog.json``.  Before any new pack
lands, this gate proves the seven existing ratified packs are
collectively well-behaved against the cognition eval — i.e. the
ADR-0072 invariant is not a per-pack accident but a structural
guarantee.  Every drafted pack added later must extend this matrix
(see ``_RATIFIED_REGISTERS`` below) and the gate must stay green.

Note on surfaces.  ``CognitiveTurnResult.surface`` is the pre-
decoration / pre-substantive composer output — the truth-path field
``compute_trace_hash`` consumes.  Substantive register transforms
(seeded markers, semantic-domain-clause appends, gloss compression)
are applied on the *post-canonical* surface stored on
``ChatRuntime.turn_log[-1].surface``.  Therefore ``result.surface``
is expected to be byte-identical across registers too — the post-
decoration variation is asserted by the existing register-tour gate
(``evals/register_tour/run_tour.py`` + ``tests/test_register_tour_demo.py``).
"""

from __future__ import annotations

import pytest

from core.config import RuntimeConfig
from evals.run_cognition_eval import load_cases, run_eval


# The seven ratified register packs on disk.  When a drafted pack
# from ``packs/register/_catalog.json`` is ratified, append its
# ``register_id`` here.  The matrix grows; the invariant doesn't bend.
_RATIFIED_REGISTERS: tuple[str, ...] = (
    "default_neutral_v1",
    "terse_v1",
    "convivial_v1",
    "pedagogical_v1",
    "precise_v1",
    "formal_v1",
    "socratic_v1",
    "succinct_v1",
    "expansive_v1",
    "exhaustive_v1",
    "warm_v1",
    "cool_v1",
    "casual_v1",
    "intense_v1",
    "playful_v1",
    "calm_v1",
    "urgent_v1",
    "serene_v1",
    "dramatic_v1",
    "sober_v1",
    "clinical_v1",
    "colloquial_v1",
    "literary_v1",
    "journalistic_v1",
    "poetic_v1",
    "assertive_v1",
    "hedged_v1",
    "inviting_v1",
    "exploratory_v1",
    "didactic_v1",
    "dialectic_v1",
    "probing_v1",
    "affirming_v1",
    "curious_v1",
    "skeptical_v1",
    "confident_uncertain_v1",
    "peer_v1",
    "mentor_v1",
    "student_v1",
    "expert_v1",
    "scholar_v1",
    "practitioner_v1",
    "novice_v1",
    "narrator_v1",
    "journalist_v1",
    "elder_v1",
    "academic_v1",
    "conversational_v1",
    "executive_v1",
    "technical_v1",
    "legal_v1",
    "medical_v1",
    "scientific_v1",
    "philosophical_v1",
    "devotional_v1",
    "mathematical_v1",
    "engineering_v1",
    "plainspoken_v1",
    "cosmopolitan_v1",
    "diplomatic_v1",
    "blunt_v1",
    "aristocratic_v1",
    "folksy_v1",
    "urbane_v1",
    "timeless_v1",
    "contemporary_v1",
    "classic_v1",
    "neoteric_v1",
    "lyrical_v1",
    "cheerful_v1",
    "somber_v1",
    "melancholic_v1",
    "awed_v1",
    "grave_v1",
    "light_v1",
    "wry_v1",
    "dry_v1",
    "gentle_v1",
    "earnest_v1",
    "documentary_v1",
    "instructional_v1",
    "persuasive_v1",
    "conciliatory_v1",
    "clarifying_v1",
    "summarizing_v1",
    "critiquing_v1",
    "comparing_v1",
    "elaborating_v1",
    "exemplifying_v1",
    "tutorial_v1",
    "interview_v1",
    "briefing_v1",
    "deposition_v1",
    "lecture_v1",
    "memo_v1",
    "review_v1",
    "story_v1",
    "elegy_v1",
    "epigram_v1",
    "manifesto_v1",
)


@pytest.fixture(scope="module")
def cases():
    return load_cases()


@pytest.fixture(scope="module")
def baseline_report(cases):
    """Unregistered baseline — every register must match this case-for-case."""
    return run_eval(cases, config=RuntimeConfig(register_pack_id=None))


@pytest.fixture(scope="module")
def baseline_by_id(baseline_report):
    return {c.case_id: c for c in baseline_report.cases}


@pytest.fixture(scope="module", params=_RATIFIED_REGISTERS)
def register_report(request, cases):
    """One eval report per ratified register pack."""
    return (request.param, run_eval(
        cases, config=RuntimeConfig(register_pack_id=request.param),
    ))


def _by_id(report):
    return {c.case_id: c for c in report.cases}


def _diff_rows(register_id: str, baseline_by_id, register_by_id, field: str):
    rows: list[str] = []
    for case_id, base in baseline_by_id.items():
        var = register_by_id[case_id]
        a = getattr(base, field)
        b = getattr(var, field)
        if a != b:
            rows.append(
                f"  {case_id}: {field} diverged under {register_id!r}\n"
                f"    baseline : {a!r}\n"
                f"    register : {b!r}"
            )
    return rows


def test_register_matrix_trace_hash_invariant(
    register_report, baseline_by_id,
):
    """``trace_hash`` byte-identical case-by-case under every ratified register.

    This is the load-bearing ADR-0072 truth-path-isolation claim.  A
    single divergence here means a register pack is leaking into the
    truth path — the entire register subsystem is invalid until fixed.
    """
    register_id, report = register_report
    rows = _diff_rows(
        register_id, baseline_by_id, _by_id(report), "trace_hash",
    )
    assert not rows, (
        f"TRUTH-PATH LEAK under register {register_id!r} — trace_hash "
        "must not vary across the register axis.\n" + "\n".join(rows)
    )


def test_register_matrix_intent_correct_invariant(
    register_report, baseline_by_id,
):
    """Intent classification runs upstream of the realizer; register
    cannot move it."""
    register_id, report = register_report
    rows = _diff_rows(
        register_id, baseline_by_id, _by_id(report), "intent_correct",
    )
    assert not rows, (
        f"UPSTREAM LEAK under register {register_id!r} — intent "
        "classification cannot depend on register.\n" + "\n".join(rows)
    )


def test_register_matrix_terms_captured_invariant(
    register_report, baseline_by_id,
):
    """Eval-scored ``terms_captured`` is computed off the pre-
    decoration / canonical surface; register must not perturb it."""
    register_id, report = register_report
    rows = _diff_rows(
        register_id, baseline_by_id, _by_id(report), "terms_captured",
    )
    assert not rows, (
        f"GROUNDING METRIC LEAK under register {register_id!r} — "
        "terms_captured varies across registers.\n" + "\n".join(rows)
    )


def test_register_matrix_surface_contains_pass_invariant(
    register_report, baseline_by_id,
):
    """``surface_contains_pass`` scored off canonical surface — must
    not vary by register."""
    register_id, report = register_report
    rows = _diff_rows(
        register_id, baseline_by_id, _by_id(report),
        "surface_contains_pass",
    )
    assert not rows, (
        f"GROUNDING METRIC LEAK under register {register_id!r} — "
        "surface_contains_pass varies across registers.\n"
        + "\n".join(rows)
    )


def test_register_matrix_versor_closure_invariant(
    register_report, baseline_by_id,
):
    """``versor_condition < 1e-6`` is a property of the truth path."""
    register_id, report = register_report
    rows = _diff_rows(
        register_id, baseline_by_id, _by_id(report), "versor_closure",
    )
    assert not rows, (
        f"FIELD INVARIANT DRIFT under register {register_id!r} — "
        "versor_closure varies across registers.\n" + "\n".join(rows)
    )


def test_register_matrix_versor_condition_byte_identical(
    register_report, baseline_by_id,
):
    """Stronger than closure: the exact ``versor_condition`` float
    must be byte-identical.  Catches drift below the closure
    threshold that closure-only would miss."""
    register_id, report = register_report
    rows = _diff_rows(
        register_id, baseline_by_id, _by_id(report), "versor_condition",
    )
    assert not rows, (
        f"FIELD STATE LEAK under register {register_id!r} — "
        "versor_condition is not byte-identical.\n" + "\n".join(rows)
    )


def test_register_matrix_canonical_surface_byte_identical(
    register_report, baseline_by_id,
):
    """``CognitiveTurnResult.surface`` is the pre-decoration /
    canonical composer output (the truth-path field
    ``compute_trace_hash`` consumes).  Substantive register transforms
    apply downstream on ``turn_log[-1].surface``; the canonical
    must remain byte-identical across the register axis.

    If this test ever fails for a non-null register, the substantive
    transform has leaked into the canonical surface and the
    truth-path-isolation contract is broken.
    """
    register_id, report = register_report
    rows = _diff_rows(
        register_id, baseline_by_id, _by_id(report), "surface",
    )
    assert not rows, (
        f"CANONICAL SURFACE LEAK under register {register_id!r} — "
        "substantive transforms have escaped into the pre-decoration "
        "surface that feeds compute_trace_hash.\n" + "\n".join(rows)
    )


def test_register_matrix_aggregate_metrics_byte_identical(
    register_report, baseline_report,
):
    """Every aggregate count on the eval report matches baseline."""
    register_id, report = register_report
    deltas: list[str] = []
    for field in (
        "total",
        "intent_correct",
        "terms_captured",
        "terms_expected",
        "surface_grounded",
        "versor_closures",
    ):
        a = getattr(baseline_report, field)
        b = getattr(report, field)
        if a != b:
            deltas.append(
                f"  {field}: baseline={a} register({register_id})={b}"
            )
    assert not deltas, (
        f"AGGREGATE METRIC DRIFT under register {register_id!r} — "
        "ADR-0072 aggregate-invariant claim violated.\n"
        + "\n".join(deltas)
    )


def test_register_matrix_covers_every_ratified_pack():
    """Meta-test: the parametrized matrix must cover exactly the
    set of ratified register packs on disk.  When a drafted pack is
    ratified, both ``scripts/ratify_register_packs.py::REGISTER_IDS``
    AND this file's ``_RATIFIED_REGISTERS`` must be widened together.
    """
    from scripts.ratify_register_packs import REGISTER_IDS

    matrix = set(_RATIFIED_REGISTERS)
    script = set(REGISTER_IDS)
    only_in_matrix = matrix - script
    only_in_script = script - matrix
    assert not only_in_matrix and not only_in_script, (
        "Register-matrix drift: the ratified register set and the "
        "test matrix have diverged.\n"
        f"  only in matrix : {sorted(only_in_matrix)}\n"
        f"  only in script : {sorted(only_in_script)}\n"
        "When ratifying a new register pack, widen "
        "scripts/ratify_register_packs.py::REGISTER_IDS AND "
        "tests/test_cognition_eval_register_matrix.py::_RATIFIED_REGISTERS "
        "in the same change."
    )

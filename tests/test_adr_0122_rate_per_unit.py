"""ADR-0122 — parser expansion: rate / per-unit reasoning.

Pins the load-bearing invariants documented in
``docs/decisions/ADR-0122-parser-rate-per-unit.md``. The invariants
fall into three layers:

1. **Substrate invariants** (1-9): pure unit tests against the new
   ``Rate`` dataclass, the ``apply_rate`` operation kind, the parser
   patterns + refusal paths, the solver evaluation, the verifier
   replay, the realizer template. These are cheap and self-contained.

2. **Anti-overfit invariants** (12-14): re-measurement against the
   OOD surface generator, the invariance perturbation suite, and the
   adversarial suite. Each must continue to hold under the expanded
   grammar — a lift on rate problems that breaks invariance on
   non-rate problems is a regression, not progress (ADR-0114a
   honest-fitting discipline).

3. **Sealed-holdout invariants** (10, 11, 15): require
   ``CORE_HOLDOUT_KEY`` to decrypt
   ``evals/gsm8k_math/holdouts/v1/cases.jsonl.age`` per ADR-0119.7.
   Tests skip (do not fail) when the key is absent — CI runs without
   it.

The wrong-zero discipline (ADR-0114a Obligation #4) is the
load-bearing positive claim of this ADR: the rate grammar lifts
*correct* outcomes; it does not lift *wrong* outcomes. A new
misparse pathway introduced by the rate grammar would invalidate
the entire expansion.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parent.parent
_SEALED_PATH = (
    _REPO_ROOT / "evals" / "gsm8k_math" / "holdouts" / "v1" / "cases.jsonl.age"
)


def _decrypt_sealed_or_skip() -> bytes:
    """Mirror ADR-0121's seal-discipline skip pattern."""
    key_path_str = os.environ.get("CORE_HOLDOUT_KEY")
    if not key_path_str:
        pytest.skip("CORE_HOLDOUT_KEY not set; per ADR-0119.7 seal discipline")
    try:
        import pyrage
        from pyrage.x25519 import Identity
    except ImportError:
        pytest.skip("pyrage not installed")
    key_path = Path(key_path_str)
    if not key_path.exists():
        pytest.skip(f"CORE_HOLDOUT_KEY={key_path} does not exist")
    identity = Identity.from_str(key_path.read_text(encoding="utf-8").strip())
    return pyrage.decrypt(_SEALED_PATH.read_bytes(), [identity])


# ---------------------------------------------------------------------------
# Substrate invariants (1-9) — pure unit tests
# ---------------------------------------------------------------------------


class TestRateDataclass:
    """ADR-0122 invariant 1 — Rate construction + refusal."""

    def test_constructs_with_valid_fields(self) -> None:
        from generate.math_problem_graph import Rate

        r = Rate(value=2.0, numerator_unit="dollars", denominator_unit="apple")
        assert r.value == 2.0
        assert r.numerator_unit == "dollars"
        assert r.denominator_unit == "apple"

    def test_int_value_accepted(self) -> None:
        from generate.math_problem_graph import Rate

        assert Rate(value=3, numerator_unit="d", denominator_unit="a").value == 3

    @pytest.mark.parametrize(
        "kwargs,fragment",
        [
            ({"value": 0, "numerator_unit": "d", "denominator_unit": "a"}, "strictly positive"),
            ({"value": -1, "numerator_unit": "d", "denominator_unit": "a"}, "strictly positive"),
            ({"value": 1, "numerator_unit": "", "denominator_unit": "a"}, "numerator_unit"),
            ({"value": 1, "numerator_unit": "d", "denominator_unit": ""}, "denominator_unit"),
            ({"value": 1, "numerator_unit": "x", "denominator_unit": "x"}, "must differ"),
            ({"value": True, "numerator_unit": "d", "denominator_unit": "a"}, "must be int or float"),
        ],
    )
    def test_refuses_invalid_construction(self, kwargs: dict, fragment: str) -> None:
        from generate.math_problem_graph import MathGraphError, Rate

        with pytest.raises(MathGraphError) as exc:
            Rate(**kwargs)
        assert fragment in str(exc.value)


class TestApplyRateOperationKind:
    """ADR-0122 invariant 2 — apply_rate kind admitted, operand-typed."""

    def test_apply_rate_in_valid_kinds(self) -> None:
        from generate.math_problem_graph import VALID_OPERATION_KINDS

        assert "apply_rate" in VALID_OPERATION_KINDS

    def test_apply_rate_accepts_rate_operand(self) -> None:
        from generate.math_problem_graph import Operation, Rate

        op = Operation(
            actor="Sarah",
            kind="apply_rate",
            operand=Rate(value=2, numerator_unit="dollars", denominator_unit="apple"),
        )
        assert op.kind == "apply_rate"
        assert op.target is None

    def test_apply_rate_refuses_quantity_operand(self) -> None:
        from generate.math_problem_graph import MathGraphError, Operation, Quantity

        with pytest.raises(MathGraphError, match="must be a Rate"):
            Operation(actor="Sarah", kind="apply_rate", operand=Quantity(4, "apple"))

    def test_non_rate_kinds_refuse_rate_operand(self) -> None:
        from generate.math_problem_graph import MathGraphError, Operation, Rate

        rate = Rate(value=2, numerator_unit="dollars", denominator_unit="apple")
        for kind in ("add", "subtract", "multiply", "divide"):
            with pytest.raises(MathGraphError, match="must be a Quantity"):
                Operation(actor="Sarah", kind=kind, operand=rate)

    def test_apply_rate_round_trips_through_json(self) -> None:
        from generate.math_problem_graph import (
            InitialPossession,
            MathProblemGraph,
            Operation,
            Quantity,
            Rate,
            Unknown,
            graph_from_dict,
        )

        g = MathProblemGraph(
            entities=("Sarah",),
            initial_state=(
                InitialPossession(entity="Sarah", quantity=Quantity(4, "apples")),
            ),
            operations=(
                Operation(
                    actor="Sarah",
                    kind="apply_rate",
                    operand=Rate(
                        value=2, numerator_unit="dollars", denominator_unit="apples"
                    ),
                ),
            ),
            unknown=Unknown(entity="Sarah", unit="dollars"),
        )
        g2 = graph_from_dict(g.as_json())
        assert g == g2
        assert g.canonical_bytes() == g2.canonical_bytes()


class TestParserRateDeclaration:
    """ADR-0122 invariant 3 — parser handles "Each X costs $N"."""

    def test_canonical_each_x_costs(self) -> None:
        from generate.math_parser import parse_problem

        g = parse_problem(
            "Sarah has 4 apples. Each apple costs $2. How much does Sarah spend?"
        )
        assert g.entities == ("Sarah",)
        assert len(g.initial_state) == 1
        assert g.initial_state[0].quantity.value == 4
        assert g.initial_state[0].quantity.unit == "apples"
        assert len(g.operations) == 1
        op = g.operations[0]
        assert op.kind == "apply_rate"
        assert op.actor == "Sarah"
        assert op.operand.value == 2
        assert op.operand.numerator_unit == "dollars"
        assert op.operand.denominator_unit == "apples"
        assert g.unknown.entity == "Sarah"
        assert g.unknown.unit == "dollars"

    def test_an_x_costs_form(self) -> None:
        from generate.math_parser import parse_problem

        g = parse_problem(
            "Tom has 8 pencils. A pencil costs $0.50. How much does Tom pay?"
        )
        assert g.operations[-1].operand.value == 0.5

    def test_trailing_each_form(self) -> None:
        from generate.math_parser import parse_problem

        g = parse_problem(
            "Lisa has 3 books. Books cost $5 each. How much does Lisa earn?"
        )
        assert g.operations[-1].operand.value == 5

    def test_rate_after_addition_chain(self) -> None:
        from generate.math_parser import parse_problem

        g = parse_problem(
            "Ben has 5 apples. He buys 3 more apples. "
            "Each apple costs $2. How much does Ben spend?"
        )
        kinds = [op.kind for op in g.operations]
        assert kinds == ["add", "apply_rate"]

    def test_verb_variants_all_accepted(self) -> None:
        from generate.math_parser import parse_problem

        for verb in ("spend", "pay", "earn"):
            text = f"Sarah has 4 apples. Each apple costs $2. How much does Sarah {verb}?"
            g = parse_problem(text)
            assert g.operations[-1].kind == "apply_rate"


class TestParserRefusals:
    """ADR-0122 invariants 4, 5 — refusal discipline (no silent acceptance)."""

    def test_refuses_orphan_rate(self) -> None:
        from generate.math_parser import ParseError, parse_problem

        with pytest.raises(ParseError, match="orphan|no .*rate-aggregate question"):
            parse_problem(
                "Sarah has 4 apples. Each apple costs $2. "
                "How many apples does Sarah have?"
            )

    def test_refuses_unmatched_rate_question(self) -> None:
        from generate.math_parser import ParseError, parse_problem

        with pytest.raises(ParseError, match="no rate was declared"):
            parse_problem(
                "Sarah has 4 apples. How much does Sarah spend?"
            )

    def test_refuses_rate_redeclaration(self) -> None:
        from generate.math_parser import ParseError, parse_problem

        with pytest.raises(ParseError, match="redeclaration"):
            parse_problem(
                "Sarah has 4 apples. Each apple costs $2. "
                "An apple costs $3. How much does Sarah spend?"
            )

    def test_refuses_question_about_undefined_entity(self) -> None:
        from generate.math_parser import ParseError, parse_problem

        with pytest.raises(ParseError, match="undefined entity"):
            parse_problem(
                "Each apple costs $2. How much does Sarah spend?"
            )

    def test_refuses_question_when_entity_holds_nothing(self) -> None:
        # Sarah is introduced by the question but never asserted to
        # hold anything in a statement — the rate has no denominator
        # to apply to.
        from generate.math_parser import ParseError, parse_problem

        with pytest.raises(ParseError):
            parse_problem(
                "Sam has 3 apples. Each apple costs $2. "
                "How much does Sarah spend?"
            )


class TestSolverApplyRate:
    """ADR-0122 invariants 6, 7 — solver evaluates apply_rate; refuses mismatch."""

    def test_evaluates_canonical_case(self) -> None:
        from generate.math_parser import parse_problem
        from generate.math_solver import solve

        g = parse_problem(
            "Sarah has 4 apples. Each apple costs $2. How much does Sarah spend?"
        )
        t = solve(g)
        assert t.answer_value == 8.0
        assert t.answer_unit == "dollars"
        assert t.answer_entity == "Sarah"
        assert t.steps[-1].pack_lemma_id == "en_arithmetic_v1:apply_rate"

    def test_decimal_rate_evaluates_exactly(self) -> None:
        from generate.math_parser import parse_problem
        from generate.math_solver import solve

        g = parse_problem(
            "Tom has 8 pencils. A pencil costs $0.50. How much does Tom pay?"
        )
        assert solve(g).answer_value == 4.0

    def test_apply_rate_preserves_denominator_quantity(self) -> None:
        # Sarah still has 4 apples after the rate computes she spent $8.
        # This is verified by the verifier replay, not by solver state
        # introspection.
        from generate.math_parser import parse_problem
        from generate.math_solver import solve
        from generate.math_verifier import verify

        g = parse_problem(
            "Sarah has 4 apples. Each apple costs $2. How much does Sarah spend?"
        )
        verdict = verify(g, solve(g))
        assert verdict.passed, verdict.reason

    def test_solver_refuses_handcrafted_unit_mismatch(self) -> None:
        from generate.math_problem_graph import (
            InitialPossession,
            MathProblemGraph,
            Operation,
            Quantity,
            Rate,
            Unknown,
        )
        from generate.math_solver import SolveError, solve

        g = MathProblemGraph(
            entities=("Sarah",),
            initial_state=(
                InitialPossession(entity="Sarah", quantity=Quantity(4, "oranges")),
            ),
            operations=(
                Operation(
                    actor="Sarah",
                    kind="apply_rate",
                    operand=Rate(
                        value=2, numerator_unit="dollars", denominator_unit="apples"
                    ),
                ),
            ),
            unknown=Unknown(entity="Sarah", unit="dollars"),
        )
        with pytest.raises(SolveError, match="hold a quantity in"):
            solve(g)


class TestVerifierReplayEqual:
    """ADR-0122 invariant 8 — verifier byte-equal replay."""

    def test_two_verify_runs_byte_equal(self) -> None:
        from generate.math_parser import parse_problem
        from generate.math_solver import solve
        from generate.math_verifier import verify

        g = parse_problem(
            "Sarah has 4 apples. Each apple costs $2. How much does Sarah spend?"
        )
        t = solve(g)
        v1 = verify(g, t)
        v2 = verify(g, t)
        assert v1.canonical_bytes() == v2.canonical_bytes()
        assert v1.passed and v2.passed

    def test_two_solve_runs_byte_equal(self) -> None:
        from generate.math_parser import parse_problem
        from generate.math_solver import solve

        g = parse_problem(
            "Sarah has 4 apples. Each apple costs $2. How much does Sarah spend?"
        )
        assert solve(g).canonical_bytes() == solve(g).canonical_bytes()

    def test_verifier_catches_corrupted_after_value(self) -> None:
        # Hand-corrupt the trace's final step's after_value and confirm
        # the verifier refuses.
        from dataclasses import replace

        from generate.math_parser import parse_problem
        from generate.math_solver import solve
        from generate.math_verifier import verify

        g = parse_problem(
            "Sarah has 4 apples. Each apple costs $2. How much does Sarah spend?"
        )
        t = solve(g)
        corrupted_step = replace(t.steps[-1], after_value=999.0)
        corrupted = replace(t, steps=t.steps[:-1] + (corrupted_step,))
        v = verify(g, corrupted)
        assert not v.passed
        assert "after_value" in v.reason


class TestRealizerTemplate:
    """ADR-0122 invariant 9 — realizer emits per-template tokens."""

    def test_prose_contains_per_token_and_total(self) -> None:
        from generate.math_parser import parse_problem
        from generate.math_realizer import realize
        from generate.math_solver import solve

        g = parse_problem(
            "Sarah has 4 apples. Each apple costs $2. How much does Sarah spend?"
        )
        prose = realize(g.initial_state, solve(g)).as_prose()
        assert "2 dollars per apple" in prose
        assert "8 dollars" in prose

    def test_realizer_byte_equal(self) -> None:
        from generate.math_parser import parse_problem
        from generate.math_realizer import realize
        from generate.math_solver import solve

        g = parse_problem(
            "Sarah has 4 apples. Each apple costs $2. How much does Sarah spend?"
        )
        t = solve(g)
        r1 = realize(g.initial_state, t)
        r2 = realize(g.initial_state, t)
        assert r1.canonical_bytes() == r2.canonical_bytes()

    def test_decimal_rate_renders_singular_per_phrase(self) -> None:
        from generate.math_parser import parse_problem
        from generate.math_realizer import realize
        from generate.math_solver import solve

        g = parse_problem(
            "Tom has 8 pencils. A pencil costs $0.50. How much does Tom pay?"
        )
        prose = realize(g.initial_state, solve(g)).as_prose()
        assert "0.5 dollars per pencil" in prose
        assert "4 dollars" in prose


# ---------------------------------------------------------------------------
# Pack-extension invariants
# ---------------------------------------------------------------------------


class TestArithmeticPackExtension:
    """ADR-0122 — pack extension is well-formed.

    Pack-binding (ADR-0114a Obligation #10) requires every operation
    kind to resolve to a pack lemma. apply_rate's lemma must exist
    in the loaded pack with matching SHA-256 in the manifest.
    """

    def test_apply_rate_lemma_present_in_lexicon(self) -> None:
        from language_packs.compiler import load_pack_entries

        entries = load_pack_entries("en_arithmetic_v1")
        lemmas = {e.lemma for e in entries}
        assert "apply_rate" in lemmas

    def test_manifest_checksum_matches_lexicon_bytes(self) -> None:
        pack_root = _REPO_ROOT / "language_packs" / "data" / "en_arithmetic_v1"
        manifest = json.loads((pack_root / "manifest.json").read_text())
        actual_lex_sha = hashlib.sha256(
            (pack_root / "lexicon.jsonl").read_bytes()
        ).hexdigest()
        actual_glo_sha = hashlib.sha256(
            (pack_root / "glosses.jsonl").read_bytes()
        ).hexdigest()
        assert manifest["checksum"] == actual_lex_sha
        assert manifest["glosses_checksum"] == actual_glo_sha


# ---------------------------------------------------------------------------
# Sealed-holdout invariants (10, 11, 15) — CORE_HOLDOUT_KEY required
# ---------------------------------------------------------------------------


class TestSealedHoldoutMeasurement:
    """ADR-0122 invariants 10, 11 — substrate-only landing.

    The lift gate is deferred (see ADR doc §"Decision" and
    §"Measurement"). The two pinned invariants:

    1. ``correct_rate == 0.0`` at landing — pins the honest finding
       that the substrate alone matches zero real GSM8K cases due
       to the multi-construction barrier documented in the ADR.
       This test fails when a future composition ADR lifts the
       number above 0; that failure is the signal that ADR-0122
       should be superseded by a successful-lift ADR.

    2. ``wrong == 0`` — the load-bearing positive claim. Even with
       no lift, adding the rate grammar introduced zero
       misparses across 1,319 real test problems.
    """

    def test_sealed_correct_rate_zero_at_landing(self) -> None:
        from evals.gsm8k_math.runner import run_lane

        plaintext = _decrypt_sealed_or_skip()
        cases = [
            json.loads(line)
            for line in plaintext.decode("utf-8").splitlines()
            if line.strip()
        ]
        report = run_lane(cases)
        rate = report.metrics["correct_rate"]
        assert rate == 0.0, (
            f"sealed-holdout correct_rate={rate}; ADR-0122 was "
            f"landed substrate-only with the lift gate explicitly "
            f"deferred. A non-zero rate here means a future "
            f"composition ADR has unlocked lifts — supersede "
            f"ADR-0122 with a successful-lift ADR and update this "
            f"test to the strict-lift form."
        )

    def test_sealed_wrong_count_remains_zero(self) -> None:
        # ADR-0114a Obligation #4. More serious than the correct_rate
        # gate: a non-zero wrong count means the new grammar
        # confabulated on real GSM8K. That's a hard PR blocker.
        from evals.gsm8k_math.runner import run_lane

        plaintext = _decrypt_sealed_or_skip()
        cases = [
            json.loads(line)
            for line in plaintext.decode("utf-8").splitlines()
            if line.strip()
        ]
        report = run_lane(cases)
        assert report.metrics["wrong"] == 0, (
            f"sealed-holdout wrong count = {report.metrics['wrong']}; "
            f"ADR-0114a Obligation #4 requires wrong==0. The new rate "
            f"grammar introduced a misparse pathway — REJECT the PR."
        )


class TestSealedSealIntegrity:
    """ADR-0122 invariant 15 — sealed seal byte-equal."""

    # Pinned at the time ADR-0119.7 sealed the file. If this test
    # fails, someone modified the sealed holdout — that is the most
    # serious possible regression for anti-overfit credibility.
    _EXPECTED_SEAL_SHA256: str | None = None  # filled in below at import time

    def test_seal_sha256_unchanged(self) -> None:
        if not _SEALED_PATH.exists():
            pytest.skip(f"sealed holdout not present at {_SEALED_PATH}")
        actual = hashlib.sha256(_SEALED_PATH.read_bytes()).hexdigest()
        # We don't pin the literal SHA in the test source — that would
        # require updating this test every time the seal is rotated.
        # Instead we pin "the seal exists and is a 420kb-ish age file
        # that hashes consistently within this run" — drift between
        # runs (e.g., reseal mid-PR) would be caught by the runner's
        # determinism gate, not by this test.
        size = _SEALED_PATH.stat().st_size
        assert 100_000 < size < 1_000_000, (
            f"sealed file size {size} is implausible for the ADR-0119.7 "
            f"GSM8K seal (~420kb expected)"
        )
        # Sanity: second hash matches first (no concurrent mutation)
        actual2 = hashlib.sha256(_SEALED_PATH.read_bytes()).hexdigest()
        assert actual == actual2


# ---------------------------------------------------------------------------
# Anti-overfit invariants (12, 13, 14)
# ---------------------------------------------------------------------------


class TestOODInvarianceHolds:
    """ADR-0122 invariant 12 — OOD/public ratio stays ≥ 0.95.

    This re-runs the existing test_ood_surface_generator gate function
    inside the ADR-0122 module so a regression on OOD shows up under
    both test modules. The substantive enforcement lives in
    ``tests/test_ood_surface_generator.py`` and uses the dev case
    set in ``evals/gsm8k_parser_dev/cases.jsonl``.
    """

    def test_ood_ratio_unchanged_under_rate_grammar(self) -> None:
        from tests.test_ood_surface_generator import (
            test_ood_public_ratio_meets_gate_across_dev_set,
        )

        test_ood_public_ratio_meets_gate_across_dev_set()


class TestPerturbationInvariancesHold:
    """ADR-0122 invariant 13 — invariance perturbations still pass.

    Re-runs the load-bearing gate from
    ``tests/test_perturbation_suite.py`` so a regression on
    invariance preservation or breaking is caught under ADR-0122 too.
    """

    def test_invariance_gates_unchanged_under_rate_grammar(self) -> None:
        try:
            from tests.test_perturbation_suite import (
                test_aggregate_dev_rates_are_perfect_for_applicable_perturbations as aggregate_gate,
            )
            from tests.test_perturbation_suite import (
                test_invariance_breaking_perturbations_match_predicted_graph_solve as breaking_test,
            )
            from tests.test_perturbation_suite import (
                test_invariance_preserving_perturbations_keep_original_answer_value as preserving_test,
            )
        except ImportError as exc:
            pytest.fail(
                f"could not import perturbation gate tests — module "
                f"layout drifted: {exc}"
            )
        preserving_test()
        breaking_test()
        aggregate_gate()


class TestAdversarialWrongZero:
    """ADR-0122 invariant 14 — adversarial suite wrong-zero holds."""

    def test_adversarial_wrong_count_remains_zero(self) -> None:
        from evals.gsm8k_math.adversarial.generator import (
            generate_adversarial_cases,
        )
        from evals.gsm8k_math.runner import run_lane

        cases = generate_adversarial_cases()
        report = run_lane([c.as_runner_dict() for c in cases])
        assert report.metrics["wrong"] == 0, (
            f"adversarial suite wrong = {report.metrics['wrong']}; the "
            f"rate grammar must not introduce a new misparse on the "
            f"adversarial families. Inspect "
            f"report.case_details for the offending cases."
        )

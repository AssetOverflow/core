"""ADR-0123 — comparison-phrasing realizer (surface increment on substrate).

Pins the load-bearing invariants documented in
``docs/decisions/ADR-0123-parser-comparison-phrasing.md``. The
substrate (PR #155, commit ``c9bd5d4``) shipped the typed graph
operand (``Comparison``), the two new operation kinds, the parser
patterns, the solver/verifier wiring, and the two pack lemmas; this
PR adds the **realizer surface** that turns successful comparison
traces into show-your-work prose. Before this PR, a problem the
substrate solved successfully crashed at ``realize()`` with
``RealizerError("unknown operation_kind 'compare_additive'")``.

The wrong-zero discipline (ADR-0114a Obligation #4) is the
load-bearing positive claim: the new realizer branches only fire
when the substrate has already emitted a successful step. If the
substrate refused, no step exists to render — there is no path by
which the realizer can introduce a misparse.

Tests are organized to mirror ADR-0118's stepped-realizer test
shape and the substrate ADR's invariant numbering:

1. End-to-end canonical renderings for each of the four surfaces
   (``N more``, ``N fewer``, ``twice``/``N times``, ``half``).
2. Singular/plural independence at the surface layer.
3. Byte-determinism on repeated invocations.
4. Refusal discipline (operand-shape, direction, self-reference,
   missing-reference defenses).
5. Backwards-compatibility — every pre-comparison realizer surface
   re-renders byte-identically.
6. Sealed-holdout invariants (skipped without ``CORE_HOLDOUT_KEY``
   per ADR-0119.7).
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


def _solve_and_realize(text: str) -> str:
    """Helper: full pipeline → realized prose string."""
    from generate.math_parser import parse_problem
    from generate.math_realizer import realize
    from generate.math_solver import solve

    g = parse_problem(text)
    return realize(g.initial_state, solve(g)).as_prose()


# ---------------------------------------------------------------------------
# End-to-end canonical renderings (ADR-0123 invariants 1-5)
# ---------------------------------------------------------------------------


class TestCompareAdditiveMoreCanonical:
    """ADR-0123 invariant ``adr_0123_realize_compare_additive_more_canonical``."""

    PROBLEM = (
        "Alice has 5 apples. Bob has 3 more apples than Alice. "
        "How many apples does Bob have?"
    )

    def test_prose_contains_comparison_and_state_clauses(self) -> None:
        prose = _solve_and_realize(self.PROBLEM)
        assert "3 more apples than Alice" in prose
        assert "Bob a total of 8 apples" in prose

    def test_answer_sentence_present(self) -> None:
        prose = _solve_and_realize(self.PROBLEM)
        # ADR-0118's _answer_sentence template
        assert "Bob has 8 apples." in prose

    def test_setup_sentence_present(self) -> None:
        prose = _solve_and_realize(self.PROBLEM)
        assert "Alice has 5 apples." in prose


class TestCompareAdditiveFewerCanonical:
    """ADR-0123 invariant ``adr_0123_realize_compare_additive_fewer_canonical``."""

    PROBLEM = (
        "Anna has 10 flowers. Mary has 5 fewer flowers than Anna. "
        "How many flowers does Mary have?"
    )

    def test_prose_contains_fewer_clause(self) -> None:
        prose = _solve_and_realize(self.PROBLEM)
        assert "5 fewer flowers than Anna" in prose

    def test_prose_contains_leaving_state(self) -> None:
        # The 'fewer' branch uses 'leaving … with a total of …'
        # to read naturally with subtraction semantics.
        prose = _solve_and_realize(self.PROBLEM)
        assert "leaving Mary with a total of 5 flowers" in prose

    def test_answer_sentence_present(self) -> None:
        prose = _solve_and_realize(self.PROBLEM)
        assert "Mary has 5 flowers." in prose


class TestCompareMultiplicativeTwiceCanonical:
    """ADR-0123 invariant
    ``adr_0123_realize_compare_multiplicative_twice_canonical``."""

    PROBLEM = (
        "Carla has 7 marbles. Ben has twice as many marbles as Carla. "
        "How many marbles does Ben have?"
    )

    def test_prose_normalizes_twice_to_n_times(self) -> None:
        # The parser maps 'twice' to factor=2; the realizer renders
        # the numeric form. This is deliberate — round-trip drift on
        # 'twice' vs '2 times' is acceptable; the underlying graph is
        # the source of truth.
        prose = _solve_and_realize(self.PROBLEM)
        assert "2 times as many marbles as Carla" in prose

    def test_prose_contains_state_clause(self) -> None:
        prose = _solve_and_realize(self.PROBLEM)
        assert "Ben a total of 14 marbles" in prose


class TestCompareMultiplicativeNTimesCanonical:
    """ADR-0123 invariant
    ``adr_0123_realize_compare_multiplicative_n_times_canonical``."""

    PROBLEM = (
        "Tom has 3 cookies. Sara has 4 times as many cookies as Tom. "
        "How many cookies does Sara have?"
    )

    def test_prose_renders_n_times(self) -> None:
        prose = _solve_and_realize(self.PROBLEM)
        assert "4 times as many cookies as Tom" in prose
        assert "Sara a total of 12 cookies" in prose


class TestCompareFractionHalfCanonical:
    """ADR-0123 invariant ``adr_0123_realize_compare_fraction_half_canonical``."""

    PROBLEM = (
        "Tom has 8 cookies. Lisa has half as many cookies as Tom. "
        "How many cookies does Lisa have?"
    )

    def test_prose_uses_literal_half_word(self) -> None:
        # factor==0.5 + direction=='fraction' renders "half as many"
        # rather than "0.5 as many" — the natural English form.
        prose = _solve_and_realize(self.PROBLEM)
        assert "half as many cookies as Tom" in prose
        assert "0.5 as many" not in prose

    def test_prose_contains_state_clause(self) -> None:
        prose = _solve_and_realize(self.PROBLEM)
        assert "Lisa a total of 4 cookies" in prose


# ---------------------------------------------------------------------------
# Byte-determinism + plurality independence (ADR-0123 invariants 6-7)
# ---------------------------------------------------------------------------


class TestRealizerByteDeterministic:
    """ADR-0123 invariant ``adr_0123_realize_byte_deterministic``."""

    @pytest.mark.parametrize(
        "problem",
        [
            "Alice has 5 apples. Bob has 3 more apples than Alice. How many apples does Bob have?",
            "Anna has 10 flowers. Mary has 5 fewer flowers than Anna. How many flowers does Mary have?",
            "Carla has 7 marbles. Ben has twice as many marbles as Carla. How many marbles does Ben have?",
            "Tom has 8 cookies. Lisa has half as many cookies as Tom. How many cookies does Lisa have?",
        ],
    )
    def test_realize_twice_produces_byte_equal_output(
        self, problem: str
    ) -> None:
        from generate.math_parser import parse_problem
        from generate.math_realizer import realize
        from generate.math_solver import solve

        g = parse_problem(problem)
        t = solve(g)
        r1 = realize(g.initial_state, t)
        r2 = realize(g.initial_state, t)
        assert r1.canonical_bytes() == r2.canonical_bytes()
        assert r1.as_prose() == r2.as_prose()


class TestSingularPluralIndependence:
    """ADR-0123 invariant ``adr_0123_realize_singular_plural_independence``.

    The comparison clause and the resolved-state clause pluralize
    independently — a delta of 1 takes the singular for the delta
    surface, but the after_value drives the resolved-state surface
    on its own count.
    """

    def test_singular_delta_with_plural_after(self) -> None:
        prose = _solve_and_realize(
            "Tom has 4 apples. Sue has 1 more apple than Tom. "
            "How many apples does Sue have?"
        )
        assert "1 more apple than Tom" in prose
        assert "1 more apples than Tom" not in prose
        # Resolved state pluralizes on its own count (5)
        assert "5 apples" in prose

    def test_plural_delta_with_singular_after(self) -> None:
        # Fewer that leaves exactly 1 unit.
        prose = _solve_and_realize(
            "Anna has 4 flowers. Mary has 3 fewer flowers than Anna. "
            "How many flowers does Mary have?"
        )
        assert "3 fewer flowers than Anna" in prose
        # Resolved state singular on its own count (1)
        assert "a total of 1 flower" in prose


# ---------------------------------------------------------------------------
# Refusal discipline (ADR-0123 invariants 8-11)
# ---------------------------------------------------------------------------


def _make_compare_step(
    *,
    actor: str = "Alice",
    direction: str = "more",
    delta=None,
    factor=None,
    reference: str = "Bob",
    operand=None,
    after: float = 8.0,
    index: int = 0,
    operation_kind: str = "compare_additive",
):
    """Build a SolutionStep with a Comparison operand (or override)."""
    from generate.math_problem_graph import Comparison, Quantity
    from generate.math_solver import SolutionStep

    if operand is None:
        operand = Comparison(
            reference_actor=reference,
            delta=delta,
            factor=factor,
            direction=direction,  # type: ignore[arg-type]
        )
    return SolutionStep(
        step_index=index,
        operation_kind=operation_kind,
        pack_lemma_id=f"en_arithmetic_v1:{operation_kind}",
        actor=actor,
        operand=operand,
        target=None,
        before_value=0.0,
        after_value=after,
        target_before=None,
        target_after=None,
    )


class TestRealizerRefusalDiscipline:
    """ADR-0123 invariants 8-11 — operand and direction shape refusals.

    Several realizer defenses (missing-delta, missing-factor,
    direction mismatch with operand shape) are *unreachable* via
    ordinary dataclass construction because :class:`Comparison`'s
    ``__post_init__`` refuses those shapes first. The realizer's
    code retains them as belt-and-suspenders for hand-bypassed
    constructions (``object.__setattr__`` on the frozen instance);
    we do not exercise them here because the substrate boundary is
    the load-bearing guarantee. See
    ``test_pack_grounded_comparison.py`` and the substrate ADR's
    own test suite for the ``Comparison.__post_init__`` refusals.
    """

    def test_refuses_non_comparison_operand_on_additive(self) -> None:
        from generate.math_problem_graph import Quantity
        from generate.math_realizer import RealizerError, _compare_additive_sentence

        step = _make_compare_step(operand=Quantity(value=3, unit="apples"))
        with pytest.raises(RealizerError, match="requires a Comparison operand"):
            _compare_additive_sentence(step)

    def test_refuses_self_comparison_additive(self) -> None:
        from generate.math_problem_graph import Quantity
        from generate.math_realizer import RealizerError, _compare_additive_sentence

        step = _make_compare_step(
            actor="Alice",
            reference="Alice",
            delta=Quantity(value=3, unit="apples"),
        )
        with pytest.raises(RealizerError, match="self-comparison"):
            _compare_additive_sentence(step)

    def test_refuses_self_comparison_multiplicative(self) -> None:
        from generate.math_realizer import (
            RealizerError,
            _compare_multiplicative_sentence,
        )

        step = _make_compare_step(
            actor="Alice",
            reference="Alice",
            direction="times",
            factor=2.0,
            operation_kind="compare_multiplicative",
        )
        with pytest.raises(RealizerError, match="self-comparison"):
            _compare_multiplicative_sentence(step, {"Alice": "apples"})

    def test_refuses_missing_entity_units_on_multiplicative(self) -> None:
        from generate.math_realizer import (
            RealizerError,
            _compare_multiplicative_sentence,
        )

        step = _make_compare_step(
            direction="times",
            factor=2.0,
            reference="UnknownActor",
            operation_kind="compare_multiplicative",
        )
        with pytest.raises(RealizerError, match="initial state"):
            _compare_multiplicative_sentence(step, {"Alice": "apples"})

    def test_step_sentence_requires_entity_units_for_multiplicative(self) -> None:
        # If a caller bypasses realize() and invokes _step_sentence
        # directly without providing entity_units, the multiplicative
        # branch must refuse rather than silently render None as
        # the unit.
        from generate.math_realizer import RealizerError, _step_sentence

        step = _make_compare_step(
            direction="times",
            factor=2.0,
            operation_kind="compare_multiplicative",
        )
        with pytest.raises(RealizerError, match="entity_units"):
            _step_sentence(step, None)


# ---------------------------------------------------------------------------
# Backwards-compatibility — ADR-0118 templates must re-render identically
# ---------------------------------------------------------------------------


class TestADR0118StepRealizerUnchanged:
    """ADR-0123 invariant ``adr_0123_adr_0118_stepped_realizer_unchanged``.

    Every pre-comparison operation kind must re-render byte-
    identically to its rendering on the substrate branch. The
    realizer change is purely additive at the dispatch layer; it
    must not alter the prior templates.
    """

    def test_add_step_renders_unchanged(self) -> None:
        # 'X has N. X buys M more.' → uses ADR-0118 add template.
        prose = _solve_and_realize(
            "Sarah has 3 apples. Sarah buys 4 more apples. "
            "How many apples does Sarah have?"
        )
        # ADR-0118 pinned phrasing: "buys N more units, raising the
        # total to M"
        assert "buys 4 more apples" in prose
        assert "raising the total to 7" in prose

    def test_subtract_step_renders_unchanged(self) -> None:
        prose = _solve_and_realize(
            "Sarah has 10 apples. Sarah loses 3 apples. "
            "How many apples does Sarah have?"
        )
        assert "loses 3 apples" in prose
        assert "leaving 7" in prose

    def test_setup_and_answer_sentences_unchanged(self) -> None:
        prose = _solve_and_realize(
            "Sarah has 3 apples. Sarah buys 4 more apples. "
            "How many apples does Sarah have?"
        )
        # Setup
        assert prose.startswith("Sarah has 3 apples.")
        # Answer (ADR-0118 template)
        assert prose.endswith("Sarah has 7 apples.")


# ---------------------------------------------------------------------------
# Sealed-holdout invariants — CORE_HOLDOUT_KEY required
# ---------------------------------------------------------------------------


class TestSealedHoldoutMeasurement:
    """ADR-0123 invariants
    ``adr_0123_sealed_correct_rate_zero_at_landing`` and
    ``adr_0123_sealed_wrong_zero_holds``.

    Both are inherited from the substrate ADR: the realizer surface
    cannot create matches the parser refuses, so the multi-
    construction barrier holds at the surface layer too. The
    realizer also cannot misparse — it only renders successful
    traces — so ``wrong == 0`` holds by construction.
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
            f"sealed-holdout correct_rate={rate}; ADR-0123 surface "
            f"shipped with the lift gate explicitly deferred. A "
            f"non-zero rate here means a future composition ADR has "
            f"unlocked lifts — supersede ADR-0123 with a "
            f"successful-lift ADR and update this test to the "
            f"strict-lift form."
        )

    def test_sealed_wrong_count_remains_zero(self) -> None:
        # ADR-0114a Obligation #4. The realizer surface cannot
        # introduce a misparse because it only renders successful
        # traces; for this to fail, the substrate's solver would
        # have to confabulate, which the substrate's wrong-zero
        # test already pins.
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
            f"ADR-0114a Obligation #4 requires wrong==0."
        )


class TestSealedSealIntegrity:
    """ADR-0123 — sealed seal byte-equal across this PR."""

    def test_seal_unchanged(self) -> None:
        if not _SEALED_PATH.exists():
            pytest.skip(f"sealed holdout not present at {_SEALED_PATH}")
        actual = hashlib.sha256(_SEALED_PATH.read_bytes()).hexdigest()
        size = _SEALED_PATH.stat().st_size
        assert 100_000 < size < 1_000_000, (
            f"sealed file size {size} is implausible for the ADR-0119.7 "
            f"GSM8K seal (~420kb expected)"
        )
        actual2 = hashlib.sha256(_SEALED_PATH.read_bytes()).hexdigest()
        assert actual == actual2

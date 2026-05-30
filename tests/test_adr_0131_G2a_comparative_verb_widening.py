"""ADR-0131.G.2a — comparative anchor-verb widening + multi-word units.

The candidate-graph comparative extractor (ADR-0131.G.2) only recognized the
anchor verbs ``has``/``have`` and single-word units. Real GSM8K comparative
statements use a wider verb set (``does``/``collected``/``gained``/``studied`` …)
and multi-word units (``jumping jacks``). This widens both, staying wrong=0-safe:

- The widened verb set EXCLUDES polarity-inverting verbs (lose/spend/give/sell/
  win) — admitting those could read a comparison backwards.
- The round-trip filter is unchanged: the comparator anchor (``twice``/``N
  times``/``more``/``fewer``) and the reference actor must still ground; the
  multi-word unit grounds via the existing multi-word branch of ``_unit_grounds``.

Failing-under-violation: each asserts a specific extraction that flips if the
widening is reverted. The wrong=0 obligation is covered by the G2_comparatives
lane (29/29, wrong=0) and train_sample staying 3/47/0.
"""

from __future__ import annotations

from generate.math_candidate_parser import extract_operation_candidates


def _compare_ops(sentence: str):
    return [
        c for c in extract_operation_candidates(sentence)
        if c.op.kind in ("compare_additive", "compare_multiplicative")
    ]


def test_does_verb_multiplicative_multiword_unit() -> None:
    """'Brooke does three times as many jumping jacks as Sidney' — the
    canonical real-GSM8K (case 0024) form: 'does' verb + multi-word unit."""
    ops = _compare_ops("Brooke does three times as many jumping jacks as Sidney.")
    assert len(ops) == 1
    op = ops[0].op
    assert op.kind == "compare_multiplicative"
    assert op.actor == "Brooke"
    assert op.operand.reference_actor == "Sidney"
    assert op.operand.factor == 3.0


def test_collected_verb_twice_anchor() -> None:
    """'Cindy collected twice as many cards as Nicole' — 'collected' verb."""
    ops = _compare_ops("Cindy collected twice as many cards as Nicole.")
    assert len(ops) == 1
    assert ops[0].op.operand.factor == 2.0
    assert ops[0].op.operand.reference_actor == "Nicole"


def test_legacy_has_form_still_works() -> None:
    """Regression: the original 'has' form is unaffected."""
    ops = _compare_ops("Alice has 3 more apples than Bob.")
    assert len(ops) == 1
    assert ops[0].op.kind == "compare_additive"
    assert ops[0].op.operand.reference_actor == "Bob"


def test_polarity_inverting_verb_not_admitted() -> None:
    """wrong=0 guard: 'lost' inverts polarity in a comparison context and is
    deliberately EXCLUDED — it must not produce a comparative candidate."""
    ops = _compare_ops("Alice lost twice as many apples as Bob.")
    assert ops == []


def test_spend_verb_not_admitted() -> None:
    """wrong=0 guard: 'spent' is excluded (polarity-inverting)."""
    ops = _compare_ops("Alice spent three times as many dollars as Bob.")
    assert ops == []

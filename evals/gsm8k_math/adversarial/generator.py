"""ADR-0119.5 — adversarial case generator for gsm8k_math (Obligation #8).

Emits a deterministic suite of math-word-problem cases designed to
exploit weak grammar coverage in the ADR-0115 parser. Three outcome
families per case:

- ``expected_outcome == "correct"`` — case stays within the grammar
  and produces a numeric answer
- ``expected_outcome == "refused"`` — case is deliberately outside the
  grammar; the parser/solver MUST refuse with a typed error
- (deliberately never authored) ``expected_outcome == "wrong"`` —
  the gate is that the runner emits **zero wrong** on this suite.
  A wrong outcome here means CORE silently misparsed an adversarial
  input — exactly the failure mode ADR-0114a Obligation #8 names

The generator is pure / deterministic: same call → byte-equal case list.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AdversarialCase:
    """One adversarial probe with its expected outcome."""

    case_id: str
    problem: str
    expected_outcome: str  # "correct" | "refused"
    family: str  # which adversarial pattern this probes
    expected_answer: float | None
    expected_unit: str | None

    def as_runner_dict(self) -> dict[str, Any]:
        """Render as a dict the lane runner can consume."""
        # For "refused" expectations, use placeholder expected values; the
        # runner will produce its own refusal regardless of these.
        return {
            "id": self.case_id,
            "problem": self.problem,
            "expected_answer": (
                self.expected_answer if self.expected_answer is not None else 0
            ),
            "expected_unit": (
                self.expected_unit if self.expected_unit is not None else "items"
            ),
        }


def _refused(case_id: str, problem: str, family: str) -> AdversarialCase:
    return AdversarialCase(
        case_id=case_id,
        problem=problem,
        expected_outcome="refused",
        family=family,
        expected_answer=None,
        expected_unit=None,
    )


def _correct(
    case_id: str,
    problem: str,
    family: str,
    expected_answer: float,
    expected_unit: str,
) -> AdversarialCase:
    return AdversarialCase(
        case_id=case_id,
        problem=problem,
        expected_outcome="correct",
        family=family,
        expected_answer=expected_answer,
        expected_unit=expected_unit,
    )


# ---------------------------------------------------------------------------
# Adversarial families
# ---------------------------------------------------------------------------
#
# Each family is a generator function that yields AdversarialCase records.
# Adding a family requires extending FAMILY_REGISTRY below and incrementing
# the family ordinal prefix in case ids.


def _family_conditional_phrasing() -> list[AdversarialCase]:
    """Conditional / time-modal phrasing — ADR-0115 §Phase 1.1 boundary."""
    return [
        _refused(
            "adv-cnd-001",
            "If Sam had 5 apples, how many apples does Sam have?",
            "conditional_phrasing",
        ),
        _refused(
            "adv-cnd-002",
            "When Tom buys 3 marbles, how many marbles does Tom have?",
            "conditional_phrasing",
        ),
        _refused(
            "adv-cnd-003",
            "Suppose Anna has 10 books. How many books does Anna have?",
            "conditional_phrasing",
        ),
        _refused(
            "adv-cnd-004",
            "Had Sam bought 3 apples, would he have 8 apples?",
            "conditional_phrasing",
        ),
    ]


def _family_compound_questions() -> list[AdversarialCase]:
    """Multiple ? sentences — runner refuses (single question required)."""
    return [
        _refused(
            "adv-cmp-001",
            "Sam has 5 apples. How many apples does Sam have? How many does Tom have?",
            "compound_questions",
        ),
        _refused(
            "adv-cmp-002",
            "Anna has 3 marbles. How many marbles does Anna have? And how many does Ben have?",
            "compound_questions",
        ),
        _refused(
            "adv-cmp-003",
            "Tom buys 4 candies. Tom has how many candies? Sam has how many?",
            "compound_questions",
        ),
    ]


def _family_undefined_entity_question() -> list[AdversarialCase]:
    """Question references an entity never introduced — runner refuses."""
    return [
        _refused(
            "adv-und-001",
            "Sam has 5 apples. How many apples does Tom have?",
            "undefined_entity_question",
        ),
        _refused(
            "adv-und-002",
            "Anna has 3 marbles. How many marbles does Chris have?",
            "undefined_entity_question",
        ),
        _refused(
            "adv-und-003",
            "Lisa has 10 books. How many books does Doria have?",
            "undefined_entity_question",
        ),
    ]


def _family_unknown_verb() -> list[AdversarialCase]:
    """Verb not in the registered tables — parser refuses."""
    return [
        _refused(
            "adv-vrb-001",
            "Sam has 5 apples. He polishes 3 more. How many apples does Sam have?",
            "unknown_verb",
        ),
        _refused(
            "adv-vrb-002",
            "Tom has 12 candies. He admires 4. How many candies does Tom have?",
            "unknown_verb",
        ),
        _refused(
            "adv-vrb-003",
            "Anna has 8 marbles. She catalogues 3. How many marbles does Anna have?",
            "unknown_verb",
        ),
        _refused(
            "adv-vrb-004",
            "Lisa has 10 books. She measures 2 more. How many books does Lisa have?",
            "unknown_verb",
        ),
        _refused(
            "adv-vrb-005",
            "Owen has 7 cups. He inspects 1. How many cups does Owen have?",
            "unknown_verb",
        ),
    ]


def _family_empty_or_whitespace() -> list[AdversarialCase]:
    """Empty / whitespace-only input."""
    return [
        _refused("adv-emp-001", "", "empty_or_whitespace"),
        _refused("adv-emp-002", "   ", "empty_or_whitespace"),
        _refused("adv-emp-003", "\n\t  \n", "empty_or_whitespace"),
    ]


def _family_no_question() -> list[AdversarialCase]:
    """Statement-only input — no question sentence; runner refuses."""
    return [
        _refused(
            "adv-noq-001",
            "Sam has 5 apples. He buys 3 more.",
            "no_question",
        ),
        _refused(
            "adv-noq-002",
            "Anna has 10 marbles.",
            "no_question",
        ),
        _refused(
            "adv-noq-003",
            "Tom buys 4 candies. Sam buys 5.",
            "no_question",
        ),
    ]


def _family_numbers_spelled_out() -> list[AdversarialCase]:
    """Numbers as words — parser refuses (numeric tokens required)."""
    return [
        _refused(
            "adv-spw-001",
            "Sam has five apples. He buys three more. How many apples does Sam have?",
            "numbers_spelled_out",
        ),
        _refused(
            "adv-spw-002",
            "Anna has ten marbles. She gives two to Ben. How many marbles does Anna have?",
            "numbers_spelled_out",
        ),
        _refused(
            "adv-spw-003",
            "Tom has twelve candies. He eats four. How many candies does Tom have?",
            "numbers_spelled_out",
        ),
    ]


def _family_passive_voice() -> list[AdversarialCase]:
    """Passive constructions outside grammar."""
    return [
        _refused(
            "adv-psv-001",
            "Sam has 5 apples. 3 more apples are bought by Sam. How many apples does Sam have?",
            "passive_voice",
        ),
        _refused(
            "adv-psv-002",
            "10 marbles are given to Ben by Anna. How many marbles does Ben have?",
            "passive_voice",
        ),
        _refused(
            "adv-psv-003",
            "Tom has 12 candies. 4 candies are eaten by Tom. How many candies does Tom have?",
            "passive_voice",
        ),
    ]


def _family_red_herring_numbers() -> list[AdversarialCase]:
    """Numbers embedded in adversarial positions.

    Mixed expected outcomes: some cases the parser handles cleanly
    (digit-in-name is allowed by the grammar's ``[A-Z]\\w+`` entity
    rule); others fall outside grammar and refuse. Both shapes
    pinned here — the load-bearing assertion is that NONE silently
    misparse (wrong outcome).
    """
    return [
        _correct(
            "adv-red-001",
            # Numeric character inside an entity name — parser's [A-Z]\w+
            # allows this; behavior is documented and correct
            "Tom2 has 5 apples. He buys 3 more. How many apples does Tom2 have?",
            "red_herring_numbers",
            expected_answer=8,
            expected_unit="apples",
        ),
        _refused(
            "adv-red-002",
            # Multiple numerals in initial-possession
            "Sam has 5 6 apples. How many apples does Sam have?",
            "red_herring_numbers",
        ),
        _refused(
            "adv-red-003",
            # Number in possessive position with non-allowed trailing PP
            "Sam has 5 apples for $2 each. How many apples does Sam have?",
            "red_herring_numbers",
        ),
    ]


def _family_question_only() -> list[AdversarialCase]:
    """Question with no introductory statements — entity undefined."""
    return [
        _refused(
            "adv-qon-001",
            "How many apples does Sam have?",
            "question_only",
        ),
        _refused(
            "adv-qon-002",
            "How many marbles does Anna have now?",
            "question_only",
        ),
    ]


def _family_mid_sentence_punctuation() -> list[AdversarialCase]:
    """Embedded ? or . inside what should be a single sentence."""
    return [
        _refused(
            "adv-mid-001",
            "Sam has 5? apples. He buys 3 more. How many apples does Sam have?",
            "mid_sentence_punctuation",
        ),
        _refused(
            "adv-mid-002",
            "Tom has 12 candies! He eats 4. How many candies does Tom have?",
            "mid_sentence_punctuation",
        ),
    ]


def _family_subtle_in_grammar() -> list[AdversarialCase]:
    """Edge cases that LOOK adversarial but should parse correctly.

    Stays within grammar; runner must produce ``correct``, not refuse
    or misparse. These prove the gate isn't trivially satisfied by
    refusing everything.
    """
    return [
        _correct(
            "adv-sub-001",
            "Sam has 1 apple. He buys 3 more. How many apples does Sam have?",
            "subtle_in_grammar",
            expected_answer=4,
            expected_unit="apples",
        ),
        _correct(
            "adv-sub-002",
            # Zero quantity initial
            "Tom has 0 candies. He buys 5 more. How many candies does Tom have?",
            "subtle_in_grammar",
            expected_answer=5,
            expected_unit="candies",
        ),
        _correct(
            "adv-sub-003",
            # Same entity name appears in trailing PP — parser must ignore PP
            "Anna has 8 marbles. She finds 2 marbles on the floor. How many marbles does Anna have?",
            "subtle_in_grammar",
            expected_answer=10,
            expected_unit="marbles",
        ),
        _correct(
            "adv-sub-004",
            # Many entities, one transfer
            "Tom has 4 stickers. Sara has 7 stickers. Lex has 3 stickers. Tom gives 2 to Sara. How many stickers does Tom have?",
            "subtle_in_grammar",
            expected_answer=2,
            expected_unit="stickers",
        ),
    ]


FAMILY_REGISTRY: tuple = (
    _family_conditional_phrasing,
    _family_compound_questions,
    _family_undefined_entity_question,
    _family_unknown_verb,
    _family_empty_or_whitespace,
    _family_no_question,
    _family_numbers_spelled_out,
    _family_passive_voice,
    _family_red_herring_numbers,
    _family_question_only,
    _family_mid_sentence_punctuation,
    _family_subtle_in_grammar,
)


def generate_adversarial_cases() -> list[AdversarialCase]:
    """Return the full deterministic adversarial suite (≥ 30 cases).

    Same call → byte-equal list. Order is the family registry order,
    then within-family authoring order.
    """
    out: list[AdversarialCase] = []
    for family_fn in FAMILY_REGISTRY:
        out.extend(family_fn())
    return out

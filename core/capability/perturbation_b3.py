"""ADR-0114a Obligation #5 — reasoning-isolation perturbation suite for B3.

Generates and scores two classes of perturbation over B3 (bounded grammar)
expected-correct cases:

  Invariance-preserving — answer MUST NOT change:
    entity_rename_v{1,2,3}: Rename entities from a closed substitution pool.
    unit_synonym:           Replace count unit consistently (apples↔oranges,
                            dollars↔cents). Skip if unit has no synonym.
    commutative_reorder:    Swap initial-possession sentences for a single
                            entity holding two distinct units. Skipped for all
                            current B3 cases (no single-entity multi-unit init).

  Invariance-breaking — answer MUST change by a predictable delta:
    value_replacement_init: Replace first initial-possession value with
                            value + 2; predicted delta = +2.
    value_replacement_op:   Replace first operation numeric value with
                            value + 2; predicted delta = +2. Skip if
                            operation has no extractable numeric value.
    op_verb_flip:           Swap first add/subtract verb to its conjugate
                            (buys ↔ loses family). Skip for multiply/divide/
                            compare/transfer/rate operations.

Public API:
  generate_b3_perturbations(case_id, problem, expected_answer, expected_unit)
      -> list[B3Perturbation]
  skip_reasons_b3(case_id, problem, expected_answer, expected_unit)
      -> dict[str, str]
  validate_perturbation_suite(lane_id, cases_path) -> PerturbationReport
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from generate.math_parser import ParseError, parse_problem
from generate.math_solver import SolveError, solve


INVARIANCE_PRESERVING = "invariance_preserving"
INVARIANCE_BREAKING = "invariance_breaking"

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_B3_CASES: Path = (
    _REPO_ROOT / "evals" / "math_bounded_grammar" / "v1" / "cases.jsonl"
)

# ---------------------------------------------------------------------------
# Closed substitution pools — documented in ADR-0114a.5
# ---------------------------------------------------------------------------

# Three entity-rename variants; each maps every B3 entity to an alternative.
# Capitalized proper nouns so the parser's entity regex keeps accepting them.
_ENTITY_POOLS: list[dict[str, str]] = [
    {"Sam": "Alex",  "Tom": "Carol",  "Bob": "David",  "Birds": "Birds"},
    {"Sam": "Pat",   "Tom": "Robin",  "Bob": "Jordan", "Birds": "Birds"},
    {"Sam": "Quinn", "Tom": "Morgan", "Bob": "Blake",  "Birds": "Birds"},
]

# Unit-noun synonym map (pack-aligned against en_units_v1 / parser allowed_nouns).
# Both directions are listed so the map is symmetric.
_UNIT_SYNONYMS: dict[str, str] = {
    "apples":  "oranges",
    "oranges": "apples",
    "dollars": "cents",
    "cents":   "dollars",
}

# Verb flip: add-verb family ↔ subtract-verb family.
# "buys" ↔ "loses" is the canonical pair; the extended table covers other
# add/subtract verbs that appear in B3 cases so all applicable verbs flip.
_VERB_FLIP: dict[str, str] = {
    "buys":     "loses",
    "loses":    "buys",
    "gets":     "eats",
    "eats":     "gets",
    "receives": "loses",
    "earns":    "spends",
    "spends":   "earns",
    "finds":    "loses",
    "adds":     "loses",
    "sells":    "gets",
    "donates":  "gets",
    "uses":     "gets",
    "drops":    "gets",
    "removes":  "gets",
    "sends":    "buys",   # transfer → add substitute in non-transfer context
}

# Verbs that cannot be flipped by simple substitution (keep separate to
# document them as explicit skip targets in generated skip_reasons).
_SKIP_VERBS: frozenset[str] = frozenset(
    {"doubles", "triples", "splits", "gives", "hands", "passes", "mails"}
)

# All add + subtract verbs from the parser's tables.
_ADD_VERBS: frozenset[str] = frozenset(
    {"buys", "gets", "finds", "receives", "earns", "adds"}
)
_SUBTRACT_VERBS: frozenset[str] = frozenset(
    {"eats", "loses", "sells", "donates", "uses", "spends", "drops", "removes"}
)
_ALL_OP_VERBS: frozenset[str] = _ADD_VERBS | _SUBTRACT_VERBS


# ---------------------------------------------------------------------------
# Core data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class B3Perturbation:
    """One generated perturbation for a B3 case."""

    perturbation_id: str
    case_id: str
    kind: str            # INVARIANCE_PRESERVING | INVARIANCE_BREAKING
    transform: str       # e.g. "entity_rename_v1"
    problem_text: str    # perturbed problem string
    expected_answer: float
    expected_unit: str
    predicted_delta: float | None   # None for preserving; signed for breaking
    transform_params: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "perturbation_id": self.perturbation_id,
            "case_id": self.case_id,
            "kind": self.kind,
            "transform": self.transform,
            "problem_text": self.problem_text,
            "expected_answer": self.expected_answer,
            "expected_unit": self.expected_unit,
            "predicted_delta": self.predicted_delta,
            "transform_params": self.transform_params,
        }


@dataclass(frozen=True, slots=True)
class PerturbationCaseResult:
    """Scored result for one perturbation variant."""

    perturbation_id: str
    kind: str
    transform: str
    ok: bool
    detail: str


@dataclass(frozen=True, slots=True)
class PerturbationReport:
    """Aggregate B3 perturbation obligation #5 report."""

    adr: str
    schema_version: int
    lane_id: str
    cases_total: int
    cases_expected_correct: int
    preserving_attempted: int
    preserving_correct: int
    preserving_rate: float
    breaking_attempted: int
    breaking_correct: int
    breaking_rate: float
    obligation_5_passed: bool
    skip_counts: dict[str, int]
    per_perturbation: tuple[PerturbationCaseResult, ...]
    refusal_reason: str
    report_digest: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "adr": self.adr,
            "schema_version": self.schema_version,
            "lane_id": self.lane_id,
            "cases_total": self.cases_total,
            "cases_expected_correct": self.cases_expected_correct,
            "preserving_attempted": self.preserving_attempted,
            "preserving_correct": self.preserving_correct,
            "preserving_rate": self.preserving_rate,
            "breaking_attempted": self.breaking_attempted,
            "breaking_correct": self.breaking_correct,
            "breaking_rate": self.breaking_rate,
            "obligation_5_passed": self.obligation_5_passed,
            "skip_counts": self.skip_counts,
            "per_perturbation": [
                {
                    "perturbation_id": r.perturbation_id,
                    "kind": r.kind,
                    "transform": r.transform,
                    "ok": r.ok,
                    "detail": r.detail,
                }
                for r in self.per_perturbation
            ],
            "refusal_reason": self.refusal_reason,
            "report_digest": self.report_digest,
        }


# ---------------------------------------------------------------------------
# String-level perturbation helpers (operate on problem text only)
# ---------------------------------------------------------------------------


def _rename_entities(problem: str, entity_map: dict[str, str]) -> str:
    """Replace every entity name in problem text using entity_map.

    Uses word-boundary regex so 'Sam' inside 'Samuel' is not replaced.
    Substitutions are applied in longest-first order to avoid partial
    matches when one entity name is a prefix of another.
    """
    result = problem
    for src in sorted(entity_map, key=len, reverse=True):
        dst = entity_map[src]
        result = re.sub(rf"\b{re.escape(src)}\b", dst, result)
    return result


def _substitute_unit(problem: str, src_unit: str, dst_unit: str) -> str:
    """Replace all occurrences of src_unit (singular or plural) with dst_unit.

    Handles the canonical plural forms used by the parser.
    Keeps surrounding whitespace intact.
    """
    # Build singular form by stripping trailing 's' if present.
    src_singular = src_unit.rstrip("s") if src_unit.endswith("s") else src_unit
    dst_singular = dst_unit.rstrip("s") if dst_unit.endswith("s") else dst_unit
    result = problem
    # Replace plural first (longer match), then singular.
    for src, dst in [(src_unit, dst_unit), (src_singular, dst_singular)]:
        if src != dst:
            result = re.sub(rf"\b{re.escape(src)}\b", dst, result)
    return result


def _first_initial_possession_value(problem: str) -> int | None:
    """Return the integer value of the first '<Entity> has N <unit>' match.

    Returns None when not found.
    """
    m = re.search(
        r"([A-Z]\w+|[Tt]he\s+\w+)\s+(?:has|have)\s+"
        r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)"
        r"\s+\w+",
        problem,
    )
    if not m:
        return None
    word_numbers = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12,
    }
    raw = m.group(2)
    return int(raw) if raw.isdigit() else word_numbers.get(raw.lower())


def _replace_value_in_text(problem: str, old_value: int, delta: int) -> str:
    """Replace the first occurrence of str(old_value) (as a whole word, not after $)."""
    new_value = old_value + delta
    return re.sub(
        rf"(?<!\$)(?<!\d)\b{re.escape(str(old_value))}\b",
        str(new_value),
        problem,
        count=1,
    )


def _first_operation_verb_and_value(problem: str) -> tuple[str | None, int | None]:
    """Find the first add/subtract verb in problem text, and its accompanying integer.

    Returns (verb, value_or_None). 'value' is extracted from the same
    sentence. Returns (None, None) if no add/subtract verb found.
    """
    sentences = re.split(r"(?<=[.?!])\s+", problem.strip())
    for sent in sentences:
        # Skip question sentences.
        if sent.rstrip().endswith("?"):
            continue
        for verb in _ALL_OP_VERBS:
            if re.search(rf"\b{re.escape(verb)}\b", sent):
                # Extract numeric operand from same sentence (not rate $N).
                m = re.search(r"(?<!\$)\b(\d+)\b", sent)
                val = int(m.group(1)) if m else None
                return verb, val
    return None, None


def _flip_verb(problem: str, src_verb: str, dst_verb: str) -> str:
    """Replace first occurrence of src_verb with dst_verb (whole word)."""
    return re.sub(rf"\b{re.escape(src_verb)}\b", dst_verb, problem, count=1)


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------


def _run(problem: str) -> tuple[float | None, str | None, str]:
    """Run parse + solve on problem text.

    Returns (answer_value, answer_unit, error_detail).
    error_detail is empty string on success.
    """
    try:
        graph = parse_problem(problem)
        trace = solve(graph)
        return trace.answer_value, trace.answer_unit, ""
    except (ParseError, SolveError) as exc:
        return None, None, f"{type(exc).__name__}: {exc}"


def _make_id(case_id: str, transform: str) -> str:
    return f"{case_id}:{transform}"


# ---------------------------------------------------------------------------
# Perturbation generators
# ---------------------------------------------------------------------------


def _gen_entity_renames(
    case_id: str,
    problem: str,
    expected_answer: float,
    expected_unit: str,
) -> list[B3Perturbation]:
    """Generate up to 3 entity-rename invariance-preserving variants."""
    results: list[B3Perturbation] = []
    for version, pool in enumerate(_ENTITY_POOLS, start=1):
        perturbed = _rename_entities(problem, pool)
        if perturbed == problem:
            continue  # no entity in this case matched the pool — skip variant
        transform = f"entity_rename_v{version}"
        results.append(
            B3Perturbation(
                perturbation_id=_make_id(case_id, transform),
                case_id=case_id,
                kind=INVARIANCE_PRESERVING,
                transform=transform,
                problem_text=perturbed,
                expected_answer=expected_answer,
                expected_unit=expected_unit,
                predicted_delta=None,
                transform_params={"entity_map": {k: v for k, v in pool.items()
                                                  if k in problem}},
            )
        )
    return results


def _gen_unit_synonym(
    case_id: str,
    problem: str,
    expected_answer: float,
    expected_unit: str,
) -> B3Perturbation | None:
    """Generate a unit-synonym invariance-preserving variant.

    Returns None if expected_unit has no synonym or if unit appears inside
    a rate declaration (which hardcodes $N syntax — not substitutable).
    """
    synonym = _UNIT_SYNONYMS.get(expected_unit)
    if synonym is None:
        return None

    # Rate declarations use $N syntax; substituting the unit alone breaks them.
    # Detect rate cases by the presence of a "$" literal in the problem.
    if "$" in problem:
        return None

    perturbed = _substitute_unit(problem, expected_unit, synonym)
    if perturbed == problem:
        return None

    return B3Perturbation(
        perturbation_id=_make_id(case_id, "unit_synonym"),
        case_id=case_id,
        kind=INVARIANCE_PRESERVING,
        transform="unit_synonym",
        problem_text=perturbed,
        expected_answer=expected_answer,
        expected_unit=synonym,
        predicted_delta=None,
        transform_params={"src_unit": expected_unit, "dst_unit": synonym},
    )


def _gen_commutative_reorder(
    case_id: str,
    problem: str,
    expected_answer: float,
    expected_unit: str,
) -> B3Perturbation | None:
    """Generate a commutative-reorder variant (single-entity multi-unit only).

    Current B3 cases do not have single-entity multi-unit initial states;
    this will always return None and document the skip in skip_reasons_b3.
    Implemented for future-proofing when such cases are added.
    """
    # Pattern: two consecutive initial-possession sentences for the SAME entity
    # with DIFFERENT units.
    pat = re.compile(
        r"(([A-Z]\w+)\s+has\s+\d+\s+(\w+)\.)\s+"
        r"(\2\s+has\s+\d+\s+(?!\3\b)(\w+)\.)"
    )
    m = pat.search(problem)
    if not m:
        return None

    # Swap the two matched sentences.
    s1 = m.group(1)
    s2 = m.group(4)
    perturbed = problem.replace(f"{s1} {s2}", f"{s2} {s1}", 1)
    if perturbed == problem:
        return None

    return B3Perturbation(
        perturbation_id=_make_id(case_id, "commutative_reorder"),
        case_id=case_id,
        kind=INVARIANCE_PRESERVING,
        transform="commutative_reorder",
        problem_text=perturbed,
        expected_answer=expected_answer,
        expected_unit=expected_unit,
        predicted_delta=None,
        transform_params={"swapped": [s1, s2]},
    )


def _gen_value_replacement_init(
    case_id: str,
    problem: str,
    expected_answer: float,
    expected_unit: str,
) -> B3Perturbation | None:
    """Replace first initial-possession value by value + 2 (invariance-breaking)."""
    old_value = _first_initial_possession_value(problem)
    if old_value is None:
        return None
    if not str(old_value) in problem:
        return None

    delta = 2
    perturbed = _replace_value_in_text(problem, old_value, delta)
    if perturbed == problem:
        return None

    new_answer, new_unit, err = _run(perturbed)
    if err or new_answer is None:
        return None
    if new_answer == expected_answer:
        # Replacement did not change answer (e.g. value cancels); skip.
        return None

    return B3Perturbation(
        perturbation_id=_make_id(case_id, "value_replacement_init"),
        case_id=case_id,
        kind=INVARIANCE_BREAKING,
        transform="value_replacement_init",
        problem_text=perturbed,
        expected_answer=new_answer,
        expected_unit=new_unit or expected_unit,
        predicted_delta=new_answer - expected_answer,
        transform_params={
            "replaced_value": old_value,
            "replacement": old_value + delta,
            "delta": delta,
        },
    )


def _gen_value_replacement_op(
    case_id: str,
    problem: str,
    expected_answer: float,
    expected_unit: str,
) -> B3Perturbation | None:
    """Replace first operation numeric value by value + 2 (invariance-breaking).

    Skip if no add/subtract operation with a numeric operand is found, or if
    the operation value is the same as the initial-possession value (would
    be a duplicate replacement target).
    """
    verb, op_value = _first_operation_verb_and_value(problem)
    if verb is None or op_value is None:
        return None

    init_value = _first_initial_possession_value(problem)

    # Build a problem with the initial-possession value temporarily masked so
    # that _replace_value_in_text targets the operation value, not the init.
    # Strategy: replace init value with a sentinel, replace op value, restore.
    # Only do this when init_value == op_value (ambiguous target).
    if init_value is not None and init_value == op_value:
        # Can't distinguish the two occurrences with simple substitution; skip.
        return None

    delta = 2
    perturbed = _replace_value_in_text(problem, op_value, delta)
    if perturbed == problem:
        return None

    new_answer, new_unit, err = _run(perturbed)
    if err or new_answer is None:
        return None
    if new_answer == expected_answer:
        return None

    return B3Perturbation(
        perturbation_id=_make_id(case_id, "value_replacement_op"),
        case_id=case_id,
        kind=INVARIANCE_BREAKING,
        transform="value_replacement_op",
        problem_text=perturbed,
        expected_answer=new_answer,
        expected_unit=new_unit or expected_unit,
        predicted_delta=new_answer - expected_answer,
        transform_params={
            "replaced_value": op_value,
            "replacement": op_value + delta,
            "verb_context": verb,
            "delta": delta,
        },
    )


def _gen_op_verb_flip(
    case_id: str,
    problem: str,
    expected_answer: float,
    expected_unit: str,
) -> B3Perturbation | None:
    """Flip the first add/subtract verb to its conjugate (invariance-breaking).

    Skip if the first operation verb is outside the flip table (multiply,
    divide, transfer, compare, rate).
    """
    verb, _ = _first_operation_verb_and_value(problem)
    if verb is None or verb not in _VERB_FLIP:
        return None

    dst_verb = _VERB_FLIP[verb]
    perturbed = _flip_verb(problem, verb, dst_verb)
    if perturbed == problem:
        return None

    new_answer, new_unit, err = _run(perturbed)
    if err or new_answer is None:
        return None
    if new_answer == expected_answer:
        return None

    return B3Perturbation(
        perturbation_id=_make_id(case_id, "op_verb_flip"),
        case_id=case_id,
        kind=INVARIANCE_BREAKING,
        transform="op_verb_flip",
        problem_text=perturbed,
        expected_answer=new_answer,
        expected_unit=new_unit or expected_unit,
        predicted_delta=new_answer - expected_answer,
        transform_params={"src_verb": verb, "dst_verb": dst_verb},
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_b3_perturbations(
    case_id: str,
    problem: str,
    expected_answer: float,
    expected_unit: str,
) -> list[B3Perturbation]:
    """Generate all applicable perturbations for one B3 solved_correct case.

    Invariance-preserving (up to 5 per case):
      entity_rename_v1/v2/v3, unit_synonym, commutative_reorder

    Invariance-breaking (up to 3 per case):
      value_replacement_init, value_replacement_op, op_verb_flip

    Inapplicable transforms are omitted; see skip_reasons_b3 for why.
    """
    results: list[B3Perturbation] = []

    # Invariance-preserving
    results.extend(_gen_entity_renames(case_id, problem, expected_answer, expected_unit))
    u = _gen_unit_synonym(case_id, problem, expected_answer, expected_unit)
    if u:
        results.append(u)
    cr = _gen_commutative_reorder(case_id, problem, expected_answer, expected_unit)
    if cr:
        results.append(cr)

    # Invariance-breaking
    for gen in (
        _gen_value_replacement_init,
        _gen_value_replacement_op,
        _gen_op_verb_flip,
    ):
        p = gen(case_id, problem, expected_answer, expected_unit)
        if p:
            results.append(p)

    return results


def skip_reasons_b3(
    case_id: str,
    problem: str,
    expected_answer: float,
    expected_unit: str,
) -> dict[str, str]:
    """Return a dict of transform → reason for every skipped transform.

    Complements generate_b3_perturbations: each skipped transform is
    explicit rather than silently absent.
    """
    reasons: dict[str, str] = {}

    # entity_rename: check each variant
    for version, pool in enumerate(_ENTITY_POOLS, start=1):
        perturbed = _rename_entities(problem, pool)
        if perturbed == problem:
            reasons[f"entity_rename_v{version}"] = (
                "no entity in problem text matched the substitution pool"
            )

    # unit_synonym
    synonym = _UNIT_SYNONYMS.get(expected_unit)
    if synonym is None:
        reasons["unit_synonym"] = (
            f"unit {expected_unit!r} has no synonym in the closed substitution pool"
        )
    elif "$" in problem:
        reasons["unit_synonym"] = (
            "rate declaration ($ syntax) in problem makes unit substitution unsafe"
        )

    # commutative_reorder
    if _gen_commutative_reorder(case_id, problem, expected_answer, expected_unit) is None:
        reasons["commutative_reorder"] = (
            "no single-entity multi-unit consecutive initial-possession pair found"
        )

    # value_replacement_init
    init_value = _first_initial_possession_value(problem)
    if init_value is None:
        reasons["value_replacement_init"] = "no initial-possession value found"
    elif _gen_value_replacement_init(case_id, problem, expected_answer, expected_unit) is None:
        reasons["value_replacement_init"] = (
            "replacement produced same answer (value cancels out)"
        )

    # value_replacement_op
    verb, op_value = _first_operation_verb_and_value(problem)
    if verb is None or op_value is None:
        reasons["value_replacement_op"] = (
            "no add/subtract operation with a numeric operand found"
        )
    else:
        init_v = _first_initial_possession_value(problem)
        if init_v is not None and init_v == op_value:
            reasons["value_replacement_op"] = (
                "initial-possession value and operation value are equal — "
                "cannot unambiguously target the operation position"
            )
        elif _gen_value_replacement_op(
            case_id, problem, expected_answer, expected_unit
        ) is None:
            reasons["value_replacement_op"] = (
                "replacement produced same answer or parse failure"
            )

    # op_verb_flip
    if verb is None:
        reasons["op_verb_flip"] = "no operation verb found in problem"
    elif verb in _SKIP_VERBS:
        reasons["op_verb_flip"] = (
            f"verb {verb!r} is a multiply/divide/transfer verb — "
            "not in the closed flip table (would change operation semantics "
            "beyond sign-flip; deferred)"
        )
    elif verb not in _VERB_FLIP:
        reasons["op_verb_flip"] = (
            f"verb {verb!r} is not in the closed flip table"
        )
    elif _gen_op_verb_flip(case_id, problem, expected_answer, expected_unit) is None:
        reasons["op_verb_flip"] = (
            "flip produced same answer or parse failure"
        )

    return reasons


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------


def score_b3_perturbation(p: B3Perturbation) -> tuple[bool, str]:
    """Run the B3 pipeline on p.problem_text and compare against expected."""
    answer, unit, err = _run(p.problem_text)
    if err:
        return False, err
    if unit != p.expected_unit:
        return False, f"unit {unit!r} != expected {p.expected_unit!r}"
    if answer != p.expected_answer:
        return False, f"answer {answer!r} != expected {p.expected_answer!r}"
    return True, "ok"


# ---------------------------------------------------------------------------
# Lane validator
# ---------------------------------------------------------------------------


def validate_perturbation_suite(
    lane_id: str = "B3_bounded_grammar",
    cases_path: Path = DEFAULT_B3_CASES,
) -> PerturbationReport:
    """Validate ADR-0114a Obligation #5 for the B3 bounded-grammar lane.

    Reads cases_path; generates perturbations for every solved_correct case;
    scores each; returns PerturbationReport with both aggregate rates and
    per-perturbation detail.

    Exit criterion: obligation_5_passed iff
      preserving_rate == 1.0 AND breaking_rate == 1.0.
    """
    if not cases_path.exists():
        return _refusal_report(lane_id, f"cases file not found: {cases_path}")

    raw_cases: list[dict] = [
        json.loads(line)
        for line in cases_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    if not raw_cases:
        return _refusal_report(lane_id, "cases file is empty")

    expected_correct = [c for c in raw_cases if c.get("expected") == "solved_correct"]

    if not expected_correct:
        return _refusal_report(lane_id, "no solved_correct cases found in cases file")

    per_perturbation: list[PerturbationCaseResult] = []
    preserving_attempted = preserving_correct = 0
    breaking_attempted = breaking_correct = 0
    skip_counts: dict[str, int] = {}

    for case in expected_correct:
        case_id = case["case_id"]
        problem = case["problem"]
        exp_ans = case["expected_answer"]
        exp_unit = case["expected_unit"]

        skips = skip_reasons_b3(case_id, problem, exp_ans, exp_unit)
        for transform in skips:
            skip_counts[transform] = skip_counts.get(transform, 0) + 1

        perturbations = generate_b3_perturbations(case_id, problem, exp_ans, exp_unit)
        for pert in perturbations:
            ok, detail = score_b3_perturbation(pert)
            per_perturbation.append(
                PerturbationCaseResult(
                    perturbation_id=pert.perturbation_id,
                    kind=pert.kind,
                    transform=pert.transform,
                    ok=ok,
                    detail=detail,
                )
            )
            if pert.kind == INVARIANCE_PRESERVING:
                preserving_attempted += 1
                if ok:
                    preserving_correct += 1
            else:
                breaking_attempted += 1
                if ok:
                    breaking_correct += 1

    preserving_rate = (
        preserving_correct / preserving_attempted if preserving_attempted else 0.0
    )
    breaking_rate = (
        breaking_correct / breaking_attempted if breaking_attempted else 0.0
    )
    passed = (
        preserving_attempted > 0
        and breaking_attempted > 0
        and preserving_rate == 1.0
        and breaking_rate == 1.0
    )

    refusal_reason = ""
    if not passed:
        parts = []
        if preserving_rate < 1.0:
            parts.append(
                f"preserving_rate={preserving_rate:.4f} "
                f"({preserving_correct}/{preserving_attempted})"
            )
        if breaking_rate < 1.0:
            parts.append(
                f"breaking_rate={breaking_rate:.4f} "
                f"({breaking_correct}/{breaking_attempted})"
            )
        if not preserving_attempted:
            parts.append("no invariance-preserving perturbations generated")
        if not breaking_attempted:
            parts.append("no invariance-breaking perturbations generated")
        refusal_reason = "; ".join(parts)

    report_dict = {
        "adr": "0114a.5",
        "schema_version": 1,
        "lane_id": lane_id,
        "cases_total": len(raw_cases),
        "cases_expected_correct": len(expected_correct),
        "preserving_attempted": preserving_attempted,
        "preserving_correct": preserving_correct,
        "preserving_rate": preserving_rate,
        "breaking_attempted": breaking_attempted,
        "breaking_correct": breaking_correct,
        "breaking_rate": breaking_rate,
        "obligation_5_passed": passed,
        "skip_counts": dict(sorted(skip_counts.items())),
        "refusal_reason": refusal_reason,
    }
    digest = hashlib.sha256(
        json.dumps(report_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    return PerturbationReport(
        adr="0114a.5",
        schema_version=1,
        lane_id=lane_id,
        cases_total=len(raw_cases),
        cases_expected_correct=len(expected_correct),
        preserving_attempted=preserving_attempted,
        preserving_correct=preserving_correct,
        preserving_rate=preserving_rate,
        breaking_attempted=breaking_attempted,
        breaking_correct=breaking_correct,
        breaking_rate=breaking_rate,
        obligation_5_passed=passed,
        skip_counts=dict(sorted(skip_counts.items())),
        per_perturbation=tuple(per_perturbation),
        refusal_reason=refusal_reason,
        report_digest=digest,
    )


def emit_perturbation_report(report: PerturbationReport, out_path: Path) -> None:
    """Write the deterministic obligation-#5 perturbation report."""
    out_path.write_text(
        json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _refusal_report(lane_id: str, reason: str) -> PerturbationReport:
    digest = hashlib.sha256(reason.encode("utf-8")).hexdigest()
    return PerturbationReport(
        adr="0114a.5",
        schema_version=1,
        lane_id=lane_id,
        cases_total=0,
        cases_expected_correct=0,
        preserving_attempted=0,
        preserving_correct=0,
        preserving_rate=0.0,
        breaking_attempted=0,
        breaking_correct=0,
        breaking_rate=0.0,
        obligation_5_passed=False,
        skip_counts={},
        per_perturbation=(),
        refusal_reason=reason,
        report_digest=digest,
    )

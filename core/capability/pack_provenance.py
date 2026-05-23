"""ADR-0114a Obligation #10 — Operation provenance via pack.

> Every ``SolutionTrace.steps[*].pack_lemma_id`` resolves to a real
> lexicon entry in the domain's operator pack.

The solver already enforces this at solve time (``_resolve_pack_lemmas``
in :mod:`generate.math_solver` fails closed if any operation kind has
no resolving pack lemma). This module provides the **external
auditor**: independent of the solver, it reads the pack lexicon
on disk, re-solves each case in a lane, and validates every step's
``pack_lemma_id`` parses + resolves to a lexicon entry.

Why an external auditor matters: a bug in ``_resolve_pack_lemmas``
could in principle emit synthesized ids that don't exist on disk.
The auditor re-reads the pack and re-walks the trace from raw
lexicon bytes. Belt-and-braces per ADR-0114a's anti-overfitting
discipline.

This module wires obligation #10 for **B3 (bounded grammar)** —
the lane whose pipeline (parser → graph → solver → verifier)
exercises ``math_solver`` end-to-end and produces traces with
non-trivial step counts. Equivalents for B1 (symbolic equivalence)
and B2 (teaching corpus) are deferred to separate sub-ADRs because:

  - B1's verification path is algebra-based, not arithmetic-step-
    based; the pack-lemma notion needs reframing.
  - B2 may exercise the same solver depending on its corpus
    contents; the auditor below can be extended once that's
    confirmed case-by-case.

Per ADR-0114a's audit discipline this auditor is pure: no I/O
beyond reading the pack lexicon and the lane's cases.jsonl;
deterministic — same lexicon + cases produce a byte-equal report.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from generate.math_candidate_graph import parse_and_solve
from generate.math_solver import SolutionTrace, SolveError, solve


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# The math domain's operator pack — same constant the solver uses.
DEFAULT_MATH_PACK_ID: str = "en_arithmetic_v1"
DEFAULT_MATH_LEXICON: Path = (
    _REPO_ROOT / "language_packs" / "data" / DEFAULT_MATH_PACK_ID / "lexicon.jsonl"
)

# Default B3 lane location.
DEFAULT_B3_CASES: Path = (
    _REPO_ROOT / "evals" / "math_bounded_grammar" / "v1" / "cases.jsonl"
)


class PackProvenanceError(Exception):
    """Raised when the pack lexicon cannot be read or parsed."""


@dataclass(frozen=True, slots=True)
class CaseProvenance:
    """Per-case provenance result."""

    case_id: str
    outcome: str  # "validated" | "skipped_unsolved" | "violated"
    step_count: int
    pack_lemma_ids: tuple[str, ...]
    unresolved_lemma_ids: tuple[str, ...]
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "outcome": self.outcome,
            "step_count": self.step_count,
            "pack_lemma_ids": list(self.pack_lemma_ids),
            "unresolved_lemma_ids": list(self.unresolved_lemma_ids),
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class PackProvenanceReport:
    """Aggregate lane report."""

    pack_id: str
    lane_id: str
    cases_total: int
    cases_validated: int
    cases_skipped_unsolved: int
    cases_violated: int
    obligation_10_passed: bool
    distinct_lemma_ids_observed: tuple[str, ...]
    distinct_lemma_ids_in_pack: tuple[str, ...]
    per_case: tuple[CaseProvenance, ...]
    refusal_reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "adr": "0114a.10",
            "schema_version": 1,
            "pack_id": self.pack_id,
            "lane_id": self.lane_id,
            "cases_total": self.cases_total,
            "cases_validated": self.cases_validated,
            "cases_skipped_unsolved": self.cases_skipped_unsolved,
            "cases_violated": self.cases_violated,
            "obligation_10_passed": self.obligation_10_passed,
            "distinct_lemma_ids_observed": list(self.distinct_lemma_ids_observed),
            "distinct_lemma_ids_in_pack": list(self.distinct_lemma_ids_in_pack),
            "per_case": [c.as_dict() for c in self.per_case],
            "refusal_reason": self.refusal_reason,
        }


def _load_lexicon_lemmas(lexicon_path: Path) -> set[str]:
    """Read the pack lexicon and return the set of lemma surfaces.

    The pack_lemma_id format is ``<pack_id>:<lemma>``; we resolve
    against the ``lemma`` field of each lexicon entry.
    """
    if not lexicon_path.exists():
        raise PackProvenanceError(
            f"pack lexicon not found: {lexicon_path}"
        )
    lemmas: set[str] = set()
    for line_no, raw in enumerate(
        lexicon_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not raw.strip():
            continue
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise PackProvenanceError(
                f"{lexicon_path}:{line_no}: invalid JSON: {exc}"
            ) from exc
        lemma = entry.get("lemma")
        if not isinstance(lemma, str) or not lemma:
            raise PackProvenanceError(
                f"{lexicon_path}:{line_no}: entry missing 'lemma' field"
            )
        lemmas.add(lemma)
    if not lemmas:
        raise PackProvenanceError(f"pack lexicon is empty: {lexicon_path}")
    return lemmas


def _parse_lemma_id(lemma_id: str) -> tuple[str, str] | None:
    """Parse ``<pack_id>:<lemma>`` into its components. Returns None
    on malformed input — the validator treats that as a violation.
    """
    if not isinstance(lemma_id, str) or ":" not in lemma_id:
        return None
    pack_id, _, lemma = lemma_id.partition(":")
    if not pack_id or not lemma:
        return None
    return pack_id, lemma


def _validate_trace(
    trace: SolutionTrace,
    *,
    expected_pack_id: str,
    pack_lemmas: set[str],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Walk a trace's steps; return (observed_ids, unresolved_ids).

    A lemma id is unresolved if:
      - it doesn't parse as ``<pack_id>:<lemma>``, OR
      - its pack_id != expected, OR
      - its lemma isn't in the pack's lexicon.
    """
    observed: list[str] = []
    unresolved: list[str] = []
    for step in trace.steps:
        lemma_id = step.pack_lemma_id
        observed.append(lemma_id)
        parsed = _parse_lemma_id(lemma_id)
        if parsed is None:
            unresolved.append(lemma_id)
            continue
        pack_id, lemma = parsed
        if pack_id != expected_pack_id or lemma not in pack_lemmas:
            unresolved.append(lemma_id)
    return tuple(observed), tuple(unresolved)


def _solve_case(problem: str) -> SolutionTrace | None:
    """Re-run the candidate-graph pipeline on a case's problem string.

    Returns the trace iff the pipeline admits AND solves; ``None`` for
    refused cases (those are skipped by the auditor — obligation #10
    only applies to cases that *did* produce a trace).
    """
    cg = parse_and_solve(problem)
    if not cg.is_admitted:
        return None
    assert cg.selected_graph is not None
    try:
        return solve(cg.selected_graph)
    except SolveError:
        return None


def validate_lane(
    *,
    lane_id: str = "B3_bounded_grammar",
    cases_path: Path = DEFAULT_B3_CASES,
    pack_id: str = DEFAULT_MATH_PACK_ID,
    lexicon_path: Path = DEFAULT_MATH_LEXICON,
) -> PackProvenanceReport:
    """Validate obligation #10 on a B-lane.

    For each case in the lane: re-run the pipeline, collect every
    solver step's ``pack_lemma_id``, and verify each parses + resolves
    to a lemma in the on-disk pack lexicon.

    Returns ``obligation_10_passed = True`` iff every case that
    produced a trace had every step's pack_lemma_id resolve cleanly.
    Refused cases are skipped (no trace to validate).
    """
    try:
        pack_lemmas = _load_lexicon_lemmas(lexicon_path)
    except PackProvenanceError as exc:
        return PackProvenanceReport(
            pack_id=pack_id,
            lane_id=lane_id,
            cases_total=0,
            cases_validated=0,
            cases_skipped_unsolved=0,
            cases_violated=0,
            obligation_10_passed=False,
            distinct_lemma_ids_observed=(),
            distinct_lemma_ids_in_pack=(),
            per_case=(),
            refusal_reason=str(exc),
        )

    if not cases_path.exists():
        return PackProvenanceReport(
            pack_id=pack_id,
            lane_id=lane_id,
            cases_total=0,
            cases_validated=0,
            cases_skipped_unsolved=0,
            cases_violated=0,
            obligation_10_passed=False,
            distinct_lemma_ids_observed=(),
            distinct_lemma_ids_in_pack=tuple(sorted(pack_lemmas)),
            per_case=(),
            refusal_reason=f"cases file not found: {cases_path}",
        )

    cases = [
        json.loads(line)
        for line in cases_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    per_case: list[CaseProvenance] = []
    observed_all: set[str] = set()
    validated = skipped = violated = 0

    for case in cases:
        case_id = case.get("case_id", "")
        problem = case.get("problem", "")
        expected = case.get("expected", "solved_correct")
        # Refusal-expected cases never produce a trace by design.
        if expected == "refused":
            per_case.append(CaseProvenance(
                case_id=case_id,
                outcome="skipped_unsolved",
                step_count=0,
                pack_lemma_ids=(),
                unresolved_lemma_ids=(),
                reason="case expected to refuse",
            ))
            skipped += 1
            continue

        trace = _solve_case(problem)
        if trace is None:
            per_case.append(CaseProvenance(
                case_id=case_id,
                outcome="skipped_unsolved",
                step_count=0,
                pack_lemma_ids=(),
                unresolved_lemma_ids=(),
                reason="pipeline did not produce a trace",
            ))
            skipped += 1
            continue

        observed, unresolved = _validate_trace(
            trace, expected_pack_id=pack_id, pack_lemmas=pack_lemmas,
        )
        observed_all.update(observed)
        if unresolved:
            per_case.append(CaseProvenance(
                case_id=case_id,
                outcome="violated",
                step_count=len(trace.steps),
                pack_lemma_ids=observed,
                unresolved_lemma_ids=unresolved,
                reason=(
                    f"{len(unresolved)} step(s) with unresolved pack_lemma_id "
                    f"(expected pack_id {pack_id!r})"
                ),
            ))
            violated += 1
        else:
            per_case.append(CaseProvenance(
                case_id=case_id,
                outcome="validated",
                step_count=len(trace.steps),
                pack_lemma_ids=observed,
                unresolved_lemma_ids=(),
            ))
            validated += 1

    return PackProvenanceReport(
        pack_id=pack_id,
        lane_id=lane_id,
        cases_total=len(cases),
        cases_validated=validated,
        cases_skipped_unsolved=skipped,
        cases_violated=violated,
        obligation_10_passed=(violated == 0 and validated > 0),
        distinct_lemma_ids_observed=tuple(sorted(observed_all)),
        distinct_lemma_ids_in_pack=tuple(
            sorted(f"{pack_id}:{lemma}" for lemma in pack_lemmas)
        ),
        per_case=tuple(per_case),
        refusal_reason=(
            "" if violated == 0 and validated > 0
            else (
                f"{violated} case(s) with unresolved pack_lemma_id"
                if violated > 0
                else "no case produced a trace to validate"
            )
        ),
    )


def emit_provenance_report(
    report: PackProvenanceReport, out_path: Path,
) -> None:
    """Write the deterministic obligation-#10 audit report."""
    out_path.write_text(
        json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

"""Contemplation v0 pass manager (N6) — a single bounded pass chain.

```text
Pass 1  route the problem across the R1/R2 setup compilers   (N3)
Pass 2  classify + enrich each attempt with its failure family (N4)
Pass 3  decide the terminal state
Pass 4  optionally emit a proposal-only artifact              (N5)
```

No loops, no recursion, no background daemon, no L10 runtime — one bounded pass that ends in
exactly one `Terminal`. The recursive "reread with findings" loop is deferred until we have
proof the classifications are useful.

The load-bearing rule: a problem that one organ recognizes as a **substantive boundary** (a
correct wrong=0 refusal) must NEVER generate a proposal merely because the *other* organ refused
with a growth reason. So classification is **boundary-first**, and `input_shape` ("this organ does
not recognize the shape") is treated as non-blocking, not as a boundary. Proposals are emitted
only for genuine growth-surface gaps with no substantive boundary in play — and even then only
proposal-only artifacts (N5), never a mounted change.

Off-serving: imports the R1/R2 organs (`generate`) + the comprehension-attempt layer (`core`);
imports no `evals`, no `generate.derivation`, no `core.reliability_gate`. In v0 the R1 numeric
answer is the eval lane's domain — a routed R1 setup is `SOLVED_VERIFIED` (admissible,
forward-substitutable by construction); R2 is solved + verified end to end here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, TYPE_CHECKING

from core.comprehension_attempt import (
    ComprehensionAttempt,
    cmb_is_authoritative,
    cmb_reason,
    emit_proposal,
    enrich_family,
    family_for_reason,
    route_setup,
)
from generate.answer_choices.verify import verify_answer_choice
from generate.combined_rate_comprehension.reader import read_combined_rate_problem
from generate.combined_rate_comprehension.solver import solve_combined_rate
from generate.constraint_comprehension.reader import read_constraint_problem
from generate.constraint_comprehension.solver import answer_constraint_problem
from generate.rate_comprehension.reader import read_rate_problem
from generate.rate_comprehension.solver import solve_rate
from generate.contemplation.findings import Finding, Terminal
from generate.meaning_graph.reader import Refusal

if TYPE_CHECKING:
    from core.epistemic_disclosure.limitation import LimitationAssessment
    from core.epistemic_questions.delivery import DeliveryOutcome

#: Substantive boundaries that are *recognized-but-unsupported* capabilities (not hard errors).
_UNSUPPORTED_FAMILIES = frozenset(
    {
        "unsupported_system_size",
        "unsupported_clause_shape",
        "unsupported_rate_duration",
    }
)
# Note: ``unsupported_temporal_state`` is deliberately NOT here — its clock-marker detector can
# fire on non-rate text, so it is a generic REFUSED_KNOWN_BOUNDARY, not a recognized-rate-capability.
#: The non-substantive "this organ does not recognize the shape" family — never blocks a proposal.
_NOT_MY_DOMAIN = "input_shape"


@dataclass(frozen=True, slots=True)
class ContemplationResult:
    """The outcome of one bounded contemplation pass."""

    terminal: Terminal
    findings: tuple[Finding, ...]
    attempts: tuple[ComprehensionAttempt, ...]
    selected_organ: str | None = None
    answer: int | None = None
    family: str | None = None
    proposal_path: str | None = None
    message: str | None = None


def _delivery_outcome_for_limitation(assessment: LimitationAssessment) -> DeliveryOutcome:
    """Helper to delegate to deliver_ask, pure and testable."""
    from core.epistemic_questions.delivery import deliver_ask
    return deliver_ask(assessment)


def _handle_ask_delivery(
    assessment: LimitationAssessment,
    family_name: str,
    findings: list[Finding],
    attempts: tuple[ComprehensionAttempt, ...],
    text: str,
    proposal_root: Path | None,
    question_root: Path | None,
    exercise_ask: bool,
    selected_organ: str | None = None,
) -> ContemplationResult:
    outcome = _delivery_outcome_for_limitation(assessment)
    if outcome.terminal == Terminal.QUESTION_NEEDED:
        assert outcome.question is not None
        import json
        from core.epistemic_questions.delivery import question_path

        path = question_path(outcome.question, question_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(outcome.question.to_json_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )

        findings.append(Finding("ask", f"emitted question-only {assessment.blocking_reason}"))
        findings.append(Finding("terminal", Terminal.QUESTION_NEEDED.value))
        return ContemplationResult(
            Terminal.QUESTION_NEEDED, tuple(findings), attempts,
            selected_organ=selected_organ, family=family_name,
            proposal_path=str(path),
        )
    else:
        findings.append(Finding("ask", f"unrenderable ask: {outcome.fallback_reason}"))
        findings.append(Finding("terminal", outcome.terminal.value))
        if outcome.terminal == Terminal.PROPOSAL_EMITTED:
            from core.comprehension_attempt.failure_family import family_by_name
            family_obj = family_by_name(family_name)
            if family_obj is not None:
                path = emit_proposal(text, family_obj, attempts, root=proposal_root)
                return ContemplationResult(
                    Terminal.PROPOSAL_EMITTED, tuple(findings), attempts,
                    selected_organ=selected_organ, family=family_name,
                    proposal_path=str(path) if path else None,
                )
        return ContemplationResult(
            outcome.terminal, tuple(findings), attempts,
            selected_organ=selected_organ, family=family_name,
        )


def contemplate(
    text: str,
    *,
    options: dict[str, Any] | None = None,
    answer_key: str | None = None,
    proposal_root: Path | None = None,
    question_root: Path | None = None,
    case_id: str | None = None,
    exercise_ask: bool = False,
) -> ContemplationResult:
    """Run one bounded contemplation pass over *text*."""
    findings: list[Finding] = []

    # Pass 1 — route.
    route = route_setup(text, case_id=case_id)
    findings.append(Finding("route", f"status={route.status}"))

    # Pass 2 — classify + enrich.
    attempts = tuple(enrich_family(a) for a in route.attempts)
    findings.append(
        Finding(
            "classify",
            "; ".join(
                f"{a.organ}:{a.outcome}:{a.family or a.refusal_reason or '-'}" for a in attempts
            ),
        )
    )

    # Pass 3/4 — terminal (+ maybe emit).
    if route.status == "ambiguous":
        findings.append(Finding("terminal", Terminal.AMBIGUOUS_ORGAN.value))
        return ContemplationResult(Terminal.AMBIGUOUS_ORGAN, tuple(findings), attempts)

    if route.status == "routed":
        assert route.selected is not None
        if route.selected.organ == "r2_constraints":
            return _solve_and_verify_r2(text, options, answer_key, findings, attempts, proposal_root, question_root, exercise_ask)
        if route.selected.organ == "r3_rate":
            return _solve_and_verify_r3(text, options, answer_key, findings, attempts, proposal_root, question_root, exercise_ask)
        if route.selected.organ == "r4_combined_rate":
            return _solve_and_verify_cmb(text, options, answer_key, findings, attempts, proposal_root, question_root, exercise_ask)
        findings.append(Finding("solve", "r1 admissible setup (numeric answer is the eval lane in v0)"))
        findings.append(Finding("terminal", Terminal.SOLVED_VERIFIED.value))
        return ContemplationResult(
            Terminal.SOLVED_VERIFIED, tuple(findings), attempts, selected_organ="r1_quantitative"
        )

    # route.status == "all_refused"
    return _classify_all_refused(text, attempts, findings, proposal_root, question_root, exercise_ask)


def _solve_and_verify_r2(
    text: str,
    options: dict[str, Any] | None,
    answer_key: str | None,
    findings: list[Finding],
    attempts: tuple[ComprehensionAttempt, ...],
    proposal_root: Path | None,
    question_root: Path | None,
    exercise_ask: bool,
) -> ContemplationResult:
    problem = read_constraint_problem(text)
    assert not isinstance(problem, Refusal)  # routed => the reader admitted a setup
    value = answer_constraint_problem(problem)
    if isinstance(value, Refusal):
        findings.append(Finding("solve", f"solver refused: {value.reason}"))
        from core.comprehension_attempt.failure_family import family_by_name
        from core.epistemic_disclosure.limitation import assess_from_family
        family_obj = family_by_name(value.reason)
        if family_obj is not None:
            assessment = assess_from_family(family_obj)
            if assessment.resolution_action == "ask_question":
                if exercise_ask:
                    return _handle_ask_delivery(
                        assessment, family_obj.name, findings, attempts, text, proposal_root, question_root, exercise_ask,
                        selected_organ="r2_constraints"
                    )
        findings.append(Finding("terminal", Terminal.REFUSED_KNOWN_BOUNDARY.value))
        return ContemplationResult(
            Terminal.REFUSED_KNOWN_BOUNDARY, tuple(findings), attempts,
            selected_organ="r2_constraints", family=_family_name(value.reason),
        )
    if options is not None:
        verdict = verify_answer_choice(value, options, answer_key, noun=problem.query.unit)
        if isinstance(verdict, Refusal):
            findings.append(Finding("verify", f"answer-choice refused: {verdict.reason}"))
            findings.append(Finding("terminal", Terminal.REFUSED_KNOWN_BOUNDARY.value))
            return ContemplationResult(
                Terminal.REFUSED_KNOWN_BOUNDARY, tuple(findings), attempts,
                selected_organ="r2_constraints", answer=value,
            )
        if verdict.status == "contradiction":
            findings.append(Finding("verify", verdict.message))
            findings.append(Finding("terminal", Terminal.CONTRADICTION_DETECTED.value))
            return ContemplationResult(
                Terminal.CONTRADICTION_DETECTED, tuple(findings), attempts,
                selected_organ="r2_constraints", answer=value,
                family="answer_key_contradiction", message=verdict.message,
            )
        findings.append(Finding("verify", verdict.message))
    findings.append(Finding("solve", f"value={value}"))
    findings.append(Finding("terminal", Terminal.SOLVED_VERIFIED.value))
    return ContemplationResult(
        Terminal.SOLVED_VERIFIED, tuple(findings), attempts,
        selected_organ="r2_constraints", answer=value,
    )


def _solve_and_verify_r3(
    text: str,
    options: dict[str, Any] | None,
    answer_key: str | None,
    findings: list[Finding],
    attempts: tuple[ComprehensionAttempt, ...],
    proposal_root: Path | None,
    question_root: Path | None,
    exercise_ask: bool,
) -> ContemplationResult:
    problem = read_rate_problem(text)
    assert not isinstance(problem, Refusal)  # routed => the reader admitted a setup
    value = solve_rate(problem)
    if isinstance(value, Refusal):
        findings.append(Finding("solve", f"solver refused: {value.reason}"))
        from core.comprehension_attempt.failure_family import family_by_name
        from core.epistemic_disclosure.limitation import assess_from_family
        family_obj = family_by_name(value.reason)
        if family_obj is not None:
            assessment = assess_from_family(family_obj)
            if assessment.resolution_action == "ask_question":
                if exercise_ask:
                    return _handle_ask_delivery(
                        assessment, family_obj.name, findings, attempts, text, proposal_root, question_root, exercise_ask,
                        selected_organ="r3_rate"
                    )
        findings.append(Finding("terminal", Terminal.REFUSED_KNOWN_BOUNDARY.value))
        return ContemplationResult(
            Terminal.REFUSED_KNOWN_BOUNDARY, tuple(findings), attempts,
            selected_organ="r3_rate", family=_family_name(value.reason),
        )
    if options is not None:
        verdict = verify_answer_choice(value, options, answer_key)
        if isinstance(verdict, Refusal):
            findings.append(Finding("verify", f"answer-choice refused: {verdict.reason}"))
            findings.append(Finding("terminal", Terminal.REFUSED_KNOWN_BOUNDARY.value))
            return ContemplationResult(
                Terminal.REFUSED_KNOWN_BOUNDARY, tuple(findings), attempts,
                selected_organ="r3_rate", answer=value,
            )
        if verdict.status == "contradiction":
            findings.append(Finding("verify", verdict.message))
            findings.append(Finding("terminal", Terminal.CONTRADICTION_DETECTED.value))
            return ContemplationResult(
                Terminal.CONTRADICTION_DETECTED, tuple(findings), attempts,
                selected_organ="r3_rate", answer=value,
                family="answer_key_contradiction", message=verdict.message,
            )
        findings.append(Finding("verify", verdict.message))
    findings.append(Finding("solve", f"value={value}"))
    findings.append(Finding("terminal", Terminal.SOLVED_VERIFIED.value))
    return ContemplationResult(
        Terminal.SOLVED_VERIFIED, tuple(findings), attempts,
        selected_organ="r3_rate", answer=value,
    )


def _solve_and_verify_cmb(
    text: str,
    options: dict[str, Any] | None,
    answer_key: str | None,
    findings: list[Finding],
    attempts: tuple[ComprehensionAttempt, ...],
    proposal_root: Path | None,
    question_root: Path | None,
    exercise_ask: bool,
) -> ContemplationResult:
    problem = read_combined_rate_problem(text)
    assert not isinstance(problem, Refusal)  # routed => the reader admitted a setup
    value = solve_combined_rate(problem)
    if isinstance(value, Refusal):
        # The prose WAS understood (reader setup_correct); the resulting math is outside v1's
        # answerable boundary. A solver refusal is a terminal boundary, never a proposal — and the
        # reason is namespaced cmb_* so it resolves to the CMB solver family, not R2/R3's.
        findings.append(Finding("solve", f"solver refused: {value.reason}"))
        from core.comprehension_attempt.failure_family import family_by_name
        from core.epistemic_disclosure.limitation import assess_from_family
        reason = cmb_reason(value.reason)
        family_obj = family_by_name(reason)
        if family_obj is not None:
            assessment = assess_from_family(family_obj)
            if assessment.resolution_action == "ask_question":
                if exercise_ask:
                    return _handle_ask_delivery(
                        assessment, family_obj.name, findings, attempts, text, proposal_root, question_root, exercise_ask,
                        selected_organ="r4_combined_rate"
                    )
        findings.append(Finding("terminal", Terminal.REFUSED_KNOWN_BOUNDARY.value))
        return ContemplationResult(
            Terminal.REFUSED_KNOWN_BOUNDARY, tuple(findings), attempts,
            selected_organ="r4_combined_rate", family=_family_name(cmb_reason(value.reason)),
        )
    if options is not None:
        verdict = verify_answer_choice(value, options, answer_key)
        if isinstance(verdict, Refusal):
            findings.append(Finding("verify", f"answer-choice refused: {verdict.reason}"))
            findings.append(Finding("terminal", Terminal.REFUSED_KNOWN_BOUNDARY.value))
            return ContemplationResult(
                Terminal.REFUSED_KNOWN_BOUNDARY, tuple(findings), attempts,
                selected_organ="r4_combined_rate", answer=value,
            )
        if verdict.status == "contradiction":
            findings.append(Finding("verify", verdict.message))
            findings.append(Finding("terminal", Terminal.CONTRADICTION_DETECTED.value))
            return ContemplationResult(
                Terminal.CONTRADICTION_DETECTED, tuple(findings), attempts,
                selected_organ="r4_combined_rate", answer=value,
                family="answer_key_contradiction", message=verdict.message,
            )
        findings.append(Finding("verify", verdict.message))
    findings.append(Finding("solve", f"value={value}"))
    findings.append(Finding("terminal", Terminal.SOLVED_VERIFIED.value))
    return ContemplationResult(
        Terminal.SOLVED_VERIFIED, tuple(findings), attempts,
        selected_organ="r4_combined_rate", answer=value,
    )


def _classify_all_refused(
    text: str,
    attempts: tuple[ComprehensionAttempt, ...],
    findings: list[Finding],
    proposal_root: Path | None,
    question_root: Path | None,
    exercise_ask: bool,
) -> ContemplationResult:
    # CMB-over-R3 precedence (family side): when CMB substantively recognized the text, R3's broader
    # partial classification is suppressed, so CMB's sharper diagnosis owns the terminal/proposal
    # (e.g. a reciprocal combined-rate text proposes a CMB fixture, not R3's rate_underdetermined).
    considered = attempts
    if cmb_is_authoritative(attempts):
        considered = tuple(a for a in attempts if a.organ != "r3_rate")

    families = [(a, family_for_reason(a.refusal_reason)) for a in considered]

    # Boundary-first: a substantive recognized boundary blocks any proposal or ASK.
    for _attempt, family in families:
        if family is not None and family.must_remain_refused and family.name != _NOT_MY_DOMAIN:
            terminal = (
                Terminal.REFUSED_UNSUPPORTED_FAMILY
                if family.name in _UNSUPPORTED_FAMILIES
                else Terminal.REFUSED_KNOWN_BOUNDARY
            )
            findings.append(Finding("terminal", f"{terminal.value} via {family.name}"))
            return ContemplationResult(terminal, tuple(findings), attempts, family=family.name)

    # Check for ASK delivery only after substantive boundaries are ruled out.
    for attempt in considered:
        from core.epistemic_disclosure.limitation import assess_from_attempt
        assessment = assess_from_attempt(attempt)
        if assessment is not None and assessment.resolution_action == "ask_question":
            if exercise_ask:
                return _handle_ask_delivery(
                    assessment, assessment.blocking_reason, findings, attempts, text, proposal_root, question_root, exercise_ask
                )

    # No substantive boundary: a genuine growth surface may emit a proposal-only artifact.
    for _attempt, family in families:
        if family is not None and family.proposal_allowed:
            path = emit_proposal(text, family, attempts, root=proposal_root)
            findings.append(Finding("propose", f"emitted proposal-only {family.name}"))
            findings.append(Finding("terminal", Terminal.PROPOSAL_EMITTED.value))
            return ContemplationResult(
                Terminal.PROPOSAL_EMITTED, tuple(findings), attempts,
                family=family.name, proposal_path=str(path) if path else None,
            )

    findings.append(Finding("terminal", Terminal.NO_PROGRESS.value))
    return ContemplationResult(Terminal.NO_PROGRESS, tuple(findings), attempts)


def _family_name(reason: str | None) -> str | None:
    family = family_for_reason(reason)
    return family.name if family is not None else None


__all__ = ["ContemplationResult", "contemplate"]

"""ADR-0117 — `SolutionTrace` verifier.

Re-applies every step of a :class:`SolutionTrace` from the input graph's
initial state and asserts byte-equal reproduction of ``answer_value``.
Hardens ADR-0114a Obligation #3 (every correct answer ships with a
replay-equal trace) at verifier fidelity.

The verifier is **independent of the solver**. The solver could be
buggy, malicious, or tampered with after the fact; the verifier
re-derives the answer using only:

- the input :class:`MathProblemGraph`
- the operation semantics documented in ADR-0116 (add / subtract /
  transfer / multiply / divide)
- the per-step ``actor`` / ``operand`` / ``target`` declared in each
  :class:`SolutionStep`

It then cross-checks against the values the trace claims:

- ``graph_canonical_hash`` matches a fresh hash of the graph
- per-step ``before_value`` / ``after_value`` match the verifier's
  fresh computation
- ``answer_value`` matches the verifier's resolved unknown
- every step's ``pack_lemma_id`` resolves to a real lexicon entry in
  the loaded pack (ADR-0114a Obligation #10 re-checked at verify
  time)

Any mismatch raises :class:`VerificationError` with the offending step
index and a typed reason. Same input always produces the same verdict
(determinism).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from generate.math_problem_graph import MathProblemGraph, Quantity, Rate, Unknown
from generate.math_solver import (
    REQUIRED_PACK_ID,
    SolutionStep,
    SolutionTrace,
    SolveError,
    _resolve_pack_lemmas,
)


class VerificationError(ValueError):
    """Raised when a trace fails to verify against its graph."""


@dataclass(frozen=True, slots=True)
class VerifierVerdict:
    """Typed outcome of a verification pass.

    ``passed`` is ``True`` only if every check held. ``reason`` is
    empty on pass and names the first failed check on fail. ``checks``
    records every check the verifier ran (in order) along with the
    pass/fail status of each, so external readers can audit which
    invariants held.
    """

    passed: bool
    reason: str
    checks: tuple[tuple[str, bool, str], ...]  # (name, passed, detail)
    graph_canonical_hash: str
    trace_answer_value: float
    verifier_answer_value: float

    def as_json(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "reason": self.reason,
            "checks": [
                {"name": n, "passed": p, "detail": d}
                for n, p, d in self.checks
            ],
            "graph_canonical_hash": self.graph_canonical_hash,
            "trace_answer_value": self.trace_answer_value,
            "verifier_answer_value": self.verifier_answer_value,
        }

    def canonical_bytes(self) -> bytes:
        return json.dumps(
            self.as_json(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")


def verify(graph: MathProblemGraph, trace: SolutionTrace) -> VerifierVerdict:
    """Run all verifier checks against ``trace`` for ``graph``.

    Pure function: same (graph, trace) -> byte-equal verdict.
    """
    checks: list[tuple[str, bool, str]] = []
    fresh_hash = hashlib.sha256(graph.canonical_bytes()).hexdigest()

    # Check 1 — graph hash matches
    hash_ok = trace.graph_canonical_hash == fresh_hash
    checks.append(
        (
            "graph_canonical_hash_matches",
            hash_ok,
            (
                ""
                if hash_ok
                else f"trace declares {trace.graph_canonical_hash!r} but graph hashes to {fresh_hash!r}"
            ),
        )
    )

    # Check 2 — pack id matches
    pack_ok = trace.pack_id == REQUIRED_PACK_ID
    checks.append(
        (
            "pack_id_matches",
            pack_ok,
            (
                ""
                if pack_ok
                else f"trace declares pack {trace.pack_id!r}, expected {REQUIRED_PACK_ID!r}"
            ),
        )
    )

    # Check 3 — pack lemma ids resolve
    try:
        pack_bindings = _resolve_pack_lemmas()
        lemmas_ok = True
        lemma_detail = ""
    except SolveError as exc:
        pack_bindings = {}
        lemmas_ok = False
        lemma_detail = f"pack resolution failed: {exc}"
    checks.append(("pack_lemmas_resolve", lemmas_ok, lemma_detail))

    # Check 4 — every step's pack_lemma_id matches the resolved binding
    if lemmas_ok:
        step_binding_ok = True
        step_binding_detail = ""
        for step in trace.steps:
            expected = pack_bindings.get(step.operation_kind)
            if expected is None:
                step_binding_ok = False
                step_binding_detail = (
                    f"step {step.step_index} declares unknown operation kind "
                    f"{step.operation_kind!r}"
                )
                break
            if step.pack_lemma_id != expected:
                step_binding_ok = False
                step_binding_detail = (
                    f"step {step.step_index} declares pack_lemma_id "
                    f"{step.pack_lemma_id!r}, expected {expected!r}"
                )
                break
        checks.append(
            (
                "step_pack_lemma_ids_match_bindings",
                step_binding_ok,
                step_binding_detail,
            )
        )
    else:
        checks.append(
            (
                "step_pack_lemma_ids_match_bindings",
                False,
                "skipped: pack resolution failed",
            )
        )

    # Check 5 — replay every step from the graph's initial state
    state: dict[tuple[str, str], float] = {}
    for p in graph.initial_state:
        state[(p.entity, p.quantity.unit)] = float(p.quantity.value)

    replay_ok = True
    replay_detail = ""
    for step in trace.steps:
        try:
            _verify_step(step, state)
        except VerificationError as exc:
            replay_ok = False
            replay_detail = str(exc)
            break
    checks.append(("step_replay_matches_before_after", replay_ok, replay_detail))

    # Check 6 — verifier's resolved answer matches trace's answer
    verifier_answer = _resolve_answer(
        Unknown(entity=trace.answer_entity, unit=trace.answer_unit), state
    )
    answer_ok = (
        replay_ok
        and verifier_answer is not None
        and verifier_answer == trace.answer_value
    )
    checks.append(
        (
            "answer_value_reproduces",
            answer_ok,
            (
                ""
                if answer_ok
                else (
                    f"verifier resolved {verifier_answer!r}, trace declared "
                    f"{trace.answer_value!r}"
                )
            ),
        )
    )

    all_passed = all(p for _, p, _ in checks)
    reason = ""
    if not all_passed:
        for name, p, detail in checks:
            if not p:
                reason = f"{name}: {detail}" if detail else name
                break

    return VerifierVerdict(
        passed=all_passed,
        reason=reason,
        checks=tuple(checks),
        graph_canonical_hash=fresh_hash,
        trace_answer_value=trace.answer_value,
        verifier_answer_value=(
            verifier_answer if verifier_answer is not None else float("nan")
        ),
    )


def _verify_step(step: SolutionStep, state: dict[tuple[str, str], float]) -> None:
    # apply_rate carries a Rate operand whose key shape differs from
    # Quantity (denominator_unit instead of unit). Branch early so the
    # type discrimination is explicit, not punned through attribute
    # lookup.
    if step.operation_kind == "apply_rate":
        _verify_apply_rate_step(step, state)
        return

    if not isinstance(step.operand, Quantity):
        raise VerificationError(
            f"step {step.step_index} kind={step.operation_kind!r} "
            f"requires Quantity operand; got {type(step.operand).__name__}"
        )
    key = (step.actor, step.operand.unit)
    fresh_before = state.get(key, 0.0)
    if fresh_before != step.before_value:
        raise VerificationError(
            f"step {step.step_index} declares before_value={step.before_value}, "
            f"verifier computed {fresh_before}"
        )
    v = float(step.operand.value)
    if step.operation_kind == "add":
        fresh_after = fresh_before + v
        state[key] = fresh_after
    elif step.operation_kind == "subtract":
        fresh_after = fresh_before - v
        state[key] = fresh_after
    elif step.operation_kind == "transfer":
        if step.target is None:
            raise VerificationError(
                f"step {step.step_index} kind=transfer has no target"
            )
        fresh_after = fresh_before - v
        state[key] = fresh_after
        tgt_key = (step.target, step.operand.unit)
        fresh_target_before = state.get(tgt_key, 0.0)
        if (
            step.target_before is None
            or fresh_target_before != step.target_before
        ):
            raise VerificationError(
                f"step {step.step_index} declares target_before="
                f"{step.target_before}, verifier computed {fresh_target_before}"
            )
        fresh_target_after = fresh_target_before + v
        state[tgt_key] = fresh_target_after
        if (
            step.target_after is None
            or fresh_target_after != step.target_after
        ):
            raise VerificationError(
                f"step {step.step_index} declares target_after="
                f"{step.target_after}, verifier computed {fresh_target_after}"
            )
    elif step.operation_kind == "multiply":
        fresh_after = fresh_before * v
        state[key] = fresh_after
    elif step.operation_kind == "divide":
        if v == 0:
            raise VerificationError(
                f"step {step.step_index} divides by zero"
            )
        fresh_after = fresh_before / v
        state[key] = fresh_after
    else:
        raise VerificationError(
            f"step {step.step_index} declares unknown kind {step.operation_kind!r}"
        )
    if fresh_after != step.after_value:
        raise VerificationError(
            f"step {step.step_index} declares after_value={step.after_value}, "
            f"verifier computed {fresh_after}"
        )


def _verify_apply_rate_step(
    step: SolutionStep, state: dict[tuple[str, str], float]
) -> None:
    """Verify an apply_rate step (ADR-0122).

    Re-applies the rate against the denominator-unit state, checks
    ``before_value`` / ``after_value`` byte-equal, writes the result
    to the numerator-unit key. The denominator-unit quantity is
    preserved (the actor still holds the input quantity after the
    derived value is computed).
    """
    if not isinstance(step.operand, Rate):
        raise VerificationError(
            f"step {step.step_index} kind=apply_rate requires Rate "
            f"operand; got {type(step.operand).__name__}"
        )
    rate = step.operand
    denom_key = (step.actor, rate.denominator_unit)
    if denom_key not in state:
        raise VerificationError(
            f"step {step.step_index} kind=apply_rate references "
            f"({step.actor!r}, {rate.denominator_unit!r}) which is not "
            f"in verifier state"
        )
    fresh_before = state[denom_key]
    if fresh_before != step.before_value:
        raise VerificationError(
            f"step {step.step_index} declares before_value="
            f"{step.before_value}, verifier computed {fresh_before}"
        )
    fresh_after = fresh_before * float(rate.value)
    if fresh_after != step.after_value:
        raise VerificationError(
            f"step {step.step_index} declares after_value="
            f"{step.after_value}, verifier computed {fresh_after}"
        )
    if step.target is not None:
        raise VerificationError(
            f"step {step.step_index} kind=apply_rate must not declare "
            f"a target; got {step.target!r}"
        )
    state[(step.actor, rate.numerator_unit)] = fresh_after


def _resolve_answer(
    unknown: Unknown, state: dict[tuple[str, str], float]
) -> float | None:
    if unknown.entity is None:
        return sum(v for (_, unit), v in state.items() if unit == unknown.unit)
    return state.get((unknown.entity, unknown.unit))

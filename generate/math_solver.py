"""ADR-0116 — Deterministic math solver over MathProblemGraph.

Consumes the typed graph produced by the ADR-0115 parser and emits a
:class:`SolutionTrace` — an ordered list of operation applications
ending at a numeric answer. Pure function: same graph always produces
the same trace; same trace replays to the same answer byte-equal.

Architectural commitments (ADR-0114a):

- **Obligation #3** — Every correct answer ships with a replay-equal
  trace. ``SolutionTrace.canonical_bytes()`` is byte-deterministic;
  ADR-0117 verifier replays the trace and reproduces ``answer_value``.
- **Obligation #4** — Refusal is first-class. Under-determined or
  inconsistent graphs raise :class:`SolveError` rather than producing
  a fabricated answer.
- **Obligation #9** — Determinism. Pure-Python integer/float arithmetic
  in a fixed order; no platform-dependent state.
- **Obligation #10** — Operation provenance via the pack. Every step
  in the trace carries a ``pack_lemma_id`` resolved at solve time from
  the loaded ``en_arithmetic_v1`` pack. If the pack does not provide
  the required lemma, solve fails loudly. Changing the pack changes
  the resolved set deterministically.

The "expert" tier (ADR-0120) is not in scope here; ADR-0116 is the
Phase 2 substrate the eventual capability claim will rest on.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from generate.math_problem_graph import (
    Comparison,
    MathProblemGraph,
    Operation,
    PartitionChunk,
    Quantity,
    Rate,
    Unknown,
)


REQUIRED_PACK_ID: str = "en_arithmetic_v1"

# Operation kind → required pack lemma. The solver MUST resolve every
# operation through one of these lemmas; if the pack does not provide
# the lemma, the solver fails. This is the load-bearing pack-binding
# discharge of ADR-0114a Obligation #10.
_OPERATION_REQUIRED_LEMMAS: dict[str, str] = {
    "add": "add",
    "subtract": "subtract",
    "transfer": "transfer",
    "multiply": "multiply",
    "divide": "divide",
    "apply_rate": "apply_rate",
    "compare_additive": "compare_additive",
    "compare_multiplicative": "compare_multiplicative",
    "unit_partition": "divide",
}


class SolveError(ValueError):
    """Raised when a graph cannot be solved (typed refusal).

    Refusal reasons:
        - the arithmetic pack is missing or does not provide a required
          lemma (load-bearing pack-binding failure)
        - the unknown references state that was never asserted by any
          ``InitialPossession`` and never produced by any operation
        - division by zero
        - any other under-determined-graph condition
    """


@dataclass(frozen=True, slots=True)
class SolutionStep:
    """One operation application in the trace.

    Every field is determined-by-construction from the graph + prior
    steps; no field is computed via floating-point inexactness in a
    way that varies across platforms. The verifier (ADR-0117) re-walks
    the steps and re-applies the operation semantics; the resulting
    answer must equal ``answer_value`` byte-equal.
    """

    step_index: int
    operation_kind: str
    pack_lemma_id: str
    actor: str
    operand: "Quantity | Rate | Comparison"
    target: str | None
    before_value: float
    after_value: float
    target_before: float | None
    target_after: float | None

    def as_json(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "step_index": self.step_index,
            "operation_kind": self.operation_kind,
            "pack_lemma_id": self.pack_lemma_id,
            "actor": self.actor,
            "operand": self.operand.as_json(),
            "before_value": self.before_value,
            "after_value": self.after_value,
        }
        if self.target is not None:
            d["target"] = self.target
            d["target_before"] = self.target_before
            d["target_after"] = self.target_after
        return d


@dataclass(frozen=True, slots=True)
class SolutionTrace:
    """Replayable record of how the answer was derived.

    Carries:

    - ``pack_id`` + ``pack_lemma_ids``: which arithmetic pack provided
      the operation vocabulary (ADR-0114a Obligation #10).
    - ``graph_canonical_hash``: SHA-256 of the input graph's canonical
      bytes — pins which problem this trace solves.
    - ``steps``: per-operation record in source order.
    - ``answer_value`` + ``answer_unit`` + ``answer_entity``: the final
      resolved unknown.
    """

    pack_id: str
    graph_canonical_hash: str
    steps: tuple[SolutionStep, ...]
    answer_value: float
    answer_unit: str
    answer_entity: str | None

    def as_json(self) -> dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "graph_canonical_hash": self.graph_canonical_hash,
            "steps": [s.as_json() for s in self.steps],
            "answer_value": self.answer_value,
            "answer_unit": self.answer_unit,
            "answer_entity": self.answer_entity,
        }

    def canonical_bytes(self) -> bytes:
        return json.dumps(
            self.as_json(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")


def _resolve_pack_lemmas() -> dict[str, str]:
    """Load the arithmetic pack and resolve operation kinds to lemma ids.

    Returns a dict mapping operation kind → pack-qualified lemma id of
    the form ``"<pack_id>:<lemma>"``. Raises :class:`SolveError` if the
    pack cannot be loaded or if any required lemma is missing.

    Per ADR-0114a Obligation #10, this dispatch is load-bearing: the
    solver cannot emit a trace step without a resolved pack-lemma id.
    """
    try:
        from language_packs.compiler import load_pack_entries
    except ImportError as exc:
        raise SolveError(
            f"cannot import language_packs.compiler: {exc}"
        ) from exc

    try:
        entries = load_pack_entries(REQUIRED_PACK_ID)
    except Exception as exc:
        raise SolveError(
            f"required arithmetic pack {REQUIRED_PACK_ID!r} failed to load: {exc}"
        ) from exc

    lemma_to_entry: dict[str, str] = {}
    for entry in entries:
        lemma_to_entry[entry.lemma] = entry.entry_id

    resolved: dict[str, str] = {}
    for op_kind, required_lemma in _OPERATION_REQUIRED_LEMMAS.items():
        if required_lemma not in lemma_to_entry:
            raise SolveError(
                f"pack {REQUIRED_PACK_ID!r} missing required lemma "
                f"{required_lemma!r} for operation kind {op_kind!r}"
            )
        resolved[op_kind] = f"{REQUIRED_PACK_ID}:{required_lemma}"
    return resolved


def solve(graph: MathProblemGraph) -> SolutionTrace:
    """Solve ``graph`` and return its :class:`SolutionTrace`.

    Pure function — no I/O, no global state, no randomness. Same graph
    in produces a byte-equal trace out.

    Raises :class:`SolveError` on:
        - missing or incomplete arithmetic pack
        - division by zero
        - the unknown referencing state that does not exist after all
          operations are applied
    """
    pack_bindings = _resolve_pack_lemmas()
    state: dict[tuple[str, str], float] = {}
    for p in graph.initial_state:
        state[(p.entity, p.quantity.unit)] = float(p.quantity.value)

    steps: list[SolutionStep] = []
    for index, op in enumerate(graph.operations):
        step = _apply(op, index, state, pack_bindings)
        steps.append(step)

    answer_value, answer_unit = _resolve_unknown(graph.unknown, state)

    return SolutionTrace(
        pack_id=REQUIRED_PACK_ID,
        graph_canonical_hash=hashlib.sha256(graph.canonical_bytes()).hexdigest(),
        steps=tuple(steps),
        answer_value=answer_value,
        answer_unit=answer_unit,
        answer_entity=graph.unknown.entity,
    )


def _apply(
    op: Operation,
    index: int,
    state: dict[tuple[str, str], float],
    pack_bindings: Mapping[str, str],
) -> SolutionStep:
    # Kind-discriminated early returns for operations carrying non-Quantity
    # operands: apply_rate (ADR-0122) uses Rate; compare_* (ADR-0123) uses
    # Comparison. Handle each on its own branch so the type discrimination
    # is explicit, not punned through a duck-typed attribute lookup.
    if op.kind == "apply_rate":
        return _apply_rate(op, index, state, pack_bindings)
    if op.kind == "compare_additive":
        return _apply_compare_additive(op, index, state, pack_bindings)
    if op.kind == "compare_multiplicative":
        return _apply_compare_multiplicative(op, index, state, pack_bindings)
    if op.kind == "unit_partition":
        return _apply_unit_partition(op, index, state, pack_bindings)

    if not isinstance(op.operand, Quantity):
        raise SolveError(
            f"operation kind {op.kind!r} at step {index} requires a "
            f"Quantity operand; got {type(op.operand).__name__}"
        )
    key = (op.actor, op.operand.unit)
    before = state.get(key, 0.0)
    v = float(op.operand.value)
    target_before: float | None = None
    target_after: float | None = None

    if op.kind == "add":
        after = before + v
        state[key] = after
    elif op.kind == "subtract":
        after = before - v
        state[key] = after
    elif op.kind == "transfer":
        if op.target is None:
            raise SolveError(
                f"transfer operation at step {index} has no target"
            )
        after = before - v
        state[key] = after
        tgt_key = (op.target, op.operand.unit)
        target_before = state.get(tgt_key, 0.0)
        target_after = target_before + v
        state[tgt_key] = target_after
    elif op.kind == "multiply":
        after = before * v
        state[key] = after
    elif op.kind == "divide":
        if v == 0:
            raise SolveError(
                f"division by zero in operation at step {index}"
            )
        after = before / v
        state[key] = after
    else:
        raise SolveError(
            f"unknown operation kind {op.kind!r} at step {index}"
        )

    return SolutionStep(
        step_index=index,
        operation_kind=op.kind,
        pack_lemma_id=pack_bindings[op.kind],
        actor=op.actor,
        operand=op.operand,
        target=op.target,
        before_value=before,
        after_value=after,
        target_before=target_before,
        target_after=target_after,
    )


def _apply_rate(
    op: Operation,
    index: int,
    state: dict[tuple[str, str], float],
    pack_bindings: Mapping[str, str],
) -> SolutionStep:
    """Apply a rate operation (ADR-0122).

    Reads the actor's quantity in ``rate.denominator_unit``, multiplies
    by ``rate.value``, and stores the result under
    ``(actor, rate.numerator_unit)``. The denominator-unit quantity is
    **not** consumed — the actor still holds the same number of apples
    after computing how much they spent on them. This matches
    natural-language semantics and is how the parser's reverse
    ("orphan rate") refusal is consistent with the solver's forward
    application.

    Refuses (SolveError) when the actor has no recorded quantity in
    the rate's denominator unit — the question is asking about a rate
    application that the prior statements did not set up.
    """
    if not isinstance(op.operand, Rate):
        raise SolveError(
            f"apply_rate at step {index} requires a Rate operand; "
            f"got {type(op.operand).__name__}"
        )
    rate = op.operand
    denom_key = (op.actor, rate.denominator_unit)
    if denom_key not in state:
        raise SolveError(
            f"apply_rate at step {index} requires actor {op.actor!r} "
            f"to hold a quantity in {rate.denominator_unit!r}, but no "
            f"such state exists"
        )
    before = state[denom_key]
    after = before * float(rate.value)
    numer_key = (op.actor, rate.numerator_unit)
    state[numer_key] = after
    return SolutionStep(
        step_index=index,
        operation_kind=op.kind,
        pack_lemma_id=pack_bindings[op.kind],
        actor=op.actor,
        operand=rate,
        target=None,
        before_value=before,
        after_value=after,
        target_before=None,
        target_after=None,
    )


def _apply_compare_additive(
    op: Operation,
    index: int,
    state: dict[tuple[str, str], float],
    pack_bindings: Mapping[str, str],
) -> SolutionStep:
    """Apply an additive comparison (ADR-0123).

    "Alice has 3 more apples than Bob" → state[(Alice, apples)] =
    state[(Bob, apples)] + 3. Refuses on: missing reference state in
    delta.unit, overwrite of existing actor state, negative result.
    """
    if not isinstance(op.operand, Comparison):
        raise SolveError(
            f"compare_additive at step {index} requires a Comparison "
            f"operand; got {type(op.operand).__name__}"
        )
    cmp = op.operand
    if cmp.delta is None:
        raise SolveError(
            f"compare_additive at step {index} requires Comparison.delta; "
            f"got None"
        )
    unit = cmp.delta.unit
    ref_key = (cmp.reference_actor, unit)
    if ref_key not in state:
        raise SolveError(
            f"compare_additive at step {index} requires reference actor "
            f"{cmp.reference_actor!r} to hold a quantity in {unit!r}, "
            f"but no such state exists"
        )
    actor_key = (op.actor, unit)
    if actor_key in state:
        raise SolveError(
            f"compare_additive at step {index} would overwrite existing "
            f"state for actor {op.actor!r} in {unit!r}; refuse rather "
            f"than silently redeclare"
        )
    ref_value = state[ref_key]
    delta_v = float(cmp.delta.value)
    if cmp.direction == "more":
        after = ref_value + delta_v
    elif cmp.direction == "fewer":
        after = ref_value - delta_v
    else:
        raise SolveError(
            f"compare_additive at step {index} got unexpected direction "
            f"{cmp.direction!r}; expected 'more' or 'fewer'"
        )
    if after < 0:
        raise SolveError(
            f"compare_additive at step {index} would yield negative "
            f"quantity {after!r} for actor {op.actor!r} in {unit!r}; "
            f"refuse rather than emit a nonsensical answer"
        )
    state[actor_key] = after
    return SolutionStep(
        step_index=index,
        operation_kind=op.kind,
        pack_lemma_id=pack_bindings[op.kind],
        actor=op.actor,
        operand=cmp,
        target=None,
        before_value=0.0,
        after_value=after,
        target_before=None,
        target_after=None,
    )


def _apply_unit_partition(
    op: Operation,
    index: int,
    state: dict[tuple[str, str], float],
    pack_bindings: Mapping[str, str],
) -> SolutionStep:
    """Apply a fixed-size unit partition (Gate A2a).

    Reads ``(actor, chunk.unit)`` from prior state, requires an exact
    integer quotient, and writes ``(actor, chunk.result_unit)``.
    The dividend-unit quantity is preserved (partition is derived state).
    """
    if not isinstance(op.operand, PartitionChunk):
        raise SolveError(
            f"unit_partition at step {index} requires a "
            f"PartitionChunk operand; got {type(op.operand).__name__}"
        )
    chunk = op.operand
    dividend_key = (op.actor, chunk.unit)
    if dividend_key not in state:
        raise SolveError(
            f"unit_partition at step {index} requires actor {op.actor!r} "
            f"to hold a quantity in {chunk.unit!r}, but no such state exists"
        )
    before = state[dividend_key]
    chunk_size = float(chunk.value)
    if chunk_size == 0:
        raise SolveError(
            f"unit_partition at step {index} refuses zero chunk size"
        )
    quotient = before / chunk_size
    if abs(quotient - round(quotient)) > 1e-9 or quotient <= 0:
        raise SolveError(
            f"unit_partition at step {index} requires an exact positive "
            f"integer quotient; got {quotient!r} from {before!r} / "
            f"{chunk_size!r}"
        )
    after = float(int(round(quotient)))
    result_key = (op.actor, chunk.result_unit)
    if result_key in state:
        raise SolveError(
            f"unit_partition at step {index} would overwrite existing state "
            f"for ({op.actor!r}, {chunk.result_unit!r}); refuse rather than "
            f"silently redeclare"
        )
    state[result_key] = after
    return SolutionStep(
        step_index=index,
        operation_kind=op.kind,
        pack_lemma_id=pack_bindings[op.kind],
        actor=op.actor,
        operand=chunk,
        target=None,
        before_value=before,
        after_value=after,
        target_before=None,
        target_after=None,
    )


def _apply_compare_multiplicative(
    op: Operation,
    index: int,
    state: dict[tuple[str, str], float],
    pack_bindings: Mapping[str, str],
) -> SolutionStep:
    """Apply a multiplicative comparison (ADR-0123).

    "Alice has 2 times as many apples as Bob" → state[(Alice, apples)]
    = state[(Bob, apples)] × 2. Unit comes from reference's state.
    Refuses on: no reference state, ambiguous (multi-unit) reference,
    overwrite of existing actor state.
    """
    if not isinstance(op.operand, Comparison):
        raise SolveError(
            f"compare_multiplicative at step {index} requires a "
            f"Comparison operand; got {type(op.operand).__name__}"
        )
    cmp = op.operand
    if cmp.factor is None:
        raise SolveError(
            f"compare_multiplicative at step {index} requires "
            f"Comparison.factor; got None"
        )
    ref_units = [
        unit for (entity, unit) in state if entity == cmp.reference_actor
    ]
    if not ref_units:
        raise SolveError(
            f"compare_multiplicative at step {index} requires reference "
            f"actor {cmp.reference_actor!r} to hold some quantity, but "
            f"no such state exists"
        )
    if len(set(ref_units)) > 1:
        raise SolveError(
            f"compare_multiplicative at step {index} is ambiguous: "
            f"reference actor {cmp.reference_actor!r} holds quantities "
            f"in multiple units {sorted(set(ref_units))!r}; refuse "
            f"rather than guess which unit the comparison applies to"
        )
    unit = ref_units[0]
    actor_key = (op.actor, unit)
    if actor_key in state:
        raise SolveError(
            f"compare_multiplicative at step {index} would overwrite "
            f"existing state for actor {op.actor!r} in {unit!r}; refuse "
            f"rather than silently redeclare"
        )
    ref_value = state[(cmp.reference_actor, unit)]
    after = ref_value * float(cmp.factor)
    state[actor_key] = after
    return SolutionStep(
        step_index=index,
        operation_kind=op.kind,
        pack_lemma_id=pack_bindings[op.kind],
        actor=op.actor,
        operand=cmp,
        target=None,
        before_value=0.0,
        after_value=after,
        target_before=None,
        target_after=None,
    )


def _resolve_unknown(
    unknown: Unknown, state: Mapping[tuple[str, str], float]
) -> tuple[float, str]:
    """Look up the answer the question asks for.

    For ``entity is None`` (total-across question), sums every state
    entry whose unit matches ``unknown.unit``. For a single-entity
    question, returns that entity's quantity of ``unknown.unit`` — or
    raises if no such state was ever asserted or produced.
    """
    if unknown.entity is None:
        total = sum(v for (_, unit), v in state.items() if unit == unknown.unit)
        return total, unknown.unit
    key = (unknown.entity, unknown.unit)
    if key not in state:
        raise SolveError(
            f"unknown references state ({unknown.entity!r}, {unknown.unit!r}) "
            f"that was never asserted or produced by any operation"
        )
    return state[key], unknown.unit

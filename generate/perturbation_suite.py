"""ADR-0125 — semantic perturbation suite for GSM8K-style dev cases.

This module builds on ADR-0118a's deterministic OOD surface generator.
It keeps every surface inside the ADR-0115 Phase 1.1 pattern registry
while applying semantic perturbations that either preserve the answer or
change the replayed trace in a predicted way.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from generate.math_parser import (
    _ADD_VERBS,
    _SUBTRACT_VERBS,
    _TRANSFER_VERBS,
)
from generate.math_problem_graph import (
    InitialPossession,
    MathProblemGraph,
    Operation,
    Quantity,
)
from generate.math_solver import SolutionTrace, solve
from generate.ood_surface_generator import (
    _ENTITY_REGISTRY,
    _entity_map,
    _number,
    _rename_graph,
    _render_graph,
    _surface_unit,
    _unit_map,
)


INVARIANCE_PRESERVING = "invariance_preserving"
INVARIANCE_BREAKING = "invariance_breaking"

TRANSFORMS: tuple[str, ...] = (
    "rename_entities",
    "rename_units",
    "reorder_independent_initial_possessions",
    "reorder_independent_operations",
    "replace_verb_with_synonym",
    "add_zero_quantity_entity",
    "swap_non_commuting_operations",
)


@dataclass(frozen=True, slots=True)
class Perturbation:
    original_id: str
    perturbation_id: str
    kind: str
    transform: str
    transform_params: dict[str, Any]
    problem_text: str
    expected_graph: MathProblemGraph
    expected_answer: float
    expected_unit: str


def generate_perturbations(
    problem: str,
    ground_truth_graph: MathProblemGraph,
    *,
    seed: int,
) -> list[Perturbation]:
    """Return one semantic perturbation per applicable transform.

    Inapplicable transforms are skipped; call ``skip_reasons`` with the
    same inputs to report those skips at scoring time.
    """
    if not isinstance(problem, str) or not problem.strip():
        raise ValueError("problem must be a non-empty string")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer")

    original_id = _original_id_from_seed(seed)
    builders = (
        _rename_entities,
        _rename_units,
        _reorder_independent_initial_possessions,
        _reorder_independent_operations,
        _replace_verb_with_synonym,
        _add_zero_quantity_entity,
        _swap_non_commuting_operations,
    )
    perturbations: list[Perturbation] = []
    for build in builders:
        perturbation = build(
            problem=problem,
            graph=ground_truth_graph,
            original_id=original_id,
            seed=seed,
        )
        if perturbation is not None:
            perturbations.append(perturbation)
    return perturbations


def skip_reasons(
    problem: str,
    ground_truth_graph: MathProblemGraph,
    *,
    seed: int,
) -> dict[str, str]:
    """Return deterministic skip reasons for inapplicable transforms."""
    del problem, seed
    reasons: dict[str, str] = {}
    if len(ground_truth_graph.initial_state) < 2:
        reasons[
            "reorder_independent_initial_possessions"
        ] = "requires at least two initial possessions"
    if _independent_operation_order(ground_truth_graph) is None:
        reasons[
            "reorder_independent_operations"
        ] = "requires at least two pairwise independent operations"
    if _first_synonym_slot(ground_truth_graph) is None:
        reasons[
            "replace_verb_with_synonym"
        ] = "requires a first add/subtract/transfer operation"
    if _zero_entity_name(ground_truth_graph, 0) is None:
        reasons["add_zero_quantity_entity"] = "requires an unused registry entity"
    if _non_commuting_swap(ground_truth_graph) is None:
        reasons[
            "swap_non_commuting_operations"
        ] = "requires two same-entity operations whose swap changes trace"
    return reasons


def _rename_entities(
    *, problem: str, graph: MathProblemGraph, original_id: str, seed: int
) -> Perturbation:
    del problem
    entity_map = _entity_map(graph, seed)
    renamed = _rename_graph(graph, entity_map, {u: u for u in _ordered_units(graph)})
    return _perturbation(
        original_id=original_id,
        suffix="rename_ent",
        kind=INVARIANCE_PRESERVING,
        transform="rename_entities",
        params={"entity_map": entity_map},
        graph=renamed,
    )


def _rename_units(
    *, problem: str, graph: MathProblemGraph, original_id: str, seed: int
) -> Perturbation:
    del problem
    unit_map = _unit_map(graph, seed)
    renamed = _rename_graph(graph, {e: e for e in graph.entities}, unit_map)
    return _perturbation(
        original_id=original_id,
        suffix="rename_unit",
        kind=INVARIANCE_PRESERVING,
        transform="rename_units",
        params={"unit_map": unit_map},
        graph=renamed,
    )


def _reorder_independent_initial_possessions(
    *, problem: str, graph: MathProblemGraph, original_id: str, seed: int
) -> Perturbation | None:
    del problem, seed
    if len(graph.initial_state) < 2:
        return None
    reordered_initial = tuple(reversed(graph.initial_state))
    reordered_entities = _entities_for(
        initial_state=reordered_initial,
        operations=graph.operations,
        fallback=graph.entities,
    )
    reordered = MathProblemGraph(
        entities=reordered_entities,
        initial_state=reordered_initial,
        operations=graph.operations,
        unknown=graph.unknown,
    )
    return _perturbation(
        original_id=original_id,
        suffix="reorder_init",
        kind=INVARIANCE_PRESERVING,
        transform="reorder_independent_initial_possessions",
        params={"order": "reversed", "count": len(graph.initial_state)},
        graph=reordered,
    )


def _reorder_independent_operations(
    *, problem: str, graph: MathProblemGraph, original_id: str, seed: int
) -> Perturbation | None:
    del problem, seed
    new_order = _independent_operation_order(graph)
    if new_order is None:
        return None
    reordered = MathProblemGraph(
        entities=graph.entities,
        initial_state=graph.initial_state,
        operations=new_order,
        unknown=graph.unknown,
    )
    return _perturbation(
        original_id=original_id,
        suffix="reorder_ops",
        kind=INVARIANCE_PRESERVING,
        transform="reorder_independent_operations",
        params={"order": "reversed", "count": len(graph.operations)},
        graph=reordered,
    )


def _replace_verb_with_synonym(
    *, problem: str, graph: MathProblemGraph, original_id: str, seed: int
) -> Perturbation | None:
    slot = _first_synonym_slot(graph)
    if slot is None:
        return None
    index, verbs = slot
    original_verb = _first_operation_verb(problem)
    verb = _choose_synonym(verbs, original_verb, seed)
    if verb is None:
        return None
    params = {
        "operation_index": index,
        "replacement_verb": verb,
        "original_verb": original_verb,
    }
    return _perturbation(
        original_id=original_id,
        suffix="verb_syn",
        kind=INVARIANCE_PRESERVING,
        transform="replace_verb_with_synonym",
        params=params,
        graph=graph,
        problem_text=_render_graph_with_operation_verbs(graph, {index: verb}),
    )


def _add_zero_quantity_entity(
    *, problem: str, graph: MathProblemGraph, original_id: str, seed: int
) -> Perturbation | None:
    del problem
    entity = _zero_entity_name(graph, seed)
    if entity is None:
        return None
    unit = graph.unknown.unit
    zero = InitialPossession(entity=entity, quantity=Quantity(value=0, unit=unit))
    expanded = MathProblemGraph(
        entities=(entity, *graph.entities),
        initial_state=(zero, *graph.initial_state),
        operations=graph.operations,
        unknown=graph.unknown,
    )
    return _perturbation(
        original_id=original_id,
        suffix="zero_entity",
        kind=INVARIANCE_PRESERVING,
        transform="add_zero_quantity_entity",
        params={"entity": entity, "quantity": 0, "unit": unit},
        graph=expanded,
    )


def _swap_non_commuting_operations(
    *, problem: str, graph: MathProblemGraph, original_id: str, seed: int
) -> Perturbation | None:
    del problem, seed
    swap = _non_commuting_swap(graph)
    if swap is None:
        return None
    i, j = swap
    operations = list(graph.operations)
    operations[i], operations[j] = operations[j], operations[i]
    swapped = MathProblemGraph(
        entities=graph.entities,
        initial_state=graph.initial_state,
        operations=tuple(operations),
        unknown=graph.unknown,
    )
    original_trace = solve(graph)
    expected_trace = solve(swapped)
    return _perturbation(
        original_id=original_id,
        suffix="swap_noncomm",
        kind=INVARIANCE_BREAKING,
        transform="swap_non_commuting_operations",
        params={
            "swapped_indices": [i, j],
            "original_answer": original_trace.answer_value,
            "original_trace_hash": _trace_hash(original_trace),
            "expected_trace_hash": _trace_hash(expected_trace),
        },
        graph=swapped,
    )


def _perturbation(
    *,
    original_id: str,
    suffix: str,
    kind: str,
    transform: str,
    params: dict[str, Any],
    graph: MathProblemGraph,
    problem_text: str | None = None,
) -> Perturbation:
    trace = solve(graph)
    return Perturbation(
        original_id=original_id,
        perturbation_id=f"{original_id}:{suffix}",
        kind=kind,
        transform=transform,
        transform_params=params,
        problem_text=problem_text if problem_text is not None else _render_graph(graph),
        expected_graph=graph,
        expected_answer=trace.answer_value,
        expected_unit=trace.answer_unit,
    )


def _original_id_from_seed(seed: int) -> str:
    if 1 <= seed <= 999:
        return f"gpd-{seed:03d}"
    return f"seed-{seed}"


def _ordered_units(graph: MathProblemGraph) -> tuple[str, ...]:
    units: list[str] = []

    def add(unit: str) -> None:
        if unit not in units:
            units.append(unit)

    for possession in graph.initial_state:
        add(possession.quantity.unit)
    for operation in graph.operations:
        add(operation.operand.unit)
    add(graph.unknown.unit)
    return tuple(units)


def _entities_for(
    *,
    initial_state: tuple[InitialPossession, ...],
    operations: tuple[Operation, ...],
    fallback: tuple[str, ...],
) -> tuple[str, ...]:
    entities: list[str] = []

    def add(entity: str | None) -> None:
        if entity is not None and entity not in entities:
            entities.append(entity)

    for possession in initial_state:
        add(possession.entity)
    for operation in operations:
        add(operation.actor)
        add(operation.target)
    for entity in fallback:
        add(entity)
    return tuple(entities)


def _independent_operation_order(graph: MathProblemGraph) -> tuple[Operation, ...] | None:
    if len(graph.operations) < 2:
        return None
    affected: list[set[tuple[str, str]]] = [_affected_state(op) for op in graph.operations]
    for i, left in enumerate(affected):
        for right in affected[i + 1 :]:
            if left & right:
                return None
    reversed_ops = tuple(reversed(graph.operations))
    if reversed_ops == graph.operations:
        return None
    return reversed_ops


def _affected_state(operation: Operation) -> set[tuple[str, str]]:
    out = {(operation.actor, operation.operand.unit)}
    if operation.target is not None:
        out.add((operation.target, operation.operand.unit))
    return out


def _first_synonym_slot(
    graph: MathProblemGraph,
) -> tuple[int, tuple[str, ...]] | None:
    if not graph.operations:
        return None
    operation = graph.operations[0]
    if operation.kind == "add":
        return 0, tuple(sorted(_ADD_VERBS))
    if operation.kind == "subtract":
        return 0, tuple(sorted(_SUBTRACT_VERBS))
    if operation.kind == "transfer":
        return 0, tuple(sorted(_TRANSFER_VERBS))
    return None


def _first_operation_verb(problem: str) -> str | None:
    words = problem.replace(",", " ").replace(".", " ").split()
    lower_verbs = _ADD_VERBS | _SUBTRACT_VERBS | _TRANSFER_VERBS
    for word in words:
        lowered = word.lower()
        if lowered in lower_verbs:
            return lowered
    return None


def _choose_synonym(
    verbs: tuple[str, ...], original_verb: str | None, seed: int
) -> str | None:
    candidates = [v for v in verbs if v != original_verb]
    if not candidates:
        return None
    return candidates[seed % len(candidates)]


def _zero_entity_name(graph: MathProblemGraph, seed: int) -> str | None:
    used = set(graph.entities)
    candidates = [name for name in _ENTITY_REGISTRY if name not in used]
    if not candidates:
        return None
    return candidates[seed % len(candidates)]


def _non_commuting_swap(graph: MathProblemGraph) -> tuple[int, int] | None:
    original_trace = solve(graph)
    for i, left in enumerate(graph.operations):
        for j in range(i + 1, len(graph.operations)):
            right = graph.operations[j]
            if _affected_state(left) != _affected_state(right):
                continue
            operations = list(graph.operations)
            operations[i], operations[j] = operations[j], operations[i]
            swapped = MathProblemGraph(
                entities=graph.entities,
                initial_state=graph.initial_state,
                operations=tuple(operations),
                unknown=graph.unknown,
            )
            swapped_trace = solve(swapped)
            if swapped_trace.canonical_bytes() != original_trace.canonical_bytes():
                return i, j
    return None


def _trace_hash(trace: SolutionTrace) -> str:
    return hashlib.sha256(trace.canonical_bytes()).hexdigest()


def _render_graph_with_operation_verbs(
    graph: MathProblemGraph, operation_verbs: dict[int, str]
) -> str:
    sentences: list[str] = []
    for possession in graph.initial_state:
        value = possession.quantity.value
        unit = _surface_unit(possession.quantity.unit, value)
        sentences.append(f"{possession.entity} has {_number(value)} {unit}.")

    for index, operation in enumerate(graph.operations):
        value = operation.operand.value
        unit = _surface_unit(operation.operand.unit, value)
        verb = operation_verbs.get(index)
        if operation.kind == "add":
            chosen = verb if verb is not None else "buys"
            sentence = f"{operation.actor} {chosen} {_number(value)} more {unit}."
        elif operation.kind == "subtract":
            chosen = verb if verb is not None else "loses"
            sentence = f"{operation.actor} {chosen} {_number(value)} {unit}."
        elif operation.kind == "transfer":
            chosen = verb if verb is not None else "gives"
            sentence = (
                f"{operation.actor} {chosen} {_number(value)} {unit} "
                f"to {operation.target}."
            )
        elif operation.kind == "multiply":
            chosen = "doubles" if operation.operand.value == 2 else "triples"
            sentence = f"{operation.actor} {chosen} his {operation.operand.unit}."
        elif operation.kind == "divide":
            sentence = (
                f"{operation.actor} splits them evenly into "
                f"{_number(value)} groups and keeps one group."
            )
        else:
            raise ValueError(f"unsupported operation kind: {operation.kind!r}")
        sentences.append(sentence)

    question_unit = _surface_unit(graph.unknown.unit, 2)
    if graph.unknown.entity is None:
        sentences.append(f"How many {question_unit} do they have in total?")
    else:
        sentences.append(
            f"How many {question_unit} does {graph.unknown.entity} have now?"
        )
    return " ".join(sentences)

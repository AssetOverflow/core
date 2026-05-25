"""ADR-0118a — deterministic OOD surface generator for math dev cases.

The generator varies surface form while staying inside the ADR-0115
Phase 1.1 parser grammar. It renders from ``MathProblemGraph`` rather
than performing ad hoc text edits, so entity order, operation order, and
solver-visible arithmetic remain explicit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from generate.math_problem_graph import (
    InitialPossession,
    MathProblemGraph,
    Operation,
    Quantity,
    Unknown,
)
from generate.math_solver import solve


_ENTITY_REGISTRY = (
    "Quill",
    "Renn",
    "Sable",
    "Thora",
    "Ulric",
    "Vesta",
    "Wren",
    "Xan",
    "Ynez",
    "Zora",
    "Arlo",
    "Brae",
    "Cedric",
    "Doria",
    "Eira",
    "Finch",
    "Grim",
    "Hale",
    "Indra",
    "Jora",
)
_UNIT_REGISTRY = (
    "nebulae",
    "spires",
    "lanterns",
    "ingots",
    "shards",
    "scrolls",
    "talismans",
    "obsidians",
    "feathers",
    "runes",
    "crystals",
    "pelts",
    "moonbeams",
    "embers",
    "ledgers",
    "phials",
    "compasses",
    "trinkets",
)
_SCALE_FACTORS = (2, 3, 5)

_TRANSFORMS = ("rename_entities", "rename_units", "scale_numbers_by_k")
_TRANSFORM_SHORT = {
    "rename_entities": "rename_ent",
    "rename_units": "rename_unit",
}

# ``Wren`` appears in the public dev split. Keep the required fixed
# registry visible, but never select public-overlapping names.
_PUBLIC_DEV_ENTITY_EXCLUSIONS = frozenset({"Wren"})


@dataclass(frozen=True, slots=True)
class OODVariant:
    original_id: str
    variant_id: str
    transform: str
    transform_params: dict[str, Any]
    problem_text: str
    expected_graph_after_unrename: MathProblemGraph
    expected_answer: float
    expected_unit: str


def generate_ood_variants(
    problem: str,
    ground_truth_graph: MathProblemGraph,
    *,
    seed: int,
    n: int = 3,
) -> list[OODVariant]:
    """Return deterministic OOD variants for one public dev problem.

    ``problem`` participates in the deterministic seed stream so that two
    different surfaces with the same graph cannot accidentally share the
    same variant rotation. No I/O, global mutable state, or unseeded
    randomness is used.
    """
    if not isinstance(problem, str) or not problem.strip():
        raise ValueError("problem must be a non-empty string")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer")
    if n < 0:
        raise ValueError("n must be non-negative")

    original_id = _original_id_from_seed(seed)
    start = _stable_offset(problem, seed)
    variants: list[OODVariant] = []
    for index in range(n):
        transform = _TRANSFORMS[(start + index) % len(_TRANSFORMS)]
        variants.append(
            _build_variant(
                original_id=original_id,
                graph=ground_truth_graph,
                seed=seed,
                transform=transform,
            )
        )
    return variants


def _build_variant(
    *,
    original_id: str,
    graph: MathProblemGraph,
    seed: int,
    transform: str,
) -> OODVariant:
    entity_map = _entity_map(graph, seed)
    unit_map = _unit_map(graph, seed)
    k: int | None = None
    working = graph
    params: dict[str, Any] = {}

    if transform == "scale_numbers_by_k":
        k = _SCALE_FACTORS[seed % len(_SCALE_FACTORS)]
        working = _scale_graph(graph, k)
        params["k"] = k

    surface_graph = _rename_graph(working, entity_map, unit_map)
    trace = solve(surface_graph)
    if k is not None:
        params["scaled_answer"] = trace.answer_value

    short = f"scale_k{k}" if k is not None else _TRANSFORM_SHORT[transform]
    return OODVariant(
        original_id=original_id,
        variant_id=f"{original_id}:{short}",
        transform=transform,
        transform_params=params,
        problem_text=_render_graph(surface_graph),
        expected_graph_after_unrename=graph,
        expected_answer=trace.answer_value,
        expected_unit=trace.answer_unit,
    )


def _original_id_from_seed(seed: int) -> str:
    if 1 <= seed <= 999:
        return f"gpd-{seed:03d}"
    return f"seed-{seed}"


def _stable_offset(problem: str, seed: int) -> int:
    return (sum(problem.encode("utf-8")) + seed) % len(_TRANSFORMS)


def _entity_map(graph: MathProblemGraph, seed: int) -> dict[str, str]:
    names = [n for n in _ENTITY_REGISTRY if n not in _PUBLIC_DEV_ENTITY_EXCLUSIONS]
    offset = seed % len(names)
    if len(graph.entities) > len(names):
        raise ValueError("not enough OOD entity names for graph")
    selected = [names[(offset + i) % len(names)] for i in range(len(graph.entities))]
    return dict(zip(graph.entities, selected, strict=True))


def _unit_map(graph: MathProblemGraph, seed: int) -> dict[str, str]:
    units = _ordered_units(graph)
    stable_units = [u for u in _UNIT_REGISTRY if u.endswith("s")]
    offset = (seed * 2) % len(stable_units)
    if len(units) > len(stable_units):
        raise ValueError("not enough OOD unit names for graph")
    selected = [stable_units[(offset + i) % len(stable_units)] for i in range(len(units))]
    return dict(zip(units, selected, strict=True))


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


def _rename_graph(
    graph: MathProblemGraph, entity_map: dict[str, str], unit_map: dict[str, str]
) -> MathProblemGraph:
    return MathProblemGraph(
        entities=tuple(entity_map[e] for e in graph.entities),
        initial_state=tuple(
            InitialPossession(
                entity=entity_map[p.entity],
                quantity=Quantity(
                    value=p.quantity.value,
                    unit=unit_map[p.quantity.unit],
                ),
            )
            for p in graph.initial_state
        ),
        operations=tuple(
            Operation(
                actor=entity_map[o.actor],
                kind=o.kind,
                operand=Quantity(
                    value=o.operand.value,
                    unit=unit_map[o.operand.unit],
                ),
                target=entity_map[o.target] if o.target is not None else None,
            )
            for o in graph.operations
        ),
        unknown=Unknown(
            entity=entity_map[graph.unknown.entity]
            if graph.unknown.entity is not None
            else None,
            unit=unit_map[graph.unknown.unit],
        ),
    )


def _scale_graph(graph: MathProblemGraph, k: int) -> MathProblemGraph:
    return MathProblemGraph(
        entities=graph.entities,
        initial_state=tuple(
            InitialPossession(
                entity=p.entity,
                quantity=Quantity(value=p.quantity.value * k, unit=p.quantity.unit),
            )
            for p in graph.initial_state
        ),
        operations=tuple(_scale_operation(o, k) for o in graph.operations),
        unknown=graph.unknown,
    )


def _scale_operation(operation: Operation, k: int) -> Operation:
    value = operation.operand.value
    if operation.kind in {"add", "subtract", "transfer"}:
        value *= k
    return Operation(
        actor=operation.actor,
        kind=operation.kind,
        operand=Quantity(value=value, unit=operation.operand.unit),
        target=operation.target,
    )


def _render_graph(graph: MathProblemGraph) -> str:
    sentences: list[str] = []
    for possession in graph.initial_state:
        value = possession.quantity.value
        unit = _surface_unit(possession.quantity.unit, value)
        sentences.append(f"{possession.entity} has {_number(value)} {unit}.")

    for operation in graph.operations:
        value = operation.operand.value
        unit = _surface_unit(operation.operand.unit, value)
        if operation.kind == "add":
            sentence = f"{operation.actor} buys {_number(value)} more {unit}."
        elif operation.kind == "subtract":
            sentence = f"{operation.actor} loses {_number(value)} {unit}."
        elif operation.kind == "transfer":
            sentence = (
                f"{operation.actor} gives {_number(value)} {unit} "
                f"to {operation.target}."
            )
        elif operation.kind == "multiply":
            verb = "doubles" if operation.operand.value == 2 else "triples"
            sentence = f"{operation.actor} {verb} his {operation.operand.unit}."
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


def _surface_unit(unit: str, value: int | float) -> str:
    if value == 1:
        return _singular(unit)
    return unit


_IRREGULAR_SINGULAR: dict[str, str] = {
    "scarves": "scarf", "wolves": "wolf", "leaves": "leaf", "halves": "half",
    "loaves": "loaf", "thieves": "thief", "shelves": "shelf", "knives": "knife",
    "lives": "life", "wives": "wife", "children": "child", "men": "man",
    "women": "woman", "feet": "foot", "teeth": "tooth", "mice": "mouse",
    "geese": "goose",
}


def _singular(unit: str) -> str:
    if unit in _IRREGULAR_SINGULAR:
        return _IRREGULAR_SINGULAR[unit]
    if unit.endswith("ies"):
        return unit[:-3] + "y"
    if unit.endswith("es") and unit[-3:-2] in {"s", "x", "z"}:
        return unit[:-2]
    if unit.endswith("s"):
        return unit[:-1]
    return unit


def _number(value: int | float) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)

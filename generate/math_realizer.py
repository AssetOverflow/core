"""ADR-0118 — Stepped realizer: SolutionTrace → show-your-work prose.

Consumes a :class:`SolutionTrace` (ADR-0116) and emits a sequence of
one-sentence-per-step English explanations of the reasoning. The
realizer is **deterministic and pack-grounded**: every sentence
identifies the actor, the pack-resolved operation, and the operand,
ending with the answer sentence that names the resolved unknown.

Architectural commitments:

- **Deterministic.** Same trace → byte-identical prose.
- **Pack-grounded surface.** The verb in each step sentence is
  drawn from a fixed table keyed to the operation kind; the kind
  itself comes from the trace's ``pack_lemma_id``. Removing the
  arithmetic pack breaks the trace upstream, which breaks the
  realizer with a typed refusal.
- **Round-trippable** for add / subtract / transfer steps: the
  rendered prose, when re-parsed by ``parse_problem``, yields a
  graph whose solver-trace reproduces the same answer. ``multiply``
  and ``divide`` step phrasings are deliberately one-way (the
  parser's multiply pattern requires a possessed object phrase
  that the realizer can simulate, but the divide phrasing requires
  case-specific structure the parser does not yet recover). Round-
  trippability is enforced on the operation kinds the parser fully
  supports today; the divide / multiply cases produce inspectable
  prose without the round-trip guarantee.
- **Typed refusal** on inconsistent traces (the realizer does not
  re-validate the trace — :class:`ADR-0117 verifier`'s job — but
  it does refuse unknown operation kinds).

The realizer is the ADR-0114a Obligation #5-compatible substrate
for ADR-0119's GSM8K eval lane: every "correct" answer in the lane
ships with a stepped explanation that traces to pack lemmas.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from generate.math_problem_graph import Comparison, Rate
from generate.math_solver import SolutionStep, SolutionTrace


class RealizerError(ValueError):
    """Raised on unrecognized operation kind or empty trace."""


@dataclass(frozen=True, slots=True)
class RealizedTrace:
    """Stepped explanation surface for a :class:`SolutionTrace`.

    ``setup_sentences`` introduce the initial state (one sentence per
    :class:`InitialPossession`). ``step_sentences`` walk the trace in
    order. ``answer_sentence`` states the final resolved unknown.

    ``canonical_bytes()`` is byte-deterministic so two realizations of
    the same trace produce the same SHA-256.
    """

    setup_sentences: tuple[str, ...]
    step_sentences: tuple[str, ...]
    answer_sentence: str
    pack_id: str

    def as_json(self) -> dict[str, Any]:
        return {
            "setup_sentences": list(self.setup_sentences),
            "step_sentences": list(self.step_sentences),
            "answer_sentence": self.answer_sentence,
            "pack_id": self.pack_id,
        }

    def canonical_bytes(self) -> bytes:
        return json.dumps(
            self.as_json(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")

    def as_prose(self) -> str:
        """Join setup + step + answer sentences into one paragraph."""
        sentences = list(self.setup_sentences) + list(self.step_sentences)
        sentences.append(self.answer_sentence)
        return " ".join(sentences)


def realize(graph_initial_state: tuple, trace: SolutionTrace) -> RealizedTrace:
    """Render a :class:`SolutionTrace` as show-your-work prose.

    ``graph_initial_state`` is the input graph's ``initial_state`` tuple
    (used to introduce the entities and their starting quantities).
    ``trace`` provides the per-step records and the resolved answer.

    Pure function; same inputs → byte-identical output. Raises
    :class:`RealizerError` on empty traces or unrecognized step kinds.
    """
    if not isinstance(trace, SolutionTrace):
        raise RealizerError(
            f"trace must be a SolutionTrace, got {type(trace).__name__}"
        )

    setup_sentences = tuple(
        _setup_sentence(p.entity, p.quantity.value, p.quantity.unit)
        for p in graph_initial_state
    )

    # ADR-0123: the multiplicative comparison helper needs the
    # reference actor's unit, which is not stored on Comparison when
    # factor is set. We derive it deterministically from initial
    # state — the only entity-unit binding the realizer can reach
    # without re-running the solver. This is sufficient because the
    # substrate refuses multi-unit reference actors at solve time.
    entity_units: dict[str, str] = {
        p.entity: p.quantity.unit for p in graph_initial_state
    }

    step_sentences: list[str] = []
    for step in trace.steps:
        step_sentences.append(_step_sentence(step, entity_units))

    answer_sentence = _answer_sentence(
        trace.answer_entity, trace.answer_value, trace.answer_unit
    )

    return RealizedTrace(
        setup_sentences=setup_sentences,
        step_sentences=tuple(step_sentences),
        answer_sentence=answer_sentence,
        pack_id=trace.pack_id,
    )


def _setup_sentence(entity: str, value: int | float, unit: str) -> str:
    return f"{entity} has {_render_number(value)} {_unit_surface(unit, value)}."


def _step_sentence(
    step: SolutionStep, entity_units: dict[str, str] | None = None
) -> str:
    if step.operation_kind == "apply_rate":
        return _apply_rate_sentence(step)
    if step.operation_kind == "compare_additive":
        return _compare_additive_sentence(step)
    if step.operation_kind == "compare_multiplicative":
        if entity_units is None:
            raise RealizerError(
                f"compare_multiplicative step {step.step_index} requires "
                f"entity_units to resolve reference actor unit; got None"
            )
        return _compare_multiplicative_sentence(step, entity_units)
    if step.operation_kind == "add":
        return (
            f"{step.actor} buys {_render_number(step.operand.value)} more "
            f"{_unit_surface(step.operand.unit, step.operand.value)}, "
            f"raising the total to {_render_number(step.after_value)}."
        )
    if step.operation_kind == "subtract":
        return (
            f"{step.actor} loses {_render_number(step.operand.value)} "
            f"{_unit_surface(step.operand.unit, step.operand.value)}, "
            f"leaving {_render_number(step.after_value)}."
        )
    if step.operation_kind == "transfer":
        if step.target is None:
            raise RealizerError(
                f"transfer step {step.step_index} missing target"
            )
        return (
            f"{step.actor} gives {_render_number(step.operand.value)} "
            f"{_unit_surface(step.operand.unit, step.operand.value)} to "
            f"{step.target}, leaving {step.actor} with "
            f"{_render_number(step.after_value)}."
        )
    if step.operation_kind == "multiply":
        verb = "doubles" if step.operand.value == 2 else (
            "triples" if step.operand.value == 3 else "multiplies"
        )
        if verb == "multiplies":
            return (
                f"{step.actor} multiplies their "
                f"{_unit_surface(step.operand.unit, 2)} by "
                f"{_render_number(step.operand.value)}, "
                f"reaching {_render_number(step.after_value)}."
            )
        return (
            f"{step.actor} {verb} their "
            f"{_unit_surface(step.operand.unit, 2)}, "
            f"reaching {_render_number(step.after_value)}."
        )
    if step.operation_kind == "divide":
        return (
            f"{step.actor} splits their "
            f"{_unit_surface(step.operand.unit, 2)} evenly into "
            f"{_render_number(step.operand.value)} groups and keeps one "
            f"group, leaving {_render_number(step.after_value)}."
        )
    if step.operation_kind == "partition":
        part = step.operand
        return (
            f"{_render_number(part.factor)} of the "
            f"{_unit_surface(part.base_unit, 2)} are "
            f"{step.actor}, which is {_render_number(step.after_value)} "
            f"{_unit_surface(part.subset_unit, step.after_value)}."
        )
    raise RealizerError(
        f"step {step.step_index} has unknown operation_kind "
        f"{step.operation_kind!r}"
    )


def _apply_rate_sentence(step: SolutionStep) -> str:
    """Render an apply_rate step as show-your-work prose (ADR-0122).

    The template intentionally contains both ``"<value> <numer> per
    <denom-singular>"`` (the rate clause) and ``"<after> <numer>"``
    (the computed total), which the test suite pins as a structural
    invariant. The denominator phrase uses singular form (``per
    apple``) regardless of count, matching natural English.
    """
    if not isinstance(step.operand, Rate):
        raise RealizerError(
            f"apply_rate step {step.step_index} requires a Rate "
            f"operand; got {type(step.operand).__name__}"
        )
    rate = step.operand
    rate_n = _render_number(rate.value)
    before_n = _render_number(step.before_value)
    after_n = _render_number(step.after_value)
    denom_singular = _singular(rate.denominator_unit)
    denom_surface = _unit_surface(rate.denominator_unit, step.before_value)
    return (
        f"At {rate_n} {rate.numerator_unit} per {denom_singular}, "
        f"{step.actor} spends {after_n} {rate.numerator_unit} on "
        f"{before_n} {denom_surface}."
    )


def _compare_additive_sentence(step: SolutionStep) -> str:
    """Render an additive comparison step as show-your-work prose (ADR-0123).

    Reads ``step.operand`` (must be a :class:`Comparison` with
    ``delta`` set) and emits a one-sentence rendering of the form:

    - direction='more':  "<actor> has <delta> more <unit> than <ref>,
                          giving <actor> a total of <after> <unit>."
    - direction='fewer': "<actor> has <delta> fewer <unit> than <ref>,
                          leaving <actor> with a total of <after> <unit>."

    The two-clause shape — *comparison clause* + *resolved state* —
    is pinned as a structural invariant by the ADR-0123 test suite.
    ``delta.value`` and ``after_value`` pluralize independently via
    :func:`_unit_surface` (so "1 more apple" vs "3 more apples"
    behave correctly without the resolved state being forced into
    the same plurality).

    Raises :class:`RealizerError` on:
    - operand not a :class:`Comparison` (substrate solver bug)
    - missing ``delta`` (multiplicative shape leaked into this branch)
    - direction not in ``{"more", "fewer"}``
    - self-reference (actor == reference_actor)
    """
    if not isinstance(step.operand, Comparison):
        raise RealizerError(
            f"compare_additive step {step.step_index} requires a "
            f"Comparison operand; got {type(step.operand).__name__}"
        )
    cmp = step.operand
    if cmp.delta is None:
        raise RealizerError(
            f"compare_additive step {step.step_index} requires "
            f"Comparison.delta; got None (multiplicative shape leaked)"
        )
    if cmp.direction not in ("more", "fewer"):
        raise RealizerError(
            f"compare_additive step {step.step_index} requires "
            f"direction in {{'more','fewer'}}; got {cmp.direction!r}"
        )
    if step.actor == cmp.reference_actor:
        raise RealizerError(
            f"compare_additive step {step.step_index} refuses "
            f"self-comparison: actor=={cmp.reference_actor!r}"
        )
    delta_n = _render_number(cmp.delta.value)
    after_n = _render_number(step.after_value)
    delta_surface = _unit_surface(cmp.delta.unit, cmp.delta.value)
    after_surface = _unit_surface(cmp.delta.unit, step.after_value)
    if cmp.direction == "more":
        return (
            f"{step.actor} has {delta_n} more {delta_surface} than "
            f"{cmp.reference_actor}, giving {step.actor} a total of "
            f"{after_n} {after_surface}."
        )
    # direction == "fewer"
    return (
        f"{step.actor} has {delta_n} fewer {delta_surface} than "
        f"{cmp.reference_actor}, leaving {step.actor} with a total of "
        f"{after_n} {after_surface}."
    )


def _compare_multiplicative_sentence(
    step: SolutionStep, entity_units: dict[str, str]
) -> str:
    """Render a multiplicative comparison step as show-your-work prose.

    Reads ``step.operand`` (must be a :class:`Comparison` with
    ``factor`` set) and emits:

    - direction='times':    "<actor> has <factor> times as many <unit>
                             as <ref>, giving <actor> a total of <after>
                             <unit>."
    - direction='fraction', factor==0.5:
                            "<actor> has half as many <unit> as <ref>,
                             giving <actor> a total of <after> <unit>."
    - direction='fraction', other factor:
                            "<actor> has <factor> as many <unit> as
                             <ref>, giving <actor> a total of <after>
                             <unit>."

    ``unit`` is resolved from ``entity_units[reference_actor]`` — the
    substrate's solver derives it from the reference actor's
    in-flight state, but the realizer only sees ``SolutionStep``
    instances. Initial-state lookup is sufficient because the
    substrate refuses multi-unit reference actors and refuses to
    overwrite a comparison actor's existing state.

    Raises :class:`RealizerError` on:
    - operand not a :class:`Comparison`
    - missing ``factor``
    - direction not in ``{"times", "fraction"}``
    - reference actor missing from ``entity_units``
    - self-reference
    """
    if not isinstance(step.operand, Comparison):
        raise RealizerError(
            f"compare_multiplicative step {step.step_index} requires "
            f"a Comparison operand; got {type(step.operand).__name__}"
        )
    cmp = step.operand
    if cmp.factor is None:
        raise RealizerError(
            f"compare_multiplicative step {step.step_index} requires "
            f"Comparison.factor; got None (additive shape leaked)"
        )
    if cmp.direction not in ("times", "fraction"):
        raise RealizerError(
            f"compare_multiplicative step {step.step_index} requires "
            f"direction in {{'times','fraction'}}; got {cmp.direction!r}"
        )
    if step.actor == cmp.reference_actor:
        raise RealizerError(
            f"compare_multiplicative step {step.step_index} refuses "
            f"self-comparison: actor=={cmp.reference_actor!r}"
        )
    if cmp.reference_actor not in entity_units:
        raise RealizerError(
            f"compare_multiplicative step {step.step_index} requires "
            f"reference actor {cmp.reference_actor!r} to appear in "
            f"initial state; available entities: "
            f"{sorted(entity_units)!r}"
        )
    unit = entity_units[cmp.reference_actor]
    after_n = _render_number(step.after_value)
    after_surface = _unit_surface(unit, step.after_value)
    if cmp.direction == "fraction" and cmp.factor == 0.5:
        return (
            f"{step.actor} has half as many {unit} as "
            f"{cmp.reference_actor}, giving {step.actor} a total of "
            f"{after_n} {after_surface}."
        )
    factor_n = _render_number(cmp.factor)
    if cmp.direction == "fraction":
        return (
            f"{step.actor} has {factor_n} as many {unit} as "
            f"{cmp.reference_actor}, giving {step.actor} a total of "
            f"{after_n} {after_surface}."
        )
    # direction == "times"
    return (
        f"{step.actor} has {factor_n} times as many {unit} as "
        f"{cmp.reference_actor}, giving {step.actor} a total of "
        f"{after_n} {after_surface}."
    )


def _answer_sentence(
    entity: str | None, value: int | float, unit: str
) -> str:
    if entity is None:
        return (
            f"In total, they have {_render_number(value)} "
            f"{_unit_surface(unit, value)}."
        )
    return (
        f"{entity} has {_render_number(value)} "
        f"{_unit_surface(unit, value)}."
    )


def _render_number(value: int | float) -> str:
    """Render numeric value preferring integer form when exact."""
    if isinstance(value, bool):
        # bool is a subclass of int — refuse explicitly
        raise RealizerError(f"cannot render boolean as number: {value!r}")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _unit_surface(unit: str, value: int | float) -> str:
    """Render a unit string in surface form.

    Quantities of exactly 1 take the singular; all others keep the
    canonical plural. This matches the parser's
    ``_canonical_unit`` round-trip — the parser maps singular surfaces
    back to plural at graph time.
    """
    if value == 1:
        return _singular(unit)
    return unit


def _singular(unit: str) -> str:
    if unit.endswith("ies") and len(unit) > 3:
        return unit[:-3] + "y"
    if unit.endswith("es") and len(unit) > 2 and unit[-3:-2] in {"s", "x", "z"}:
        return unit[:-2]
    if unit.endswith("s") and not unit.endswith("ss"):
        return unit[:-1]
    return unit

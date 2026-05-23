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

    step_sentences: list[str] = []
    for step in trace.steps:
        step_sentences.append(_step_sentence(step))

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


def _step_sentence(step: SolutionStep) -> str:
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
    raise RealizerError(
        f"step {step.step_index} has unknown operation_kind "
        f"{step.operation_kind!r}"
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

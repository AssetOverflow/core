"""ADR-0154 (W-020b) — producer-side wiring for DerivedRecognizer registry.

Pre-ADR-0154, ``ChatRuntime.record_recognition_example`` had no
production caller — only tests invoked it.  Result: the
``_pending_recognizer_examples`` bucket stayed empty regardless of
how many turns were admitted by an attached recognizer, so
``derive_recognizer`` at the next checkpoint had nothing to
anti-unify.  The registry could never grow from live traffic, even
when ``recognition_grounded_graph`` was enabled.

Fix: in ``CognitiveTurnPipeline.run`` at the admitted-recognition
boundary, capture ``(raw_tokens, _rec_outcome.proposition)`` via
``runtime.record_recognition_example``.  Producer fires
unconditionally; consumer (``derive_recognizer`` in
``checkpoint_engine_state``) stays opt-in behind the same flag.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from chat.runtime import ChatRuntime
from core.cognition import CognitiveTurnPipeline
from core.config import DEFAULT_CONFIG
from recognition.anti_unifier import derive_recognizer
from recognition.outcome import EvidenceSpan, FeatureBundle, NegativeEvidence


def _config(*, recognition_grounded_graph: bool):
    return replace(
        DEFAULT_CONFIG,
        recognition_grounded_graph=recognition_grounded_graph,
    )


def _span(tokens: tuple[str, ...], start: int, end: int) -> EvidenceSpan:
    return EvidenceSpan(start=start, end=end, text=" ".join(tokens[start:end]))


def _bundle(
    tokens: tuple[str, ...],
    agent_span: tuple[int, int],
    count_span: tuple[int, int],
    unit_span: tuple[int, int],
    agent: str,
    count: int,
    unit: str,
) -> FeatureBundle:
    return FeatureBundle.from_mapping(
        {
            "agent": (agent, _span(tokens, *agent_span)),
            "count": (count, _span(tokens, *count_span)),
            "intentionality": (
                "possession",
                _span(
                    tokens,
                    1 if tokens[0] in {"A", "The"} else 0,
                    3 if tokens[0] in {"A", "The"} else 2,
                ),
            ),
            "modality": (
                "actual",
                NegativeEvidence(0, len(tokens), "no modal counter-marker present"),
            ),
            "polarity": ("+", NegativeEvidence(0, len(tokens), "no negator present")),
            "relation": ("has", _span(tokens, count_span[0] - 1, count_span[0])),
            "tense": ("present", _span(tokens, count_span[0] - 1, count_span[0])),
            "unit": (unit, _span(tokens, *unit_span)),
        }
    )


def _examples() -> list[tuple[tuple[str, ...], FeatureBundle]]:
    john = ("John", "has", "5", "apples")
    mary = ("Mary", "has", "3", "books")
    school = ("A", "school", "has", "100", "students")
    library = ("The", "library", "has", "12", "chairs")
    return [
        (john, _bundle(john, (0, 1), (2, 3), (3, 4), "John", 5, "apple")),
        (mary, _bundle(mary, (0, 1), (2, 3), (3, 4), "Mary", 3, "book")),
        (
            school,
            _bundle(school, (1, 2), (3, 4), (4, 5), "school", 100, "student"),
        ),
        (
            library,
            _bundle(library, (1, 2), (3, 4), (4, 5), "library", 12, "chair"),
        ),
    ]


def _recognizer():
    return derive_recognizer(_examples())


def test_admitted_turn_records_recognition_example(tmp_path: Path) -> None:
    """Admitted recognition appends (tokens, bundle) to the producer queue.

    Uses flag=False so the consumer (``checkpoint_engine_state``'s
    ``derive_recognizer``) does not drain the queue at end-of-turn;
    that lets us assert the producer's output directly.
    Recognizer attached via pipeline constructor because
    ``runtime.first_admitted_recognizer`` is gated on the flag.
    """
    runtime = ChatRuntime(
        config=_config(recognition_grounded_graph=False),
        engine_state_path=tmp_path,
    )
    pipe = CognitiveTurnPipeline(runtime, recognizer=_recognizer())
    assert runtime._pending_recognizer_examples == []

    result = pipe.run("A baker has 24 loaves", max_tokens=4)

    assert result.epistemic_graph is not None, (
        "fixture must admit; otherwise the producer hook is not exercised"
    )
    assert len(runtime._pending_recognizer_examples) == 1
    tokens, bundle = runtime._pending_recognizer_examples[0]
    assert tokens == ("A", "baker", "has", "24", "loaves")
    assert isinstance(bundle, FeatureBundle)
    # Bundle must be complete (anti-unifier invariant).
    assert {f.name for f in bundle.features} >= {
        "agent",
        "count",
        "unit",
    }


def test_producer_fires_when_consumer_flag_off(tmp_path: Path) -> None:
    """Producer must NOT be gated on ``recognition_grounded_graph``.

    The consumer (derive_recognizer at checkpoint) is opt-in; the
    producer is unconditional so flipping the flag later is not a
    cold start.  Without an attached recognizer (registry empty +
    flag off), no recognition runs at all, so we attach one
    directly to the pipeline.
    """
    runtime = ChatRuntime(
        config=_config(recognition_grounded_graph=False),
        engine_state_path=tmp_path,
    )
    pipe = CognitiveTurnPipeline(runtime, recognizer=_recognizer())

    result = pipe.run("A baker has 24 loaves", max_tokens=4)

    # Flag is off → graph derivation skipped, but producer must still
    # have captured the admitted example.
    assert result.epistemic_graph is not None  # pipeline-level admit
    assert len(runtime._pending_recognizer_examples) == 1


def test_refused_turn_does_not_record_example(tmp_path: Path) -> None:
    """Refused recognition must not populate the producer queue."""
    runtime = ChatRuntime(
        config=_config(recognition_grounded_graph=False),
        engine_state_path=tmp_path,
    )
    pipe = CognitiveTurnPipeline(runtime, recognizer=_recognizer())

    # Input that does not match the (agent, has, count, unit) pattern.
    pipe.run("Hello world", max_tokens=4)

    assert runtime._pending_recognizer_examples == []


def test_full_loop_admit_then_derive_registers_new_recognizer(
    tmp_path: Path,
) -> None:
    """End-to-end producer→consumer: with flag=True, an admitted turn
    feeds the producer queue, then ``checkpoint_engine_state`` drains
    the queue via ``derive_recognizer`` and registers the result.
    Pre-ADR-0154 this loop could not close from live traffic because
    the producer was never wired.
    """
    runtime = ChatRuntime(
        config=_config(recognition_grounded_graph=True),
        engine_state_path=tmp_path,
    )
    seed = _recognizer()
    runtime._recognizer_registry.register(seed)
    registry_size_before = len(runtime._recognizer_registry)

    CognitiveTurnPipeline(runtime).run(
        "A baker has 24 loaves", max_tokens=4
    )

    # The consumer drained the queue at checkpoint and registered the
    # newly-derived recognizer (overwriting the seed under the same
    # teaching_set_id, since derive_recognizer is byte-deterministic).
    assert runtime._pending_recognizer_examples == []
    assert len(runtime._recognizer_registry) >= registry_size_before


def test_examples_accumulate_across_admitted_turns(tmp_path: Path) -> None:
    """Multiple admitted turns append in order.

    Flag=False so the consumer does not drain between turns;
    that lets us assert producer accumulation directly.
    """
    runtime = ChatRuntime(
        config=_config(recognition_grounded_graph=False),
        engine_state_path=tmp_path,
    )
    pipe = CognitiveTurnPipeline(runtime, recognizer=_recognizer())
    pipe.run("A baker has 24 loaves", max_tokens=4)
    pipe.run("The farmer has 7 sheep", max_tokens=4)

    assert len(runtime._pending_recognizer_examples) == 2
    assert runtime._pending_recognizer_examples[0][0] == (
        "A",
        "baker",
        "has",
        "24",
        "loaves",
    )
    assert runtime._pending_recognizer_examples[1][0] == (
        "The",
        "farmer",
        "has",
        "7",
        "sheep",
    )

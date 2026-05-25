from __future__ import annotations

from dataclasses import replace

from chat.runtime import ChatRuntime
from core.cognition import CognitiveTurnPipeline
from core.config import DEFAULT_CONFIG
from engine_state import EngineStateStore
from recognition.anti_unifier import derive_recognizer
from recognition.outcome import EvidenceSpan, FeatureBundle, NegativeEvidence
from recognition.registry import RecognizerRegistry


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


def test_registry_empty_no_recognizer_passed(tmp_path) -> None:
    runtime = ChatRuntime(
        config=_config(recognition_grounded_graph=True),
        engine_state_path=tmp_path,
    )

    result = CognitiveTurnPipeline(runtime).run("A baker has 24 loaves", max_tokens=4)

    assert result.epistemic_graph is None


def test_registry_with_recognizer_wires_into_pipeline(tmp_path) -> None:
    runtime = ChatRuntime(
        config=_config(recognition_grounded_graph=True),
        engine_state_path=tmp_path,
    )
    recognizer = _recognizer()
    runtime._recognizer_registry.register(recognizer)

    result = CognitiveTurnPipeline(runtime).run("A baker has 24 loaves", max_tokens=4)

    assert result.epistemic_graph is not None
    assert result.epistemic_graph.recognizer_id == recognizer.teaching_set_id
    assert result.epistemic_graph.nodes[0].node_id.startswith(
        f"{recognizer.teaching_set_id}:"
    )


def test_flag_off_registry_ignored(tmp_path) -> None:
    runtime = ChatRuntime(
        config=_config(recognition_grounded_graph=False),
        engine_state_path=tmp_path,
    )
    runtime._recognizer_registry.register(_recognizer())

    result = CognitiveTurnPipeline(runtime).run("A baker has 24 loaves", max_tokens=4)

    assert result.epistemic_graph is None


def test_first_admitted_returns_none_on_empty() -> None:
    assert RecognizerRegistry().first_admitted() is None


def test_first_admitted_returns_registered() -> None:
    registry = RecognizerRegistry()
    recognizer = _recognizer()

    registry.register(recognizer)

    assert registry.first_admitted() == recognizer


def test_record_and_checkpoint_derives_recognizer(tmp_path) -> None:
    runtime = ChatRuntime(
        config=_config(recognition_grounded_graph=True),
        engine_state_path=tmp_path,
    )
    for tokens, bundle in _examples():
        runtime.record_recognition_example(tokens, bundle)

    runtime.checkpoint_engine_state()

    assert len(runtime._recognizer_registry) == 1
    persisted = EngineStateStore(tmp_path).load_recognizers()
    assert persisted == runtime._recognizer_registry.all()

"""Tests for the multi-sentence response eval lane predicates."""

from __future__ import annotations

from core.config import RuntimeConfig
from evals.multi_sentence_response import runner
from evals.multi_sentence_response.runner import (
    _split_sentences,
    _strip_provenance,
    run_lane,
)


def test_strip_provenance_removes_trust_boundary_tail() -> None:
    surface = (
        "truth — narrative-grounded: cognition.truth. "
        "truth grounds knowledge. No session evidence yet."
    )

    stripped = _strip_provenance(surface)

    assert stripped == "truth — narrative-grounded: cognition.truth. truth grounds knowledge."


def test_sentence_splitter_ignores_lowercase_semantic_domain_continuation() -> None:
    surface = (
        "truth — teaching-grounded: cognition.truth; logos.core. "
        "truth grounds knowledge (cognition.knowledge). No session evidence yet."
    )

    sentences = _split_sentences(surface)

    assert sentences == [
        (
            "truth — teaching-grounded: cognition.truth; logos.core. "
            "truth grounds knowledge (cognition.knowledge)."
        ),
        "No session evidence yet.",
    ]


def test_sentence_splitter_keeps_uppercase_discourse_transition() -> None:
    surface = (
        "Truth is a claim grounded by evidence. Furthermore, truth belongs "
        "to cognition.truth. In turn, truth grounds knowledge."
    )

    sentences = _split_sentences(surface)

    assert sentences == [
        "Truth is a claim grounded by evidence.",
        "Furthermore, truth belongs to cognition.truth.",
        "In turn, truth grounds knowledge.",
    ]


def test_run_lane_passes_runtime_config_to_chat_runtime(monkeypatch) -> None:
    seen_configs: list[RuntimeConfig | None] = []

    class _FakeResponse:
        surface = "Truth is grounded. Furthermore, truth belongs to cognition.truth."
        grounding_source = "pack"

    class _FakeRuntime:
        def __init__(self, config=None):
            seen_configs.append(config)

        def chat(self, prompt: str) -> _FakeResponse:  # noqa: ARG002
            return _FakeResponse()

    monkeypatch.setattr(runner, "ChatRuntime", _FakeRuntime)
    cases = [
        {
            "id": "flag_on_truth",
            "category": "explain",
            "prompt": "Explain truth.",
            "subject_lemma": "truth",
            "expects_connective": True,
        }
    ]
    cfg = RuntimeConfig(discourse_planner=True)

    report = run_lane(cases, config=cfg)

    assert seen_configs == [cfg]
    assert report.case_details[0]["connective_present"] is True

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


def test_priming_prompts_run_before_scored_prompt(monkeypatch) -> None:
    """Priming turns must run on the same runtime instance and only
    the scored prompt may be measured.  The ``primed`` field on the
    case result must record whether priming engaged.
    """

    prompts_seen: list[str] = []

    class _FakeResponse:
        surface = "Truth is grounded. Furthermore, truth belongs to cognition.truth."
        grounding_source = "teaching"

    class _FakeRuntime:
        def __init__(self, config=None):  # noqa: ARG002
            self.id = id(self)

        def chat(self, prompt: str) -> _FakeResponse:
            prompts_seen.append(prompt)
            return _FakeResponse()

    monkeypatch.setattr(runner, "ChatRuntime", _FakeRuntime)
    cases = [
        {
            "id": "primed_case",
            "category": "narrative",
            "prompt": "Tell me about truth.",
            "subject_lemma": "truth",
            "expects_connective": False,
            "priming_prompts": ["What is truth?", "Hello"],
        }
    ]

    report = run_lane(cases, config=RuntimeConfig(discourse_planner=True))

    # Both priming prompts ran before the scored prompt — in order.
    assert prompts_seen == ["What is truth?", "Hello", "Tell me about truth."]
    detail = report.case_details[0]
    assert detail["primed"] is True
    # The scored surface is what was returned for the last chat call.
    assert "Furthermore" in detail["surface"]


def test_priming_default_is_cold_start(monkeypatch) -> None:
    """A case without ``priming_prompts`` (or with an empty list) must
    run cold-start; ``primed`` is False.
    """

    prompts_seen: list[str] = []

    class _FakeResponse:
        surface = "Truth."
        grounding_source = "vault"

    class _FakeRuntime:
        def __init__(self, config=None):  # noqa: ARG002
            pass

        def chat(self, prompt: str) -> _FakeResponse:
            prompts_seen.append(prompt)
            return _FakeResponse()

    monkeypatch.setattr(runner, "ChatRuntime", _FakeRuntime)
    cases = [
        {
            "id": "cold_case",
            "category": "explain",
            "prompt": "Explain truth.",
            "subject_lemma": "truth",
            "expects_connective": True,
        },
        {
            "id": "empty_priming_case",
            "category": "narrative",
            "prompt": "Tell me about truth.",
            "subject_lemma": "truth",
            "expects_connective": False,
            "priming_prompts": [],
        },
    ]

    report = run_lane(cases)

    assert prompts_seen == ["Explain truth.", "Tell me about truth."]
    for detail in report.case_details:
        assert detail["primed"] is False


def test_primed_multi_sentence_rate_separates_from_aggregate(monkeypatch) -> None:
    """The ``primed_multi_sentence_rate`` metric reports only on cases
    that actually exercised priming, so cold-start cases never inflate
    or depress it.
    """

    class _FakeResponse:
        def __init__(self, surface: str) -> None:
            self.surface = surface
            self.grounding_source = "teaching"

    class _FakeRuntime:
        def __init__(self, config=None):  # noqa: ARG002
            self._turn = 0

        def chat(self, prompt: str) -> _FakeResponse:  # noqa: ARG002
            self._turn += 1
            if self._turn <= 1:
                # priming turn — single sentence
                return _FakeResponse("Truth is X.")
            return _FakeResponse(
                "Truth is X. Furthermore, truth belongs to cognition.truth."
            )

    monkeypatch.setattr(runner, "ChatRuntime", _FakeRuntime)
    cases = [
        {
            "id": "cold",
            "category": "explain",
            "prompt": "Explain truth.",
            "subject_lemma": "truth",
            "expects_connective": True,
        },
        {
            "id": "primed",
            "category": "narrative",
            "prompt": "Tell me about truth.",
            "subject_lemma": "truth",
            "expects_connective": False,
            "priming_prompts": ["What is truth?"],
        },
    ]

    report = run_lane(cases)

    assert report.metrics["primed_cases"] == 1
    assert report.metrics["primed_multi_sentence_rate"] == 1.0

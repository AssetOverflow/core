"""Tests for the long-form replay benchmark.

Verifies the CORE-side determinism claim and the optional LLM
comparison contract.  The LLM side is exercised with a synthetic
nondeterministic callable so no API key is required.
"""

from __future__ import annotations

import itertools

from benchmarks.replay_vs_llm import (
    DEFAULT_LONGFORM_PROMPTS,
    compare_to_llm,
    replay_determinism_report,
)


class TestCoreReplayDeterminism:
    def test_default_prompts_are_bit_identical_across_runs(self):
        report = replay_determinism_report(
            list(DEFAULT_LONGFORM_PROMPTS[:2]), runs=3
        )
        assert report.runs_per_prompt == 3
        assert report.all_deterministic
        assert report.core_deterministic_rate == 1.0

    def test_priming_does_not_break_determinism(self):
        report = replay_determinism_report(
            ["What does truth ground?"],
            runs=2,
            priming=("Wisdom grounds knowledge.",),
        )
        assert report.all_deterministic
        assert all(r.unique_count == 1 for r in report.core_results)

    def test_hash_is_sha256_of_surface(self):
        report = replay_determinism_report(["What is wisdom?"], runs=2)
        res = report.core_results[0]
        assert len(res.surface_hashes[0]) == 64
        assert res.surface_hashes[0] == res.surface_hashes[1]


class TestLlmComparison:
    def test_no_llm_callable_yields_only_core_results(self):
        report = compare_to_llm(
            list(DEFAULT_LONGFORM_PROMPTS[:1]), runs=2, llm_callable=None
        )
        assert report.llm_results == ()
        assert report.llm_deterministic_rate is None
        assert report.core_deterministic_rate == 1.0

    def test_nondeterministic_llm_callable_is_detected(self):
        counter = itertools.count()

        def jittery_llm(prompt: str) -> str:
            return f"{prompt} -> answer #{next(counter)}"

        report = compare_to_llm(
            ["What is wisdom?"], runs=3, llm_callable=jittery_llm
        )
        assert report.core_deterministic_rate == 1.0
        assert report.llm_deterministic_rate == 0.0
        assert report.llm_results[0].unique_count == 3

    def test_deterministic_llm_callable_matches_core(self):
        def fixed_llm(prompt: str) -> str:
            return "fixed answer"

        report = compare_to_llm(
            ["What is wisdom?"], runs=2, llm_callable=fixed_llm
        )
        assert report.core_deterministic_rate == 1.0
        assert report.llm_deterministic_rate == 1.0

    def test_summary_renders_both_sides_when_llm_supplied(self):
        def fixed_llm(_: str) -> str:
            return "fixed"

        report = compare_to_llm(
            ["What is wisdom?"], runs=2, llm_callable=fixed_llm
        )
        out = report.summary()
        assert "CORE deterministic rate" in out
        assert "LLM deterministic rate" in out

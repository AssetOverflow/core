"""Long-form replay benchmark: CORE bit-identical replay vs frontier-LLM
surface variability on the same input.

CORE's structural claim is that a fixed (pack, vault, seed) state produces
a byte-identical surface across repeated runs.  Frontier LLMs, even with
``temperature=0``, exhibit per-run surface variability driven by sampler
noise, backend nondeterminism, and rolling model updates.  This benchmark
makes that asymmetry measurable.

Usage:

    from benchmarks.replay_vs_llm import (
        replay_determinism_report,
        compare_to_llm,
    )

    # CORE-only — no API key required.  Verifies bit-identical replay
    # across N runs of the same prompt through the same pipeline.
    report = replay_determinism_report(prompts, runs=5)
    assert report.all_deterministic

    # Optional LLM comparison.  ``llm_callable(prompt) -> str`` is any
    # bring-your-own function — no provider lock-in, no API code in the
    # benchmark itself.  When omitted, only the CORE side is reported.
    report = compare_to_llm(prompts, llm_callable=my_openai_caller, runs=5)
    print(report.summary())

The CORE side is the load-bearing claim and runs without external
dependencies; the LLM comparison is opt-in for a research workstation
that already holds the relevant credentials.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Callable

from chat.runtime import ChatRuntime


@dataclass(frozen=True, slots=True)
class PromptReplayResult:
    """Per-prompt determinism evidence for one side (CORE or LLM)."""

    prompt: str
    surfaces: tuple[str, ...]
    surface_hashes: tuple[str, ...]
    unique_count: int

    @property
    def deterministic(self) -> bool:
        return self.unique_count == 1


@dataclass(frozen=True, slots=True)
class ReplayReport:
    """Aggregate determinism report across N prompts × R runs."""

    core_results: tuple[PromptReplayResult, ...]
    llm_results: tuple[PromptReplayResult, ...] = ()
    runs_per_prompt: int = 0

    @property
    def core_deterministic_rate(self) -> float:
        if not self.core_results:
            return 0.0
        wins = sum(1 for r in self.core_results if r.deterministic)
        return wins / len(self.core_results)

    @property
    def llm_deterministic_rate(self) -> float | None:
        if not self.llm_results:
            return None
        wins = sum(1 for r in self.llm_results if r.deterministic)
        return wins / len(self.llm_results)

    @property
    def all_deterministic(self) -> bool:
        return self.core_deterministic_rate == 1.0

    def summary(self) -> str:
        lines = [
            f"Long-form replay benchmark — {len(self.core_results)} prompts × {self.runs_per_prompt} runs",
            f"  CORE deterministic rate: {self.core_deterministic_rate:.1%} "
            f"({sum(1 for r in self.core_results if r.deterministic)}/{len(self.core_results)} bit-identical)",
        ]
        if self.llm_results:
            llm_rate = self.llm_deterministic_rate or 0.0
            mean_unique = (
                sum(r.unique_count for r in self.llm_results)
                / max(1, len(self.llm_results))
            )
            lines.append(
                f"  LLM deterministic rate:  {llm_rate:.1%} — "
                f"mean unique surfaces per prompt: {mean_unique:.2f}"
            )
        return "\n".join(lines)


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _make_core_runner(priming: tuple[str, ...]) -> Callable[[str], str]:
    """Build a CORE runner that primes a fresh ChatRuntime with the
    supplied sequence before each call.

    Each invocation gets its own runtime so the determinism claim is
    over the *pipeline* (pack, vault, seed, priming sequence) rather
    than the in-memory session state of one runtime instance.  That is
    the stronger guarantee — if the priming + prompt yields identical
    bytes across two cold-start runtimes, the pipeline is fully
    deterministic for that input.
    """
    def runner(prompt: str) -> str:
        rt = ChatRuntime()
        for p in priming:
            rt.chat(p)
        resp = rt.chat(prompt)
        return resp.articulation_surface or resp.surface or ""
    return runner


def _replay_one(prompt: str, runner: Callable[[str], str], runs: int) -> PromptReplayResult:
    surfaces: list[str] = []
    hashes: list[str] = []
    for _ in range(runs):
        surf = runner(prompt)
        surfaces.append(surf)
        hashes.append(_sha256(surf))
    return PromptReplayResult(
        prompt=prompt,
        surfaces=tuple(surfaces),
        surface_hashes=tuple(hashes),
        unique_count=len(set(hashes)),
    )


def replay_determinism_report(
    prompts: list[str],
    *,
    runs: int = 5,
    priming: tuple[str, ...] = (),
) -> ReplayReport:
    """Run each prompt through CORE ``runs`` times and report bit-identity.

    Pure CORE-side benchmark — no LLM comparison.  Each prompt should
    produce ``unique_count == 1`` (one distinct surface hash across all
    runs).  Any prompt with ``unique_count > 1`` is a determinism
    regression worth investigating.

    ``priming`` is an optional sequence of prior turns played into each
    fresh runtime before the prompt.  Useful for benchmarking surfaces
    that depend on vault state (e.g. compositionality probes).
    """
    runner = _make_core_runner(priming)
    results = tuple(_replay_one(p, runner, runs) for p in prompts)
    return ReplayReport(core_results=results, runs_per_prompt=runs)


def compare_to_llm(
    prompts: list[str],
    *,
    llm_callable: Callable[[str], str] | None = None,
    runs: int = 5,
    priming: tuple[str, ...] = (),
) -> ReplayReport:
    """Run each prompt through CORE and (optionally) through an LLM and
    compare per-prompt surface determinism on both sides.

    ``llm_callable`` is any bring-your-own function from prompt to
    surface string.  No provider lock-in: pass an OpenAI/Anthropic/
    local-model wrapper that already lives in the caller's project.
    When ``llm_callable`` is None this is equivalent to
    ``replay_determinism_report``.

    ``priming`` is forwarded to the CORE side only — the LLM is called
    on the bare prompt since it has no equivalent of CORE's vault.
    """
    core_runner = _make_core_runner(priming)
    core = tuple(_replay_one(p, core_runner, runs) for p in prompts)
    llm: tuple[PromptReplayResult, ...] = ()
    if llm_callable is not None:
        llm = tuple(_replay_one(p, llm_callable, runs) for p in prompts)
    return ReplayReport(core_results=core, llm_results=llm, runs_per_prompt=runs)


# A small set of cognition-pack-grounded long-form prompts the benchmark
# can be invoked with out-of-the-box.  Callers can pass their own list;
# this is just a default that exercises the realizer and operator paths.
DEFAULT_LONGFORM_PROMPTS: tuple[str, ...] = (
    "What is wisdom?",
    "What does truth ground?",
    "What does truth ground in knowledge?",
    "What is judgment?",
    "What does wisdom precede?",
)



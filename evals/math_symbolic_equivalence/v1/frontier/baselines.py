"""Frozen frontier-baseline citations for adjacent math benchmarks.

ADR-0131.1.F establishes the comparison context for the B1 symbolic
equivalence lane. Because B1's univariate polynomial canonical
equivalence is not a standard published benchmark, we pin frontier
scores from **adjacent** benchmarks (MATH-Algebra subset, MATH-500,
MMLU mathematics) as the published-context anchor. These are
deliberately *not* claimed as head-to-head numbers — the head-to-head
is computed live by :mod:`frontier_runner` when API keys are present.

The citation discipline mirrors ADR-0045 / ADR-0119.4: every entry has
a vendor, model, score, source URL, source date, and benchmark scope.
URLs are checked for shape only — they are not de-referenced at test
time.

To add a new citation: append to the appropriate vendor block. The
test :func:`tests.test_adr_0131_1_F_frontier.test_citations_well_formed`
enforces the schema.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Final, Mapping


_AnthropicCitations: tuple[Mapping[str, str | float], ...] = (
    MappingProxyType({
        "vendor": "Anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "benchmark": "MATH (level 1-5, hendrycks)",
        "score": 0.781,
        "metric": "exact_match",
        "source_url": (
            "https://www.anthropic.com/news/claude-3-5-sonnet"
        ),
        "source_date": "2024-06-20",
        "note": (
            "Reported on the full MATH test set (5000 problems). "
            "B1's univariate polynomial scope is a strict subset of "
            "the MATH algebra sub-domain."
        ),
    }),
    MappingProxyType({
        "vendor": "Anthropic",
        "model": "claude-opus-4-1-20250805",
        "benchmark": "AIME 2025 (high-school olympiad-style algebra)",
        "score": 0.901,
        "metric": "exact_match",
        "source_url": "https://www.anthropic.com/claude/opus",
        "source_date": "2025-08-05",
        "note": (
            "AIME problems exceed B1's bounded scope by a wide "
            "margin; reported here as upper-bound context for "
            "frontier symbolic capability."
        ),
    }),
)

_OpenAICitations: tuple[Mapping[str, str | float], ...] = (
    MappingProxyType({
        "vendor": "OpenAI",
        "model": "gpt-4o-2024-05-13",
        "benchmark": "MATH (level 1-5, hendrycks)",
        "score": 0.764,
        "metric": "exact_match",
        "source_url": "https://openai.com/index/hello-gpt-4o/",
        "source_date": "2024-05-13",
        "note": (
            "Same full MATH test set as the Anthropic citation; "
            "scope caveat applies."
        ),
    }),
)

_GoogleCitations: tuple[Mapping[str, str | float], ...] = (
    MappingProxyType({
        "vendor": "Google",
        "model": "gemini-1.5-pro-001",
        "benchmark": "MATH (level 1-5, hendrycks)",
        "score": 0.674,
        "metric": "exact_match",
        "source_url": (
            "https://blog.google/technology/ai/google-gemini-update-"
            "flash-ai-assistant-io-2024/"
        ),
        "source_date": "2024-05-14",
        "note": "Same MATH test set; scope caveat applies.",
    }),
)


ADJACENT_BENCHMARK_CITATIONS: Final[tuple[Mapping[str, str | float], ...]] = (
    *_AnthropicCitations,
    *_OpenAICitations,
    *_GoogleCitations,
)


SCOPE_DISCLAIMER: Final[str] = (
    "Citations above measure frontier capability on the full MATH "
    "benchmark (Hendrycks et al., 2021), which spans algebra, "
    "geometry, number theory, and combinatorics across five difficulty "
    "levels. B1 (ADR-0131.1) measures univariate polynomial canonical "
    "equivalence — a strict subset of the algebra sub-domain. The "
    "citations are not claimed as head-to-head scores on B1; the "
    "head-to-head, when run, is reported separately via "
    "frontier_runner with provider responses cached for replay."
)

"""The capability-index schema + pure aggregation (Phase 1 core).

Pure functions over per-domain counts — no lane execution here (that is
``adapters.py``), so the math is trivially testable and the anti-gaming property
is provable in isolation.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DomainResult:
    """One domain's outcome counts on its independent-gold lane."""

    domain: str
    correct: int
    wrong: int
    refused: int

    @property
    def total(self) -> int:
        return self.correct + self.wrong + self.refused

    @property
    def attempted(self) -> int:
        """Committed an answer (not refused)."""
        return self.correct + self.wrong

    @property
    def coverage(self) -> float:
        """Fraction it was willing to answer."""
        return self.attempted / self.total if self.total else 0.0

    @property
    def accuracy(self) -> float:
        """Accuracy OF COMMITTED answers (1.0 when it commits nothing wrong)."""
        return self.correct / self.attempted if self.attempted else 1.0


@dataclass(frozen=True, slots=True)
class CapabilityIndex:
    domains: tuple[DomainResult, ...]

    @property
    def wrong_total(self) -> int:
        return sum(d.wrong for d in self.domains)

    @property
    def assert_mode_valid(self) -> bool:
        """Assert-mode invariant: zero wrong commits across all domains."""
        return self.wrong_total == 0

    @property
    def _attempted(self) -> int:
        return sum(d.attempted for d in self.domains)

    @property
    def _total(self) -> int:
        return sum(d.total for d in self.domains)

    @property
    def coverage(self) -> float:
        """Micro coverage across all cases."""
        return self._attempted / self._total if self._total else 0.0

    @property
    def accuracy(self) -> float:
        """Micro accuracy of committed answers."""
        correct = sum(d.correct for d in self.domains)
        return correct / self._attempted if self._attempted else 1.0

    @property
    def coverage_geomean(self) -> float:
        """Geometric mean of per-domain coverage — the anti-gaming headline.

        Zero if ANY domain has zero coverage, so a narrow per-domain win cannot
        move it; it rises only when breadth rises. This is "general, not narrow"
        as a number.
        """
        if not self.domains:
            return 0.0
        # geomean = exp(mean(log(coverage))); any 0 -> 0.
        if any(d.coverage <= 0.0 for d in self.domains):
            return 0.0
        log_sum = sum(math.log(d.coverage) for d in self.domains)
        return math.exp(log_sum / len(self.domains))

    @property
    def breadth(self) -> int:
        """How many domains the engine covers at all."""
        return sum(1 for d in self.domains if d.coverage > 0.0)

    @property
    def min_domain_coverage(self) -> float:
        return min((d.coverage for d in self.domains), default=0.0)

    @property
    def capability_score(self) -> float:
        """The single number: breadth-aware coverage × accuracy, hard-gated on
        the assert-mode invariant (any wrong commit zeroes it)."""
        if not self.assert_mode_valid:
            return 0.0
        return self.coverage_geomean * self.accuracy


def aggregate(results: list[DomainResult]) -> CapabilityIndex:
    """Aggregate per-domain results into the cross-domain index."""
    return CapabilityIndex(domains=tuple(results))


def deterministic_digest(index: CapabilityIndex) -> str:
    """SHA-256 over the per-domain counts + verdict axes (reproducible)."""
    payload = {
        "domains": [
            {"domain": d.domain, "correct": d.correct, "wrong": d.wrong, "refused": d.refused}
            for d in sorted(index.domains, key=lambda d: d.domain)
        ],
        "wrong_total": index.wrong_total,
        "assert_mode_valid": index.assert_mode_valid,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def index_to_dict(index: CapabilityIndex) -> dict:
    """JSON-safe report view of the index."""
    return {
        "capability_score": round(index.capability_score, 6),
        "coverage_geomean": round(index.coverage_geomean, 6),
        "coverage_micro": round(index.coverage, 6),
        "accuracy_micro": round(index.accuracy, 6),
        "breadth": index.breadth,
        "min_domain_coverage": round(index.min_domain_coverage, 6),
        "wrong_total": index.wrong_total,
        "assert_mode_valid": index.assert_mode_valid,
        "deterministic_digest": deterministic_digest(index),
        "domains": [
            {
                "domain": d.domain,
                "correct": d.correct,
                "wrong": d.wrong,
                "refused": d.refused,
                "coverage": round(d.coverage, 6),
                "accuracy": round(d.accuracy, 6),
            }
            for d in sorted(index.domains, key=lambda d: d.domain)
        ],
    }

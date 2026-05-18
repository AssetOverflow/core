"""Teaching-loop determinism benchmark.

Run the full reviewed-corpus extension pipeline (propose → replay-
equivalence gate → operator accept) N times against the same input.
Assert byte-identical artifacts every run:

  - proposal_id           (SHA-256 of canonical-JSON payload)
  - replay baseline       (cognition lane metrics on active corpus)
  - replay candidate      (cognition lane metrics on transient corpus)
  - regressed_metrics     (sorted tuple)
  - corpus_append_chain_id

Also report latency:
  - per-iteration wall-time (mean / p50 / p95)
  - total wall-time

Trust boundary: the benchmark writes ONLY to tempdir-scoped paths.
The active teaching corpus on disk is byte-identical pre/post.
Asserted in the report and in the test.
"""

from __future__ import annotations

import shutil
import statistics
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from chat import teaching_grounding as _tg
from teaching.discovery import DiscoveryCandidate, EvidencePointer
from teaching.proposals import (
    ProposalLog,
    accept_proposal,
    propose_from_candidate,
)


# Canonical demo candidate — identical to the learning-loop demo's
# operator-augmented payload.  Same input → same artifacts on every
# iteration; that's the entire benchmark thesis.
def _canonical_candidate() -> DiscoveryCandidate:
    return DiscoveryCandidate(
        candidate_id="bench_canonical_001",
        proposed_chain={
            "subject": "thought", "intent": "cause",
            "connective": "reveals", "object": "meaning",
        },
        trigger="would_have_grounded",
        source_turn_trace="",
        pack_consistent=True,
        boundary_clean=True,
        polarity="affirms",
        claim_domain="factual",
        evidence=(
            EvidencePointer(
                source="corpus",
                ref="cause_creation_reveals_meaning",
                polarity="affirms",
                epistemic_status="coherent",
            ),
        ),
    )


@dataclass(frozen=True, slots=True)
class _IterationArtifact:
    proposal_id: str
    replay_baseline: tuple[tuple[str, float], ...]
    replay_candidate: tuple[tuple[str, float], ...]
    regressed_metrics: tuple[str, ...]
    chain_id_written: str
    elapsed_s: float


@dataclass(frozen=True, slots=True)
class TeachingLoopBenchReport:
    runs: int
    unique_proposal_ids: int
    unique_replay_baselines: int
    unique_replay_candidates: int
    unique_regressed_metrics: int
    unique_chain_ids: int
    deterministic: bool
    active_corpus_byte_identical: bool
    elapsed_mean_s: float
    elapsed_p50_s: float
    elapsed_p95_s: float
    elapsed_total_s: float
    sample_proposal_id: str
    sample_chain_id: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "runs": self.runs,
            "unique_proposal_ids": self.unique_proposal_ids,
            "unique_replay_baselines": self.unique_replay_baselines,
            "unique_replay_candidates": self.unique_replay_candidates,
            "unique_regressed_metrics": self.unique_regressed_metrics,
            "unique_chain_ids": self.unique_chain_ids,
            "deterministic": self.deterministic,
            "active_corpus_byte_identical": self.active_corpus_byte_identical,
            "elapsed_mean_s": round(self.elapsed_mean_s, 4),
            "elapsed_p50_s": round(self.elapsed_p50_s, 4),
            "elapsed_p95_s": round(self.elapsed_p95_s, 4),
            "elapsed_total_s": round(self.elapsed_total_s, 4),
            "sample_proposal_id": self.sample_proposal_id,
            "sample_chain_id": self.sample_chain_id,
        }


def _freeze_metrics(d: dict[str, float]) -> tuple[tuple[str, float], ...]:
    """Convert a metrics dict to a sorted tuple-of-pairs (hashable, ordered)."""
    return tuple(sorted((k, round(float(v), 6)) for k, v in d.items()))


def _percentile(values: list[float], pct: float) -> float:
    """Inclusive percentile via linear interpolation.  Pure stdlib so
    the bench has no numpy dependency on this path."""
    if not values:
        return 0.0
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * pct / 100.0
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    if lo == hi:
        return s[lo]
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def run_teaching_loop_determinism(runs: int = 10) -> TeachingLoopBenchReport:
    """Execute the full propose → replay → accept loop ``runs`` times
    against the same candidate, then assert byte-identical artifacts.

    Trust boundary: the active corpus is read once at the start and
    once at the end; any byte difference is a defect.  All writes
    are confined to tempdirs created inside this function.
    """
    active_path = _tg._CORPUS_PATH
    active_bytes_before = active_path.read_bytes() if active_path.exists() else b""

    artifacts: list[_IterationArtifact] = []
    total_t0 = time.perf_counter()

    for _ in range(runs):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "proposals.jsonl"
            transient = Path(tmpdir) / "cognition_chains_v1.jsonl"
            if active_path.exists():
                shutil.copyfile(active_path, transient)
            else:
                transient.write_text("", encoding="utf-8")

            log = ProposalLog(log_path)
            candidate = _canonical_candidate()

            t0 = time.perf_counter()
            proposal = propose_from_candidate(candidate, log=log)
            rec = log.find(proposal.proposal_id) or {}
            ev = rec.get("replay_evidence") or {}

            chain_id = accept_proposal(
                proposal.proposal_id, log=log,
                corpus_path=transient,
                review_date="2026-05-18",
                operator_note="bench",
            )
            elapsed = time.perf_counter() - t0

            artifacts.append(_IterationArtifact(
                proposal_id=proposal.proposal_id,
                replay_baseline=_freeze_metrics(ev.get("baseline", {})),
                replay_candidate=_freeze_metrics(ev.get("candidate", {})),
                regressed_metrics=tuple(ev.get("regressed_metrics") or ()),
                chain_id_written=chain_id,
                elapsed_s=elapsed,
            ))

    elapsed_total = time.perf_counter() - total_t0
    elapsed_values = [a.elapsed_s for a in artifacts]

    active_bytes_after = active_path.read_bytes() if active_path.exists() else b""

    unique_pids = len({a.proposal_id for a in artifacts})
    unique_baselines = len({a.replay_baseline for a in artifacts})
    unique_candidates = len({a.replay_candidate for a in artifacts})
    unique_regressed = len({a.regressed_metrics for a in artifacts})
    unique_chain_ids = len({a.chain_id_written for a in artifacts})

    deterministic = (
        unique_pids == 1
        and unique_baselines == 1
        and unique_candidates == 1
        and unique_regressed == 1
        and unique_chain_ids == 1
    )

    return TeachingLoopBenchReport(
        runs=runs,
        unique_proposal_ids=unique_pids,
        unique_replay_baselines=unique_baselines,
        unique_replay_candidates=unique_candidates,
        unique_regressed_metrics=unique_regressed,
        unique_chain_ids=unique_chain_ids,
        deterministic=deterministic,
        active_corpus_byte_identical=(active_bytes_before == active_bytes_after),
        elapsed_mean_s=statistics.mean(elapsed_values) if elapsed_values else 0.0,
        elapsed_p50_s=_percentile(elapsed_values, 50.0),
        elapsed_p95_s=_percentile(elapsed_values, 95.0),
        elapsed_total_s=elapsed_total,
        sample_proposal_id=artifacts[0].proposal_id if artifacts else "",
        sample_chain_id=artifacts[0].chain_id_written if artifacts else "",
    )


__all__ = [
    "TeachingLoopBenchReport",
    "run_teaching_loop_determinism",
]

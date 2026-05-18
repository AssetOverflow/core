"""Teaching-loop determinism benchmark — falsifiable claim test.

The bench itself runs at any N ≥ 1; the test pins the headline claim
at a low N for fast CI.  Headline claim:

  "N identical inputs produce N byte-identical proposal artifacts,
   the active corpus is byte-identical pre/post, and the wall-time
   distribution is well-formed."

If determinism breaks anywhere in the pipeline (proposal_id hashing,
replay-equivalence gate, accept-side corpus_append, ProposalLog
replay), at least one of the ``unique_*`` counts in the bench report
will exceed 1 and this test fails.

Performance: a module-scoped fixture shares one ``runs=3`` invocation
across every test in this file.  Each ``run_teaching_loop_determinism``
call runs the propose/replay/accept pipeline N times; cutting from 5
calls (runs=3,2,2,3,2 = 12 pipeline runs) to 1 call (3 runs) is a
~4× speedup with no contract loss.
"""

from __future__ import annotations

import json

import pytest

from benchmarks.teaching_loop import run_teaching_loop_determinism


@pytest.fixture(scope="module")
def bench_report():
    """Single ``runs=3`` invocation shared across every test in this
    file.  ``runs=3`` is the highest N any individual test asks for,
    so the determinism / latency / serialisation assertions all hold
    against the same report."""
    return run_teaching_loop_determinism(runs=3)


def test_teaching_loop_is_deterministic_across_three_runs(bench_report) -> None:
    assert bench_report.deterministic is True
    assert bench_report.active_corpus_byte_identical is True
    assert bench_report.unique_proposal_ids == 1
    assert bench_report.unique_replay_baselines == 1
    assert bench_report.unique_replay_candidates == 1
    assert bench_report.unique_regressed_metrics == 1
    assert bench_report.unique_chain_ids == 1


def test_proposal_id_is_a_sha256_prefix(bench_report) -> None:
    pid = bench_report.sample_proposal_id
    assert len(pid) == 32
    assert all(c in "0123456789abcdef" for c in pid)


def test_chain_id_matches_canonical_layout(bench_report) -> None:
    assert bench_report.sample_chain_id == "cause_thought_reveals_meaning"


def test_latency_stats_are_well_formed(bench_report) -> None:
    assert bench_report.elapsed_mean_s > 0.0
    assert bench_report.elapsed_p50_s > 0.0
    assert bench_report.elapsed_p95_s >= bench_report.elapsed_p50_s
    assert bench_report.elapsed_total_s >= bench_report.elapsed_mean_s * bench_report.runs * 0.9


def test_report_serialises_to_json(bench_report) -> None:
    blob = json.dumps(bench_report.as_dict(), sort_keys=True)
    assert "deterministic" in blob
    assert "active_corpus_byte_identical" in blob

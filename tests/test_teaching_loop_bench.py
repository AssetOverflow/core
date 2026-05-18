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
"""

from __future__ import annotations

from benchmarks.teaching_loop import run_teaching_loop_determinism


def test_teaching_loop_is_deterministic_across_three_runs() -> None:
    report = run_teaching_loop_determinism(runs=3)
    assert report.deterministic is True
    assert report.active_corpus_byte_identical is True
    assert report.unique_proposal_ids == 1
    assert report.unique_replay_baselines == 1
    assert report.unique_replay_candidates == 1
    assert report.unique_regressed_metrics == 1
    assert report.unique_chain_ids == 1


def test_proposal_id_is_a_sha256_prefix() -> None:
    report = run_teaching_loop_determinism(runs=2)
    pid = report.sample_proposal_id
    assert len(pid) == 32
    assert all(c in "0123456789abcdef" for c in pid)


def test_chain_id_matches_canonical_layout() -> None:
    report = run_teaching_loop_determinism(runs=2)
    assert report.sample_chain_id == "cause_thought_reveals_meaning"


def test_latency_stats_are_well_formed() -> None:
    report = run_teaching_loop_determinism(runs=3)
    assert report.elapsed_mean_s > 0.0
    assert report.elapsed_p50_s > 0.0
    assert report.elapsed_p95_s >= report.elapsed_p50_s
    assert report.elapsed_total_s >= report.elapsed_mean_s * report.runs * 0.9


def test_report_serialises_to_json() -> None:
    import json
    report = run_teaching_loop_determinism(runs=2)
    blob = json.dumps(report.as_dict(), sort_keys=True)
    assert "deterministic" in blob
    assert "active_corpus_byte_identical" in blob

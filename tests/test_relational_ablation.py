"""The ablation verdict — pinned as the honest experimental result.

The field-reasoner wedge's measurement #2/#3 on the simple additive/part-whole
micro-domain: the geometric field reader is **decoration** — it catches no
comprehension error the symbolic reader makes, and the only place it changes the
admitted set is by *losing* coverage (refusing a correct answer at the precision
ceiling). This test pins that finding; if a future change makes the field genuinely
catch a symbolic error, ``field_caught_symbolic_errors`` becomes non-empty and the
PASS assertion here must be revisited (a deliberately meaningful pin).

The one INVARIANT that must always hold regardless of the verdict: the field never
commits a wrong answer (wrong=0 is structural).
"""

from __future__ import annotations

from evals.relational_metric.ablation import run


def test_field_never_commits_wrong():
    """wrong=0 — the non-negotiable. The field refuses rather than commit a bad int."""
    report = run()
    assert report["field_wrong_commits"] == [], report["field_wrong_commits"]


def test_verdict_is_honest_c3_on_this_domain():
    """On forward-substitutable additive relations the field adds no independent signal:
    geometric translation == arithmetic addition, so it catches zero symbolic errors."""
    report = run()
    assert report["field_caught_symbolic_errors"] == []
    assert report["verdict"].startswith("C3")


def test_field_only_changes_admitted_set_by_losing_coverage():
    """The admitted set differs from symbolic-alone only because the field REFUSES a
    correct answer (the precision ceiling) — a liability, not error-catching signal."""
    report = run()
    assert report["admitted_set_changed"] is True
    assert report["gate_admitted_count"] < report["symbolic_alone_admitted_count"]
    assert report["field_lost_coverage"]  # non-empty: the ceiling case


def test_readers_agree_and_are_both_correct_on_committable_classes():
    """Per-class diversity is ZERO on every committable class — the readers are
    redundant here (the dossier's predicted common-mode on a metric-trivial domain)."""
    report = run()
    for cls, stats in report["per_class"].items():
        if cls.startswith("coverage_"):
            continue
        assert stats["disagree"] == 0
        assert stats["double_fault"] == 0
        assert stats["both_correct"] == stats["n"]

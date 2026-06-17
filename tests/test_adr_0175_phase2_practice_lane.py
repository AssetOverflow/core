"""ADR-0175 Phase 2 — sealed practice lane.

A NEW lane (never the wrong=0-pinned train_sample serving runner) that runs the
train-sample cases in *practice* mode: scores correct/wrong/refused as practice
metrics, feeds per-class counts into the Phase 1 ledger, diagnoses every refusal
(§8 skill/knowledge/ambiguity), and emits elimination records for wrongs.

Live capability contract (monotonic, not frozen):
- wrong == 0 is hard;
- correct >= historical floor, refused <= historical ceiling;
- total count fixed; every refusal diagnosed; eliminations track wrongs only.

The historical floor/ceiling (6 correct / 44 refused / 0 wrong of 50) is the
Inc1-era rebaseline snapshot — not a design target or ceiling on capability lift.
Phase 2 proves the *regime*: lane, ledger wiring, diagnosis, elimination schema,
and the seal. Attempt-generating search is Phase 3.

Invariants exercised by failing-under-violation tests:
- #1 seal           -> TestSealInvariant
- #3 determinism    -> TestDeterminismInvariant
"""

from __future__ import annotations

import dataclasses

import pytest

from core.reliability_gate import conservative_floor
from core.learning_arena.report import PracticeReport
from evals.gsm8k_math.practice.v1.runner import (
    OPERATION_CLASSES,
    REFUSAL_DIAGNOSES,
    EliminationRecord,
    build_report,
    classify_operation,
    diagnose_refusal,
    run_practice,
)

# Historical floor/ceiling from Inc1 rebaseline (2026-06-17). Monotonic contract:
# correct may rise, refused may fall, wrong must stay 0. Not a capability ceiling.
BASELINE_CORRECT = 6
BASELINE_WRONG = 0
BASELINE_REFUSED = 44
TRAIN_SAMPLE_COUNT = 50


def _assert_monotonic_capability_contract(rep: PracticeReport) -> None:
    """CORE practice-lane live contract: wrong=0 hard; counts monotonic vs floor."""
    counts = rep.counts
    assert counts["wrong"] == BASELINE_WRONG
    assert counts["correct"] >= BASELINE_CORRECT
    assert counts["refused"] <= BASELINE_REFUSED
    assert (
        counts["correct"] + counts["wrong"] + counts["refused"]
        == TRAIN_SAMPLE_COUNT
    )
    assert len(rep.elimination_records) == counts["wrong"]
    assert len(rep.refusal_diagnoses) == counts["refused"]
    assert all(d in REFUSAL_DIAGNOSES for d in rep.refusal_diagnoses.values())
    diagnosis_counts = rep.as_dict()["diagnosis_counts"]
    assert sum(diagnosis_counts.values()) == counts["refused"]


# A stub CaseOutcome shape compatible with what the practice lane reads.
@dataclasses.dataclass(frozen=True)
class _StubOutcome:
    case_id: str
    outcome: str
    reason: str | None = None
    actual_answer: float | None = None


def _case(cid: str, expr: str, gold: float, q: str = "Q?") -> dict:
    return {
        "case_id": cid,
        "question": q,
        "answer_numeric": gold,
        "answer_expression": expr,
    }


# ---------------------------------------------------------------------------
# classify_operation — gold-derived primary operation class
# ---------------------------------------------------------------------------

class TestClassifyOperation:
    def test_multiplicative_when_star_present(self) -> None:
        assert classify_operation("a x b = <<15*10=150>>150 then <<150*3=450>>450") == "multiplicative"

    def test_divisive_when_only_division(self) -> None:
        assert classify_operation("<<20/5=4>>4 and <<4+0=4>>4") == "divisive"

    def test_additive_when_no_mul_or_div(self) -> None:
        assert classify_operation("<<2+4=6>>6 and <<6-1=5>>5") == "additive"

    def test_classes_are_closed_set(self) -> None:
        for expr in ["<<1*2=2>>", "<<4/2=2>>", "<<1+1=2>>", "no annotations here"]:
            assert classify_operation(expr) in OPERATION_CLASSES


# ---------------------------------------------------------------------------
# diagnose_refusal — §8 skill / knowledge / ambiguity router
# ---------------------------------------------------------------------------

class TestDiagnoseRefusal:
    def test_empty_injection_is_skill_gap(self) -> None:
        r = "candidate_graph: recognizer matched but produced no injection for statement: 'X.' (category=discrete_count_statement)"
        assert diagnose_refusal(r) == "skill_gap"

    def test_no_admissible_statement_is_knowledge_gap(self) -> None:
        assert diagnose_refusal("candidate_graph: no admissible candidate for statement: 'X.'") == "knowledge_gap"

    def test_branches_disagree_is_genuine_ambiguity(self) -> None:
        assert diagnose_refusal("candidate_graph: branches disagree on answer (distinct values: [1, 2])") == "genuine_ambiguity"

    def test_every_diagnosis_in_closed_set(self) -> None:
        for r in ["anything", "", "no admissible candidate for question: 'Q?'", "no branch produced a solvable graph"]:
            assert diagnose_refusal(r) in REFUSAL_DIAGNOSES


# ---------------------------------------------------------------------------
# run_practice — ledger wiring + diagnosis + elimination records
# ---------------------------------------------------------------------------

class TestRunPractice:
    def test_ledger_is_per_class_and_totals_match(self) -> None:
        cases = [
            _case("m1", "<<2*3=6>>", 6.0),
            _case("m2", "<<2*3=6>>", 6.0),
            _case("a1", "<<2+3=5>>", 5.0),
        ]
        def scorer(adapted):  # all refuse
            return _StubOutcome(adapted["id"], "refused", reason="no admissible candidate for statement: 'x'")
        rep = run_practice(cases, scorer=scorer)
        assert sum(t.attempted for t in rep.ledger.values()) == 3
        assert rep.ledger["multiplicative"].refused == 2
        assert rep.ledger["additive"].refused == 1

    def test_reliability_flows_from_phase1(self) -> None:
        cases = [_case(f"m{i}", "<<2*3=6>>", 6.0) for i in range(40)]
        def scorer(adapted):
            return _StubOutcome(adapted["id"], "correct", actual_answer=6.0)
        rep = run_practice(cases, scorer=scorer)
        tally = rep.ledger["multiplicative"]
        assert tally.correct == 40
        assert tally.reliability == conservative_floor(40, 40)
        assert tally.reliability >= 0.85  # 40 clean commitments clears propose

    def test_wrong_emits_elimination_record(self) -> None:
        cases = [_case("w1", "<<2*3=6>>", 6.0)]
        def scorer(adapted):
            return _StubOutcome(adapted["id"], "wrong", reason="got 5", actual_answer=5.0)
        rep = run_practice(cases, scorer=scorer)
        assert rep.counts["wrong"] == 1
        assert len(rep.elimination_records) == 1
        rec = rep.elimination_records[0]
        assert rec.case_id == "w1"
        assert rec.class_name == "multiplicative"
        assert rec.attempted == 5.0
        assert rec.gold == 6.0

    def test_refusal_diagnosed(self) -> None:
        cases = [_case("r1", "<<2*3=6>>", 6.0)]
        def scorer(adapted):
            return _StubOutcome(adapted["id"], "refused", reason="candidate_graph: branches disagree on answer (distinct values: [1, 2])")
        rep = run_practice(cases, scorer=scorer)
        assert rep.refusal_diagnoses["r1"] == "genuine_ambiguity"

    def test_practice_tolerates_wrong_no_exit_failure(self) -> None:
        # practice does NOT gate on wrong==0 (that is serving's contract)
        cases = [_case("w1", "<<2*3=6>>", 6.0)]
        def scorer(adapted):
            return _StubOutcome(adapted["id"], "wrong", reason="x", actual_answer=99.0)
        rep = run_practice(cases, scorer=scorer)
        assert rep.counts["wrong"] == 1  # recorded, not rejected
        assert rep.as_dict()["regime"] == "practice"

    def test_elimination_record_is_frozen(self) -> None:
        rec = EliminationRecord("c", "multiplicative", 1.0, 2.0, "r")
        with pytest.raises(dataclasses.FrozenInstanceError):
            rec.gold = 9.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Live lane over train sample — monotonic capability contract
# ---------------------------------------------------------------------------

class TestLiveLane:
    def test_live_practice_meets_monotonic_capability_contract(self) -> None:
        # Historical floor 6/44/0; future correct-count lift must not fail this test.
        # Eliminations remain tied to wrong attempts only (zero at current baseline).
        rep = build_report()
        _assert_monotonic_capability_contract(rep)

    def test_every_refusal_is_diagnosed(self) -> None:
        rep = build_report()
        _assert_monotonic_capability_contract(rep)
        # Redundant pins kept explicit: no refusal silently drops from diagnostics.
        assert len(rep.refusal_diagnoses) == rep.counts["refused"]
        assert sum(rep.as_dict()["diagnosis_counts"].values()) == rep.counts["refused"]


# ---------------------------------------------------------------------------
# Invariant #1 — the seal (nothing leaks to serving)
# ---------------------------------------------------------------------------

class TestSealInvariant:
    def test_practice_does_not_change_serving_score(self) -> None:
        from evals.gsm8k_math.train_sample.v1.runner import (
            _CASES_PATH,
            _load_cases,
            build_report as serving_build_report,
        )
        cases = _load_cases(_CASES_PATH)
        serving_before = serving_build_report(cases)
        build_report()  # run practice over same cases
        serving_after = serving_build_report(cases)
        assert serving_before["counts"] == serving_after["counts"]
        assert serving_after["counts"]["wrong"] == BASELINE_WRONG
        assert serving_after["counts"]["correct"] >= BASELINE_CORRECT
        assert serving_after["counts"]["refused"] <= BASELINE_REFUSED

    def test_no_serving_module_imports_the_practice_lane(self) -> None:
        import subprocess
        from pathlib import Path
        repo = Path(__file__).resolve().parents[1]
        # the engine/serving path must not import the practice lane
        out = subprocess.run(
            ["grep", "-rl", "practice.v1.runner", "--include=*.py", "generate", "chat"],
            cwd=repo, capture_output=True, text=True,
        )
        assert out.stdout.strip() == ""


# ---------------------------------------------------------------------------
# Invariant #3 — determinism / replay
# ---------------------------------------------------------------------------

class TestDeterminismInvariant:
    def test_report_byte_identical_across_runs(self) -> None:
        import json
        a = json.dumps(build_report().as_dict(), sort_keys=True)
        b = json.dumps(build_report().as_dict(), sort_keys=True)
        assert a == b

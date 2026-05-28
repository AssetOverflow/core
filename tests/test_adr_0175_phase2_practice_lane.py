"""ADR-0175 Phase 2 — sealed practice lane.

A NEW lane (never the wrong=0-pinned train_sample serving runner) that runs the
47 train cases in *practice* mode: scores correct/wrong/refused as practice
metrics, feeds per-class counts into the Phase 1 ledger, diagnoses every refusal
(§8 skill/knowledge/ambiguity), and emits elimination records for wrongs.

On the current pipeline the engine still refuses rather than guesses, so the
practice ledger mirrors serving (3 correct / 0 wrong / 47 refused, of 50) and
zero eliminations fire live — the attempt-generating search is Phase 3. Phase 2
proves the *regime*: the lane, the ledger wiring, the diagnosis, the elimination
schema, and the seal.

Invariants exercised by failing-under-violation tests:
- #1 seal           -> TestSealInvariant
- #3 determinism    -> TestDeterminismInvariant
"""

from __future__ import annotations

import dataclasses

import pytest

from core.reliability_gate import conservative_floor
from evals.gsm8k_math.practice.v1.runner import (
    OPERATION_CLASSES,
    REFUSAL_DIAGNOSES,
    EliminationRecord,
    build_report,
    classify_operation,
    diagnose_refusal,
    run_practice,
)


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
# Live lane over the real 47 — mirrors serving on the current pipeline
# ---------------------------------------------------------------------------

class TestLiveLane:
    def test_live_practice_mirrors_serving_today(self) -> None:
        # With the refuse-preferring engine, practice == serving (3/47/0).
        # Attempts/eliminations go live in Phase 3.
        rep = build_report()
        assert rep.counts == {"correct": 3, "wrong": 0, "refused": 47}
        assert len(rep.elimination_records) == 0  # no wrongs yet

    def test_every_refusal_is_diagnosed(self) -> None:
        rep = build_report()
        assert len(rep.refusal_diagnoses) == 47
        assert all(d in REFUSAL_DIAGNOSES for d in rep.refusal_diagnoses.values())


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
        build_report()  # run practice
        serving = serving_build_report(_load_cases(_CASES_PATH))
        assert serving["counts"] == {"correct": 3, "wrong": 0, "refused": 47}

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

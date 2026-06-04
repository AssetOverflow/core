"""ADR-0199 PR-2 — the cross-domain learning-arena engine.

Proves exactly the PR-2 gate: the extracted engine reuses the single pinned
floor (L-1), holds the seal (L-3), is a deterministic fold (L-4), and the GSM8K
math instance preserves its committed golden queue. Tier-2 scoring is optional
and remains inert unless a domain supplies a verifier.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.learning_arena import (
    BaseAttempt,
    Problem,
    run_practice,
)
from core.reasoning import TIER2_VERIFIED, Tier2Verdict
from core.reliability_gate import conservative_floor

_REPO = Path(__file__).resolve().parents[1]


# --- a tiny synthetic domain (no heavy deps) ----------------------------------


@dataclass(frozen=True, slots=True)
class _StubSolver:
    """Reads the verdict the synthetic payload declares; pure and total."""

    domain_id: str = "stub"

    def attempt(self, problem: Problem) -> BaseAttempt:
        p = problem.payload
        return BaseAttempt(
            committed=p["verdict"] != "refused",
            answer=p.get("answer"),
            reason=p.get("reason", ""),
            case_id=problem.problem_id,
        )


@dataclass(frozen=True, slots=True)
class _StubTether:
    domain_id: str = "stub"

    def is_correct(self, attempt: BaseAttempt, problem: Problem) -> bool:
        return problem.payload["verdict"] == "correct"

    def gold_answer(self, problem: Problem) -> float:
        return float(problem.payload["gold"])


@dataclass(frozen=True, slots=True)
class _StubTier2Verifier:
    domain_id: str = "stub"

    def verify(self, attempt: BaseAttempt, problem: Problem) -> Tier2Verdict:
        if not problem.payload.get("t2", False):
            return Tier2Verdict(False, "insufficient_evidence")
        return Tier2Verdict(
            True,
            TIER2_VERIFIED,
            commitment_key=str(attempt.answer),
            evidence_hash=f"hash:{attempt.case_id}",
            structural_signatures=("shape-a", "shape-b"),
        )


def _problems() -> list[Problem]:
    return [
        Problem("c1", "alpha", {"verdict": "correct", "answer": 9.0, "gold": 9.0}),
        Problem("c2", "alpha", {"verdict": "wrong", "answer": 7.0, "gold": 10.0,
                                "reason": "off by three"}),
        Problem("c3", "beta", {"verdict": "refused", "reason": "branches disagree"}),
        Problem("c4", "alpha", {"verdict": "correct", "answer": 4.0, "gold": 4.0}),
    ]


def _diagnose(reason: str) -> str:
    return "genuine_ambiguity" if "disagree" in reason else "knowledge_gap"


# --- L-4: deterministic fold + correct accounting -----------------------------


def test_engine_counts_ledger_eliminations_diagnoses():
    rep = run_practice(_problems(), _StubSolver(), _StubTether(), diagnose=_diagnose)
    assert rep.counts == {"correct": 2, "wrong": 1, "refused": 1}

    alpha = rep.ledger["alpha"]
    assert (alpha.correct, alpha.wrong, alpha.refused) == (2, 1, 0)
    assert (alpha.t2_verified, alpha.t2_agrees_gold) == (0, 0)
    beta = rep.ledger["beta"]
    assert (beta.correct, beta.wrong, beta.refused) == (0, 0, 1)

    assert len(rep.elimination_records) == 1
    elim = rep.elimination_records[0]
    assert (elim.case_id, elim.class_name, elim.attempted, elim.gold) == (
        "c2", "alpha", 7.0, 10.0,
    )
    assert rep.refusal_diagnoses == {"c3": "genuine_ambiguity"}


def test_engine_is_deterministic():
    a = run_practice(_problems(), _StubSolver(), _StubTether(), diagnose=_diagnose)
    b = run_practice(_problems(), _StubSolver(), _StubTether(), diagnose=_diagnose)
    assert json.dumps(a.as_dict(), sort_keys=True) == json.dumps(b.as_dict(), sort_keys=True)


def test_optional_tier2_verifier_populates_anchor_precision() -> None:
    problems = [
        Problem("c1", "alpha", {"verdict": "correct", "answer": 9.0, "gold": 9.0, "t2": True}),
        Problem("c2", "alpha", {"verdict": "wrong", "answer": 7.0, "gold": 10.0, "t2": True}),
        Problem("c3", "alpha", {"verdict": "correct", "answer": 4.0, "gold": 4.0, "t2": False}),
        Problem("c4", "alpha", {"verdict": "refused", "reason": "no graph", "t2": True}),
    ]

    rep = run_practice(
        problems,
        _StubSolver(),
        _StubTether(),
        diagnose=_diagnose,
        tier2_verifier=_StubTier2Verifier(),
    )

    alpha = rep.ledger["alpha"]
    assert (alpha.correct, alpha.wrong, alpha.refused) == (2, 1, 1)
    assert alpha.t2_verified == 2
    assert alpha.t2_agrees_gold == 1
    per_class = rep.as_dict()["per_class"]["alpha"]
    assert per_class["t2_verified"] == 2
    assert per_class["t2_agrees_gold"] == 1
    assert per_class["t2_precision"] == alpha.t2_precision


# --- L-1: one shared pinned floor; no per-arena pessimism constant ------------


def test_engine_reliability_flows_through_shared_floor():
    rep = run_practice(_problems(), _StubSolver(), _StubTether(), diagnose=_diagnose)
    alpha = rep.ledger["alpha"]
    # reliability is exactly the shared conservative_floor over committed counts.
    assert alpha.reliability == conservative_floor(alpha.correct, alpha.committed)


def test_learning_arena_defines_no_floor_constants():
    pkg = _REPO / "core" / "learning_arena"
    for src in pkg.glob("*.py"):
        text = src.read_text(encoding="utf-8")
        assert "WILSON_Z" not in text, f"{src.name} must not redefine the floor"
        assert "N_MIN" not in text, f"{src.name} must not redefine the floor"


# --- L-3: the seal — no serving module imports the arena ----------------------


def test_seal_no_serving_imports_learning_arena():
    res = subprocess.run(
        ["grep", "-rl", "learning_arena", "--include=*.py", "generate", "chat"],
        cwd=_REPO, capture_output=True, text=True,
    )
    assert res.stdout.strip() == "", (
        "a serving module imports the learning arena (seal violation):\n" + res.stdout
    )


# --- behavior parity: the GSM8K math instance reproduces its golden -----------


def test_gsm8k_instance_reproduces_committed_queue():
    from evals.gsm8k_math.practice.v1.propose_runner import (
        build_ratification_queue,
        resolve_pooled_scorer,
    )

    golden_path = (
        _REPO / "evals" / "gsm8k_math" / "practice" / "v1" / "ratification_queue.json"
    )
    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    produced = build_ratification_queue(scorer=resolve_pooled_scorer)
    assert json.dumps(produced, sort_keys=True) == json.dumps(golden, sort_keys=True)

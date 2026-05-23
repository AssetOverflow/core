"""ADR-0131.2 — Math teaching corpus lane runner (v1).

Loads ``cases.jsonl``, runs each case through the propose-ratify-replay loop,
classifies the outcome against the expected verdict, and writes a deterministic
``report.json``.

CLI: ``python -m evals.math_teaching_corpus.v1.runner``
  exit status 0 if exit criterion passes, 1 otherwise.

Exit criterion (per ADR-0131 Benchmark 2):
  correct_rate == 1.0 (all chains pass)
  wrong        == 0
"""

from __future__ import annotations

import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from chat.teaching_grounding import TeachingCorpusSpec
import chat.teaching_grounding as _tg
from teaching.discovery import DiscoveryCandidate, EvidencePointer
from teaching.proposals import (
    ProposalError,
    ProposalLog,
    accept_proposal,
    propose_from_candidate,
)

_HERE = Path(__file__).resolve().parent
_CASES_PATH = _HERE / "cases.jsonl"
_REPORT_PATH = _HERE / "report.json"

_CORRECT_RATE_MIN = 1.0
_WRONG_MAX = 0


@dataclass(frozen=True, slots=True)
class CaseOutcome:
    case_id: str
    category: str
    expected: str
    actual: str
    verdict_class: str  # "correct" | "wrong" | "refused"
    reason: str

    def as_dict(self) -> dict[str, str]:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "expected": self.expected,
            "actual": self.actual,
            "verdict_class": self.verdict_class,
            "reason": self.reason,
        }


def hash_candidate_id(proposed_chain: dict[str, Any]) -> str:
    import hashlib
    payload = {
        "proposed_chain": proposed_chain,
        "trigger": "would_have_grounded",
        "source_turn_trace": "",
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _score_one(
    case: dict[str, Any],
    log: ProposalLog,
    temp_math_corpus_path: Path,
) -> CaseOutcome:
    """Propose and ratify a single case, checking replay-equivalence."""
    expected = case["expected"]
    proposed_chain = case["proposed_chain"]
    
    # 1. Construct the DiscoveryCandidate
    candidate = DiscoveryCandidate(
        candidate_id=hash_candidate_id(proposed_chain),
        proposed_chain=proposed_chain,
        trigger="would_have_grounded",
        source_turn_trace="",
        pack_consistent=True,
        boundary_clean=True,
        polarity="affirms",
        claim_domain="factual",
        evidence=(
            EvidencePointer(
                source="corpus",
                ref="cause_truth_grounds_knowledge",
                polarity="affirms",
                epistemic_status="coherent",
            ),
        ),
    )

    try:
        # 2. Propose candidate
        proposal = propose_from_candidate(candidate, log=log)
        
        # 3. Read back proposal to inspect replay
        proposal_state = log.current_state().get(proposal.proposal_id)
        if not proposal_state:
            actual = "refused"
            verdict_class = "refused" if expected == "refused" else "wrong"
            reason = "proposal not found in log"
        elif proposal_state["state"] == "rejected":
            # Auto-rejected due to regression
            actual = "not_equivalent"
            verdict_class = "correct" if expected == "not_equivalent" else "wrong"
            reason = proposal_state.get("operator_note", "auto-rejected")
        elif proposal_state["state"] == "pending":
            # Ready for ratification
            accept_proposal(
                proposal.proposal_id,
                log=log,
                corpus_path=temp_math_corpus_path,
                review_date="2026-05-23",
                operator_note="accepted in Benchmark 2",
            )
            actual = "replay_equivalent"
            verdict_class = "correct" if expected == "replay_equivalent" else "wrong"
            reason = ""
        else:
            actual = proposal_state["state"]
            verdict_class = "wrong"
            reason = f"unexpected proposal state: {actual}"

    except ProposalError as exc:
        actual = "refused"
        verdict_class = "refused" if expected == "refused" else "wrong"
        reason = str(exc)
    except Exception as exc:
        actual = "error"
        verdict_class = "wrong"
        reason = f"{exc.__class__.__name__}: {exc}"

    return CaseOutcome(
        case_id=case["case_id"],
        category=case["category"],
        expected=expected,
        actual=actual,
        verdict_class=verdict_class,
        reason=reason,
    )


def _load_cases(path: Path = _CASES_PATH) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def build_report(cases: list[dict[str, Any]]) -> dict[str, Any]:
    # We set up a temporary environment for the proposal log and math corpus
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_log_path = Path(tmpdir) / "proposals.jsonl"
        temp_math_corpus_path = Path(tmpdir) / "math_teaching_v1.jsonl"
        
        log = ProposalLog(path=temp_log_path)
        
        # Dynamically register the math corpus so the replay loop considers it
        original_corpora = _tg.TEACHING_CORPORA
        math_spec = TeachingCorpusSpec(
            corpus_id="math_teaching_v1",
            path=temp_math_corpus_path,
            pack_id="en_mathematics_logic_v1",
        )
        
        try:
            _tg.TEACHING_CORPORA = original_corpora + (math_spec,)
            _tg.clear_teaching_caches()
            
            outcomes = []
            for c in cases:
                outcomes.append(_score_one(c, log, temp_math_corpus_path))
                
        finally:
            # Restore original corpora specs and clear caches
            _tg.TEACHING_CORPORA = original_corpora
            _tg.clear_teaching_caches()

    counts = {"correct": 0, "wrong": 0, "refused": 0}
    for o in outcomes:
        counts[o.verdict_class] += 1

    total = len(outcomes)
    correct_rate = counts["correct"] / total if total else 0.0
    passed = (correct_rate >= _CORRECT_RATE_MIN) and (counts["wrong"] <= _WRONG_MAX)

    return {
        "schema_version": 1,
        "adr": "0131.2",
        "benchmark": "math_teaching_corpus_v1",
        "cases_path": str(_CASES_PATH.relative_to(_HERE.parent.parent.parent)),
        "sample_count": total,
        "counts": counts,
        "correct_rate": correct_rate,
        "exit_criterion": {
            "correct_rate_min": _CORRECT_RATE_MIN,
            "wrong_max": _WRONG_MAX,
            "passed": passed,
        },
        "per_case": [o.as_dict() for o in outcomes],
    }


def write_report(report: dict[str, Any], path: Path = _REPORT_PATH) -> None:
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    cases = _load_cases()
    report = build_report(cases)
    write_report(report)
    return 0 if report["exit_criterion"]["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())

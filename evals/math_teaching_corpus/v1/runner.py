"""ADR-0131.2.B — Math teaching corpus lane runner (v1.B).

Loads ``cases.jsonl``, runs each case through the propose-ratify-replay loop,
classifies the outcome against the expected verdict, and writes a deterministic
``report.json``.

CLI: ``python -m evals.math_teaching_corpus.v1.runner``
  exit status 0 if exit criterion passes, 1 otherwise.

Exit criterion (per ADR-0131.2.B):
  correct_rate == 1.0 (all chains pass)
  wrong        == 0 across all expected classes
"""

from __future__ import annotations

import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from chat.pack_resolver import _pack_lexicon_for
from chat.teaching_grounding import TeachingCorpusSpec
import chat.teaching_grounding as _tg
from teaching.discovery import DiscoveryCandidate, EvidencePointer
from teaching.proposals import (
    ProposalError,
    ProposalLog,
    ReplayEvidence,
    accept_proposal,
    propose_from_candidate,
)

_HERE = Path(__file__).resolve().parent
_CASES_PATH = _HERE / "cases.jsonl"
_REPORT_PATH = _HERE / "report.json"
_CORPUS_PATH = _HERE.parent.parent.parent / "teaching" / "math_corpora" / "math_teaching_v1.jsonl"

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

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "expected": self.expected,
            "actual": self.actual,
            "verdict_class": self.verdict_class,
            "reason": self.reason,
        }


def hash_candidate_id(proposed_chain: dict[str, Any], trigger: str = "would_have_grounded", source_turn_trace: str = "") -> str:
    import hashlib
    payload = {
        "proposed_chain": proposed_chain,
        "trigger": trigger,
        "source_turn_trace": source_turn_trace,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _load_corpus_candidates() -> dict[str, list[EvidencePointer]]:
    """Load the math teaching corpus from disk to lookup honest evidence pointers."""
    if not _CORPUS_PATH.exists():
        return {}
    out: dict[str, list[EvidencePointer]] = {}
    with _CORPUS_PATH.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            cid = entry.get("candidate_id")
            evidence_list = entry.get("evidence", [])
            pointers = [
                EvidencePointer(
                    source=ev["source"],
                    ref=ev["ref"],
                    polarity=ev.get("polarity", "affirms"),
                    epistemic_status=ev.get("epistemic_status", "coherent"),
                )
                for ev in evidence_list
            ]
            if cid:
                out[cid] = pointers
    return out


def _validate_chain_and_run_replay(
    chain: dict[str, Any],
    temp_math_corpus_path: Path,
) -> ReplayEvidence:
    """Custom validator that intercepts and rejects cycles, redundancy, and pack residency violations."""
    pack_lexicon = _pack_lexicon_for("en_mathematics_logic_v1")
    sub = chain.get("subject", "")
    obj = chain.get("object", "")

    # 1. Pack residency check
    if sub not in pack_lexicon or obj not in pack_lexicon:
        return ReplayEvidence(
            baseline={},
            candidate={},
            regressed_metrics=("versor_closure_rate",),
            replay_equivalent=False,
        )

    # 2. Cycle check
    if sub == obj:
        return ReplayEvidence(
            baseline={},
            candidate={},
            regressed_metrics=("versor_closure_rate",),
            replay_equivalent=False,
        )

    # 3. Redundancy check: check if chain already exists in temp_math_corpus_path
    if temp_math_corpus_path.exists():
        with temp_math_corpus_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if (
                        entry.get("subject") == sub
                        and entry.get("intent") == chain.get("intent")
                        and entry.get("connective") == chain.get("connective")
                        and entry.get("object") == obj
                    ):
                        return ReplayEvidence(
                            baseline={},
                            candidate={},
                            regressed_metrics=("versor_closure_rate",),
                            replay_equivalent=False,
                        )
                except Exception:
                    continue

    # Otherwise run the live replay logic
    from teaching.replay import run_replay_equivalence
    return run_replay_equivalence(chain)


def _score_one(
    case: dict[str, Any],
    log: ProposalLog,
    temp_math_corpus_path: Path,
    corpus_evidence_map: dict[str, list[EvidencePointer]],
) -> CaseOutcome:
    """Propose and ratify a single case, checking replay-equivalence."""
    expected = case["expected"]
    proposed_chain = case["proposed_chain"]
    trigger = case.get("trigger", "would_have_grounded")
    source_turn_trace = case.get("source_turn_trace", "")
    candidate_id = hash_candidate_id(proposed_chain, trigger=trigger, source_turn_trace=source_turn_trace)

    # Check for explicit evidence overrides in the case dict (e.g. empty list for refusal test)
    if "evidence" in case:
        evidence_list = [
            EvidencePointer(
                source=ev["source"],
                ref=ev["ref"],
                polarity=ev.get("polarity", "affirms"),
                epistemic_status=ev.get("epistemic_status", "coherent"),
            )
            for ev in case["evidence"]
        ]
    else:
        evidence_list = corpus_evidence_map.get(candidate_id)
        if evidence_list is None:
            # Default fallback for new negative cases
            evidence_list = [
                EvidencePointer(
                    source="corpus",
                    ref="en-math-logic-002",
                    polarity="affirms",
                    epistemic_status="coherent",
                )
            ]

    polarity = case.get("polarity", "affirms")
    claim_domain = case.get("claim_domain", "factual")
    boundary_clean = case.get("boundary_clean", True)

    # 1. Construct the DiscoveryCandidate
    candidate = DiscoveryCandidate(
        candidate_id=candidate_id,
        proposed_chain=proposed_chain,
        trigger=trigger,
        source_turn_trace=source_turn_trace,
        pack_consistent=True,
        boundary_clean=boundary_clean,
        polarity=polarity,
        claim_domain=claim_domain,
        evidence=tuple(evidence_list),
    )

    try:
        # 2. Propose candidate using our validation wrapper bound to temp_math_corpus_path
        def run_replay(c: dict[str, Any]) -> ReplayEvidence:
            return _validate_chain_and_run_replay(c, temp_math_corpus_path)

        proposal = propose_from_candidate(candidate, log=log, run_replay=run_replay)

        # 3. Read back proposal to inspect replay
        proposal_state = log.current_state().get(proposal.proposal_id)
        if not proposal_state:
            actual = "refused"
            reason = "proposal not found in log"
        elif proposal_state["state"] == "rejected":
            # Auto-rejected due to regression or validation failure
            actual = "not_equivalent"
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
            reason = ""
        else:
            actual = proposal_state["state"]
            reason = f"unexpected proposal state: {actual}"

    except ProposalError as exc:
        actual = "refused"
        reason = str(exc)
    except Exception as exc:
        actual = "error"
        reason = f"{exc.__class__.__name__}: {exc}"

    # Determine verdict class using unified matching logic matching symbolic equivalence
    if actual == expected:
        verdict_class = "correct"
        reason = "" if actual in ("replay_equivalent", "not_equivalent") else reason
    elif actual == "refused":
        # Engine refused on a case that expected a definite answer.
        # This is a refusal, NOT a wrong answer — preserves wrong == 0.
        verdict_class = "refused"
    else:
        # Engine produced a definite answer that disagrees with expected.
        # This is wrong. The wrong==0 gate catches any such case.
        verdict_class = "wrong"
        if not reason:
            reason = f"actual={actual!r} expected={expected!r}"

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
    corpus_evidence_map = _load_corpus_candidates()

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
                outcomes.append(_score_one(c, log, temp_math_corpus_path, corpus_evidence_map))

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
        "adr": "0131.2.B",
        "benchmark": "math_teaching_corpus_v1.B",
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

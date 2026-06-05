"""The decoration instrument — does the geometric FIELD reader add independent signal?

Measurements #2 (ablation) and #3 (per-class diversity) of the field-reasoner wedge
falsifiable experiment. For each case it runs BOTH readers and the real
``verify_tier2_agreement`` gate, then asks the only questions that matter:

- **field_caught_symbolic_errors** — cases where the SYMBOLIC reader commits a WRONG
  answer (≠ gold) but the agreement gate REFUSES (the field disagreed or refused).
  This is the dossier's measurement-#2 PASS signal: the field refusing a comprehension
  error the symbol path alone admits.
- **field_lost_coverage** — cases where the symbolic reader commits the CORRECT answer
  but the gate refuses *because of the field* (field refused or disagreed). The field
  subtracting a correct answer is a liability, not signal.
- **admitted_set_changed** — does the gate's admitted set differ from symbolic-alone?
- per-class double-fault / agreement diversity.

VERDICT:
- ``PASS`` iff ``field_caught_symbolic_errors > 0`` (the field adds error-catching
  signal) and never commits a wrong answer.
- ``C3`` (field is decoration / a coverage liability on this domain) otherwise — a
  sanctioned, honest outcome: the symbolic reading carries the capability.

Run:  PYTHONPATH=. .venv/bin/python -m evals.relational_metric.ablation
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from core.reasoning import OperatorEvidence, verify_tier2_agreement
from evals.relational_metric.oracle import OracleError, oracle_answer
from generate.relational_field_reader import READER_LINEAGE as FIELD_LINEAGE
from generate.relational_field_reader import read_relational as field_read
from generate.relational_symbolic_reader import READER_LINEAGE as SYM_LINEAGE
from generate.relational_symbolic_reader import read_relational as sym_read

_CASES = Path(__file__).resolve().parent / "v1" / "cases.jsonl"


def _commit_key(answer: int, unit: str | None) -> str:
    return f"{answer}:{unit}"


def _gate_admits(field_r: Any, sym_r: Any) -> int | None:
    """Run the real Tier-2 gate; return the agreed answer or None (refuse)."""
    if field_r.refused or sym_r.refused:
        return None
    ev_field = OperatorEvidence(
        domain="relational_metric", operator="field_read", outcome="committed",
        reason="field_commit", input_keys=(), check_keys=(),
        commitment_key=_commit_key(field_r.answer, field_r.answer_unit),
        structural_signature="field.geometric.number_line",
        reader_lineage=FIELD_LINEAGE,
    )
    ev_sym = OperatorEvidence(
        domain="relational_metric", operator="symbolic_read", outcome="committed",
        reason="symbolic_commit", input_keys=(), check_keys=(),
        commitment_key=_commit_key(sym_r.answer, sym_r.answer_unit),
        structural_signature="symbolic.arithmetic.schema",
        reader_lineage=SYM_LINEAGE,
    )
    verdict = verify_tier2_agreement((ev_field, ev_sym))
    return field_r.answer if verdict.verified else None


def run() -> dict[str, Any]:
    cases = [json.loads(l) for l in _CASES.read_text().splitlines() if l.strip()]

    rows: list[dict[str, Any]] = []
    per_class: dict[str, dict[str, int]] = defaultdict(
        lambda: {"n": 0, "agree_commit": 0, "disagree": 0,
                 "both_correct": 0, "double_fault": 0}
    )
    field_caught: list[str] = []
    field_lost_coverage: list[str] = []
    field_wrong: list[dict[str, Any]] = []

    for case in cases:
        cid, cls = case["id"], case["class"]
        try:
            gold = oracle_answer(case["relations"], case["query"])
        except OracleError:
            continue
        f = field_read(case["text"])
        s = sym_read(case["text"])
        gate = _gate_admits(f, s)

        f_ans = None if f.refused else f.answer
        s_ans = None if s.refused else s.answer
        sym_alone = s_ans  # symbolic-alone admits its committed answer

        pc = per_class[cls]
        pc["n"] += 1
        if f_ans is not None and s_ans is not None:
            if f_ans == s_ans:
                pc["agree_commit"] += 1
                if f_ans == gold:
                    pc["both_correct"] += 1
            else:
                pc["disagree"] += 1
            if f_ans != gold and s_ans != gold:
                pc["double_fault"] += 1

        # The field's own wrong=0 (it must never commit a wrong answer).
        if f_ans is not None and f_ans != gold:
            field_wrong.append({"id": cid, "field": f_ans, "gold": gold})

        # measurement #2 signals
        if s_ans is not None and s_ans != gold and gate is None:
            field_caught.append(cid)  # symbolic committed WRONG; gate refused
        if s_ans is not None and s_ans == gold and gate is None:
            field_lost_coverage.append(cid)  # symbolic correct; gate refused

        rows.append({
            "id": cid, "class": cls, "gold": gold,
            "field": f_ans, "field_refused": f.refused and f.refusal_reason,
            "symbolic": s_ans, "symbolic_refused": s.refused and s.refusal_reason,
            "gate_admits": gate, "symbolic_alone": sym_alone,
        })

    gate_admitted = {r["id"]: r["gate_admits"] for r in rows if r["gate_admits"] is not None}
    symbolic_admitted = {r["id"]: r["symbolic_alone"] for r in rows if r["symbolic_alone"] is not None}
    admitted_changed = gate_admitted != symbolic_admitted

    verdict = (
        "PASS" if (field_caught and not field_wrong)
        else "C3_field_is_decoration_or_liability"
    )

    return {
        "total": len(rows),
        "verdict": verdict,
        "field_caught_symbolic_errors": field_caught,
        "field_lost_coverage": field_lost_coverage,
        "field_wrong_commits": field_wrong,
        "admitted_set_changed": admitted_changed,
        "gate_admitted_count": len(gate_admitted),
        "symbolic_alone_admitted_count": len(symbolic_admitted),
        "per_class": {k: dict(v) for k, v in per_class.items()},
        "rows": rows,
    }


def main() -> int:
    report = run()
    summary = {k: v for k, v in report.items() if k != "rows"}
    print(json.dumps(summary, indent=2))
    # The instrument is non-failing: a C3 verdict is a sanctioned, honest outcome.
    # It only hard-fails if the field ever commits a WRONG answer (wrong=0 breach).
    if report["field_wrong_commits"]:
        print("FIELD COMMITTED A WRONG ANSWER (wrong!=0 breach):",
              report["field_wrong_commits"], file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

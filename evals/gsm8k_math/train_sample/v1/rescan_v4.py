"""ADR-0136.S.4 post-rescan — barrier-shift ledger v4 over 50-case GSM8K train sample.

Measurement-only.  Runs ``parse_and_solve`` on every case on current main
(post-S.4), compares to v3 taxonomy (ADR-0136.S.3-post-rescan), and writes:

- ``refusal_rescan_v4.json`` — per-case barrier-shift ledger (v3 → v4).
- ``refusal_taxonomy_v4.json`` — updated taxonomy reflecting post-S.4 parser.

Aborts on any ``wrong`` admission (answer != expected).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from generate.math_candidate_graph import parse_and_solve

_HERE = Path(__file__).resolve().parent
_CASES_PATH = _HERE / "cases.jsonl"
_V3_TAXONOMY_PATH = _HERE / "refusal_taxonomy_v3.json"
_V3_RESCAN_PATH = _HERE / "refusal_rescan_v3.json"
_RESCAN_V4_PATH = _HERE / "refusal_rescan_v4.json"
_TAXONOMY_V4_PATH = _HERE / "refusal_taxonomy_v4.json"

# Matches both refusal-reason shapes the candidate-graph emits:
#   "no admissible candidate for {statement|question}: '<text>'"
#   "recognizer matched but produced no injection for statement: '<text>' (category=<c>)"
# (PR #359 added the second shape + trailing "(category=...)").  Greedy capture
# with an anchored closing quote tolerates statements containing apostrophes
# (e.g. "Rudolph's"); the optional category suffix is consumed after the quote.
_FIRST_REFUSAL_RE = re.compile(
    r"(?:no admissible candidate for|recognizer matched but produced no injection for) "
    r"(?:statement|question): ['\"](.+)['\"](?:\s*\(category=[^)]*\))?\s*$"
)

# Barrier reclassification for cases whose first-refusal sentence changed since v3.
# This rescan re-runs the LIVE reader (see module docstring), so it tracks the
# reader's current divergence from the v3 baseline — not only the S.4 cut.
#
# S.4 originally shifted two cases (0038, 0046) by widening initial-state subject
# shapes (indefinite-article + prepositional-prefix existential). Later capability
# waves (ADR-0163-D.2 discrete-count, 0174 held-hypothesis, 0178 compose, 0191
# completeness guard, 0192 discrete_count) advanced the reader past five more
# v3-era barriers, shifting their first-refusal one sentence deeper. All shifts
# are soundness-preserving (the cases still refuse; wrong stays 0). Each shifted
# case carries an override documenting its new first-refusal barrier.
# NOTE: because this asserts against the live reader, future reader advances will
# add shifts here — a follow-up should cut a frozen v5 snapshot or derive the
# expected set from the committed artifact instead of the live run.
_V4_BARRIER_OVERRIDES: dict[str, dict[str, Any]] = {
    "gsm8k-train-sample-v1-0019": {
        "primary_barrier": "percentage_rate",
        "secondary_barriers": ["rate_price"],
        "notes": (
            "Reader now resolves the prior '$400 per vet appointment' barrier; "
            "first refusal moved to 'After the first appointment, John paid $100 "
            "for pet insurance that covers 80% of the subsequent visits' — needs "
            "percentage_rate (80% of a subsequent-visit set)."
        ),
    },
    "gsm8k-train-sample-v1-0023": {
        "primary_barrier": "compound_comparative",
        "secondary_barriers": ["fraction_operand"],
        "notes": (
            "Reader now resolves 'Nicole collected 400 Pokemon cards' (initial); "
            "refuses on 'Cindy collected twice as many, and Rex collected half of "
            "Nicole and Cindy's combined total' — needs compound_comparative "
            "('twice as many') plus fraction_operand ('half of combined')."
        ),
    },
    "gsm8k-train-sample-v1-0025": {
        "primary_barrier": "distributive_multiply",
        "secondary_barriers": ["complex_question"],
        "notes": (
            "Reader now resolves 'Lilibeth fills 6 baskets where each basket holds "
            "50 strawberries'; refuses on the question 'If three of Lilibeth's "
            "friends pick the same amount as her, how many ... in all?' — needs "
            "distributive_multiply (3 friends x her amount) over a total question."
        ),
    },
    "gsm8k-train-sample-v1-0027": {
        "primary_barrier": "fraction_operand",
        "secondary_barriers": ["compound_statement"],
        "notes": (
            "Reader now resolves 'Malcolm has 240 followers on Instagram and 500 "
            "on Facebook'; refuses on 'The number of followers he has on Twitter "
            "is half the number ... on Instagram and Facebook combined' — needs "
            "fraction_operand ('half of combined')."
        ),
    },
    "gsm8k-train-sample-v1-0047": {
        "primary_barrier": "partition_divide",
        "secondary_barriers": [],
        "notes": (
            "Reader now resolves 'John bakes 12 coconut macaroons, each weighing "
            "5 ounces'; refuses on 'He then packs an equal number of the macaroons "
            "in 4 different brown bags' — needs partition_divide (12 / 4 equal)."
        ),
    },
    "gsm8k-train-sample-v1-0038": {
        "primary_barrier": "compound_comparative",
        "secondary_barriers": ["aggregate_sum"],
        "notes": (
            "Sentence 1 (novel_initial_form) now resolves via S.4's "
            "_INITIAL_THERE_ARE_PREFIX_RE to (building, 100, ladies). Refuses "
            "on sentence 2: 'There are three times that many girls at a party "
            "being held on the second floor of the building' — needs "
            "compound_comparative parsing ('three times that many') with "
            "cross-sentence reference to the prior 100."
        ),
    },
    "gsm8k-train-sample-v1-0046": {
        "primary_barrier": "fraction_operand",
        "secondary_barriers": ["percentage_of"],
        "notes": (
            "Sentence 1 (novel_initial_form) now resolves via S.4's "
            "_INITIAL_HAS_INDEF_RE to (school, 100, students). Refuses on "
            "sentence 2: 'Half of the students are girls, the other half are "
            "boys' — needs fraction_operand parsing + downstream percentage_of "
            "on the 20%/10% sentences."
        ),
    },
}


def _load_cases() -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in _CASES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _extract_first_refusal(reason: str | None) -> str | None:
    if reason is None:
        return None
    body = reason.removeprefix("candidate_graph: ")
    m = _FIRST_REFUSAL_RE.search(body)
    return m.group(1) if m else None


def _classify_current_barrier(
    case_id: str,
    v3_barrier: str,
    cur_outcome: str,
    prev_first_ref: str | None,
    cur_first_ref: str | None,
) -> str:
    if cur_outcome == "admitted":
        return "admitted"
    if cur_first_ref == prev_first_ref:
        return v3_barrier
    override = _V4_BARRIER_OVERRIDES.get(case_id)
    if override is None:
        raise RuntimeError(
            f"{case_id}: first-refusal shifted but no v4 override registered. "
            f"v3={prev_first_ref!r} v4={cur_first_ref!r}"
        )
    return override["primary_barrier"]


def build_rescan() -> tuple[dict[str, Any], dict[str, Any]]:
    cases = _load_cases()
    v3_data = json.loads(_V3_RESCAN_PATH.read_text(encoding="utf-8"))
    v3_by_id = {c["case_id"]: c for c in v3_data["per_case"]}
    v3_tax = json.loads(_V3_TAXONOMY_PATH.read_text(encoding="utf-8"))
    v3_tax_by_id = {c["case_id"]: c for c in v3_tax["per_case"]}

    rescan_per_case: list[dict[str, Any]] = []
    tax_per_case: list[dict[str, Any]] = []
    admitted: list[str] = []
    wrong: list[tuple[str, float, float]] = []
    barrier_shifted_count = 0

    for c in cases:
        cid = c["case_id"]
        r = parse_and_solve(c["question"])
        cur_outcome = "admitted" if r.answer is not None else "refused"
        cur_first_ref = _extract_first_refusal(r.refusal_reason)
        cur_reason = r.refusal_reason

        if cur_outcome == "admitted":
            if r.answer == c["answer_numeric"]:
                admitted.append(cid)
            else:
                wrong.append((cid, r.answer, c["answer_numeric"]))

        prev = v3_by_id[cid]
        prev_outcome = prev["current_outcome"]
        prev_first_ref = prev["current_first_refusal"]
        prev_barrier = v3_tax_by_id[cid]["primary_barrier"]
        cur_barrier = _classify_current_barrier(
            cid, prev_barrier, cur_outcome, prev_first_ref, cur_first_ref
        )

        outcome_changed = cur_outcome != prev_outcome
        first_ref_changed = cur_first_ref != prev_first_ref
        barrier_changed = cur_barrier != prev_barrier
        shifted = outcome_changed or first_ref_changed or barrier_changed
        if shifted:
            barrier_shifted_count += 1

        rescan_per_case.append({
            "case_id": cid,
            "previous_outcome": prev_outcome,
            "current_outcome": cur_outcome,
            "previous_primary_barrier": prev_barrier,
            "current_primary_barrier": cur_barrier,
            "barrier_shifted": shifted,
            "new_admission": cur_outcome == "admitted" and prev_outcome != "admitted",
            "previous_first_refusal": prev_first_ref,
            "current_first_refusal": cur_first_ref,
            "current_refusal_reason": cur_reason,
            "notes": _V4_BARRIER_OVERRIDES.get(cid, {}).get("notes", ""),
        })

        v3_tax_entry = v3_tax_by_id[cid]
        if cid in _V4_BARRIER_OVERRIDES and cur_outcome == "refused":
            ov = _V4_BARRIER_OVERRIDES[cid]
            tax_per_case.append({
                "case_id": cid,
                "primary_barrier": ov["primary_barrier"],
                "secondary_barriers": ov["secondary_barriers"],
                "notes": ov["notes"],
            })
        else:
            tax_per_case.append({
                "case_id": cid,
                "primary_barrier": cur_barrier,
                "secondary_barriers": v3_tax_entry.get("secondary_barriers", []),
                "notes": v3_tax_entry.get("notes", ""),
            })

    if wrong:
        raise RuntimeError(f"wrong admissions detected: {wrong}")

    rescan = {
        "schema_version": 1,
        "adr": "0136.S.4-post-rescan",
        "description": (
            "Per-case barrier-shift ledger comparing v3 (post-S.3) to v4 "
            "(post-S.4) behavior of parse_and_solve."
        ),
        "summary": {
            "total_cases": len(cases),
            "admitted": len(admitted),
            "wrong": len(wrong),
            "refused": len(cases) - len(admitted),
            "barrier_shifted_v3_to_v4": barrier_shifted_count,
        },
        "per_case": rescan_per_case,
    }

    taxonomy = {
        "schema_version": 2,
        "adr": "0136.S.4-post-rescan",
        "description": (
            "Post-S.4 refusal taxonomy. Schema identical to v3; primary_barrier "
            "vocabulary unchanged."
        ),
        "summary": {
            "total_cases": len(cases),
            "admitted": len(admitted),
            "wrong": len(wrong),
            "refused": len(cases) - len(admitted),
        },
        "per_case": tax_per_case,
    }

    return rescan, taxonomy


def main() -> int:
    rescan, taxonomy = build_rescan()
    _RESCAN_V4_PATH.write_text(
        json.dumps(rescan, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _TAXONOMY_V4_PATH.write_text(
        json.dumps(taxonomy, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"v4 rescan: admitted={rescan['summary']['admitted']}/"
        f"{rescan['summary']['total_cases']} wrong={rescan['summary']['wrong']} "
        f"shifted_v3_to_v4={rescan['summary']['barrier_shifted_v3_to_v4']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

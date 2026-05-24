"""ADR-0136.S.2 post-rescan — barrier-shift ledger over 50-case GSM8K train sample.

Measurement-only.  Runs ``parse_and_solve`` on every case, compares current
refusal behavior to the v1 taxonomy (ADR-0136.S.0), and writes two artifacts:

- ``refusal_rescan_v2.json`` — per-case barrier-shift ledger.
- ``refusal_taxonomy_v2.json`` — updated taxonomy reflecting post-S.1/S.2 parser.

Aborts on any ``wrong`` admission (answer ≠ expected).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from generate.math_candidate_graph import parse_and_solve

_HERE = Path(__file__).resolve().parent
_CASES_PATH = _HERE / "cases.jsonl"
_V1_TAXONOMY_PATH = _HERE / "refusal_taxonomy.json"
_RESCAN_PATH = _HERE / "refusal_rescan_v2.json"
_TAXONOMY_V2_PATH = _HERE / "refusal_taxonomy_v2.json"

_FIRST_REFUSAL_RE = re.compile(
    r"no admissible candidate for (?:statement|question): ['\"](.+?)['\"]$"
)

_CURRENT_BARRIERS: dict[str, str] = {
    "gsm8k-train-sample-v1-0001": "rate_earnings",
    "gsm8k-train-sample-v1-0002": "partition_divide",
    "gsm8k-train-sample-v1-0003": "novel_initial_verb",
    "gsm8k-train-sample-v1-0004": "fraction_operand",
    "gsm8k-train-sample-v1-0005": "fraction_operand",
    "gsm8k-train-sample-v1-0006": "temporal_age_anchor",
    "gsm8k-train-sample-v1-0007": "conditional_question",
    "gsm8k-train-sample-v1-0008": "conditional_question",
    "gsm8k-train-sample-v1-0009": "conditional_question",
    "gsm8k-train-sample-v1-0010": "compound_statement",
    "gsm8k-train-sample-v1-0011": "rate_price",
    "gsm8k-train-sample-v1-0012": "compound_statement",
    "gsm8k-train-sample-v1-0013": "compound_statement",
    "gsm8k-train-sample-v1-0014": "admitted",
    "gsm8k-train-sample-v1-0015": "compound_multi_event",
    "gsm8k-train-sample-v1-0016": "compound_statement",
    "gsm8k-train-sample-v1-0017": "conditional_branch",
    "gsm8k-train-sample-v1-0018": "admitted",
    "gsm8k-train-sample-v1-0019": "rate_price",
    "gsm8k-train-sample-v1-0020": "multi_entity_initial",
    "gsm8k-train-sample-v1-0021": "distributive_multiply",
    "gsm8k-train-sample-v1-0022": "context_filler",
    "gsm8k-train-sample-v1-0023": "novel_initial_verb",
    "gsm8k-train-sample-v1-0024": "multi_day_accumulation",
    "gsm8k-train-sample-v1-0025": "distributive_multiply",
    "gsm8k-train-sample-v1-0026": "distributive_each_actor",
    "gsm8k-train-sample-v1-0027": "multi_attribute_accumulation",
    "gsm8k-train-sample-v1-0028": "novel_initial_form",
    "gsm8k-train-sample-v1-0029": "compound_comparative",
    "gsm8k-train-sample-v1-0030": "novel_initial_form",
    "gsm8k-train-sample-v1-0031": "context_filler",
    "gsm8k-train-sample-v1-0032": "compound_statement",
    "gsm8k-train-sample-v1-0033": "compound_statement",
    "gsm8k-train-sample-v1-0034": "capacity_rate",
    "gsm8k-train-sample-v1-0035": "complex_question",
    "gsm8k-train-sample-v1-0036": "compound_comparative",
    "gsm8k-train-sample-v1-0037": "goal_statement",
    "gsm8k-train-sample-v1-0038": "novel_initial_form",
    "gsm8k-train-sample-v1-0039": "novel_initial_verb",
    "gsm8k-train-sample-v1-0040": "multi_entity_initial",
    "gsm8k-train-sample-v1-0041": "fraction_operand",
    "gsm8k-train-sample-v1-0042": "admitted",
    "gsm8k-train-sample-v1-0043": "compound_comparative",
    "gsm8k-train-sample-v1-0044": "percentage_rate",
    "gsm8k-train-sample-v1-0045": "novel_initial_form",
    "gsm8k-train-sample-v1-0046": "novel_initial_form",
    "gsm8k-train-sample-v1-0047": "novel_initial_verb",
    "gsm8k-train-sample-v1-0048": "temporal_frequency",
    "gsm8k-train-sample-v1-0049": "context_filler",
    "gsm8k-train-sample-v1-0050": "temporal_frequency",
}

_CURRENT_NOTES: dict[str, str] = {
    "gsm8k-train-sample-v1-0001": "multi-stmt earnings; short-circuit needs single stmt+q",
    "gsm8k-train-sample-v1-0002": "splits into 25-foot sections = partition op",
    "gsm8k-train-sample-v1-0003": "context filler now parses; donated not in verb set",
    "gsm8k-train-sample-v1-0004": "indef qty now parses; fraction ops (half, 1/4) block",
    "gsm8k-train-sample-v1-0005": "3/4 fraction operand in temporal decrease",
    "gsm8k-train-sample-v1-0006": "age anchor: 8 pages when 6 years old",
    "gsm8k-train-sample-v1-0007": "multi-entity stmt now parses; question has if-clause",
    "gsm8k-train-sample-v1-0008": "context filler now parses; question has if-clause",
    "gsm8k-train-sample-v1-0009": "if-clause question: If Jen has 150 ducks",
    "gsm8k-train-sample-v1-0010": "two ops in one sentence: had X but lost Y",
    "gsm8k-train-sample-v1-0011": "$2 per cup in relative clause",
    "gsm8k-train-sample-v1-0012": "ate half = compound + fraction",
    "gsm8k-train-sample-v1-0013": "10 one-hour videos each day = nested quantities",
    "gsm8k-train-sample-v1-0014": "ADMITTED via S.1 capacity short-circuit",
    "gsm8k-train-sample-v1-0015": "subway+train+bike multi-event in one sentence",
    "gsm8k-train-sample-v1-0016": "2 more than 5 miles AND 3 less than 17 signs",
    "gsm8k-train-sample-v1-0017": "context filler now parses; or-choice pricing blocks",
    "gsm8k-train-sample-v1-0018": "ADMITTED via S.2 capacity short-circuit",
    "gsm8k-train-sample-v1-0019": "context filler now parses; 3 appts at $400 each",
    "gsm8k-train-sample-v1-0020": "multi-entity initial: 2+2+3 animals in one stmt",
    "gsm8k-train-sample-v1-0021": "context filler now parses; 15lb x 10rep x 3set",
    "gsm8k-train-sample-v1-0022": "context filler still blocks: earning in rel clause",
    "gsm8k-train-sample-v1-0023": "collected not in verb set",
    "gsm8k-train-sample-v1-0024": "4 values across Mon-Thu in one sentence",
    "gsm8k-train-sample-v1-0025": "context filler now parses; 6 baskets x 50 each",
    "gsm8k-train-sample-v1-0026": "each actor: Aaron and Carson each saved $40",
    "gsm8k-train-sample-v1-0027": "240 Instagram + 500 Facebook in one stmt",
    "gsm8k-train-sample-v1-0028": "context filler now parses; It cost $100k = novel form",
    "gsm8k-train-sample-v1-0029": "context filler now parses; 3x comparative blocks",
    "gsm8k-train-sample-v1-0030": "context filler now parses; It is a 2-hour drive",
    "gsm8k-train-sample-v1-0031": "intent sentence: wants to go = context filler",
    "gsm8k-train-sample-v1-0032": "context filler now parses; draws AND colors",
    "gsm8k-train-sample-v1-0033": "12 years old AND 7 times her age in one stmt",
    "gsm8k-train-sample-v1-0034": "context filler now parses; within vs in preposition",
    "gsm8k-train-sample-v1-0035": "pronoun now resolves; question too complex (modal)",
    "gsm8k-train-sample-v1-0036": "context filler now parses; 3x comparative blocks",
    "gsm8k-train-sample-v1-0037": "goal statement: wants to lose 10 pounds",
    "gsm8k-train-sample-v1-0038": "there are a hundred = existential + spelled number",
    "gsm8k-train-sample-v1-0039": "context filler now parses; gained not in verb set",
    "gsm8k-train-sample-v1-0040": "context filler now parses; 2+5+7+3+1 multi-entity",
    "gsm8k-train-sample-v1-0041": "all of 1 pan + 75% of 2nd = fraction operand",
    "gsm8k-train-sample-v1-0042": "ADMITTED via S.2 conditional-op question",
    "gsm8k-train-sample-v1-0043": "context filler now parses; twice as much comparative",
    "gsm8k-train-sample-v1-0044": "10% simple interest = percentage rate",
    "gsm8k-train-sample-v1-0045": "context filler now parses; Each survey has = novel",
    "gsm8k-train-sample-v1-0046": "A school has 100 = novel initial form (indef article)",
    "gsm8k-train-sample-v1-0047": "bakes not in verb set + embedded per-unit",
    "gsm8k-train-sample-v1-0048": "context filler now parses; every week frequency",
    "gsm8k-train-sample-v1-0049": "context filler: trying to find = intent",
    "gsm8k-train-sample-v1-0050": "every other day for 2 weeks = temporal frequency",
}

_CURRENT_SECONDARY: dict[str, list[str]] = {
    "gsm8k-train-sample-v1-0001": ["conditional_branch", "multi_statement"],
    "gsm8k-train-sample-v1-0002": ["fraction_operand", "coreference_pronoun"],
    "gsm8k-train-sample-v1-0003": ["distributive_multiply", "rate_price"],
    "gsm8k-train-sample-v1-0004": ["conditional_question"],
    "gsm8k-train-sample-v1-0005": [],
    "gsm8k-train-sample-v1-0006": ["multi_step_complex"],
    "gsm8k-train-sample-v1-0007": ["multi_entity_initial"],
    "gsm8k-train-sample-v1-0008": ["distributive_multiply"],
    "gsm8k-train-sample-v1-0009": ["compound_comparative"],
    "gsm8k-train-sample-v1-0010": ["fraction_operand"],
    "gsm8k-train-sample-v1-0011": ["context_filler"],
    "gsm8k-train-sample-v1-0012": ["fraction_operand", "coreference_pronoun"],
    "gsm8k-train-sample-v1-0013": ["temporal_frequency"],
    "gsm8k-train-sample-v1-0014": [],
    "gsm8k-train-sample-v1-0015": ["compound_comparative"],
    "gsm8k-train-sample-v1-0016": ["rate_question"],
    "gsm8k-train-sample-v1-0017": ["rate_price"],
    "gsm8k-train-sample-v1-0018": [],
    "gsm8k-train-sample-v1-0019": ["percentage_of", "conditional_branch"],
    "gsm8k-train-sample-v1-0020": ["rate_comparative"],
    "gsm8k-train-sample-v1-0021": [],
    "gsm8k-train-sample-v1-0022": ["rate_earnings", "compound_comparative"],
    "gsm8k-train-sample-v1-0023": ["fraction_operand", "distributive_divide"],
    "gsm8k-train-sample-v1-0024": [],
    "gsm8k-train-sample-v1-0025": [],
    "gsm8k-train-sample-v1-0026": ["fraction_operand"],
    "gsm8k-train-sample-v1-0027": ["multi_step_complex"],
    "gsm8k-train-sample-v1-0028": ["rate_price", "temporal_frequency"],
    "gsm8k-train-sample-v1-0029": ["rate_comparative"],
    "gsm8k-train-sample-v1-0030": ["compound_comparative"],
    "gsm8k-train-sample-v1-0031": ["implicit_group_count"],
    "gsm8k-train-sample-v1-0032": ["percentage_of"],
    "gsm8k-train-sample-v1-0033": ["multi_step_complex"],
    "gsm8k-train-sample-v1-0034": ["percentage_of", "capacity_rate"],
    "gsm8k-train-sample-v1-0035": ["coreference_pronoun"],
    "gsm8k-train-sample-v1-0036": ["compound_comparative"],
    "gsm8k-train-sample-v1-0037": [],
    "gsm8k-train-sample-v1-0038": [],
    "gsm8k-train-sample-v1-0039": ["multi_step_complex"],
    "gsm8k-train-sample-v1-0040": ["leg_count"],
    "gsm8k-train-sample-v1-0041": ["percentage_of"],
    "gsm8k-train-sample-v1-0042": [],
    "gsm8k-train-sample-v1-0043": ["rate_comparative"],
    "gsm8k-train-sample-v1-0044": [],
    "gsm8k-train-sample-v1-0045": ["rate_price"],
    "gsm8k-train-sample-v1-0046": ["percentage_of"],
    "gsm8k-train-sample-v1-0047": ["embedded_per_unit"],
    "gsm8k-train-sample-v1-0048": [],
    "gsm8k-train-sample-v1-0049": ["compound_multi_event", "rate_comparative"],
    "gsm8k-train-sample-v1-0050": [],
}


def _extract_first_refusal(reason: str | None) -> str | None:
    if not reason:
        return None
    m = _FIRST_REFUSAL_RE.search(reason)
    return m.group(1) if m else reason


def _load_v1_taxonomy() -> dict[str, dict[str, Any]]:
    data = json.loads(_V1_TAXONOMY_PATH.read_text(encoding="utf-8"))
    return {entry["case_id"]: entry for entry in data["per_case"]}


def build_rescan() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cases = [
        json.loads(line)
        for line in _CASES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(cases) == 50, f"Expected 50 cases, got {len(cases)}"
    v1_tax = _load_v1_taxonomy()

    rescan_records: list[dict[str, Any]] = []
    taxonomy_records: list[dict[str, Any]] = []
    for case in cases:
        cid = case["case_id"]
        r = parse_and_solve(case["question"])
        current_outcome = "admitted" if r.answer is not None else "refused"

        if r.answer is not None:
            assert r.answer == case["answer_numeric"], (
                f"WRONG: {cid} answer={r.answer} expected={case['answer_numeric']}"
            )

        v1_entry = v1_tax.get(cid, {})
        previous_barrier = v1_entry.get("primary_barrier", "unknown")
        previous_outcome = "refused"

        current_barrier = _CURRENT_BARRIERS[cid]
        barrier_shifted = previous_barrier != current_barrier
        new_admission = current_outcome == "admitted" and previous_outcome == "refused"

        rescan_records.append({
            "case_id": cid,
            "previous_outcome": previous_outcome,
            "current_outcome": current_outcome,
            "previous_primary_barrier": previous_barrier,
            "current_primary_barrier": current_barrier,
            "barrier_shifted": barrier_shifted,
            "new_admission": new_admission,
            "current_first_refusal": _extract_first_refusal(r.refusal_reason),
            "current_refusal_reason": r.refusal_reason,
            "notes": _CURRENT_NOTES.get(cid, ""),
        })

        taxonomy_records.append({
            "case_id": cid,
            "primary_barrier": current_barrier,
            "secondary_barriers": _CURRENT_SECONDARY.get(cid, []),
            "note": _CURRENT_NOTES.get(cid, ""),
        })

    return rescan_records, taxonomy_records


def _barrier_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in records:
        b = r["primary_barrier"]
        counts[b] = counts.get(b, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: (-x[1], x[0])))


def write_rescan(
    rescan_records: list[dict[str, Any]],
    taxonomy_records: list[dict[str, Any]],
) -> None:
    admitted = sum(1 for r in rescan_records if r["current_outcome"] == "admitted")
    shifted = sum(1 for r in rescan_records if r["barrier_shifted"])

    rescan_out = {
        "schema_version": 2,
        "adr": "0136.S.2-post-rescan",
        "description": (
            "Barrier-shift ledger over 50 GSM8K train-sample cases, "
            "comparing v1 taxonomy (ADR-0136.S.0) to current parser "
            "behavior post-S.1/S.2."
        ),
        "summary": {
            "total_cases": 50,
            "admitted": admitted,
            "refused": 50 - admitted,
            "wrong": 0,
            "barrier_shifted_count": shifted,
            "new_admissions": [
                r["case_id"] for r in rescan_records if r["new_admission"]
            ],
        },
        "per_case": rescan_records,
    }
    _RESCAN_PATH.write_text(
        json.dumps(rescan_out, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )

    taxonomy_out = {
        "schema_version": 2,
        "adr": "0136.S.2-post-rescan",
        "description": (
            "Updated refusal taxonomy reflecting post-S.1/S.2 parser. "
            "Supersedes v1 (ADR-0136.S.0)."
        ),
        "summary": {
            "total_cases": 50,
            "admitted": admitted,
            "refused": 50 - admitted,
            "primary_barrier_counts": _barrier_counts(taxonomy_records),
        },
        "per_case": taxonomy_records,
    }
    _TAXONOMY_V2_PATH.write_text(
        json.dumps(taxonomy_out, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    rescan, taxonomy = build_rescan()
    write_rescan(rescan, taxonomy)
    admitted = sum(1 for r in rescan if r["current_outcome"] == "admitted")
    shifted = sum(1 for r in rescan if r["barrier_shifted"])
    print(
        f"ADR-0136.S.2 rescan: admitted={admitted}/50, wrong=0, "
        f"barrier_shifted={shifted}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

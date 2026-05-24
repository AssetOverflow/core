"""ADR-0136.S.3 post-rescan — barrier-shift ledger v3 over 50-case GSM8K train sample.

Measurement-only.  Runs ``parse_and_solve`` on every case on current main
(post-S.3), compares to v2 taxonomy (ADR-0136.S.2-post-rescan), and writes:

- ``refusal_rescan_v3.json`` — per-case barrier-shift ledger (v2 → v3).
- ``refusal_taxonomy_v3.json`` — updated taxonomy reflecting post-S.3 parser.

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
_V2_TAXONOMY_PATH = _HERE / "refusal_taxonomy_v2.json"
_V2_RESCAN_PATH = _HERE / "refusal_rescan_v2.json"
_RESCAN_V3_PATH = _HERE / "refusal_rescan_v3.json"
_TAXONOMY_V3_PATH = _HERE / "refusal_taxonomy_v3.json"

_FIRST_REFUSAL_RE = re.compile(
    r"no admissible candidate for (?:statement|question): ['\"](.+?)['\"]$"
)

# Barrier reclassification for cases whose first-refusal sentence changed since v2.
# Empty unless S.3 (or later) shifts a barrier.  S.3 shifted exactly one case.
_V3_BARRIER_OVERRIDES: dict[str, dict[str, Any]] = {
    "gsm8k-train-sample-v1-0010": {
        "primary_barrier": "fraction_operand",
        "secondary_barriers": ["coreference_quantity", "comparative_arithmetic"],
        "notes": (
            "Sentence 1 (compound_statement) now resolves via S.3's "
            "_INIT_MUTATION_RE to Yun=8 paperclips. Refuses on sentence 2: "
            "'Marion has 1/4 more than what Yun currently has, plus 7' — "
            "needs fraction_operand parsing + coreference to Yun's current "
            "quantity + comparative-additive arithmetic."
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
    v2_barrier: str,
    cur_outcome: str,
    prev_first_ref: str | None,
    cur_first_ref: str | None,
) -> str:
    """Carry over v2 barrier unless first-refusal shifted; then use override."""
    if cur_outcome == "admitted":
        return "admitted"
    if cur_first_ref == prev_first_ref:
        return v2_barrier
    override = _V3_BARRIER_OVERRIDES.get(case_id)
    if override is None:
        raise RuntimeError(
            f"{case_id}: first-refusal shifted but no v3 override registered. "
            f"v2={prev_first_ref!r} v3={cur_first_ref!r}"
        )
    return override["primary_barrier"]


def build_rescan() -> tuple[dict[str, Any], dict[str, Any]]:
    cases = _load_cases()
    v2_data = json.loads(_V2_RESCAN_PATH.read_text(encoding="utf-8"))
    v2_by_id = {c["case_id"]: c for c in v2_data["per_case"]}
    v2_tax = json.loads(_V2_TAXONOMY_PATH.read_text(encoding="utf-8"))
    v2_tax_by_id = {c["case_id"]: c for c in v2_tax["per_case"]}

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

        prev = v2_by_id[cid]
        prev_outcome = prev["current_outcome"]
        prev_first_ref = prev["current_first_refusal"]
        prev_barrier = v2_tax_by_id[cid]["primary_barrier"]
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
            "notes": _V3_BARRIER_OVERRIDES.get(cid, {}).get("notes", ""),
        })

        v2_tax_entry = v2_tax_by_id[cid]
        if cid in _V3_BARRIER_OVERRIDES and cur_outcome == "refused":
            ov = _V3_BARRIER_OVERRIDES[cid]
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
                "secondary_barriers": v2_tax_entry.get("secondary_barriers", []),
                "notes": v2_tax_entry.get("notes", ""),
            })

    if wrong:
        raise RuntimeError(f"wrong admissions detected: {wrong}")

    rescan = {
        "schema_version": 1,
        "adr": "0136.S.3-post-rescan",
        "description": (
            "Per-case barrier-shift ledger comparing v2 (post-S.2) to v3 "
            "(post-S.3) behavior of parse_and_solve."
        ),
        "summary": {
            "total_cases": len(cases),
            "admitted": len(admitted),
            "wrong": len(wrong),
            "refused": len(cases) - len(admitted),
            "barrier_shifted_v2_to_v3": barrier_shifted_count,
        },
        "per_case": rescan_per_case,
    }

    taxonomy = {
        "schema_version": 2,
        "adr": "0136.S.3-post-rescan",
        "description": (
            "Post-S.3 refusal taxonomy. Schema identical to v2; primary_barrier "
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
    _RESCAN_V3_PATH.write_text(
        json.dumps(rescan, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _TAXONOMY_V3_PATH.write_text(
        json.dumps(taxonomy, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"v3 rescan: admitted={rescan['summary']['admitted']}/"
        f"{rescan['summary']['total_cases']} wrong={rescan['summary']['wrong']} "
        f"shifted_v2_to_v3={rescan['summary']['barrier_shifted_v2_to_v3']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

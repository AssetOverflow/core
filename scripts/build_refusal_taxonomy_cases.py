"""ADR-0163 Phase A — build the refusal_taxonomy v1 case set.

Reads ``evals/gsm8k_math/train_sample/v1/report.json`` and emits one JSONL
record per refused case, extracting the embedded statement out of the
``refusal_reason`` string so the lane operates on the statement itself
(not on the reason envelope).

The output is deterministic: cases are sorted by ``case_id`` and serialized
with ``sort_keys=True`` and ``ensure_ascii=False``.

Usage::

    uv run python scripts/build_refusal_taxonomy_cases.py \\
        --report evals/gsm8k_math/train_sample/v1/report.json \\
        --out evals/refusal_taxonomy/v1/cases.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Matches both refusal-reason shapes the candidate-graph emits (PR #359 added
# the second shape + the trailing "(category=...)"):
#   "candidate_graph: no admissible candidate for {statement|question}: '<text>'"
#   "candidate_graph: recognizer matched but produced no injection for statement: '<text>' (category=<c>)"
_STATEMENT_RE = re.compile(
    r"^candidate_graph:\s*"
    r"(?:no admissible candidate for|recognizer matched but produced no injection for)\s+"
    r"(?:statement|question):\s*['\"](.+)['\"]"
    r"(?:\s*\(category=[^)]*\))?\s*$",
    re.DOTALL,
)


def extract_statement(reason: str) -> str | None:
    """Pull the embedded statement out of a refusal reason.

    Returns ``None`` if the reason does not match the expected envelope.
    """

    match = _STATEMENT_RE.match(reason.strip())
    if not match:
        return None
    return match.group(1).strip()


def build_cases(report_path: Path) -> list[dict[str, str]]:
    payload = json.loads(report_path.read_text())
    per_case = payload.get("per_case", [])
    out: list[dict[str, str]] = []
    for case in per_case:
        if case.get("verdict") != "refused":
            continue
        reason = case.get("reason", "")
        statement = extract_statement(reason)
        if statement is None:
            continue
        out.append({
            "case_id": case["case_id"],
            "statement": statement,
            "refusal_reason": reason,
        })
    out.sort(key=lambda r: r["case_id"])
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("evals/gsm8k_math/train_sample/v1/report.json"),
        help="path to a GSM8K eval report containing refused cases",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("evals/refusal_taxonomy/public/v1/cases.jsonl"),
        help="output JSONL path",
    )
    args = parser.parse_args(argv)

    if not args.report.exists():
        parser.error(f"report not found: {args.report}")

    cases = build_cases(args.report)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        for record in cases:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            handle.write("\n")

    print(f"wrote {len(cases)} cases to {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

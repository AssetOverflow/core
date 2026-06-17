#!/usr/bin/env python3
"""Deterministic frontier analyzer for GSM8K train-sample proxy reports.

Reads a report.json (the exact artifact produced by
evals/gsm8k_math/train_sample/v1/runner.py) and emits a stable,
replayable bucket summary focused on the recognized-but-uninjected
frontier and other refusal classes.

Usage:
    uv run python scripts/gsm8k_frontier_report.py \
        evals/gsm8k_math/train_sample/v1/report.json

Output is JSON (sorted keys, deterministic) followed by a short
human-readable Markdown summary. No timestamps, no nondeterminism.

This tool is part of Workstream A Increment 2 measurement substrate.
It makes the "recognized_no_injection (category=rate_with_currency)"
class visible as a first-class, replayable artifact rather than
relying on ad-hoc reading of the raw report.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# The exact refusal reason prefix emitted by math_candidate_graph
# when a recognizer match exists but the injector returned ().
_RECOGNIZED_NO_INJ = "candidate_graph: recognizer matched but produced no injection"

# Other canonical reason fragments observed in the proxy reports.
# Order here is for stable bucket priority (first match wins).
_BUCKET_PATTERNS: list[tuple[str, str]] = [
    ("wrong", "wrong"),
    ("fast-path", "fast_path_correct"),
    ("no admissible candidate for question", "no_admissible_question"),
    ("no admissible candidate for statement", "no_admissible_statement"),
    ("no solvable branch", "no_solvable_branch"),
    ("incomplete reading", "incomplete_reading"),
    (_RECOGNIZED_NO_INJ, "recognized_no_injection"),
]

def _classify_reason(reason: str) -> str:
    """Map a per_case.reason string to a stable frontier bucket."""
    if not reason:
        return "other_refused"
    r = reason.lower()
    for needle, bucket in _BUCKET_PATTERNS:
        if needle.lower() in r:
            return bucket
    if "refused" in r or not reason.strip():
        return "other_refused"
    return "other"

def _extract_category(reason: str) -> str | None:
    """For recognized_no_injection reasons, pull the (category=...) value."""
    if _RECOGNIZED_NO_INJ not in reason:
        return None
    m = re.search(r"category=([a-zA-Z0-9_]+)", reason)
    return m.group(1) if m else None

def analyze_report(report_path: Path | str) -> dict[str, Any]:
    """Pure function: return a deterministic summary dict for the report."""
    p = Path(report_path)
    data: dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))

    per_case = data.get("per_case", []) or []
    counts: dict[str, int] = defaultdict(int)
    no_inj_by_cat: dict[str, int] = defaultdict(int)
    total_refused = 0
    total_correct = 0

    for case in per_case:
        verdict = str(case.get("verdict", "")).lower()
        reason = str(case.get("reason", "") or "")
        if verdict == "correct":
            total_correct += 1
            bucket = _classify_reason(reason)
            counts[bucket] += 1
            continue

        total_refused += 1
        bucket = _classify_reason(reason)
        counts[bucket] += 1
        if bucket == "recognized_no_injection":
            cat = _extract_category(reason)
            if cat:
                no_inj_by_cat[cat] += 1

    # Stable ordering
    ordered_counts = dict(sorted(counts.items()))
    ordered_no_inj = dict(sorted(no_inj_by_cat.items()))

    summary = {
        "report_source": str(p),
        "sample_count": data.get("sample_count", len(per_case)),
        "counts": {
            "correct": total_correct,
            "refused": total_refused,
            "total": total_correct + total_refused,
            **ordered_counts,
        },
        "recognized_no_injection_by_category": ordered_no_inj,
        "exit_criterion": data.get("exit_criterion", {}),
        "adr": data.get("adr"),
        "schema_version": data.get("schema_version"),
    }
    return summary

def render_markdown(summary: dict[str, Any]) -> str:
    """Stable human summary (no dates, sorted sections)."""
    lines: list[str] = []
    lines.append("# GSM8K train-sample frontier (deterministic report)")
    lines.append("")
    c = summary["counts"]
    lines.append(f"- correct: {c.get('correct', 0)}")
    lines.append(f"- refused: {c.get('refused', 0)}")
    lines.append(f"- total: {c.get('total', 0)}")
    lines.append("")
    lines.append("## Refusal buckets (stable order)")
    for k, v in summary["counts"].items():
        if k in ("correct", "refused", "total"):
            continue
        lines.append(f"- {k}: {v}")
    lines.append("")
    if summary["recognized_no_injection_by_category"]:
        lines.append("## recognized_no_injection by category (top frontier)")
        for cat, n in summary["recognized_no_injection_by_category"].items():
            lines.append(f"- {cat}: {n}")
    else:
        lines.append("## recognized_no_injection by category: (none)")
    lines.append("")
    ec = summary.get("exit_criterion", {})
    lines.append(f"exit_criterion: correct_min={ec.get('correct_min')}, passed={ec.get('passed')}, wrong_max={ec.get('wrong_max')}")
    return "\n".join(lines)

def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("Usage: scripts/gsm8k_frontier_report.py <report.json>", file=sys.stderr)
        return 2
    report_path = Path(argv[0])
    if not report_path.exists():
        print(f"ERROR: {report_path} does not exist", file=sys.stderr)
        return 1

    summary = analyze_report(report_path)
    # Deterministic JSON to stdout first (machines)
    json_out = json.dumps(summary, indent=2, sort_keys=True)
    print(json_out)
    print("\n---\n")
    # Human MD
    print(render_markdown(summary))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
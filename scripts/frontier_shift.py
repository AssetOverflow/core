#!/usr/bin/env python3
"""Frontier-shift instrument (ADR-0190 follow-up).

Decomposes the GSM8K ``train_sample`` *serving* frontier into the layers
that actually gate a flip — statement readability, question parsing, and
composition — so the next capability is chosen by **evidence of leverage**,
not by guesswork or by the (disjoint) audit reader.

For each case it computes, on the serving candidate-graph path:

- ``statement_gaps``  — the set of statement-sentence categories that produce
  NO admissible candidate (a missing injector/reader for that shape);
- ``question_parses`` — whether the question sentence yields a target;
- ``blocked_on``      — ``statement`` | ``question`` | ``both`` |
  ``composition`` (all readable + question parses, but no committed answer)
  | ``none`` (solved).

A case is **flip-ready on X** when X is the *sole* remaining blocker — the
tightest "build this next" signal. ``advances`` counts cases where a
capability is one of several blockers (it shifts them closer without
flipping). This is the same wrong=0-respecting serving path the metric
uses; it never weakens any gate.

Usage:
    python3 -m scripts.frontier_shift            # write JSON + Markdown report
    python3 -m scripts.frontier_shift --print    # also print the Markdown
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from generate.math_candidate_graph import (
    _filtered_statement_choices,
    _load_ratified_registry_or_empty,
    _split_sentences,
    parse_and_solve,
)
from generate.math_candidate_parser import (
    classify_sentence,
    extract_question_candidates,
    split_partition_clauses,
)
from generate.recognizer_match import match as _recognizer_match

_LANE = Path(__file__).resolve().parent.parent / "evals" / "gsm8k_math" / "train_sample" / "v1"
_CASES = _LANE / "cases.jsonl"
_REPORT_JSON = _LANE / "frontier_shift_report.json"
_REPORT_MD = _LANE / "frontier_shift_report.md"


def _gap_category(sentence: str, registry: tuple) -> str:
    """The recognizer's shape category for an unreadable statement, or
    ``no_recognizer_match`` when no ratified recognizer fires (a deeper
    reader gap than a missing injector)."""
    m = _recognizer_match(sentence, registry)
    if m is not None and getattr(m, "category", None) is not None:
        return f"inject:{m.category.value}"
    return "no_recognizer_match"


_DIGITS = re.compile(r"\d+")


def _statement_read_fully(sentence: str) -> bool:
    """True iff every numeric token in the statement is accounted for by some
    admissible candidate — directly (a candidate value/provenance token) OR as
    a factor of a product candidate (``5 bags of 50`` → 250 grounds both 5
    and 50).

    A statement that produces *a* candidate but drops numbers (0008's
    ``5 bags of 50 and 2 bags of 100`` → a single ``add`` using one number)
    is NOT read — counting it as readable is exactly the over-count that made
    the first version's ``flip_ready`` optimistic.
    """
    nums = [int(x) for x in _DIGITS.findall(sentence)]
    if not nums:
        return True
    cands = _filtered_statement_choices(sentence)
    if not cands:
        return False
    values: set[int] = set()
    tokens: set[int] = set()
    for c in cands:
        initial = getattr(c, "initial", None)
        if initial is not None:
            values.add(int(initial.quantity.value))
        op = getattr(c, "op", None)
        if op is not None and hasattr(op.operand, "value"):
            values.add(int(op.operand.value))
        tok = getattr(c, "matched_value_token", None)
        if tok is not None:
            try:
                tokens.add(int(tok))
            except ValueError:
                pass
    grounded = values | tokens

    def is_grounded(d: int) -> bool:
        if d in grounded:
            return True
        # factor of a product candidate (d × another source number == a value)
        return any(d2 and v == d * d2 for v in values for d2 in nums)

    return all(is_grounded(d) for d in nums)


def _analyze_case(question: str, registry: tuple) -> dict[str, Any]:
    sentences = [
        clause for s in _split_sentences(question) for clause in split_partition_clauses(s)
    ]
    statements = [s for s in sentences if not s.rstrip().endswith("?")]
    questions = [s for s in sentences if s.rstrip().endswith("?")]

    gaps: set[str] = set()
    for s in statements:
        # Serving only scores numeric_state statements; filler/non-numeric
        # are provably skippable, so they are not frontier gaps. A statement
        # is a gap when it is not READ — no candidate, OR a candidate that
        # drops numbers (mis-read), not merely "produces a candidate".
        if classify_sentence(s) != "numeric_state":
            continue
        if not _statement_read_fully(s):
            gaps.add(_gap_category(s, registry))

    question_parses = any(
        extract_question_candidates(qs, question) for qs in questions
    )
    answer = parse_and_solve(question).answer

    if answer is not None:
        blocked_on = "none"
    elif gaps and not question_parses:
        blocked_on = "both"
    elif gaps:
        blocked_on = "statement"
    elif not question_parses:
        blocked_on = "question"
    else:
        blocked_on = "composition"

    return {
        "statement_gaps": sorted(gaps),
        "question_parses": question_parses,
        "solved": answer is not None,
        "blocked_on": blocked_on,
    }


def build_report() -> dict[str, Any]:
    registry = _load_ratified_registry_or_empty()
    cases = [json.loads(line) for line in _CASES.read_text().splitlines() if line.strip()]

    per_case: list[dict[str, Any]] = []
    counts = Counter()
    # leverage tallies
    flip_ready: Counter = Counter()  # sole blocker (would-flip candidate)
    advances: Counter = Counter()  # one of several blockers

    for c in cases:
        a = _analyze_case(c["question"], registry)
        short = c["case_id"].split("-")[-1]
        per_case.append({"case_id": short, **a})
        counts[a["blocked_on"]] += 1

        gaps = a["statement_gaps"]
        if a["solved"]:
            continue
        # The "sole blocker" cases — the tightest next-flip signal.
        if a["blocked_on"] == "question":
            flip_ready["question_extractor"] += 1
        elif a["blocked_on"] == "statement" and len(gaps) == 1 and a["question_parses"]:
            flip_ready[gaps[0]] += 1
        # Advances: every blocker a still-refused case carries.
        for g in gaps:
            advances[g] += 1
        if not a["question_parses"]:
            advances["question_extractor"] += 1

    leverage = sorted(
        (
            {
                "capability": cap,
                "flip_ready": flip_ready.get(cap, 0),
                "advances": advances.get(cap, 0),
                "flip_ready_cases": sorted(
                    pc["case_id"]
                    for pc in per_case
                    if not pc["solved"]
                    and (
                        (cap == "question_extractor" and pc["blocked_on"] == "question")
                        or (
                            cap != "question_extractor"
                            and pc["blocked_on"] == "statement"
                            and pc["statement_gaps"] == [cap]
                            and pc["question_parses"]
                        )
                    )
                ),
            }
            for cap in sorted(set(flip_ready) | set(advances))
        ),
        key=lambda d: (-d["flip_ready"], -d["advances"], d["capability"]),
    )

    return {
        "instrument": "frontier_shift",
        "adr": "0190-follow-up",
        "note": "serving candidate-graph path; flip_ready = sole remaining FIRST gate",
        "caveat": (
            "flip_ready is an UPPER BOUND, not a flip guarantee. It marks the "
            "dominant first gate, but a real flip needs CORRECT reading at every "
            "layer (statement structure + question + composition), which this "
            "static tool cannot verify without solving. Known blind spots: "
            "word-number statements (classify_sentence skips some) and "
            "composition. The only reliable 'would this flip?' signal is to "
            "ATTEMPT the build and let the wrong=0 gold-tether score it. Use this "
            "to PRIORITIZE which layer is most common (question-parsing dominates), "
            "not to promise specific flips."
        ),
        "blocked_on_counts": dict(sorted(counts.items())),
        "leverage": leverage,
        "per_case": sorted(per_case, key=lambda d: d["case_id"]),
    }


def _to_markdown(report: dict[str, Any]) -> str:
    lines = ["# Frontier-shift report (serving path)", ""]
    lines.append(f"**blocked_on:** `{report['blocked_on_counts']}`")
    lines.append("")
    lines.append("## Leverage — next capability ranked by flip-readiness")
    lines.append("")
    lines.append("| capability | flip_ready | advances | flip-ready cases |")
    lines.append("|---|---|---|---|")
    for lv in report["leverage"]:
        cases = ", ".join(lv["flip_ready_cases"]) or "—"
        lines.append(
            f"| `{lv['capability']}` | {lv['flip_ready']} | {lv['advances']} | {cases} |"
        )
    lines.append("")
    lines.append("## Per case")
    lines.append("")
    lines.append("| case | blocked_on | statement_gaps | question_parses |")
    lines.append("|---|---|---|---|")
    for pc in report["per_case"]:
        gaps = ", ".join(g.replace("inject:", "") for g in pc["statement_gaps"]) or "—"
        lines.append(
            f"| {pc['case_id']} | {pc['blocked_on']} | {gaps} | {pc['question_parses']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    report = build_report()
    _REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    md = _to_markdown(report)
    _REPORT_MD.write_text(md)
    print(f"wrote {_REPORT_JSON.name} + {_REPORT_MD.name}")
    print(f"blocked_on: {report['blocked_on_counts']}")
    if "--print" in sys.argv:
        print()
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

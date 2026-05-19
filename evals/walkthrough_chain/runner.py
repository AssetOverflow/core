"""Walkthrough chain eval lane."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from chat.teaching_grounding import _all_chains_index


@dataclass
class LaneReport:
    metrics: dict[str, Any] = field(default_factory=dict)
    case_details: list[dict[str, Any]] = field(default_factory=list)


def _walk(subject: str, *, max_hops: int) -> tuple[str, ...]:
    corpus = _all_chains_index()
    path: list[str] = [subject.strip().lower()]
    seen = {path[0]}
    cursor = path[0]
    for _ in range(max(0, max_hops)):
        chain = corpus.get((cursor, "cause")) or corpus.get((cursor, "verification"))
        if chain is None:
            break
        nxt = chain.object.strip().lower()
        if not nxt or nxt in seen:
            break
        path.append(nxt)
        seen.add(nxt)
        cursor = nxt
    return tuple(path)


def run_lane(cases: list[dict[str, Any]], config: Any = None) -> LaneReport:  # noqa: ARG001
    details: list[dict[str, Any]] = []
    exact = 0
    anchored = 0
    min_hop = 0
    bounded = 0

    for case in cases:
        subject = str(case["subject"]).strip().lower()
        max_hops = int(case.get("max_hops", 2))
        expected = tuple(str(x).strip().lower() for x in case.get("expected_path", ()))
        actual = _walk(subject, max_hops=max_hops)
        exact_match = actual == expected
        anchor_match = bool(actual) and actual[0] == subject
        has_hop = len(actual) >= 2
        is_bounded = len(actual) <= max_hops + 1

        exact += int(exact_match)
        anchored += int(anchor_match)
        min_hop += int(has_hop)
        bounded += int(is_bounded)

        details.append({
            "case_id": case["id"],
            "prompt": case.get("prompt", ""),
            "subject": subject,
            "max_hops": max_hops,
            "expected_path": list(expected),
            "actual_path": list(actual),
            "path_exact": exact_match,
            "anchor_match": anchor_match,
            "min_hop": has_hop,
            "bounded": is_bounded,
        })

    total = len(cases)
    return LaneReport(
        metrics={
            "cases": total,
            "path_exact_rate": round(exact / total, 4) if total else 0.0,
            "anchor_rate": round(anchored / total, 4) if total else 0.0,
            "min_hop_rate": round(min_hop / total, 4) if total else 0.0,
            "bounded_rate": round(bounded / total, 4) if total else 0.0,
        },
        case_details=details,
    )


__all__ = ["run_lane", "LaneReport"]


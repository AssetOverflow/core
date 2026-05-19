"""Compound intent decomposition eval lane."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from generate.intent import classify_compound_intent


@dataclass
class LaneReport:
    metrics: dict[str, Any] = field(default_factory=dict)
    case_details: list[dict[str, Any]] = field(default_factory=list)


def _expected_atoms(case: dict[str, Any]) -> list[dict[str, str]]:
    atoms = case.get("expected_atoms")
    if not isinstance(atoms, list):
        return []
    out: list[dict[str, str]] = []
    for atom in atoms:
        if not isinstance(atom, dict):
            continue
        intent = str(atom.get("intent", "")).strip().lower()
        subject = str(atom.get("subject", "")).strip().lower()
        out.append({"intent": intent, "subject": subject})
    return out


def run_lane(cases: list[dict[str, Any]], config: Any = None) -> LaneReport:  # noqa: ARG001
    details: list[dict[str, Any]] = []
    exact = 0
    atom_positions = 0
    atom_correct = 0
    subject_positions = 0
    subject_correct = 0

    for case in cases:
        expected = _expected_atoms(case)
        actual = [
            {"intent": atom.tag.value, "subject": atom.subject.strip().lower()}
            for atom in classify_compound_intent(case["prompt"]).parts
        ]
        exact_match = actual == expected
        if exact_match:
            exact += 1

        for idx, exp in enumerate(expected):
            if idx >= len(actual):
                atom_positions += 1
                subject_positions += 1
                continue
            got = actual[idx]
            atom_positions += 1
            subject_positions += 1
            if got == exp:
                atom_correct += 1
            if got["subject"] == exp["subject"]:
                subject_correct += 1

        details.append({
            "case_id": case["id"],
            "prompt": case["prompt"],
            "expected_atoms": expected,
            "actual_atoms": actual,
            "exact_match": exact_match,
        })

    total = len(cases)
    return LaneReport(
        metrics={
            "cases": total,
            "decomposition_accuracy": round(exact / total, 4) if total else 0.0,
            "atom_precision": (
                round(atom_correct / atom_positions, 4) if atom_positions else 1.0
            ),
            "subject_accuracy": (
                round(subject_correct / subject_positions, 4)
                if subject_positions else 1.0
            ),
        },
        case_details=details,
    )


__all__ = ["run_lane", "LaneReport"]
